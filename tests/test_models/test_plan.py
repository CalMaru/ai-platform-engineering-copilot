import pytest
from pydantic import ValidationError

from cicd_agent.models.plan import ExecutionPlan, PlanStep


class TestPlanStep:
    def test_confirm_required_default(self):
        step = PlanStep(
            tool_name="clone_repo",
            params={"repo_url": "https://github.com/org/repo"},
            description="레포지토리 클론",
        )
        assert step.confirm_required is False

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            PlanStep(tool_name="clone_repo")


class TestExecutionPlan:
    def test_multiple_steps(self):
        steps = [
            PlanStep(
                tool_name="clone_repo",
                params={"repo_url": "https://github.com/org/repo"},
                description="레포지토리 클론",
            ),
            PlanStep(
                tool_name="build_image",
                params={"image_name": "my-app", "image_tag": "v1.0"},
                description="Docker 이미지 빌드",
            ),
            PlanStep(
                tool_name="push_image",
                params={"registry": "ecr"},
                description="이미지 push",
                confirm_required=True,
            ),
        ]
        plan = ExecutionPlan(steps=steps)
        assert len(plan.steps) == 3
        assert plan.steps[0].tool_name == "clone_repo"
        assert plan.steps[2].confirm_required is True

    def test_empty_steps(self):
        plan = ExecutionPlan(steps=[])
        assert plan.steps == []
