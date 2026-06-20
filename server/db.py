from __future__ import annotations

import aiosqlite
from dataclasses import dataclass, field
from typing import Any

from config import get_settings
from models.mp import MpFilters

# Type alias — raw row from sqlite, always dict after row_factory is set
DBRow = dict[str, Any]


# ── CONNECTION POOL ───────────────────────────────────────────────────────────

class Database:
    """
    Thin wrapper around aiosqlite.
    One shared connection opened at startup, closed at shutdown.
    Opened in read-only mode via URI — the DB file can never be
    written to through this connection, even if a bug slips through.
    """

    def __init__(self) -> None:
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        settings = get_settings()
        # ?mode=ro  — read-only at the SQLite URI level
        # check_same_thread=False is required for async use
        uri = f"file:{settings.db_path}?mode=ro"
        self._conn = await aiosqlite.connect(uri, uri=True)
        self._conn.row_factory = aiosqlite.Row
        # journal_mode and foreign_keys are write-level PRAGMAs —
        # not compatible with ?mode=ro. WAL should be set once when
        # the DB is first created by your scraper, not here.

    async def disconnect(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database.connect() has not been called")
        return self._conn


# Module-level singleton — imported by routers via get_db()
_db = Database()


async def get_db() -> Database:
    """FastAPI dependency. Returns the shared Database instance."""
    return _db


async def startup() -> None:
    await _db.connect()


async def shutdown() -> None:
    await _db.disconnect()


# ── MP REPOSITORY ─────────────────────────────────────────────────────────────

class MpRepository:
    """
    All queries against the `mps` table.
    Accepts a Database instance — easy to swap for a test fake.
    Every query uses ? placeholders. No f-string SQL, ever.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    async def get_all(self, filters: MpFilters) -> list[DBRow]:
        """
        Bulk fetch with optional state / party / free-text filters.
        Returns MPSummary-shaped rows (no assets, no liabilities).
        """
        clauses: list[str] = []
        params: list[Any] = []

        if filters.state:
            clauses.append("m.state = ?")
            params.append(filters.state)

        if filters.party:
            clauses.append("m.party = ?")
            params.append(filters.party)

        if filters.q:
            # Search name OR constituency, case-insensitive
            clauses.append("(m.name LIKE ? OR m.constituency LIKE ?)")
            like = f"%{filters.q}%"
            params.extend([like, like])

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

        # Explicit column list — never SELECT *, never expose assets here
        sql = f"""
            SELECT
                m.myneta_id,
                m.name,
                m.constituency,
                m.state,
                m.party,
                m.coalition,
                m.age,
                COALESCE(m.total_cases, 0)   AS total_cases,
                COALESCE(m.serious_cases, 0) AS serious_cases
            FROM mps m
            {where}
            ORDER BY m.name
            LIMIT ? OFFSET ?
        """
        params.extend([filters.limit, filters.offset])

        async with self._db.conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_by_id(self, myneta_id: int) -> DBRow | None:
        """
        Full row for a single MP, including assets.
        Used only by the /mps/{id} endpoint.
        """
        sql = """
            SELECT
                m.myneta_id,
                m.name,
                m.constituency,
                m.state,
                m.party,
                m.coalition,
                m.age,
                m.education,
                m.photo_url,
                m.assets_inr,
                m.liabilities_inr,
                m.self_profession,
                m.spouse_profession,
                m.voter_constituency,
                m.election,
                m.scraped_at,
                COALESCE(m.total_cases, 0)   AS total_cases,
                COALESCE(m.serious_cases, 0) AS serious_cases
            FROM mps m
            WHERE m.myneta_id = ?
            LIMIT 1
        """
        async with self._db.conn.execute(sql, [myneta_id]) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_stats(self) -> DBRow:
        """
        Aggregates for the /stats endpoint.
        Single query — no N+1.
        """
        sql = """
            SELECT
                COUNT(*)                                        AS total_mps,
                SUM(CASE WHEN total_cases > 0 THEN 1 ELSE 0 END)   AS with_cases,
                SUM(CASE WHEN serious_cases > 0 THEN 1 ELSE 0 END) AS with_serious_cases,
                CAST(AVG(assets_inr) AS INTEGER)                AS avg_assets_inr
            FROM mps
        """
        async with self._db.conn.execute(sql) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {}

    async def get_top_states_by_cases(self, limit: int = 10) -> list[DBRow]:
        sql = """
            SELECT
                state,
                SUM(total_cases) AS case_count
            FROM mps
            GROUP BY state
            ORDER BY case_count DESC
            LIMIT ?
        """
        async with self._db.conn.execute(sql, [limit]) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def list_constituencies(self) -> list[str]:
        """Used by index.html's constituency search dropdown."""
        sql = "SELECT constituency FROM mps ORDER BY constituency"
        async with self._db.conn.execute(sql) as cursor:
            rows = await cursor.fetchall()
            return [r["constituency"] for r in rows]


# ── CASE REPOSITORY ───────────────────────────────────────────────────────────

class CaseRepository:
    """All queries against the `criminal_cases` table."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def get_by_mp_id(self, myneta_id: int) -> list[DBRow]:
        sql = """
            SELECT
                id,
                serial_no,
                fir_no,
                case_no,
                court,
                ipc_sections,
                other_acts,
                charges_framed,
                charge_date,
                is_serious
            FROM criminal_cases
            WHERE mp_myneta_id = ?
            ORDER BY is_serious DESC, id ASC
        """
        async with self._db.conn.execute(sql, [myneta_id]) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

IPC_SECTIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS ipc_sections (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    section       TEXT NOT NULL UNIQUE,   -- e.g. "171F", "302", "420"
    chapter       INTEGER,
    chapter_title TEXT,
    section_title TEXT NOT NULL,
    section_desc  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ipc_sections_section ON ipc_sections(section);
"""


class IpcSectionRepository:
    """Read-only lookup repository for IPC/BNS section descriptions.
    Mirrors MpRepository/CaseRepository: takes the shared Database
    instance and goes through self._db.conn, not a raw connection
    passed in directly."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def get_by_section(self, section: str) -> DBRow | None:
        """Fetch a single section by its code. Case/whitespace tolerant —
        e.g. ' 171f ' and '171F' both resolve."""
        normalized = section.strip().upper()
        sql = (
            "SELECT section, chapter, chapter_title, section_title, section_desc "
            "FROM ipc_sections WHERE UPPER(section) = ?"
        )
        async with self._db.conn.execute(sql, [normalized]) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_many(self, sections: list[str]) -> list[DBRow]:
        """Batch fetch — used so the frontend can resolve every section in
        a case's `ipc_sections` string with a single round trip instead of
        N calls per case."""
        normalized = [s.strip().upper() for s in sections if s.strip()]
        if not normalized:
            return []
        placeholders = ",".join("?" for _ in normalized)
        sql = (
            f"SELECT section, chapter, chapter_title, section_title, section_desc "
            f"FROM ipc_sections WHERE UPPER(section) IN ({placeholders})"
        )
        async with self._db.conn.execute(sql, normalized) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# ── Helper for parsing the free-text ipc_sections column ────────────────
def parse_ipc_sections_string(raw: str | None) -> list[str]:
    """criminal_cases.ipc_sections is a raw comma/space-separated string
    like "188, 171A" or "302 307". Split it into individual codes the
    same way for both backend batch lookups and any server-side rendering."""
    if not raw:
        return []
    import re
    return [s.strip() for s in re.split(r"[,/]| and ", raw) if s.strip()]