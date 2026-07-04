"""FastAPI application entrypoint.

Run locally with:  uvicorn app.main:app --reload
(from the `backend/` directory, with the virtualenv active).
"""

from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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

    # Allow the local Vite dev server or production domains to call the API.
    origins = [origin.strip() for origin in settings.frontend_origin.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
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

    # Determine if production built frontend assets are present
    frontend_dist = os.path.abspath(settings.frontend_dist_dir)
    has_frontend = False
    if os.path.exists(frontend_dist) and os.path.isdir(frontend_dist):
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_path):
            has_frontend = True

    if has_frontend:
        # Serve frontend at the root
        @app.get("/", tags=["frontend"], include_in_schema=False)
        def read_main():
            return FileResponse(os.path.join(frontend_dist, "index.html"))

        # Mount assets folder
        assets_path = os.path.join(frontend_dist, "assets")
        if os.path.exists(assets_path) and os.path.isdir(assets_path):
            app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

        # HTML5 History API fallback for other UI routes (excluding api, docs, openapi.json)
        @app.get("/{fallback_path:path}", include_in_schema=False)
        def serve_frontend_fallback(fallback_path: str):
            if (
                fallback_path.startswith("api/")
                or fallback_path.startswith("docs")
                or fallback_path.startswith("openapi.json")
            ):
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Not Found")
            
            # Check if file exists under frontend_dist
            file_path = os.path.join(frontend_dist, fallback_path)
            if fallback_path and os.path.exists(file_path) and os.path.isfile(file_path):
                return FileResponse(file_path)
            
            return FileResponse(os.path.join(frontend_dist, "index.html"))
    else:
        @app.get("/", tags=["root"])
        def root() -> dict[str, str]:
            return {"name": "RupeeRadar API", "docs": "/docs", "health": "/api/health"}

    return app


app = create_app()
