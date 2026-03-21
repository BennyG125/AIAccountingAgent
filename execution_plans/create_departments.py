"""Execution plan: Create Departments."""
from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

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

        for i, name in enumerate(department_names):
            self._check_timeout(start_time)
            department_number = str(max_num + (i + 1) * 100)
            body = {
                "name": name,
                "departmentNumber": department_number,
            }
            result = client.post("/department", body=body)
            api_calls += 1
            if not result["success"]:
                api_errors += 1
                raise RuntimeError(
                    f"Failed to create department '{name}': "
                    f"status={result.get('status_code')}, error={result.get('error')}"
                )

        return self._make_result(api_calls=api_calls, api_errors=api_errors)
