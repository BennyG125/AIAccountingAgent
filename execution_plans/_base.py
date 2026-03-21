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
            RuntimeError: On unrecoverable API failure
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
            Raises RuntimeError if any account is not found.
        """
        numbers_str = ",".join(str(n) for n in account_numbers)
        result = client.get("/ledger/account", params={"number": numbers_str})
        if not result["success"]:
            raise RuntimeError(f"Failed to look up accounts {numbers_str}: {result}")

        accounts = {}
        for acc in result["body"].get("values", []):
            accounts[str(acc["number"])] = acc["id"]

        # Verify all requested accounts were found
        for num in account_numbers:
            if str(num) not in accounts:
                raise RuntimeError(f"Account {num} not found in this sandbox")

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
        retries with those fields removed from the body.
        Does NOT mutate the original body dict.
        """
        result = client.post(path, body=body)
        if (
            not result["success"]
            and retry_without
            and result.get("status_code") == 422
        ):
            cleaned = {k: v for k, v in body.items() if k not in retry_without}
            result = client.post(path, body=cleaned)
        return result

    def _find_or_create(
        self,
        client: TripletexClient,
        search_path: str,
        search_params: dict,
        create_path: str,
        create_body: dict,
    ) -> int:
        """Search for an entity; create if not found. Returns entity ID.

        Raises RuntimeError if both search and create fail.
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

        raise RuntimeError(
            f"Failed to find or create at {create_path}: "
            f"status={result.get('status_code')}, error={result.get('error')}"
        )

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
