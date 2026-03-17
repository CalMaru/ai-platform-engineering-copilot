from pydantic import BaseModel

from app.schemas.plan import ExecutionPlan


class StepResult(BaseModel):
    step_name: str
    success: bool
    attempt_number: int
    output: dict
    error: str | None = None


class RecoveryAdvice(BaseModel):
    recoverable: bool
    modified_parameters: dict | None = None
    explanation: str


class PipelineResult(BaseModel):
    plan: ExecutionPlan
    results: list[StepResult]
    success: bool
    error: str | None = None
