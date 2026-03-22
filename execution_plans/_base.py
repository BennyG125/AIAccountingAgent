"""Base class for deterministic execution plans."""
import logging
import time

from tripletex_api import TripletexClient

logger = logging.getLogger(__name__)

EXECUTOR_TIMEOUT = 120  # seconds — leaves ~150s for Claude fallback


class ExecutionPlan:
    """Base class for all execution plans.

    Subclasses must set task_type and implement execute().
    """

    task_type: str = ""
    description: str = ""

    def execute(self, client: TripletexClient, params: dict, start_time: float) -> dict:
        """Execute the plan against the Tripletex API.

        Args:
            client: Authenticated TripletexClient
            params: Extracted parameters from the prompt
            start_time: time.time() when execution started

        Returns:
            Result dict with status, api_calls, api_errors, etc.

        Raises:
            TimeoutError: If execution exceeds EXECUTOR_TIMEOUT
        """
        raise NotImplementedError

    def _check_timeout(self, start_time: float) -> None:
        """Raise TimeoutError if we've exceeded EXECUTOR_TIMEOUT."""
        elapsed = time.time() - start_time
        if elapsed > EXECUTOR_TIMEOUT:
            raise TimeoutError(
                f"Execution plan '{self.task_type}' timed out after {elapsed:.0f}s "
                f"(limit: {EXECUTOR_TIMEOUT}s)"
            )

    def _get_accounts(self, client, *account_numbers: str) -> dict[str, int]:
        """Look up multiple ledger accounts in a single API call.

        Args:
            client: TripletexClient
            *account_numbers: Account numbers as strings (e.g., "1920", "2400", "7770")

        Returns:
            Dict mapping account number string to account ID.
            Logs warnings for missing accounts instead of raising.
        """
        numbers_str = ",".join(str(n) for n in account_numbers)
        result = client.get("/ledger/account", params={"number": numbers_str})
        if not result["success"] and result.get("status_code") in (502, 503, 504):
            time.sleep(1)
            result = client.get("/ledger/account", params={"number": numbers_str})
        if not result["success"]:
            logger.warning("Failed to look up accounts %s: %s", numbers_str, result)
            return {}

        accounts = {}
        for acc in result["body"].get("values", []):
            accounts[str(acc["number"])] = acc["id"]

        # Log warnings for missing accounts (but don't raise)
        for num in account_numbers:
            if str(num) not in accounts:
                logger.warning("Account %s not found in this sandbox", num)

        return accounts

    def _safe_post(
        self,
        client: TripletexClient,
        path: str,
        body: dict,
        retry_without: list[str] | None = None,
    ) -> dict:
        """POST with optional field removal on 422 failure.

        If the first POST returns 422 and retry_without is specified,
        retries with those fields recursively removed from the body
        (including nested dicts and lists like postings[]).
        When stripping 'vatType' from a posting dict, also adjusts
        amountGross = amount and amountGrossCurrency = amountCurrency
        so gross equals net (no auto-VAT calculation without vatType).
        Does NOT mutate the original body dict.
        """
        result = client.post(path, body=body)
        if (
            not result["success"]
            and retry_without
            and result.get("status_code") == 422
        ):
            cleaned = self._strip_fields_recursive(body, retry_without)
            result = client.post(path, body=cleaned)
        return result

    @staticmethod
    def _strip_fields_recursive(obj, fields: list[str]):
        """Recursively strip specified fields from dicts, traversing lists.

        When stripping 'vatType' from a dict that also has 'amount',
        sets amountGross = amount and amountGrossCurrency = amountCurrency
        so the posting remains valid without VAT auto-calculation.

        Returns a new object (never mutates the original).
        """
        if isinstance(obj, dict):
            cleaned = {}
            stripped_vat = False
            for k, v in obj.items():
                if k in fields:
                    if k == "vatType":
                        stripped_vat = True
                    continue
                cleaned[k] = ExecutionPlan._strip_fields_recursive(v, fields)
            # When vatType was stripped, gross must equal net
            if stripped_vat:
                if "amount" in cleaned:
                    cleaned["amountGross"] = cleaned["amount"]
                if "amountCurrency" in cleaned:
                    cleaned["amountGrossCurrency"] = cleaned["amountCurrency"]
            return cleaned
        elif isinstance(obj, list):
            return [ExecutionPlan._strip_fields_recursive(item, fields) for item in obj]
        else:
            return obj

    def _find_or_create(
        self,
        client: TripletexClient,
        search_path: str,
        search_params: dict,
        create_path: str,
        create_body: dict,
    ) -> int | None:
        """Search for an entity; create if not found. Returns entity ID or None.

        Returns None and logs a warning if both search and create fail.
        """
        result = client.get(search_path, params=search_params)
        if result["success"]:
            values = result["body"].get("values", [])
            if values:
                return values[0]["id"]

        # Not found — create
        result = client.post(create_path, body=create_body)
        if result["success"]:
            return result["body"]["value"]["id"]

        logger.warning(
            "Failed to find or create at %s: status=%s, error=%s",
            create_path, result.get('status_code'), result.get('error'),
        )
        return None

    def _create_or_find(
        self,
        client: TripletexClient,
        create_path: str,
        create_body: dict,
        search_path: str,
        search_params: dict,
        api_calls: list,
        api_errors: list,
        id_field: str = "id",
    ) -> dict | None:
        """POST-first creation: create entity, fall back to GET search on conflict.

        Optimized for fresh sandboxes where entities rarely pre-exist.
        Saves 1 API call on the happy path vs _find_or_create.

        Args:
            client: Authenticated TripletexClient
            create_path: API path for POST creation
            create_body: Body dict for the POST request
            search_path: API path for GET search (fallback)
            search_params: Query params for the GET search
            api_calls: Mutable list [count] — incremented for each call
            api_errors: Mutable list [count] — incremented for unexpected failures
            id_field: Field name to extract the entity ID from (default "id")

        Returns:
            Dict with at least {"id": <entity_id>} on success, or None on failure.
        """
        # --- Step 1: Try POST (create) first ---
        api_calls[0] += 1
        result = client.post(create_path, body=create_body)

        if result["success"]:
            entity = result["body"].get("value", {})
            entity_id = entity.get(id_field)
            logger.info(
                "_create_or_find: created %s → %s=%s",
                create_path, id_field, entity_id,
            )
            return entity

        # --- Step 2: If conflict (already exists), fall back to GET ---
        status_code = result.get("status_code", 0)
        if status_code in (409, 422):
            logger.info(
                "_create_or_find: POST %s returned %s (already exists), "
                "falling back to GET %s",
                create_path, status_code, search_path,
            )
            api_calls[0] += 1
            search_result = client.get(search_path, params=search_params)

            if search_result["success"]:
                values = search_result["body"].get("values", [])
                if values:
                    entity = values[0]
                    logger.info(
                        "_create_or_find: found existing %s=%s via GET %s",
                        id_field, entity.get(id_field), search_path,
                    )
                    return entity

            # GET also failed or returned empty — count as error
            api_errors[0] += 1
            logger.warning(
                "_create_or_find: GET fallback %s failed or returned empty: %s",
                search_path, search_result.get("error"),
            )
            return None

        # --- Step 3: Unexpected POST failure (not 409/422) ---
        api_errors[0] += 1
        logger.warning(
            "_create_or_find: POST %s failed unexpectedly: status=%s, error=%s",
            create_path, status_code, result.get("error"),
        )
        return None

    def _make_result(
        self,
        api_calls: int,
        api_errors: int,
        time_ms: int = 0,
        error_details: list | None = None,
    ) -> dict:
        """Build a result dict matching run_agent() output shape."""
        return {
            "status": "completed",
            "iterations": 1,
            "time_ms": time_ms,
            "api_calls": api_calls,
            "api_errors": api_errors,
            "error_details": error_details,
            "executor": "deterministic",
        }
