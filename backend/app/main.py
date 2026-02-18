import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from langfuse.decorators import observe

from app.api.v1.routers import chat, documents, ingest
from app.config import get_settings
from app.core.observability import langfuse_client
from app.db.session import init_db
from app.dependencies import get_qdrant_client


logger = logging.getLogger("enterprise_rag")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Starting %s", settings.app_name)
    await init_db()
    qdrant_client = get_qdrant_client()
    logger.info("Qdrant connected to %s", qdrant_client.config.url)
    yield
    if langfuse_client:
        langfuse_client.flush()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.allowed_origins] or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts,
    )

    app.include_router(ingest.router, prefix="/api/v1", tags=["ingest"])
    app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
    app.include_router(documents.router, prefix="/api/v1", tags=["documents"])

    @app.get("/health")
    @observe()
    async def health():
        return {"status": "ok", "service": settings.app_name}

    return app


app = create_app()

