import pytest
from pydantic import ValidationError

from cicd_agent.models.recovery import RecoveryAdvice


class TestRecoveryAdvice:
    def test_retry_action(self):
        advice = RecoveryAdvice(
            action="retry",
            reason="네트워크 타임아웃, 재시도 가능",
            modified_params={"timeout": 60},
        )
        assert advice.action == "retry"
        assert advice.modified_params == {"timeout": 60}

    def test_skip_action(self):
        advice = RecoveryAdvice(
            action="skip",
            reason="선택적 단계, 건너뛰기 가능",
        )
        assert advice.action == "skip"
        assert advice.modified_params is None

    def test_abort_action(self):
        advice = RecoveryAdvice(
            action="abort",
            reason="인증 자격증명이 유효하지 않음",
        )
        assert advice.action == "abort"

    def test_invalid_action_raises(self):
        with pytest.raises(ValidationError):
            RecoveryAdvice(
                action="restart",
                reason="invalid action",
            )
