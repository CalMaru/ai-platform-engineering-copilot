# 1주차 세부 계획

**목표**: 프로젝트 기반을 세우고, `cicd_agent/` 패키지 구조와 CloneTool이 독립적으로 동작하는 상태.

**상위 계획**: [MVP 개발 계획](mvp_development_plan.md)
**설계**: [실행 레이어 설계 문서](superpowers/specs/2026-03-19-cicd-agent-execution-layer-design.md)

---

## Day 1: 프로젝트 설정 + 데이터 모델 ✅

- [x] `pyproject.toml` 의존성 정리
  - 제거: `fastapi`, `uvicorn`
  - 추가: `litellm`, `docker`, `paramiko`
  - dev 추가: `pytest-asyncio`
- [x] Pydantic v2 데이터 모델 구현 (`app/schemas/`)
- [x] 테스트 작성 및 통과 확인

> **Note**: Day 1은 구 `app/` 구조로 완료됨. 이후 `cicd_agent/` 패키지로 리팩토링 필요.

---

## Day 2: 패키지 리팩토링 + 인프라 ✅

- [x] `app/` → `cicd_agent/` 패키지 구조 전환
  - `cicd_agent/models/` — 데이터 모델
  - `cicd_agent/infra/` — 횡단 관심사 (placeholder)
  - `cicd_agent/execution/` — 실행 도메인 (placeholder)
  - `cicd_agent/planning/` — 계획 수립 도메인 (placeholder)
- [x] `pyproject.toml` 업데이트
  - 프로젝트명: `cicd-agent`
  - 의존성 추가: `gitpython`, `boto3`, `python-dotenv`, `typer`
  - `isort` 제거 → ruff `"I"` 규칙으로 대체
- [x] 데이터 모델 업데이트 (새 설계에 맞춤)
  - `models/request.py` — BuildRequest (repo_url, dockerfile_path, registry 등)
  - `models/plan.py` — ExecutionPlan, PlanStep (tool_name, confirm_required 등)
  - `models/result.py` — ToolResult, PipelineResult, ErrorType
  - `models/recovery.py` — RecoveryAdvice (action: retry/skip/abort)
- [x] 구 `app/` 디렉토리 및 `tests/schemas/` 삭제
- [x] 18개 테스트 통과, ruff check 통과

**완료 기준:**

```python
from cicd_agent.models.request import BuildRequest
from cicd_agent.models.result import ToolResult, ErrorType

request = BuildRequest(
    repo_url="https://github.com/myorg/api-server",
    image_name="api-server",
    image_tag="v1.0",
    registry="ecr",
)
assert request.branch == "main"
assert request.dockerfile_path == "Dockerfile"
```

---

## Day 3: CredentialStore + OutputSanitizer

- [ ] `cicd_agent/infra/credentials.py` 구현
  - CredentialStore: 환경변수에서 자격증명 로드
  - `get_aws_credentials()` → AWSCredentials
  - `get_ssh_config()` → SSHConfig
  - `get_docker_config()` → DockerConfig
  - 필수 변수 누락 시 `CredentialMissingError` (fail-fast)
- [ ] `cicd_agent/infra/sanitizer.py` 구현
  - OutputSanitizer: 2단계 세정
  - 1단계: 실제 비밀 값 정확 매칭
  - 2단계: 정규식 패턴 폴백 (AKIA*, password=*, token=*, PEM 키)
- [x] `.env.example` 생성
- [ ] `tests/test_infra/` 테스트 작성 및 통과 확인

**완료 기준:**

```python
os.environ["AWS_ACCESS_KEY_ID"] = "AKIAIOSFODNN7EXAMPLE"
store = CredentialStore()
creds = store.get_aws_credentials()
assert creds.access_key_id == "AKIAIOSFODNN7EXAMPLE"

sanitizer = OutputSanitizer(store)
assert "***REDACTED***" in sanitizer.sanitize("Key is AKIAIOSFODNN7EXAMPLE")
```

---

## Day 4: BaseTool + CloneTool

- [ ] `cicd_agent/execution/tools/base.py` 구현
  - BaseTool ABC: `__init__(credentials, sanitizer)`, `execute(params) → ToolResult`
  - `_safe_result(success, message, **data)` — sanitizer 적용 후 ToolResult 반환
- [ ] `cicd_agent/execution/tools/clone.py` 구현
  - GitPython 기반: `Repo.clone_from(url, path, branch=branch)`
  - 임시 디렉터리에 클론
  - 성공 시 `{"clone_dir": "/tmp/build/my-app"}` 반환
  - 실패 시 error_type 분류 (AUTH_FAILED, NOT_FOUND, NETWORK_ERROR)
- [ ] `tests/test_execution/test_clone.py` 작성 및 통과 확인

**완료 기준:**

```python
store = CredentialStore()
sanitizer = OutputSanitizer(store)
tool = CloneTool(store, sanitizer)
result = tool.execute({"repo_url": "https://github.com/octocat/Hello-World", "branch": "master"})
assert result.success
assert Path(result.data["clone_dir"]).exists()
```

---

## Day 5: DinD 스모크 테스트 + 정리 + 자격증명 격리 검증

### Docker-in-Docker 소켓 마운트 스모크 테스트

BuildTool은 컨테이너 안에서 Docker 이미지를 빌드하는 DinD 패턴을 사용한다. Week 2에서 BuildTool을 구현하기 전에, 소켓 마운트가 각 환경에서 동작하는지 확인한다.

#### macOS 테스트

```bash
# 1. 호스트의 Docker 소켓을 마운트하여 컨테이너 실행
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock docker:cli docker version

# 2. 컨테이너 안에서 간단한 이미지 빌드
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/tests/fixtures/sample-dockerfile:/workspace \
  docker:cli sh -c "cd /workspace && docker build -t dind-smoke-test . && docker rmi dind-smoke-test"
```

- [ ] `tests/fixtures/sample-dockerfile/Dockerfile` 생성 (최소 테스트용)
  ```dockerfile
  FROM alpine:3.20
  RUN echo "DinD smoke test"
  ```
- [ ] macOS에서 위 명령 수동 실행하여 성공 확인

#### Windows 테스트

Windows 머신에서 Docker Desktop (WSL2 백엔드) 환경으로 동일한 테스트 수행.

```powershell
# 1. 소켓 마운트 확인 (Windows Docker Desktop은 내부적으로 WSL2 Linux VM 사용)
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock docker:cli docker version

# 2. DinD 빌드 테스트
docker run --rm `
  -v /var/run/docker.sock:/var/run/docker.sock `
  -v ${PWD}/tests/fixtures/sample-dockerfile:/workspace `
  docker:cli sh -c "cd /workspace && docker build -t dind-smoke-test . && docker rmi dind-smoke-test"
```

- [ ] Windows에서 위 명령 수동 실행하여 성공 확인
- [ ] 실패 시: `npipe:////./pipe/docker_engine` 소켓 마운트 방식 확인
  ```powershell
  # npipe 방식 (WSL2가 아닌 Hyper-V 백엔드인 경우)
  docker run --rm -v //./pipe/docker_engine://./pipe/docker_engine docker:cli docker version
  ```

#### 결과 기록

| 환경 | Docker 백엔드 | 소켓 경로 | DinD 빌드 | 비고 |
|------|-------------|----------|----------|------|
| macOS (로컬) | Docker Desktop | `/var/run/docker.sock` | [ ] 성공 | |
| Windows (별도 머신) | Docker Desktop (WSL2) | `/var/run/docker.sock` | [ ] 성공 | |
| Windows (별도 머신) | Docker Desktop (Hyper-V) | `//./pipe/docker_engine` | [ ] 해당 시 | |

> **Note**: 이 테스트 결과를 바탕으로 Week 2 BuildTool 구현 시 `docker_host` 설정 분기를 확정한다.

---

### 자격증명 격리 검증 + 정리

- [ ] 자격증명 격리 기본 검증 테스트
  - ToolResult.message에 자격증명 패턴이 포함되지 않음
  - CredentialStore의 값이 sanitizer를 거치면 모두 마스킹됨
- [ ] 코드 정리: ruff 린트 + 포맷팅
- [ ] 테스트 커버리지 확인
- [ ] 1주차 커밋 정리

**완료 기준:**

모든 테스트 통과 + CloneTool이 GitPython으로 동작 + 자격증명이 ToolResult에 노출되지 않음 + macOS/Windows DinD 스모크 테스트 결과 기록.

---

## 1주차 산출물 요약

| 산출물 | 파일 |
|--------|------|
| 데이터 모델 | `cicd_agent/models/request.py`, `plan.py`, `result.py`, `recovery.py` |
| 인프라 | `cicd_agent/infra/credentials.py`, `sanitizer.py` |
| Tool 인터페이스 | `cicd_agent/execution/tools/base.py` |
| CloneTool | `cicd_agent/execution/tools/clone.py` |
| 환경변수 예시 | `.env.example` |
| 테스트 | `tests/test_infra/`, `tests/test_execution/` |
