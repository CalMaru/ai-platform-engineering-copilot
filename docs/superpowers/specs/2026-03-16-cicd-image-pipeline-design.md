# CI/CD 이미지 빌드 & 배포 파이프라인 에이전트 설계

## 개요

자연어 요청을 받아 Git 레포지토리에서 Docker 이미지를 빌드하고, 클라우드 레지스트리에 push하며, 필요 시 이미지를 wrapping(추가 레이어 + 플랫폼 재패키징)한 후 재push하고, Docker Compose 기반 서버에 배포하는 AI 에이전트.

## 학습 목표

- **에이전트 오케스트레이션 패턴**: LLM 기반 계획 수립 + 도구 실행 + 실패 복구 루프
- **CI/CD 도메인 지식**: 이미지 빌드, 레지스트리 관리, 컨테이너 배포 자동화

## 접근 방식: 하이브리드

LLM이 자연어를 해석하여 실행 계획(plan)을 생성하고, 고정된 실행 엔진이 계획을 순서대로 수행한다. 실패 시에만 LLM이 재개입하여 복구 전략을 제안한다.

## 아키텍처

```
┌─────────────────────────────────────────────────┐
│                  사용자 (자연어)                    │
└──────────────────────┬──────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────┐
│                 API Layer (FastAPI)               │
└──────────────────────┬───────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────┐
│              Intent Parser (LLM)                  │
│  자연어 → 구조화된 작업 요청 추출                      │
│  (repository, branch, registry, wrap 여부, 배포 등) │
└──────────────────────┬───────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────┐
│             Plan Generator (LLM)                  │
│  추출된 정보 + 설정 → 실행 단계(steps) 리스트 생성     │
│  예: [clone, build, push, wrap, push, deploy]     │
└──────────────────────┬───────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────┐
│            Execution Engine                       │
│  Plan의 각 step을 순서대로 실행                      │
│  각 step → 대응하는 Tool 호출                       │
│  실패 시 → LLM에 재질의 (Recovery Advisor)          │
└──────────────────────┬───────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────┐
│                   Tools                           │
│  ┌─────────┐ ┌─────────┐ ┌──────────────────┐   │
│  │  Clone   │ │  Build  │ │  RegistryAuth    │   │
│  └─────────┘ └─────────┘ └──────────────────┘   │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐           │
│  │  Push   │ │  Wrap   │ │  Deploy  │           │
│  └─────────┘ └─────────┘ └──────────┘           │
└──────────────────────────────────────────────────┘
```

## 데이터 모델

### BuildRequest — Intent Parser 출력

```python
class BuildRequest:
    repository_url: str         # Git 레포지토리 URL
    branch: str                 # 브랜치명
    registry: str               # 대상 레지스트리 (ECR, GCR, ACR)
    image_name: str             # 이미지 이름
    image_tag: str              # 이미지 태그
    wrap: WrapConfig | None     # wrapping 설정 (없으면 skip)
    deploy: DeployConfig | None # 배포 설정 (없으면 skip)
```

### WrapConfig

```python
class WrapConfig:
    base_layers: list[str]      # 추가할 레이어 (보안 에이전트 등)
    target_platform: str        # 재패키징 대상 플랫폼
    target_registry: str        # wrapping 이미지 push 대상
```

### DeployConfig

```python
class DeployConfig:
    host: str                   # 배포 서버 주소
    compose_file_path: str      # docker-compose 파일 경로
    service_name: str           # 업데이트할 서비스명
```

### ExecutionPlan — Plan Generator 출력

```python
class ExecutionPlan:
    steps: list[PlanStep]

class PlanStep:
    name: str                   # clone, build, push, wrap, deploy
    tool: str                   # 실행할 Tool 이름
    parameters: dict            # Tool에 전달할 파라미터
```

### StepResult — Tool 실행 결과

```python
class StepResult:
    step_name: str
    success: bool
    output: dict                # Tool 실행 결과
    error: str | None
```

## LLM 역할 분담

### 1. Intent Parser

자연어에서 `BuildRequest` 구조를 추출한다. 정보가 부족하면 기본값을 적용한다 (예: tag 미지정 시 `latest`, branch 미지정 시 `main`).

### 2. Plan Generator

`BuildRequest`를 보고 필요한 step만 포함한 `ExecutionPlan`을 생성한다. wrap이 없으면 wrap/재push 단계를 제외하고, deploy가 없으면 배포 단계를 제외한다.

### 3. Recovery Advisor

Tool 실행 실패 시 에러 메시지를 분석하고 복구 전략을 제안한다. 복구 불가능한 경우 사용자에게 명확한 에러 리포트를 반환한다.

## Tools

### CloneTool
- Git 레포지토리를 클론하고 지정된 브랜치를 체크아웃
- 입력: `repository_url`, `branch`
- 출력: 클론된 로컬 경로

### BuildTool
- 빌드 전용 컨테이너를 띄워서 Docker 이미지 빌드
- 입력: 소스 경로, `image_name`, `image_tag`
- 출력: 빌드된 이미지 ID

### RegistryAuthTool
- 클라우드 레지스트리(ECR/GCR/ACR) 인증 수행
- 입력: `registry` 종류, 인증 정보 (환경변수에서 로드)
- 출력: 인증 성공 여부

### PushTool
- 빌드된 이미지를 레지스트리에 push
- 입력: `image_name`, `image_tag`, `registry`
- 출력: push된 이미지 URI

### WrapTool
- 기존 이미지 위에 추가 레이어 적용 + 플랫폼 재패키징
- 입력: 원본 이미지, `base_layers`, `target_platform`, `target_registry`
- 출력: wrapping된 이미지 URI

### DeployTool
- SSH로 배포 서버 접속 후 docker-compose 서비스 업데이트
- 입력: `host`, `compose_file_path`, `service_name`, 새 이미지 URI
- 출력: 배포 성공 여부

## 실행 엔진 동작 흐름

1. ExecutionPlan의 step을 순서대로 실행
2. 각 step의 결과는 다음 step의 입력으로 전달 (예: BuildTool 결과 이미지 ID → PushTool 입력)
3. 실패 시 Recovery Advisor(LLM)에 에러 전달 → 복구 전략 수신 → 수정 후 재시도
4. 재시도는 step당 최대 3회
5. 복구 불가능 시 실행 중단 + 에러 반환
6. 모든 step 실행 로그는 보존

## 인증 방식

현재는 환경변수 및 설정 파일에서 credential을 로드한다. 향후 시크릿 매니저(Vault, AWS Secrets Manager) 연동으로 확장 가능하다.

## 프로젝트 구조

```
ai-platform-engineering-copilot/
├── app/
│   ├── agent/
│   │   ├── intent_parser.py      # 자연어 → BuildRequest
│   │   ├── plan_generator.py     # BuildRequest → ExecutionPlan
│   │   ├── execution_engine.py   # Plan 순서대로 실행
│   │   └── recovery_advisor.py   # 실패 시 LLM 복구 전략
│   ├── api/
│   │   ├── app.py                # FastAPI 앱
│   │   └── agent/
│   │       ├── router.py         # 엔드포인트
│   │       └── schemas.py        # API 스키마
│   ├── core/
│   │   ├── config.py             # 설정 (레지스트리, 인증 등)
│   │   └── llm_client.py         # LLM 추상화
│   ├── schemas/
│   │   ├── build_request.py      # BuildRequest, WrapConfig, DeployConfig
│   │   ├── plan.py               # ExecutionPlan, PlanStep
│   │   └── result.py             # StepResult
│   └── tools/
│       ├── base.py               # Tool 인터페이스
│       ├── clone_tool.py         # Git 클론
│       ├── build_tool.py         # 빌드 컨테이너에서 이미지 빌드
│       ├── registry_auth_tool.py # 레지스트리 인증
│       ├── push_tool.py          # 이미지 push
│       ├── wrap_tool.py          # 이미지 wrapping
│       └── deploy_tool.py        # Docker Compose 배포
├── tests/
├── docs/
├── main.py
├── pyproject.toml
└── ruff.toml
```

## 향후 확장 사항

- **사용자 확인 단계**: Plan 생성 후 사용자에게 보여주고 승인받은 뒤 실행
- **프라이빗 레지스트리 지원**: Harbor, Nexus 등
- **시크릿 매니저 연동**: Vault, AWS Secrets Manager
- **빌드 결과 리포팅**: 슬랙 알림, 웹훅 등
- **멀티 플랫폼 빌드**: `buildx`를 활용한 다중 아키텍처 지원
