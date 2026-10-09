from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import glossary, health, auth, users
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api")
    app.include_router(glossary.router, prefix="/api")

    from app.api import projects

    app.include_router(projects.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(users.router, prefix="/api")
    return app


app = create_app()
