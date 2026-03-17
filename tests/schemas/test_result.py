from app.schemas.plan import ExecutionPlan, PlanStep
from app.schemas.result import PipelineResult, RecoveryAdvice, StepResult


class TestStepResult:
    def test_success_case(self):
        result = StepResult(
            step_name="clone_repository",
            success=True,
            attempt_number=1,
            output={"path": "/tmp/repo"},
        )
        assert result.success is True
        assert result.error is None

    def test_failure_case(self):
        result = StepResult(
            step_name="docker_build",
            success=False,
            attempt_number=2,
            output={},
            error="Dockerfile not found",
        )
        assert result.success is False
        assert result.error == "Dockerfile not found"


class TestRecoveryAdvice:
    def test_recoverable(self):
        advice = RecoveryAdvice(
            recoverable=True,
            modified_parameters={"timeout": 60},
            explanation="Increased timeout for slow network",
        )
        assert advice.recoverable is True
        assert advice.modified_parameters == {"timeout": 60}

    def test_not_recoverable(self):
        advice = RecoveryAdvice(
            recoverable=False,
            explanation="Authentication credentials are invalid",
        )
        assert advice.recoverable is False
        assert advice.modified_parameters is None


class TestPipelineResult:
    def _make_plan(self) -> ExecutionPlan:
        return ExecutionPlan(
            steps=[
                PlanStep(name="clone", tool="git_clone", parameters={"url": "https://github.com/org/repo"}),
                PlanStep(name="build", tool="docker_build", parameters={"tag": "app:latest"}),
            ]
        )

    def test_success_case(self):
        plan = self._make_plan()
        results = [
            StepResult(step_name="clone", success=True, attempt_number=1, output={"path": "/tmp/repo"}),
            StepResult(step_name="build", success=True, attempt_number=1, output={"image_id": "sha256:abc"}),
        ]
        pipeline = PipelineResult(plan=plan, results=results, success=True)
        assert pipeline.success is True
        assert pipeline.error is None
        assert len(pipeline.results) == 2

    def test_failure_case(self):
        plan = self._make_plan()
        results = [
            StepResult(step_name="clone", success=True, attempt_number=1, output={"path": "/tmp/repo"}),
            StepResult(step_name="build", success=False, attempt_number=3, output={}, error="Build failed"),
        ]
        pipeline = PipelineResult(
            plan=plan,
            results=results,
            success=False,
            error="Pipeline failed at step: build",
        )
        assert pipeline.success is False
        assert pipeline.error == "Pipeline failed at step: build"

    def test_contains_plan_and_results(self):
        plan = self._make_plan()
        results = [
            StepResult(step_name="clone", success=True, attempt_number=1, output={}),
        ]
        pipeline = PipelineResult(plan=plan, results=results, success=True)
        assert isinstance(pipeline.plan, ExecutionPlan)
        assert len(pipeline.plan.steps) == 2
        assert isinstance(pipeline.results[0], StepResult)
