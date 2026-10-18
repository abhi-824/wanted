#!/usr/bin/env python3
"""
Load PRS Legislative Research MPTrack CSV into netacheck.db.

Usage:
    python3 load_mp_track.py [--db ../server/netacheck.db] [--csv ../data/MPTrackData.csv]

NOTE: this script DROPS and recreates mp_track_record on every run.
"""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# --- SCHEMA ---

SCHEMA = """
DROP TABLE IF EXISTS mp_track_record;

CREATE TABLE mp_track_record (
    prs_id                  INTEGER PRIMARY KEY,
    mp_myneta_id            INTEGER REFERENCES mps(myneta_id),
    name                    TEXT NOT NULL,
    constituency            TEXT NOT NULL,
    state                   TEXT NOT NULL,
    party                   TEXT,
    gender                  TEXT,
    age                     INTEGER,
    house                   TEXT,
    membership_type         TEXT,
    term_label              TEXT,
    term_number             INTEGER,
    term_start              TEXT,
    term_end                TEXT,
    in_office               INTEGER NOT NULL,
    education_level         TEXT,
    education_details       TEXT,
    attendance              REAL,
    debates                 INTEGER,
    questions               INTEGER,
    private_member_bills    INTEGER,
    national_avg_attendance REAL,
    national_avg_debates    REAL,
    national_avg_questions  REAL,
    national_avg_pmb        REAL,
    state_avg_attendance    REAL,
    state_avg_debates       REAL,
    state_avg_questions     REAL,
    state_avg_pmb           REAL,
    note                    TEXT,
    data_period_start       TEXT,
    data_period_end         TEXT,
    source                  TEXT NOT NULL DEFAULT 'PRS Legislative Research MPTrack',
    loaded_at               TEXT NOT NULL
);

CREATE UNIQUE INDEX idx_mp_track_myneta_id
    ON mp_track_record(mp_myneta_id)
    WHERE mp_myneta_id IS NOT NULL;
"""

INSERT_SQL = """
INSERT INTO mp_track_record (
    prs_id, mp_myneta_id,
    name, constituency, state, party, gender, age, house, membership_type,
    term_label, term_number, term_start, term_end, in_office,
    education_level, education_details,
    attendance, debates, questions, private_member_bills,
    national_avg_attendance, national_avg_debates, national_avg_questions, national_avg_pmb,
    state_avg_attendance, state_avg_debates, state_avg_questions, state_avg_pmb,
    note, data_period_start, data_period_end, source, loaded_at
) VALUES (
    ?, ?,
    ?, ?, ?, ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?,
    ?, ?,
    ?, ?, ?, ?,
    ?, ?, ?, ?,
    ?, ?, ?, ?,
    ?, ?, ?, ?, ?
);
"""

# --- PARSING ---

TERM_ORDINALS: dict[str, int] = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
}

DATA_PERIOD_RE = re.compile(
    r"from\s+(\d{2}-\d{2}-\d{4})\s+to\s+(\d{2}-\d{2}-\d{4})",
    re.IGNORECASE,
)


def _strip(value: str | None) -> str:
    return (value or "").strip()


def parse_term_number(term_label: str) -> int | None:
    label = _strip(term_label)
    if not label:
        return None
    first = label.split()[0].lower()
    return TERM_ORDINALS.get(first)


def parse_dd_mm_yyyy(raw: str) -> str | None:
    text = _strip(raw)
    if not text or text.lower() == "in office":
        return None
    try:
        day, month, year = text.split("-")
        return f"{year}-{month}-{day}"
    except ValueError:
        return None


def parse_na_real(raw: str) -> float | None:
    text = _strip(raw)
    if not text or text.upper() == "NA":
        return None
    return float(text)


def parse_na_int(raw: str) -> int | None:
    text = _strip(raw)
    if not text or text.upper() == "NA":
        return None
    return int(float(text))


def parse_age(raw: str) -> int | None:
    text = _strip(raw)
    if not text or text.upper() == "NA":
        return None
    return int(text)


def parse_data_period(note: str) -> tuple[str | None, str | None]:
    match = DATA_PERIOD_RE.search(note or "")
    if not match:
        return None, None
    return parse_dd_mm_yyyy(match.group(1)), parse_dd_mm_yyyy(match.group(2))


def row_to_tuple(row: dict[str, str], loaded_at: str) -> tuple:
    term_end_raw = _strip(row.get("term_end_date"))
    in_office = 1 if term_end_raw.lower() == "in office" else 0
    note = _strip(row.get("mp_note"))
    period_start, period_end = parse_data_period(note)

    return (
        int(_strip(row["mp_election_index"])),
        None,  # mp_myneta_id — linked in a later pipeline step if needed
        _strip(row.get("mp_name")),
        _strip(row.get("pc_name")),
        _strip(row.get("state")),
        _strip(row.get("mp_political_party")) or None,
        _strip(row.get("mp_gender")) or None,
        parse_age(row.get("mp_age", "")),
        _strip(row.get("mp_house")) or None,
        _strip(row.get("nature_membership")) or None,
        _strip(row.get("term")) or None,
        parse_term_number(row.get("term", "")),
        parse_dd_mm_yyyy(row.get("term_start_date", "")),
        parse_dd_mm_yyyy(term_end_raw),
        in_office,
        _strip(row.get("educational_qualification")) or None,
        _strip(row.get("educational_qualification_details")) or None,
        parse_na_real(row.get("attendance", "")),
        parse_na_int(row.get("debates", "")),
        parse_na_int(row.get("questions", "")),
        parse_na_int(row.get("private_member_bills", "")),
        parse_na_real(row.get("attendance_national_average", "")),
        parse_na_real(row.get("national_average_debate", "")),
        parse_na_real(row.get("national_average_questions", "")),
        parse_na_real(row.get("national_average_pmb", "")),
        parse_na_real(row.get("attendance_state_average", "")),
        parse_na_real(row.get("state_average_debate", "")),
        parse_na_real(row.get("state_average_questions", "")),
        parse_na_real(row.get("state_average_pmb", "")),
        note or None,
        period_start,
        period_end,
        "PRS Legislative Research MPTrack",
        loaded_at,
    )


# --- LOAD ---

def load(db_path: Path, csv_path: Path) -> None:
    if not csv_path.exists():
        print(f"ERROR: CSV file not found at {csv_path}", file=sys.stderr)
        sys.exit(1)

    if not db_path.exists():
        print(f"ERROR: database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    loaded_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = list(reader)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA)

        rows = [row_to_tuple(rec, loaded_at) for rec in records]
        conn.executemany(INSERT_SQL, rows)
        conn.commit()

        count = conn.execute("SELECT COUNT(*) FROM mp_track_record").fetchone()[0]
        ministers = conn.execute(
            "SELECT COUNT(*) FROM mp_track_record WHERE attendance IS NULL AND debates IS NULL"
        ).fetchone()[0]
        print(f"Loaded {len(rows)} MPTrack row(s) into mp_track_record.")
        print(f"Total rows in mp_track_record: {count}")
        print(f"Rows with NULL participation metrics (ministers / Speaker / LoP): {ministers}")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load PRS MPTrack CSV into netacheck.db")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(__file__).parent.parent / "server" / "netacheck.db",
        help="Path to netacheck.db (default: ../server/netacheck.db relative to this script)",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(__file__).parent.parent / "data" / "MPTrackData.csv",
        help="Path to MPTrackData.csv (default: ../data/MPTrackData.csv)",
    )
    args = parser.parse_args()
    load(args.db, args.csv)
