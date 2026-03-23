from enum import Enum
from typing import Any

from pydantic import BaseModel


class ErrorType(str, Enum):
    AUTH_FAILED = "auth_failed"
    NETWORK_ERROR = "network_error"
    BUILD_FAILED = "build_failed"
    NOT_FOUND = "not_found"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class ToolResult(BaseModel):
    success: bool
    tool_name: str
    message: str
    data: dict[str, Any] = {}
    error_type: ErrorType | None = None


class PipelineResult(BaseModel):
    success: bool
    steps_completed: list[ToolResult]
    failed_step: ToolResult | None = None
