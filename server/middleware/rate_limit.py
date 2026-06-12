from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

# ── LIMITER INSTANCE ──────────────────────────────────────────────────────────
# key_func: rate limit per real client IP.
# When sitting behind Cloudflare, the real IP is in X-Forwarded-For.
# slowapi reads that header automatically via get_remote_address.

limiter = Limiter(key_func=get_remote_address)


# ── PER-ENDPOINT LIMIT STRINGS ────────────────────────────────────────────────
# Defined here so routers import from one place — change limits without
# touching route handlers.

LIMIT_LIST   = "60/minute"   # GET /mps  — bulk, cacheable, relatively cheap
LIMIT_DETAIL = "30/minute"   # GET /mps/{id} — heavier, dossier page
LIMIT_STATS  = "20/minute"   # GET /stats — cached at Cloudflare anyway


# ── ERROR HANDLER ─────────────────────────────────────────────────────────────

async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Returns a clean JSON 429 instead of slowapi's default plain-text response.
    Includes Retry-After so clients can back off gracefully.
    """
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "detail": f"Too many requests. Limit: {exc.limit}",
        },
        headers={"Retry-After": "60"},
    )