from __future__ import annotations

import math
import re
from dataclasses import dataclass


def split_section_codes(raw: str | None) -> list[str]:
    """Mirrors the JS splitSectionCodes() so section grouping agrees
    between frontend pill rendering and backend scoring."""
    if not raw:
        return []
    parts = re.split(r"[,/]| and ", raw)
    return [p.strip().upper() for p in parts if p.strip()]


def score_case(section_codes: list[str], weights: dict[str, float]) -> float:
    """Step 3A: a case's score is its WORST section, not a sum — one
    minor tag-along section shouldn't dilute a murder charge, and it
    shouldn't inflate it either."""
    if not section_codes:
        return 0.0
    return max(weights.get(code, weights.get("__default__", 5.0)) for code in section_codes)


def score_mp(case_scores: list[float], k: float = 12.0) -> float:
    """Step 3B: worst case sets the floor; additional cases add a
    shrinking bonus via log so volume can't out-rank one severe case,
    but repeat offenders still rank above a one-off."""
    if not case_scores:
        return 0.0
    sorted_scores = sorted(case_scores, reverse=True)
    w_max = sorted_scores[0]
    tail_sum = sum(sorted_scores[1:])
    return w_max + k * math.log1p(tail_sum)


@dataclass(frozen=True)
class MpScore:
    myneta_id: int
    raw_score: float


def compute_percentiles(scores: list[MpScore]) -> dict[int, int]:
    """
    Step 4: midpoint-rank percentile among MPs-with-cases only.
    Returns {myneta_id: percentile_int}, clamped to [1, 99].
    """
    if not scores:
        return {}

    values = sorted(s.raw_score for s in scores)
    n = len(values)
    result: dict[int, int] = {}

    for s in scores:
        less = sum(1 for v in values if v < s.raw_score)
        equal = sum(1 for v in values if v == s.raw_score)
        pct = (less + 0.5 * equal) / n * 100
        result[s.myneta_id] = max(1, min(99, round(pct)))

    return result