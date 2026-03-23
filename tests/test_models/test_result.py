from cicd_agent.models.result import ErrorType, PipelineResult, ToolResult


class TestToolResult:
    def test_success_case(self):
        result = ToolResult(
            success=True,
            tool_name="clone_repo",
            message="레포지토리 클론 완료",
            data={"clone_dir": "/tmp/build/my-app"},
        )
        assert result.success is True
        assert result.error_type is None
        assert result.data["clone_dir"] == "/tmp/build/my-app"

    def test_failure_case(self):
        result = ToolResult(
            success=False,
            tool_name="build_image",
            message="Dockerfile not found",
            error_type=ErrorType.BUILD_FAILED,
        )
        assert result.success is False
        assert result.error_type == ErrorType.BUILD_FAILED
        assert result.data == {}


class TestErrorType:
    def test_enum_values(self):
        assert ErrorType.AUTH_FAILED == "auth_failed"
        assert ErrorType.NETWORK_ERROR == "network_error"
        assert ErrorType.BUILD_FAILED == "build_failed"
        assert ErrorType.NOT_FOUND == "not_found"
        assert ErrorType.TIMEOUT == "timeout"
        assert ErrorType.UNKNOWN == "unknown"

    def test_enum_count(self):
        assert len(ErrorType) == 6


class TestPipelineResult:
    def test_success_case(self):
        completed = [
            ToolResult(success=True, tool_name="clone_repo", message="클론 완료", data={"clone_dir": "/tmp/repo"}),
            ToolResult(success=True, tool_name="build_image", message="빌드 완료", data={"image_id": "sha256:abc"}),
        ]
        pipeline = PipelineResult(success=True, steps_completed=completed)
        assert pipeline.success is True
        assert pipeline.failed_step is None
        assert len(pipeline.steps_completed) == 2

    def test_failure_case(self):
        completed = [
            ToolResult(success=True, tool_name="clone_repo", message="클론 완료"),
        ]
        failed = ToolResult(
            success=False,
            tool_name="build_image",
            message="Build failed",
            error_type=ErrorType.BUILD_FAILED,
        )
        pipeline = PipelineResult(success=False, steps_completed=completed, failed_step=failed)
        assert pipeline.success is False
        assert pipeline.failed_step is not None
        assert pipeline.failed_step.tool_name == "build_image"
