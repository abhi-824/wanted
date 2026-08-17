from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException

from config import get_settings
from db import (
    Database,
    WritableDatabase,
    SeverityRepository,
    SeverityWriter,
    get_db,
    get_writable_db,
)
from models.severity import SeverityRecomputeResponse
from severity_weights import derive_weight, DEFAULT_WEIGHT
from services.severity import (
    split_section_codes,
    score_case,
    score_mp,
    compute_percentiles,
    MpScore,
)

router = APIRouter(prefix="/api/v1/severity", tags=["severity"])


def verify_cron_secret(x_cron_secret: str = Header(...)) -> None:
    """Simple shared-secret gate. This endpoint WRITES to the mps table
    and your CORS middleware only restricts allow_methods=['GET'] for
    browser calls — server-to-server POSTs (cron) bypass CORS entirely,
    so this header check is the actual protection, not CORS."""
    settings = get_settings()
    if x_cron_secret != settings.cron_secret:
        raise HTTPException(status_code=403, detail="Invalid cron secret")


@router.post("/recompute", response_model=SeverityRecomputeResponse)
async def recompute_severity(
    db: Database = Depends(get_db),
    wdb: WritableDatabase = Depends(get_writable_db),
    _: None = Depends(verify_cron_secret),
) -> SeverityRecomputeResponse:
    """
    Full pipeline, Steps 1-4. Call this from cron after any data refresh
    (new ADR affidavit scrape), not on a fixed schedule faster than the
    underlying data changes — there's no reason to re-run this nightly
    if criminal_cases hasn't been touched.

    Reads go through the shared read-only `db` (SeverityRepository).
    Writes go through a separate writable connection (`wdb`, via
    SeverityWriter) opened just for this request and closed after —
    the shared connection is ?mode=ro on purpose and cannot write.
    """
    repo = SeverityRepository(db)
    writer = SeverityWriter(wdb)

    # Step 1 — build weight table from current data
    section_stats = await repo.get_section_stats()
    weights: dict[str, float] = {"__default__": DEFAULT_WEIGHT}
    for row in section_stats:
        weights[row["section_code"]] = derive_weight(
            pct_serious=row["pct_serious"] or 0.0,
            occurrences=row["total_occurrences"],
            section=row["section_code"],
        )

    # Step 3 — score every case, then roll up into a raw score per MP
    case_rows = await repo.get_cases_by_mp()
    scores_by_mp: dict[int, list[float]] = {}
    for row in case_rows:
        codes = split_section_codes(row["ipc_sections"])
        if not codes:
            continue
        case_score = score_case(codes, weights)
        scores_by_mp.setdefault(row["mp_myneta_id"], []).append(case_score)

    mp_raw_scores = [
        MpScore(myneta_id=mp_id, raw_score=score_mp(case_scores))
        for mp_id, case_scores in scores_by_mp.items()
    ]

    # Step 4 — percentile among MPs-with-cases only
    percentiles = compute_percentiles(mp_raw_scores)

    results = [
        {
            "myneta_id": s.myneta_id,
            "raw_score": s.raw_score,
            "percentile": percentiles[s.myneta_id],
        }
        for s in mp_raw_scores
    ]

    written = await writer.write_scores(results)
    cleared = await writer.clear_scores_for_clean_mps()

    return SeverityRecomputeResponse(
        mps_scored=written,
        mps_cleared=cleared,
        sections_seen=len(section_stats),
        triggered_at=datetime.now(timezone.utc).isoformat(),
    )