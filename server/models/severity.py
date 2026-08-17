from __future__ import annotations

from pydantic import BaseModel


class SeverityRecomputeResponse(BaseModel):
    mps_scored: int
    mps_cleared: int
    sections_seen: int
    triggered_at: str