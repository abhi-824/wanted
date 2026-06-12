from __future__ import annotations
from dataclasses import dataclass, field
from pydantic import BaseModel, ConfigDict
from .cases import CriminalCase


# ── RESPONSE MODELS (wire-facing) ─────────────────────────────────────────────

class MPSummary(BaseModel):
    """
    Returned by GET /api/v1/mps (bulk list).
    Intentionally omits assets, liabilities, and cases — bulk responses
    should never be a scraping-friendly dump of the full dataset.
    """
    model_config = ConfigDict(from_attributes=True)

    myneta_id: int
    name: str
    constituency: str
    state: str
    party: str
    coalition: str | None = None
    age: int | None = None
    total_cases: int = 0
    serious_cases: int = 0


class MPDetail(BaseModel):
    """
    Returned by GET /api/v1/mps/{id} (single MP).
    Full profile including assets and nested criminal cases.
    Assets are only accessible via a deliberate per-MP fetch.
    """
    model_config = ConfigDict(from_attributes=True)

    # Identity (same as MPSummary)
    myneta_id: int
    name: str
    constituency: str
    state: str
    party: str
    coalition: str | None = None
    age: int | None = None
    total_cases: int = 0
    serious_cases: int = 0

    # Extended fields (not in MPSummary)
    education: str | None = None
    photo_url: str | None = None
    assets_inr: int | None = None
    liabilities_inr: int | None = None
    self_profession: str | None = None
    spouse_profession: str | None = None
    voter_constituency: str | None = None
    election: str | None = None
    scraped_at: str | None = None

    # Nested cases — empty list if clean record
    criminal_cases: list[CriminalCase] = []


# ── STATS MODELS ──────────────────────────────────────────────────────────────

class StateBucket(BaseModel):
    """One row in the top-states-by-cases breakdown."""
    state: str
    case_count: int


class StatsResponse(BaseModel):
    """Returned by GET /api/v1/stats."""
    total_mps: int
    with_cases: int
    with_serious_cases: int
    avg_assets_inr: int | None = None
    top_states_by_cases: list[StateBucket] = []


# ── INTERNAL FILTER DATACLASS (never touches the wire) ────────────────────────

@dataclass
class MpFilters:
    """
    Built from validated query params in the router, then passed to
    MpRepository.get_all(). Kept as a plain dataclass (not Pydantic) because
    it is an internal transport object, not a response model.
    """
    state: str | None = None
    party: str | None = None
    q: str | None = None        # searches name + constituency (LIKE %q%)
    limit: int = 100
    offset: int = 0