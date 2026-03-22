"""Execution plan: Create Departments."""
import logging

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

logger = logging.getLogger(__name__)

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "department_names": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of department names to create",
        }
    },
    "required": ["department_names"],
}


@register
class CreateDepartmentsPlan(ExecutionPlan):
    task_type = "create_departments"
    description = "Create one or more departments"

    def execute(self, client, params, start_time):
        self._check_timeout(start_time)

        department_names = params.get("department_names", [])
        api_calls = 0
        api_errors = 0

        # Query existing departments to find the next available number
        existing = client.get("/department", params={"count": 1000})
        api_calls += 1
        max_num = 0
        if existing["success"]:
            for dept in existing["body"].get("values", []):
                num_str = dept.get("departmentNumber", "")
                if num_str and num_str.isdigit():
                    max_num = max(max_num, int(num_str))

        # Bulk create all departments in 1 call via POST /department/list
        departments = [
            {
                "name": name,
                "departmentNumber": str(max_num + (i + 1) * 100),
            }
            for i, name in enumerate(department_names)
        ]
        result = client.post("/department/list", body=departments)
        api_calls += 1
        if not result["success"]:
            api_errors += 1
            # Fallback: try individual creates
            for dept in departments:
                self._check_timeout(start_time)
                ind_result = client.post("/department", body=dept)
                api_calls += 1
                if not ind_result["success"]:
                    api_errors += 1
                    logger.warning(
                        "Failed to create department '%s': status=%s, error=%s",
                        dept['name'], ind_result.get('status_code'), ind_result.get('error'),
                    )

        return self._make_result(api_calls=api_calls, api_errors=api_errors)
