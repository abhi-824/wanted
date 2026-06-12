from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from db import Database, MpRepository, get_db
from models.mp import StatsResponse, StateBucket
from middleware.rate_limit import limiter, LIMIT_STATS

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
@limiter.limit(LIMIT_STATS)
async def get_stats(
    request: Request,
    db:      Database = Depends(get_db),
) -> StatsResponse:
    """
    Aggregate summary stats for the index.html header strip:
    - total MPs in dataset
    - MPs with at least one pending case
    - MPs with at least one serious case
    - Average declared assets (INR)
    - Top 10 states by total case count

    This endpoint is safe to cache aggressively at Cloudflare (TTL 1hr+)
    since the underlying data only changes when a new scrape runs.
    """
    repo = MpRepository(db)

    # Two queries — both cheap, no N+1
    agg_row         = await repo.get_stats()
    top_state_rows  = await repo.get_top_states_by_cases(limit=10)

    top_states = [StateBucket(**row) for row in top_state_rows]

    return StatsResponse(
        total_mps           = agg_row.get("total_mps", 0),
        with_cases          = agg_row.get("with_cases", 0),
        with_serious_cases  = agg_row.get("with_serious_cases", 0),
        avg_assets_inr      = agg_row.get("avg_assets_inr"),
        top_states_by_cases = top_states,
    )