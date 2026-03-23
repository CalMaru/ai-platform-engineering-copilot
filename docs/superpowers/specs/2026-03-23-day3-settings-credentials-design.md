# Day 3: pydantic-settings 기반 설정 관리 + 자격증명 격리

## 1. Overview

`pydantic-settings`를 활용하여 앱 설정을 클래스로 관리하고, CredentialStore와 OutputSanitizer로 자격증명 격리를 구현한다. Docker 컨테이너와 로컬 실행 모두 `.env` 파일로 환경변수를 주입한다.

### 설계 결정

- **Settings와 CredentialStore 분리**: Settings는 앱 전체 설정, CredentialStore는 자격증명만 래핑하여 LLM에 노출되지 않도록 격리
- **`.env` 단일 방식**: 현재 설정이 전부 단일 키-값이므로 YAML은 불필요. Docker `--env-file`과도 호환
- **Settings는 `config.py`에 배치**: 앱 전체가 사용하는 설정이므로 `infra/`가 아닌 패키지 루트
- **민감 필드에 `SecretStr` 적용**: pydantic의 `SecretStr`로 실수로 로깅/직렬화될 때 비밀 값 노출 방지
- **GCR/ECR 멀티 레지스트리**: `registry_type`으로 선택, GCR이 기본값. 선택한 레지스트리의 자격증명만 필수 검증

### 부모 설계 문서(03-19)와의 차이

| 항목 | 부모 설계 | 이 설계 | 이유 |
|------|----------|---------|------|
| 레지스트리 | ECR만 | GCR(기본) + ECR 선택 | 사용자가 GCR 사용, ECR도 지원 |
| CredentialStore 데이터 소스 | `os.environ` 직접 접근 | `Settings` 객체 주입 | 단일 소스, 테스트 용이성 |
| 필수 자격증명 누락 에러 | `CredentialMissingError` | pydantic `ValidationError` (Settings) + `CredentialMissingError` (런타임) | Settings는 모든 필드 선택, CredentialStore가 registry_type에 따라 검증 |
| `get_all_secret_values` 범위 | AWS 키만 | AWS + GCR + LLM API 키 | 보안 범위 확대 |
| `python-dotenv` 의존성 | 직접 사용 | `pydantic-settings`가 내부 처리 | 의존성 단순화 |

---

## 2. 파일 구조

```
cicd_agent/
├── config.py              # Settings (pydantic-settings BaseSettings)
├── infra/
│   ├── credentials.py     # CredentialStore (Settings → 자격증명 추출)
│   ├── sanitizer.py       # OutputSanitizer (2단계 세정)
│   └── models.py          # AWSCredentials, GCRCredentials, SSHConfig, DockerConfig
```

---

## 3. Settings

`cicd_agent/config.py`

```python
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
    google_application_credentials: str | None = None   # JSON 키 파일 경로
    gcr_project_id: str | None = None                   # GCP 프로젝트 ID

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

    # --- SSH (선택, Week 4 DeployTool용) ---
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

### 특징

- `frozen=True`: 불변 보장 (KIRA 패턴)
- `@lru_cache`: 싱글턴, 설정을 한 번만 로드
- `env_file=".env"`: 로컬 실행 시 `.env` 자동 로드
- Docker 실행 시: `docker run --env-file .env` 또는 개별 `-e` 플래그로 주입
- 레지스트리 자격증명은 모두 선택 — CredentialStore가 `registry_type`에 따라 런타임에 검증

### 레지스트리별 필수 설정

| `registry_type` | 필수 환경변수 |
|-----------------|-------------|
| `gcr` | `GOOGLE_APPLICATION_CREDENTIALS`, `GCR_PROJECT_ID` |
| `ecr` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |

---

## 4. 인프라 데이터 모델

`cicd_agent/infra/models.py`

```python
from pydantic import BaseModel


class GCRCredentials(BaseModel):
    credentials_path: str       # JSON 키 파일 경로
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

---

## 5. CredentialStore

`cicd_agent/infra/credentials.py`

```python
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
        # AWS
        if self._settings.aws_access_key_id and len(self._settings.aws_access_key_id) >= 8:
            secrets.append(self._settings.aws_access_key_id)
        if self._settings.aws_secret_access_key:
            val = self._settings.aws_secret_access_key.get_secret_value()
            if len(val) >= 8:
                secrets.append(val)
        # LLM API keys
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

### Settings와의 관계

- CredentialStore는 Settings를 생성자로 주입받음
- Settings 전체를 외부에 노출하지 않고, 자격증명 관련 메서드만 제공
- `get_registry_credentials()`가 `registry_type`에 따라 적절한 자격증명 반환
- `get_all_secret_values()`는 OutputSanitizer에서 사용

### 에러 흐름

```
Settings 생성 시: registry_type이 "gcr" 또는 "ecr" 아니면 → ValidationError
CredentialStore 사용 시: 선택한 레지스트리의 자격증명 미설정 → CredentialMissingError
```

GCR JSON 키 파일의 내용은 파일 경로만 관리하고, 실제 파일 읽기는 RegistryAuthTool(Week 2)에서 수행한다.

---

## 6. OutputSanitizer

`cicd_agent/infra/sanitizer.py`

2단계 세정:

1. **실제 비밀 값 정확 매칭**: CredentialStore의 `get_all_secret_values()`로 얻은 값을 문자열 치환
2. **정규식 패턴 폴백**: `AKIA*`, `password=*`, `token=*`, PEM 키 패턴

```python
import re

from cicd_agent.infra.credentials import CredentialStore


class OutputSanitizer:
    PATTERNS = [
        (r'AKIA[0-9A-Z]{16}', '***REDACTED***'),
        (r'(?i)(password[=:]\s*)\S+', r'\1***REDACTED***'),
        (r'(?i)(token[=:]\s*)\S{8,}', r'\1***REDACTED***'),
        (r'-----BEGIN .* KEY-----[\s\S]*?-----END .* KEY-----', '***REDACTED***'),
    ]

    def __init__(self, credentials: CredentialStore):
        self._secret_values = credentials.get_all_secret_values()

    def sanitize(self, text: str) -> str:
        # 1단계: 실제 비밀 값 정확 매칭
        for secret in self._secret_values:
            text = text.replace(secret, '***REDACTED***')
        # 2단계: 정규식 패턴 폴백
        for pattern, replacement in self.PATTERNS:
            text = re.sub(pattern, replacement, text)
        return text
```

### 정규식 패턴 설계

- `password=`: 라벨 보존 (`password=***REDACTED***`)
- `token=`: 라벨 보존 + 최소 8자 이상만 매칭 (짧은 토큰 설명 텍스트 오탐 방지)
- `AKIA*`: AWS Access Key ID 고정 패턴
- PEM 키: 멀티라인 전체 매칭

---

## 7. .env.example 업데이트

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

---

## 8. 실행 환경별 동작

| 환경 | 설정 주입 방식 |
|------|--------------|
| 로컬 개발 | `.env` 파일 → pydantic-settings 자동 로드 |
| Docker | `docker run --env-file .env` 또는 `-e KEY=VAL` |
| CI/CD | 환경변수 직접 설정 (GitHub Actions secrets 등) |
| 테스트 | `monkeypatch.setenv()` 또는 `Settings(...)` 직접 생성 |

pydantic-settings는 환경변수 → `.env` 파일 순으로 우선순위를 가지므로, 환경변수가 설정되어 있으면 `.env`보다 우선한다.

GCR의 경우 `GOOGLE_APPLICATION_CREDENTIALS` 환경변수는 Google Cloud SDK와 동일한 표준 변수명을 사용한다.

---

## 9. 테스트 전략

### `@lru_cache` 테스트 격리

`get_settings()`는 `@lru_cache`로 싱글턴이므로, 테스트 간 격리를 위해 반드시 캐시를 클리어해야 한다:

```python
@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
```

### Settings 테스트 (`tests/test_config.py`)
- 기본값 확인 (registry_type="gcr", region, docker_host, llm_model 등)
- registry_type 유효성 ("gcr", "ecr"만 허용, 그 외 ValidationError)
- frozen 확인 (수정 시도 시 에러)
- `SecretStr` 필드가 `str()`로 노출되지 않는지 확인

### CredentialStore 테스트 (`tests/test_infra/test_credentials.py`)
- GCR: Settings → GCRCredentials 변환
- GCR: 자격증명 미설정 시 CredentialMissingError
- ECR: Settings → AWSCredentials 변환 (`SecretStr.get_secret_value()` 호출 확인)
- ECR: 자격증명 미설정 시 CredentialMissingError
- `get_registry_credentials()`: registry_type에 따른 분기 검증
- SSH 키 미설정 시 CredentialMissingError
- `get_all_secret_values()` 목록 검증 (8자 미만 값 제외 확인)

### OutputSanitizer 테스트 (`tests/test_infra/test_sanitizer.py`)
- 실제 값 정확 매칭으로 마스킹
- AKIA 패턴 정규식 매칭
- password/token 패턴 매칭 (라벨 보존 확인)
- PEM 키 패턴 매칭
- 민감 정보 없는 텍스트는 그대로 반환
- 2단계 순서 검증: 정규식에 매칭되지 않는 비밀 값도 1단계에서 마스킹됨

---

## 10. 의존성 변경

`pyproject.toml`:

```toml
# 추가
"pydantic-settings>=2.0.0",

# 제거
"python-dotenv>=1.0.0",   # pydantic-settings가 내부 처리
```
