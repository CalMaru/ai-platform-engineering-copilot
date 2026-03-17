from pydantic import BaseModel


class PlanStep(BaseModel):
    name: str
    tool: str
    parameters: dict
    max_attempts: int = 3


class ExecutionPlan(BaseModel):
    steps: list[PlanStep]
