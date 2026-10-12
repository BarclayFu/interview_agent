from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from interview_agent.api.routes import health, reports, resumes, sessions
from interview_agent.core.config import get_settings
from interview_agent.core.security import ProxySecretMiddleware
from interview_agent.core.telemetry import init_telemetry
from interview_agent.engine.checkpointer import close_checkpointer, init_checkpointer


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_telemetry(get_settings())
    await init_checkpointer()
    yield
    await close_checkpointer()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="interview-agent", version="0.0.1", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(ProxySecretMiddleware)
    app.include_router(health.router)
    app.include_router(resumes.router)
    app.include_router(sessions.router)
    app.include_router(reports.router)
    return app


app = create_app()
