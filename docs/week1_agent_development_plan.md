# AI Platform Engineering Copilot

## Week 1 Development Plan (Detailed)

This document describes the **Day-by-Day development plan for Week 1**
of the project.

The goal of Week 1 is to build a **working Agent MVP** that
demonstrates:

-   Agent workflow
-   Structured outputs
-   FastAPI interface
-   Basic tool integration

The system does **not need to be feature complete**.\
The primary objective is to build a **clean and extensible agent
architecture**.

------------------------------------------------------------------------

# Week 1 Objective

By the end of Week 1 the system should support:

1.  FastAPI endpoint for agent execution
2.  Agent workflow (classification → prompt → LLM → structured output)
3.  One real capability (API specification drafting)
4.  One tool integration
5.  Structured JSON output
6.  Request/response logging

------------------------------------------------------------------------

# System Workflow (Target)

    User Request
         ↓
    FastAPI Endpoint
         ↓
    Agent Orchestrator
         ↓
    Task Classification
         ↓
    Prompt Builder
         ↓
    Optional Tool Call
         ↓
    LLM Generation
         ↓
    Structured Output Parsing
         ↓
    Response

------------------------------------------------------------------------

# Recommended Repository Structure

    ai-platform-copilot
    │
    ├ app
    │
    │  ├ api
    │  │  └ agent_router.py
    │
    │  ├ agent
    │  │  ├ orchestrator.py
    │  │  ├ classifier.py
    │  │  ├ prompt_builder.py
    │  │  └ output_parser.py
    │
    │  ├ tools
    │  │  ├ base.py
    │  │  └ api_template_tool.py
    │
    │  ├ schemas
    │  │  ├ request.py
    │  │  └ response.py
    │
    │  └ core
    │     ├ config.py
    │     └ llm_client.py
    │
    ├ docs
    ├ examples
    ├ tests
    └ main.py

------------------------------------------------------------------------

# Day 1 --- Project Setup and Base Architecture

## Goal

Create the **project skeleton and base infrastructure**.

## Tasks

### 1. Create project repository

    ai-platform-copilot

Initialize git repository and create:

    README.md
    docs/
    app/
    tests/
    examples/

------------------------------------------------------------------------

### 2. Initialize Python project

Recommended tools:

-   Python 3.11+
-   uv (dependency manager)

Example:

    uv init

Install dependencies:

    uv add fastapi uvicorn pydantic httpx

------------------------------------------------------------------------

### 3. Create FastAPI server

File:

    main.py

Example:

``` python
from fastapi import FastAPI
from app.api.agent_router import router

app = FastAPI()
app.include_router(router)
```

------------------------------------------------------------------------

### 4. Create base endpoint

File:

    app/api/agent_router.py

Example:

``` python
@router.post("/agent/run")
async def run_agent(request: AgentRequest):
    return {"status": "ok"}
```

------------------------------------------------------------------------

### Day 1 Deliverable

You should be able to run:

    uvicorn main:app --reload

Swagger should show:

    POST /agent/run

------------------------------------------------------------------------

# Day 2 --- Agent Core Design

## Goal

Implement the **Agent workflow controller**.

------------------------------------------------------------------------

## Create Agent Orchestrator

File:

    app/agent/orchestrator.py

Responsibilities:

-   run agent pipeline
-   coordinate components

Example structure:

``` python
class AgentOrchestrator:

    async def run(self, request):

        task = classify_task(request.input)

        prompt = build_prompt(task, request.input)

        result = await llm.generate(prompt)

        parsed = parse_output(result)

        return parsed
```

------------------------------------------------------------------------

## Create Task Classifier

File:

    app/agent/classifier.py

Initial task types:

    api_design
    rag_configuration
    error_analysis

First implementation can be rule-based.

------------------------------------------------------------------------

### Day 2 Deliverable

Agent orchestrator works with mocked LLM output.

------------------------------------------------------------------------

# Day 3 --- Structured Output System

## Goal

Ensure the agent always returns **structured JSON responses**.

------------------------------------------------------------------------

## Create Response Schema

File:

    app/schemas/response.py

Example:

``` python
class AgentResult(BaseModel):

    task_type: str
    summary: str
    assumptions: list[str]
    result: dict
    risks: list[str]
```

------------------------------------------------------------------------

## Create Output Parser

File:

    app/agent/output_parser.py

Responsibilities:

-   parse LLM output
-   validate schema

Example:

``` python
def parse_output(text):

    data = json.loads(text)
    return AgentResult(**data)
```

------------------------------------------------------------------------

## Update Prompt Format

Prompt must enforce strict JSON output.

Example:

    Return response strictly in JSON format.

------------------------------------------------------------------------

### Day 3 Deliverable

Agent returns validated structured output.

------------------------------------------------------------------------

# Day 4 --- API Specification Feature

## Goal

Implement the **first real capability**: API specification drafting.

------------------------------------------------------------------------

## Add API Design Prompt Builder

File:

    app/agent/prompt_builder.py

Example:

``` python
def build_api_prompt(user_input):

    return f'''
You are a backend architect.

Generate a REST API specification.

User request:
{user_input}

Return JSON only.
'''
```

------------------------------------------------------------------------

## Example Input

    Design an API that returns models grouped by provider.

------------------------------------------------------------------------

## Expected Output

    Endpoint: GET /api/v1/models
    Response:
    {
      "providers": []
    }

------------------------------------------------------------------------

### Day 4 Deliverable

Agent can generate API spec drafts.

------------------------------------------------------------------------

# Day 5 --- Tool System

## Goal

Introduce **Tool-based Agent architecture**.

------------------------------------------------------------------------

## Tool Interface

File:

    app/tools/base.py

Example:

``` python
class Tool:

    name: str

    async def run(self, input: dict):
        pass
```

------------------------------------------------------------------------

## API Template Tool

File:

    app/tools/api_template_tool.py

Example:

``` python
class ApiTemplateTool(Tool):

    name = "api_template"

    async def run(self, input):

        return {
            "standard_error_format": {
                "error_code": "string",
                "message": "string"
            }
        }
```

------------------------------------------------------------------------

## Agent Tool Usage

The agent may retrieve templates before calling the LLM.

------------------------------------------------------------------------

### Day 5 Deliverable

Agent can call one tool.

------------------------------------------------------------------------

# Day 6 --- Logging and Test Dataset

## Goal

Add observability and reproducibility.

------------------------------------------------------------------------

## Request/Response Logging

Create directory:

    logs/

Save:

    request.json
    response.json

Example:

``` python
save_request(request)
save_response(response)
```

------------------------------------------------------------------------

## Create Example Inputs

Directory:

    examples/

Example files:

    api_design_1.txt
    rag_config_1.txt
    error_case_1.txt

These will be used to test agent outputs.

------------------------------------------------------------------------

### Day 6 Deliverable

Agent requests and outputs are logged.

------------------------------------------------------------------------

# Day 7 --- Demo Preparation

## Goal

Prepare a working demo.

------------------------------------------------------------------------

## Test scenarios

Prepare at least three examples.

### Example 1 --- API design

    Create API for listing models grouped by provider

### Example 2 --- RAG configuration

    String field that needs filtering and sorting

### Example 3 --- Error troubleshooting

    uv add faiss dependency error

------------------------------------------------------------------------

## Final tasks

-   Verify API endpoint
-   Validate structured output
-   Confirm tool usage
-   Document example requests

------------------------------------------------------------------------

# Week 1 Completion Criteria

Week 1 is successful if:

-   Agent workflow is implemented
-   FastAPI endpoint works
-   Structured outputs are validated
-   One tool is integrated
-   API spec generation works

------------------------------------------------------------------------

# Important Notes

Avoid over-engineering during Week 1.

Do NOT add:

-   Vector databases
-   Multi-agent orchestration
-   Complex planners
-   LangGraph / heavy frameworks

Focus on:

-   Clean architecture
-   Extensible design
-   Working MVP
