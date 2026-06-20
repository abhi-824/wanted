"""
Pydantic models for IPC/BNS section descriptions.

These power a pure lookup table — no relation to mps/criminal_cases at the
DB level. The link is made client-side / at query-time by splitting a
criminal_case's free-text `ipc_sections` string (e.g. "188, 171A") and
fetching each one here.
"""

from pydantic import BaseModel, Field


class IpcSection(BaseModel):
    section: str = Field(..., description="Section number/code, e.g. '171F'")
    chapter: int | None = Field(None, description="IPC chapter number")
    chapter_title: str | None = Field(None, description="IPC chapter heading")
    section_title: str = Field(..., description="Short title of the section")
    section_desc: str = Field(..., description="Plain-language description of the offence")

    class Config:
        from_attributes = True


class IpcSectionBatchResponse(BaseModel):
    """Response for batch lookups — keyed by section so the frontend can
    do O(1) lookups per case without re-matching order."""
    sections: dict[str, IpcSection]
    not_found: list[str] = Field(default_factory=list)