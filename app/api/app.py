from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from app.api.agent.router import agent_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def exception_handler(app: FastAPI):
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        raise exc


def middleware_handler(app: FastAPI):
    @app.middleware("http")
    async def middleware(request: Request, call_next) -> JSONResponse:
        response = await call_next(request)
        return response


def create_app():
    app = FastAPI(title="AI Platform Engineering Copilot API", version="1.0.0", lifespan=lifespan)

    app.include_router(agent_router)

    exception_handler(app)
    middleware_handler(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    return app
