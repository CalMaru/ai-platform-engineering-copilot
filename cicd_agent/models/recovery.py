from typing import Any, Literal

from pydantic import BaseModel


class RecoveryAdvice(BaseModel):
    action: Literal["retry", "skip", "abort"]
    reason: str
    modified_params: dict[str, Any] | None = None
