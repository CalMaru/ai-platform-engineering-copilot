# Day 3: Settings + CredentialStore + OutputSanitizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** pydantic-settings 기반 앱 설정 관리와 자격증명 격리(CredentialStore + OutputSanitizer)를 구현한다.

**Architecture:** Settings(config.py)가 `.env`에서 전체 설정을 로드하고, CredentialStore(infra/)가 Settings를 래핑하여 자격증명만 노출한다. OutputSanitizer가 CredentialStore의 비밀 값으로 출력을 세정한다. GCR(기본)/ECR 멀티 레지스트리 지원.

**Tech Stack:** pydantic-settings, Pydantic v2 (SecretStr), pytest

**Spec:** `docs/superpowers/specs/2026-03-23-day3-settings-credentials-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `cicd_agent/config.py` | Create | Settings (BaseSettings), get_settings() |
| `cicd_agent/infra/models.py` | Create | GCRCredentials, AWSCredentials, SSHConfig, DockerConfig |
| `cicd_agent/infra/credentials.py` | Rewrite (empty) | CredentialStore, CredentialMissingError |
| `cicd_agent/infra/sanitizer.py` | Rewrite (empty) | OutputSanitizer |
| `tests/test_config.py` | Create | Settings 테스트 |
| `tests/test_infra/test_credentials.py` | Create | CredentialStore 테스트 |
| `tests/test_infra/test_models.py` | Create | 인프라 데이터 모델 테스트 |
| `tests/test_infra/test_sanitizer.py` | Create | OutputSanitizer 테스트 |
| `tests/conftest.py` | Create | @lru_cache 격리 + 환경변수 격리 fixture |
| `pyproject.toml` | Modify | pydantic-settings 추가, python-dotenv 제거 |
| `.env.example` | Rewrite | GCR/ECR 멀티 레지스트리 반영 |
| `CLAUDE.md` | Modify | Day 3 완료 상태 반영 |

---

### Task 1: 의존성 업데이트

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: pyproject.toml 수정**

`pydantic-settings` 추가, `python-dotenv` 제거:

```toml
dependencies = [
    "boto3>=1.35.0",
    "docker>=7.1.0",
    "gitpython>=3.1.0",
    "litellm>=1.30.0",
    "paramiko>=3.5.0",
    "pydantic>=2.12.5",
    "pydantic-settings>=2.0.0",
    "typer>=0.15.0",
]
```

- [ ] **Step 2: uv sync**

Run: `uv sync`
Expected: pydantic-settings 설치, python-dotenv 제거

- [ ] **Step 3: 커밋**

```bash
git add pyproject.toml uv.lock
git commit -m ":wrench: chore: add pydantic-settings, remove python-dotenv"
```

---

### Task 2: 인프라 데이터 모델

**Files:**
- Create: `cicd_agent/infra/models.py`
- Test: `tests/test_infra/test_models.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_infra/test_models.py
from cicd_agent.infra.models import AWSCredentials, DockerConfig, GCRCredentials, SSHConfig


class TestGCRCredentials:
    def test_create(self):
        creds = GCRCredentials(
            credentials_path="/path/to/key.json",
            project_id="my-project",
        )
        assert creds.credentials_path == "/path/to/key.json"
        assert creds.project_id == "my-project"


class TestAWSCredentials:
    def test_create(self):
        creds = AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="ap-northeast-2",
        )
        assert creds.region == "ap-northeast-2"


class TestSSHConfig:
    def test_create(self):
        config = SSHConfig(key_path="/home/user/.ssh/id_rsa")
        assert config.key_path == "/home/user/.ssh/id_rsa"


class TestDockerConfig:
    def test_create(self):
        config = DockerConfig(host="unix:///var/run/docker.sock")
        assert config.host == "unix:///var/run/docker.sock"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `uv run pytest tests/test_infra/test_models.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: 구현**

```python
# cicd_agent/infra/models.py
from pydantic import BaseModel


class GCRCredentials(BaseModel):
    credentials_path: str
    project_id: str


class AWSCredentials(BaseModel):
    access_key_id: str
    secret_access_key: str
    region: str


class SSHConfig(BaseModel):
    key_path: str


class DockerConfig(BaseModel):
    host: str
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest tests/test_infra/test_models.py -v`
Expected: 4 passed

- [ ] **Step 5: 커밋**

```bash
git add cicd_agent/infra/models.py tests/test_infra/test_models.py
git commit -m ":sparkles: feat: add infra data models (GCRCredentials, AWSCredentials, SSHConfig, DockerConfig)"
```

---

### Task 3: Settings

**Files:**
- Create: `cicd_agent/config.py`
- Create: `tests/conftest.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: 테스트 작성**

> **주의**: `Settings`는 `BaseSettings`이므로 실제 환경변수와 `.env` 파일을 자동으로 읽는다. 테스트에서는 `_env_file=None`으로 `.env` 로딩을 차단하고, conftest에서 Settings 관련 환경변수를 격리한다.

```python
# tests/test_config.py
import pytest
from pydantic import SecretStr, ValidationError

from cicd_agent.config import Settings


def _make_settings(**kwargs) -> Settings:
    """테스트용 Settings 생성. .env 파일을 읽지 않음."""
    return Settings(_env_file=None, **kwargs)


class TestSettingsDefaults:
    def test_defaults_with_no_credentials(self, clean_env):
        settings = _make_settings()
        assert settings.registry_type == "gcr"
        assert settings.aws_default_region == "ap-northeast-2"
        assert settings.llm_model == "anthropic/claude-sonnet-4-20250514"
        assert settings.max_retries_per_step == 2
        assert settings.max_total_retries == 3
        assert settings.google_application_credentials is None
        assert settings.aws_access_key_id is None
        assert settings.deploy_ssh_key_path is None

    def test_docker_host_default_unix(self, clean_env):
        settings = _make_settings()
        assert "unix://" in settings.docker_host or "npipe://" in settings.docker_host


class TestSettingsRegistryType:
    def test_gcr(self):
        settings = _make_settings(registry_type="gcr")
        assert settings.registry_type == "gcr"

    def test_ecr(self):
        settings = _make_settings(registry_type="ecr")
        assert settings.registry_type == "ecr"

    def test_invalid_registry_type(self):
        with pytest.raises(ValidationError):
            _make_settings(registry_type="dockerhub")


class TestSettingsFrozen:
    def test_cannot_modify(self):
        settings = _make_settings()
        with pytest.raises(ValidationError):
            settings.registry_type = "ecr"


class TestSettingsSecretStr:
    def test_secret_not_exposed_in_str(self):
        settings = _make_settings(aws_secret_access_key="my-secret-key-12345")
        assert "my-secret-key-12345" not in str(settings.aws_secret_access_key)

    def test_secret_accessible_via_get_secret_value(self):
        settings = _make_settings(aws_secret_access_key="my-secret-key-12345")
        assert isinstance(settings.aws_secret_access_key, SecretStr)
        assert settings.aws_secret_access_key.get_secret_value() == "my-secret-key-12345"

    def test_llm_api_key_secret(self):
        settings = _make_settings(anthropic_api_key="sk-ant-12345678")
        assert "sk-ant-12345678" not in str(settings.anthropic_api_key)
        assert settings.anthropic_api_key.get_secret_value() == "sk-ant-12345678"
```

- [ ] **Step 2: conftest.py 작성 (lru_cache + 환경변수 격리)**

```python
# tests/conftest.py
import os

import pytest

from cicd_agent.config import get_settings

# Settings가 읽을 수 있는 환경변수 목록
_SETTINGS_ENV_VARS = [
    "REGISTRY_TYPE",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GCR_PROJECT_ID",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_DEFAULT_REGION",
    "DOCKER_HOST",
    "DEPLOY_SSH_KEY_PATH",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "LLM_MODEL",
    "MAX_RETRIES_PER_STEP",
    "MAX_TOTAL_RETRIES",
]


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def clean_env(monkeypatch):
    """Settings 관련 환경변수를 모두 제거하여 기본값 테스트를 격리"""
    for var in _SETTINGS_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 4: 구현**

```python
# cicd_agent/config.py
import sys
from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", frozen=True)

    # --- Registry ---
    registry_type: Literal["gcr", "ecr"] = "gcr"

    # --- GCR ---
    google_application_credentials: str | None = None
    gcr_project_id: str | None = None

    # --- AWS/ECR ---
    aws_access_key_id: str | None = None
    aws_secret_access_key: SecretStr | None = None
    aws_default_region: str = "ap-northeast-2"

    # --- Docker ---
    docker_host: str = (
        "npipe:////./pipe/docker_engine"
        if sys.platform == "win32"
        else "unix:///var/run/docker.sock"
    )

    # --- SSH (선택) ---
    deploy_ssh_key_path: str | None = None

    # --- LLM ---
    anthropic_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    llm_model: str = "anthropic/claude-sonnet-4-20250514"

    # --- Execution ---
    max_retries_per_step: int = 2
    max_total_retries: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `uv run pytest tests/test_config.py -v`
Expected: 8 passed

- [ ] **Step 6: 커밋**

```bash
git add cicd_agent/config.py tests/conftest.py tests/test_config.py
git commit -m ":sparkles: feat: add Settings with pydantic-settings (GCR/ECR, SecretStr, frozen)"
```

---

### Task 4: CredentialStore

**Files:**
- Rewrite: `cicd_agent/infra/credentials.py`
- Test: `tests/test_infra/test_credentials.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_infra/test_credentials.py
import pytest

from cicd_agent.config import Settings
from cicd_agent.infra.credentials import CredentialMissingError, CredentialStore
from cicd_agent.infra.models import AWSCredentials, GCRCredentials


def _make_settings(**kwargs) -> Settings:
    return Settings(_env_file=None, **kwargs)


class TestCredentialStoreGCR:
    def test_get_gcr_credentials(self):
        settings = _make_settings(
            google_application_credentials="/path/to/key.json",
            gcr_project_id="my-project",
        )
        store = CredentialStore(settings)
        creds = store.get_gcr_credentials()
        assert isinstance(creds, GCRCredentials)
        assert creds.credentials_path == "/path/to/key.json"
        assert creds.project_id == "my-project"

    def test_gcr_missing_credentials_path(self):
        settings = _make_settings(gcr_project_id="my-project")
        store = CredentialStore(settings)
        with pytest.raises(CredentialMissingError, match="GOOGLE_APPLICATION_CREDENTIALS"):
            store.get_gcr_credentials()

    def test_gcr_missing_project_id(self):
        settings = _make_settings(google_application_credentials="/path/to/key.json")
        store = CredentialStore(settings)
        with pytest.raises(CredentialMissingError, match="GCR_PROJECT_ID"):
            store.get_gcr_credentials()


class TestCredentialStoreECR:
    def test_get_aws_credentials(self):
        settings = _make_settings(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )
        store = CredentialStore(settings)
        creds = store.get_aws_credentials()
        assert isinstance(creds, AWSCredentials)
        assert creds.access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert creds.secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert creds.region == "ap-northeast-2"

    def test_ecr_missing_access_key(self):
        settings = _make_settings(aws_secret_access_key="secret")
        store = CredentialStore(settings)
        with pytest.raises(CredentialMissingError, match="AWS_ACCESS_KEY_ID"):
            store.get_aws_credentials()

    def test_ecr_missing_secret_key(self):
        settings = _make_settings(aws_access_key_id="AKIAIOSFODNN7EXAMPLE")
        store = CredentialStore(settings)
        with pytest.raises(CredentialMissingError, match="AWS_SECRET_ACCESS_KEY"):
            store.get_aws_credentials()


class TestCredentialStoreRegistryDispatch:
    def test_get_registry_credentials_gcr(self):
        settings = _make_settings(
            registry_type="gcr",
            google_application_credentials="/path/to/key.json",
            gcr_project_id="my-project",
        )
        store = CredentialStore(settings)
        creds = store.get_registry_credentials()
        assert isinstance(creds, GCRCredentials)

    def test_get_registry_credentials_ecr(self):
        settings = _make_settings(
            registry_type="ecr",
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )
        store = CredentialStore(settings)
        creds = store.get_registry_credentials()
        assert isinstance(creds, AWSCredentials)


class TestCredentialStoreSSH:
    def test_get_ssh_config(self):
        settings = _make_settings(deploy_ssh_key_path="/home/user/.ssh/id_rsa")
        store = CredentialStore(settings)
        config = store.get_ssh_config()
        assert config.key_path == "/home/user/.ssh/id_rsa"

    def test_ssh_missing(self):
        settings = _make_settings()
        store = CredentialStore(settings)
        with pytest.raises(CredentialMissingError, match="DEPLOY_SSH_KEY_PATH"):
            store.get_ssh_config()


class TestCredentialStoreDocker:
    def test_get_docker_config(self):
        settings = _make_settings(docker_host="unix:///var/run/docker.sock")
        store = CredentialStore(settings)
        config = store.get_docker_config()
        assert config.host == "unix:///var/run/docker.sock"


class TestCredentialStoreSecretValues:
    def test_collects_aws_and_llm_keys(self):
        settings = _make_settings(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            anthropic_api_key="sk-ant-api03-longenoughkey",
            openai_api_key="sk-openai-longenoughkey1",
        )
        store = CredentialStore(settings)
        secrets = store.get_all_secret_values()
        assert "AKIAIOSFODNN7EXAMPLE" in secrets
        assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" in secrets
        assert "sk-ant-api03-longenoughkey" in secrets
        assert "sk-openai-longenoughkey1" in secrets

    def test_excludes_short_values(self):
        settings = _make_settings(aws_access_key_id="short")
        store = CredentialStore(settings)
        secrets = store.get_all_secret_values()
        assert "short" not in secrets

    def test_empty_when_no_credentials(self, clean_env):
        settings = _make_settings()
        store = CredentialStore(settings)
        assert store.get_all_secret_values() == []

    def test_registry_type_property(self):
        settings = _make_settings(registry_type="ecr")
        store = CredentialStore(settings)
        assert store.registry_type == "ecr"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `uv run pytest tests/test_infra/test_credentials.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: 구현**

```python
# cicd_agent/infra/credentials.py
from cicd_agent.config import Settings
from cicd_agent.infra.models import AWSCredentials, DockerConfig, GCRCredentials, SSHConfig


class CredentialMissingError(Exception):
    """필요한 자격증명이 설정되지 않았을 때 발생"""
    pass


class CredentialStore:
    """Settings에서 자격증명만 추출하는 래퍼. LLM 컨텍스트에 노출되지 않음."""

    def __init__(self, settings: Settings):
        self._settings = settings

    @property
    def registry_type(self) -> str:
        return self._settings.registry_type

    def get_gcr_credentials(self) -> GCRCredentials:
        if not self._settings.google_application_credentials:
            raise CredentialMissingError(
                "GOOGLE_APPLICATION_CREDENTIALS가 설정되지 않았습니다."
            )
        if not self._settings.gcr_project_id:
            raise CredentialMissingError(
                "GCR_PROJECT_ID가 설정되지 않았습니다."
            )
        return GCRCredentials(
            credentials_path=self._settings.google_application_credentials,
            project_id=self._settings.gcr_project_id,
        )

    def get_aws_credentials(self) -> AWSCredentials:
        if not self._settings.aws_access_key_id:
            raise CredentialMissingError(
                "AWS_ACCESS_KEY_ID가 설정되지 않았습니다."
            )
        if not self._settings.aws_secret_access_key:
            raise CredentialMissingError(
                "AWS_SECRET_ACCESS_KEY가 설정되지 않았습니다."
            )
        return AWSCredentials(
            access_key_id=self._settings.aws_access_key_id,
            secret_access_key=self._settings.aws_secret_access_key.get_secret_value(),
            region=self._settings.aws_default_region,
        )

    def get_registry_credentials(self) -> GCRCredentials | AWSCredentials:
        """registry_type에 따라 적절한 자격증명을 반환"""
        if self._settings.registry_type == "gcr":
            return self.get_gcr_credentials()
        return self.get_aws_credentials()

    def get_ssh_config(self) -> SSHConfig:
        if not self._settings.deploy_ssh_key_path:
            raise CredentialMissingError(
                "DEPLOY_SSH_KEY_PATH가 설정되지 않았습니다."
            )
        return SSHConfig(key_path=self._settings.deploy_ssh_key_path)

    def get_docker_config(self) -> DockerConfig:
        return DockerConfig(host=self._settings.docker_host)

    def get_all_secret_values(self) -> list[str]:
        """OutputSanitizer에 전달할 모든 민감 값 목록. 8자 미만은 과다 마스킹 방지를 위해 제외."""
        secrets: list[str] = []
        if self._settings.aws_access_key_id and len(self._settings.aws_access_key_id) >= 8:
            secrets.append(self._settings.aws_access_key_id)
        if self._settings.aws_secret_access_key:
            val = self._settings.aws_secret_access_key.get_secret_value()
            if len(val) >= 8:
                secrets.append(val)
        for secret_field in [
            self._settings.anthropic_api_key,
            self._settings.openai_api_key,
        ]:
            if secret_field:
                val = secret_field.get_secret_value()
                if len(val) >= 8:
                    secrets.append(val)
        return secrets
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest tests/test_infra/test_credentials.py -v`
Expected: 13 passed

- [ ] **Step 5: 커밋**

```bash
git add cicd_agent/infra/credentials.py tests/test_infra/test_credentials.py
git commit -m ":sparkles: feat: add CredentialStore with GCR/ECR multi-registry support"
```

---

### Task 5: OutputSanitizer

**Files:**
- Rewrite: `cicd_agent/infra/sanitizer.py`
- Test: `tests/test_infra/test_sanitizer.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_infra/test_sanitizer.py
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `uv run pytest tests/test_infra/test_sanitizer.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: 구현**

```python
# cicd_agent/infra/sanitizer.py
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest tests/test_infra/test_sanitizer.py -v`
Expected: 9 passed

- [ ] **Step 5: 커밋**

```bash
git add cicd_agent/infra/sanitizer.py tests/test_infra/test_sanitizer.py
git commit -m ":sparkles: feat: add OutputSanitizer with 2-stage credential redaction"
```

---

### Task 6: .env.example 업데이트 + 전체 검증

**Files:**
- Rewrite: `.env.example`
- Modify: `CLAUDE.md`

- [ ] **Step 1: .env.example 업데이트**

```bash
# === Registry ===
# REGISTRY_TYPE=gcr    # gcr (기본값) 또는 ecr

# === GCR (기본) ===
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
# GCR_PROJECT_ID=your-gcp-project-id

# === AWS/ECR (선택) ===
# AWS_ACCESS_KEY_ID=your-access-key-id
# AWS_SECRET_ACCESS_KEY=your-secret-access-key
# AWS_DEFAULT_REGION=ap-northeast-2

# === Docker ===
# DOCKER_HOST=unix:///var/run/docker.sock

# === SSH (DeployTool, Week 4 선택) ===
# DEPLOY_SSH_KEY_PATH=~/.ssh/id_rsa

# === LLM ===
# ANTHROPIC_API_KEY=your-anthropic-api-key
# OPENAI_API_KEY=your-openai-api-key
# LLM_MODEL=anthropic/claude-sonnet-4-20250514

# === Execution ===
# MAX_RETRIES_PER_STEP=2
# MAX_TOTAL_RETRIES=3
```

- [ ] **Step 2: 전체 테스트 실행**

Run: `uv run pytest -v`
Expected: 전체 통과 (기존 18 + 새 테스트)

- [ ] **Step 3: ruff check**

Run: `uv run ruff check .`
Expected: All checks passed

- [ ] **Step 4: CLAUDE.md 업데이트**

Day 3 완료 상태 + Tech Stack/Conventions/Project Structure 반영:
- Current State에 Day 3 추가: `pydantic-settings 기반 Settings, CredentialStore (GCR/ECR), OutputSanitizer`
- Tech Stack: `python-dotenv` → `pydantic-settings` 변경
- Conventions: `ECR만 지원` → `GCR(기본) + ECR 선택 지원`
- Project Structure: `config.py`, `infra/models.py` 추가

- [ ] **Step 5: 커밋**

```bash
git add .env.example CLAUDE.md
git commit -m ":wrench: chore: update .env.example for GCR/ECR, update CLAUDE.md Day 3 status"
```

---

## Verification Checklist

- [ ] `uv sync` — 의존성 설치 성공
- [ ] `uv run pytest -v` — 전체 테스트 통과
- [ ] `uv run ruff check .` — 린트 통과
- [ ] `from cicd_agent.config import Settings, get_settings` — import 정상
- [ ] `from cicd_agent.infra.credentials import CredentialStore` — import 정상
- [ ] `from cicd_agent.infra.sanitizer import OutputSanitizer` — import 정상
- [ ] Settings에서 SecretStr 필드가 str()로 노출되지 않음
- [ ] GCR/ECR 자격증명 미설정 시 CredentialMissingError 발생
- [ ] OutputSanitizer가 비밀 값을 ***REDACTED***로 치환
