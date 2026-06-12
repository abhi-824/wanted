from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from db import Database, MpRepository, CaseRepository, get_db
from models.mp import MPSummary, MPDetail, MpFilters
from models.cases import CriminalCase
from middleware.rate_limit import limiter, LIMIT_LIST, LIMIT_DETAIL

router = APIRouter(prefix="/api/v1/mps", tags=["mps"])


# ── GET /api/v1/mps ───────────────────────────────────────────────────────────

@router.get("", response_model=list[MPSummary])
@limiter.limit(LIMIT_LIST)
async def list_mps(
    request: Request,                           # required by slowapi
    state:   str | None = Query(None, max_length=100),
    party:   str | None = Query(None, max_length=100),
    q:       str | None = Query(None, min_length=2, max_length=100),
    limit:   int        = Query(100, ge=1, le=200),
    offset:  int        = Query(0, ge=0),
    db:      Database   = Depends(get_db),
) -> list[MPSummary]:
    """
    Bulk MP list. Used by parliament.html (all MPs) and index.html (search).

    Query params:
    - state  : filter by state name (exact match)
    - party  : filter by party abbreviation (exact match)
    - q      : free-text search on name + constituency (min 2 chars)
    - limit  : max results, capped at 200
    - offset : pagination offset

    Does NOT return assets or criminal cases — use /mps/{id} for those.
    """
    filters = MpFilters(
        state=state,
        party=party,
        q=q,
        limit=limit,
        offset=offset,
    )
    repo = MpRepository(db)
    rows = await repo.get_all(filters)
    return [MPSummary(**row) for row in rows]


# ── GET /api/v1/mps/constituencies ────────────────────────────────────────────

@router.get("/constituencies", response_model=list[str])
@limiter.limit(LIMIT_LIST)
async def list_constituencies(
    request: Request,
    db:      Database = Depends(get_db),
) -> list[str]:
    """
    Flat sorted list of all constituency names.
    Powers the autocomplete dropdown in index.html.
    Replaces the constituencies.json file fetch.
    """
    repo = MpRepository(db)
    return await repo.list_constituencies()


# ── GET /api/v1/mps/{id} ──────────────────────────────────────────────────────

@router.get("/{myneta_id}", response_model=MPDetail)
@limiter.limit(LIMIT_DETAIL)
async def get_mp(
    request:   Request,
    myneta_id: int,
    db:        Database = Depends(get_db),
) -> MPDetail:
    """
    Full MP profile including assets and nested criminal cases.
    Used by dossier.html.

    - Assets are only reachable through this per-MP endpoint.
    - Criminal cases are ordered: serious first, then by id.
    - Returns 404 if myneta_id not found.
    """
    mp_repo   = MpRepository(db)
    case_repo = CaseRepository(db)

    mp_row = await mp_repo.get_by_id(myneta_id)
    if mp_row is None:
        raise HTTPException(status_code=404, detail=f"MP {myneta_id} not found")

    case_rows = await case_repo.get_by_mp_id(myneta_id)
    cases = [CriminalCase(**row) for row in case_rows]

    return MPDetail(**mp_row, criminal_cases=cases)