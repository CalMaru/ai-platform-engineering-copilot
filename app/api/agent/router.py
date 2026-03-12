from fastapi import APIRouter

from app.api.agent.schemas import AgentRequest

router = APIRouter(tags=["Agent"])


@router.post("/agent/run")
async def run_agent(request: AgentRequest):
    return {"status": "ok"}


agent_router = router
