"""Post-execution verification — mirrors competition scoring."""

import logging
from tripletex_api import TripletexClient

logger = logging.getLogger(__name__)


class VerificationSuite:
    def __init__(self, client: TripletexClient):
        self.client = client

    def verify(self, entity_type: str, search_params: dict, expected_fields: dict) -> dict:
        """Search for entity and verify fields match expected values."""
        searcher = getattr(self, f"_search_{entity_type}", None)
        if not searcher:
            return {"verified": False, "error": f"Unknown entity type: {entity_type}"}

        entities = searcher(search_params)
        if not entities:
            return {
                "verified": False,
                "error": f"No {entity_type} found matching {search_params}",
                "field_results": {},
            }

        entity = entities[0]
        field_results = {}
        for field, expected in expected_fields.items():
            actual = self._get_nested(entity, field)
            field_results[field] = {
                "expected": expected,
                "actual": actual,
                "match": self._values_match(actual, expected),
            }

        all_match = all(r["match"] for r in field_results.values())
        return {
            "verified": all_match,
            "entity_id": entity.get("id"),
            "field_results": field_results,
            "actual_entity": entity,
        }

    def _values_match(self, actual, expected) -> bool:
        """Flexible matching — handles case, type coercion, contains."""
        if actual is None and expected is None:
            return True
        if actual is None or expected is None:
            return False
        # String comparison: case-insensitive contains
        if isinstance(expected, str) and isinstance(actual, str):
            return expected.lower() in actual.lower()
        # Numeric: approximate
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            return abs(actual - expected) < 0.01
        return actual == expected

    def _get_nested(self, entity: dict, field: str):
        """Get nested field like 'department.name'."""
        parts = field.split(".")
        val = entity
        for p in parts:
            if isinstance(val, dict):
                val = val.get(p)
            else:
                return None
        return val

    def _search_department(self, params: dict) -> list:
        result = self.client.get("/department", params={**params, "fields": "*"})
        return result["body"].get("values", []) if result["success"] else []

    def _search_employee(self, params: dict) -> list:
        result = self.client.get("/employee", params={**params, "fields": "*"})
        return result["body"].get("values", []) if result["success"] else []

    def _search_customer(self, params: dict) -> list:
        result = self.client.get("/customer", params={**params, "fields": "*"})
        return result["body"].get("values", []) if result["success"] else []

    def _search_product(self, params: dict) -> list:
        result = self.client.get("/product", params={**params, "fields": "*"})
        return result["body"].get("values", []) if result["success"] else []

    def _search_invoice(self, params: dict) -> list:
        # Filter out None values before sending to API
        clean_params = {k: v for k, v in params.items() if v is not None}
        result = self.client.get("/invoice", params={**clean_params, "fields": "*"})
        return result["body"].get("values", []) if result["success"] else []

    def _search_travel_expense(self, params: dict) -> list:
        result = self.client.get("/travelExpense", params={**params, "fields": "*"})
        return result["body"].get("values", []) if result["success"] else []

    def _search_project(self, params: dict) -> list:
        result = self.client.get("/project", params={**params, "fields": "*"})
        return result["body"].get("values", []) if result["success"] else []
