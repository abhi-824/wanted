from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from db import Database, IpcSectionRepository, parse_ipc_sections_string, get_db
from models.ipc import IpcSection, IpcSectionBatchResponse

router = APIRouter(prefix="/api/v1/ipc", tags=["ipc"])


@router.get("/{section}", response_model=IpcSection)
async def get_ipc_section(section: str, db: Database = Depends(get_db)):
    """Single section lookup, e.g. GET /api/v1/ipc/171F"""
    repo = IpcSectionRepository(db)
    row = await repo.get_by_section(section)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Unknown section '{section}'")
    return IpcSection(**row)


@router.get("", response_model=IpcSectionBatchResponse)
async def get_ipc_sections_batch(
    sections: str = Query(
        ...,
        description="Comma-separated section codes, e.g. '188,171A,302'.",
    ),
    db: Database = Depends(get_db),
):
    repo = IpcSectionRepository(db)
    codes = parse_ipc_sections_string(sections)
    rows = await repo.get_many(codes)

    found = {row["section"].upper(): IpcSection(**row) for row in rows}
    not_found = [c for c in codes if c.strip().upper() not in found]

    return IpcSectionBatchResponse(sections=found, not_found=not_found)