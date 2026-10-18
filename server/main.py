from __future__ import annotations

from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from config import get_settings
from db import startup, shutdown
from middleware.rate_limit import limiter, rate_limit_handler
from routers import mps, stats, ipc, severity

STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"


# ── LIFESPAN ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Replaces deprecated @app.on_event handlers.
    Everything before `yield` runs at startup, after yield runs at shutdown.
    """
    await startup()     # opens SQLite connection
    yield
    await shutdown()    # closes it cleanly


# ── APP FACTORY ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Neta Check API",
        description="Public MP transparency data — 18th Lok Sabha",
        version="1.0.0",
        # Disable docs in production — no need to expose schema publicly
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        lifespan=lifespan,
    )

    # ── RATE LIMITER ──────────────────────────────────────────────────────────
    # Attach limiter to app state so slowapi can find it
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Only your own frontend origins get through.
    # Adjust ALLOWED_ORIGINS in .env as you add domains.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins_list,
        allow_credentials=False,        # no cookies needed
        allow_methods=["GET"],          # read-only API, GET only
        allow_headers=["*"],
    )

    # ── SECURITY HEADERS ──────────────────────────────────────────────────────
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"]  = "nosniff"
        response.headers["X-Frame-Options"]         = "DENY"
        response.headers["Referrer-Policy"]         = "strict-origin-when-cross-origin"
        if request.url.path.startswith("/assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif "Cache-Control" not in response.headers:
            response.headers["Cache-Control"] = "public, max-age=300"  # 5 min default
        return response

    # ── ROUTERS ───────────────────────────────────────────────────────────────
    app.include_router(mps.router)
    app.include_router(stats.router)
    app.include_router(ipc.router)
    app.include_router(severity.router)

    # ── HEALTH CHECK ──────────────────────────────────────────────────────────
    @app.get("/health", include_in_schema=False)
    async def health():
        """Used by load balancer / uptime monitor. Not rate limited."""
        return {"status": "ok", "version": "1.0.0"}

    # ── STATIC FRONTEND (Vite build → server/static) ──────────────────────────
    app.mount(
        "/assets",
        StaticFiles(directory=STATIC_DIR / "assets", check_dir=False),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)

        if full_path:
            static_root = STATIC_DIR.resolve()
            candidate = (STATIC_DIR / full_path).resolve()
            if candidate.is_relative_to(static_root) and candidate.is_file():
                return FileResponse(candidate)

        if not INDEX_HTML.is_file():
            return HTMLResponse("Frontend not built", status_code=503)

        return FileResponse(
            INDEX_HTML,
            media_type="text/html",
            headers={"Cache-Control": "no-cache"},
        )

    return app


app = create_app()


# ── ENTRY POINT ───────────────────────────────────────────────────────────────
# Run with: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=not settings.is_production,
        workers=1,          # SQLite + single connection = single worker
    )