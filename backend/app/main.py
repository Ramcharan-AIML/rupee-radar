"""FastAPI application entrypoint.

Run locally with:  uvicorn app.main:app --reload
(from the `backend/` directory, with the virtualenv active).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import routes_analysis, routes_health, routes_upload, routes_usage, routes_chat, routes_report
from app.config import get_settings
from app.store.db import init_db


def create_app() -> FastAPI:
    # Initialize SQLite database
    init_db()

    settings = get_settings()

    app = FastAPI(
        title="RupeeRadar API",
        version=__version__,
        description="AI-powered personal finance analyst — backend API.",
    )

    # Allow the local Vite dev server to call the API during development.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(routes_health.router)
    app.include_router(routes_upload.router)
    app.include_router(routes_analysis.router)
    app.include_router(routes_usage.router)
    app.include_router(routes_chat.router)
    app.include_router(routes_report.router)

    @app.get("/", tags=["root"])
    def root() -> dict[str, str]:
        return {"name": "RupeeRadar API", "docs": "/docs", "health": "/api/health"}

    return app


app = create_app()
