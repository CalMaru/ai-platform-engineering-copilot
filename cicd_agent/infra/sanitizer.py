import re

from cicd_agent.infra.credentials import CredentialStore


class OutputSanitizer:
    """도구 출력에서 자격증명을 제거하는 2단계 세정기."""

    PATTERNS = [
        (r"AKIA[0-9A-Z]{16}", "***REDACTED***"),
        (r"(?i)(password[=:]\s*)\S+", r"\1***REDACTED***"),
        (r"(?i)(token[=:]\s*)\S{8,}", r"\1***REDACTED***"),
        (r"-----BEGIN .* KEY-----[\s\S]*?-----END .* KEY-----", "***REDACTED***"),
    ]

    def __init__(self, credentials: CredentialStore):
        self._secret_values = credentials.get_all_secret_values()

    def sanitize(self, text: str) -> str:
        # 1단계: 실제 비밀 값 정확 매칭
        for secret in self._secret_values:
            text = text.replace(secret, "***REDACTED***")
        # 2단계: 정규식 패턴 폴백
        for pattern, replacement in self.PATTERNS:
            text = re.sub(pattern, replacement, text)
        return text
