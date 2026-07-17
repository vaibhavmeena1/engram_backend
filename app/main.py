"""Application entry point for the engram-backend service."""

import uvicorn

from fastapi import APIRouter
from fastapi.middleware.cors import CORSMiddleware

from vortex import CONFIG, Vortex

from app.listeners.listeners_manager import ListenersManager
from app.routers import (
    admin,
    audit,
    auth,
    memories,
    memory_proposals,
    mcp_router,
    oauth,
    personal_access_tokens,
    plugin,
    scopes,
    tags,
)
from app.services.config_service import EngramConfigService

# Register your domain routers here
routers: list[APIRouter] = [
    auth.router,
    oauth.router,
    personal_access_tokens.router,
    memories.router,
    memory_proposals.router,
    tags.router,
    scopes.router,
    admin.router,
    audit.router,
    plugin.router,
]

vortex = Vortex(
    routers=routers,
    lifespans=[*ListenersManager.listeners(), mcp_router.lifespan()],
    service_config=CONFIG.config,
)

app = vortex.create_app()

cors_settings = EngramConfigService.cors()
if cors_settings.allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_settings.allowed_origins,
        allow_credentials=cors_settings.allow_credentials,
        allow_methods=cors_settings.allow_methods,
        allow_headers=cors_settings.allow_headers,
    )

mcp_router.mount_mcp_http_app(app)


if __name__ == "__main__":
    host_config = vortex.host_config
    uvicorn.run(
        "app.main:app",
        host=host_config.HOST,
        port=int(host_config.PORT),
        reload=host_config.DEBUG,
        workers=host_config.WORKERS,
    )
