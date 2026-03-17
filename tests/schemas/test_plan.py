from app.schemas.plan import ExecutionPlan, PlanStep


class TestPlanStepDefaults:
    def test_max_attempts_default(self):
        step = PlanStep(
            name="clone_repository",
            tool="git_clone",
            parameters={"url": "https://github.com/org/repo"},
        )
        assert step.max_attempts == 3


class TestExecutionPlan:
    def test_multiple_steps(self):
        steps = [
            PlanStep(name="clone", tool="git_clone", parameters={"url": "https://github.com/org/repo"}),
            PlanStep(name="build", tool="docker_build", parameters={"tag": "my-app:latest"}),
            PlanStep(name="push", tool="docker_push", parameters={"registry": "https://registry.example.com"}),
        ]
        plan = ExecutionPlan(steps=steps)
        assert len(plan.steps) == 3
        assert plan.steps[0].name == "clone"
        assert plan.steps[2].tool == "docker_push"

    def test_empty_steps(self):
        plan = ExecutionPlan(steps=[])
        assert plan.steps == []
