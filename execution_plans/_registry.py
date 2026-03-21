"""Plan registry — maps task_type strings to ExecutionPlan instances."""

PLANS: dict[str, "ExecutionPlan"] = {}


def register(plan_class):
    """Class decorator that registers an execution plan by its task_type."""
    instance = plan_class()
    PLANS[instance.task_type] = instance
    return plan_class
