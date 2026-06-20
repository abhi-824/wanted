#!/usr/bin/env python3
"""
Load IPC/BNS section descriptions into netacheck.db.

Usage:
    python3 load_ipc_sections.py [--db ../server/netacheck.db] [--json ../data/ipc_sections.json]

Idempotent: re-running upserts on `section` (UNIQUE), so you can swap in
the full dataset later and just re-run this — existing rows get updated,
new ones inserted, nothing duplicated.

NOTE: this script DROPS and recreates ipc_sections on every run, so it's
safe to fix bad seed data by just re-running it. It is NOT meant to
preserve any manually-edited rows in this table.
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

SCHEMA = """
DROP TABLE IF EXISTS ipc_sections;

CREATE TABLE ipc_sections (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    section       TEXT NOT NULL UNIQUE,
    chapter       INTEGER,
    chapter_title TEXT,
    section_title TEXT NOT NULL,
    section_desc  TEXT NOT NULL
);
CREATE INDEX idx_ipc_sections_section ON ipc_sections(section);
"""

UPSERT_SQL = """
INSERT INTO ipc_sections (section, chapter, chapter_title, section_title, section_desc)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT(section) DO UPDATE SET
    chapter       = excluded.chapter,
    chapter_title = excluded.chapter_title,
    section_title = excluded.section_title,
    section_desc  = excluded.section_desc;
"""


def normalize_section(raw) -> str:
    """Section codes come from JSON as either int (135) or str ("171F").
    Always coerce to a stripped, uppercase string so the column has one
    consistent type/format and lookups like UPPER(section) = '171F' are
    reliable regardless of source formatting."""
    return str(raw).strip().upper()


def load(db_path: Path, json_path: Path) -> None:
    if not json_path.exists():
        print(f"ERROR: JSON file not found at {json_path}", file=sys.stderr)
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    if not isinstance(records, list):
        print("ERROR: expected a JSON array of section objects", file=sys.stderr)
        sys.exit(1)

    # NB: DB is opened normally (read-write) here, unlike the API which
    # opens it ?mode=ro. This script is the one piece allowed to write.
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)

        rows = []
        skipped = 0
        for rec in records:
            section_raw = rec.get("Section")
            if section_raw is None:
                section_raw = rec.get("section")

            section_title = (rec.get("section_title") or "").strip()
            section_desc = (rec.get("section_desc") or "").strip()

            if section_raw is None or section_raw == "" or not section_title or not section_desc:
                skipped += 1
                continue

            section = normalize_section(section_raw)
            if not section:
                skipped += 1
                continue

            rows.append((
                section,
                rec.get("chapter"),
                (rec.get("chapter_title") or "").strip() or None,
                section_title,
                section_desc,
            ))

        conn.executemany(UPSERT_SQL, rows)
        conn.commit()

        count = conn.execute("SELECT COUNT(*) FROM ipc_sections").fetchone()[0]
        print(f"Loaded/updated {len(rows)} section(s). Skipped {skipped} malformed record(s).")
        print(f"Total rows in ipc_sections table: {count}")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load IPC sections JSON into netacheck.db")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(__file__).parent.parent / "server" / "netacheck.db",
        help="Path to netacheck.db (default: ../server/netacheck.db relative to this script)",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=Path(__file__).parent.parent / "data" / "ipc_sections.json",
        help="Path to ipc_sections.json (default: ../data/ipc_sections.json)",
    )
    args = parser.parse_args()
    load(args.db, args.json)