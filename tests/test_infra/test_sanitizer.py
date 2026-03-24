from cicd_agent.config import Settings
from cicd_agent.infra.credentials import CredentialStore
from cicd_agent.infra.sanitizer import OutputSanitizer


def _make_sanitizer(**kwargs) -> OutputSanitizer:
    settings = Settings(_env_file=None, **kwargs)
    store = CredentialStore(settings)
    return OutputSanitizer(store)


class TestExactMatch:
    def test_redacts_aws_access_key(self):
        sanitizer = _make_sanitizer(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )
        text = "Key is AKIAIOSFODNN7EXAMPLE"
        assert "AKIAIOSFODNN7EXAMPLE" not in sanitizer.sanitize(text)
        assert "***REDACTED***" in sanitizer.sanitize(text)

    def test_redacts_secret_key(self):
        sanitizer = _make_sanitizer(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )
        text = "Secret: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert "wJalrXUtnFEMI" not in sanitizer.sanitize(text)

    def test_redacts_llm_api_key(self):
        sanitizer = _make_sanitizer(anthropic_api_key="sk-ant-api03-longenoughkey")
        text = "Using key sk-ant-api03-longenoughkey"
        assert "sk-ant-api03-longenoughkey" not in sanitizer.sanitize(text)

    def test_no_redaction_for_clean_text(self):
        sanitizer = _make_sanitizer()
        text = "Clone completed successfully"
        assert sanitizer.sanitize(text) == "Clone completed successfully"


class TestRegexPatterns:
    def test_akia_pattern(self):
        sanitizer = _make_sanitizer()
        text = "Found key AKIAIOSFODNN7EXAMPL3"
        result = sanitizer.sanitize(text)
        assert "AKIAIOSFODNN7EXAMPL3" not in result

    def test_password_label_preserved(self):
        sanitizer = _make_sanitizer()
        text = "password=mysecretpassword123"
        result = sanitizer.sanitize(text)
        assert "password=" in result
        assert "mysecretpassword123" not in result

    def test_token_label_preserved_long(self):
        sanitizer = _make_sanitizer()
        text = "token=abcdefghijklmnop"
        result = sanitizer.sanitize(text)
        assert "token=" in result
        assert "abcdefghijklmnop" not in result

    def test_token_short_not_redacted(self):
        sanitizer = _make_sanitizer()
        text = "token=short"
        result = sanitizer.sanitize(text)
        assert result == "token=short"

    def test_pem_key(self):
        sanitizer = _make_sanitizer()
        text = "-----BEGIN RSA KEY-----\nMIIBogIB...\n-----END RSA KEY-----"
        result = sanitizer.sanitize(text)
        assert "MIIBogIB" not in result
        assert "***REDACTED***" in result


class TestSanitizationOrder:
    def test_exact_match_catches_non_regex_secrets(self):
        """정규식 패턴에 매칭되지 않는 비밀 값도 1단계 정확 매칭으로 마스킹됨"""
        sanitizer = _make_sanitizer(anthropic_api_key="my-custom-secret-value-here")
        text = "API key: my-custom-secret-value-here"
        result = sanitizer.sanitize(text)
        assert "my-custom-secret-value-here" not in result
