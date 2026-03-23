from typing import Any

from pydantic import BaseModel


class PlanStep(BaseModel):
    tool_name: str
    params: dict[str, Any]
    description: str
    confirm_required: bool = False


class ExecutionPlan(BaseModel):
    steps: list[PlanStep]
