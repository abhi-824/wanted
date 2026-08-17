from __future__ import annotations

# Manual floor/override weights for sections where sample size in your own
# data is too thin to trust a derived pct_serious (see query 5 from earlier —
# run it, and add anything with total_occurrences < 5 that you recognize as
# obviously heinous here). Scale: 1-100.
MANUAL_OVERRIDES: dict[str, float] = {
    "302":  100,  # murder
    "303":  100,  # murder by life-convict
    "304":   90,  # culpable homicide not amounting to murder
    "304B":  95,  # dowry death
    "376":  100,  # rape
    "376D": 100,  # gang rape
    "364A": 95,   # kidnapping for ransom
    "307":  70,   # attempt to murder
    "395":  55,   # dacoity
    "121":  90,   # waging war against the state
    # add more as you find them in query 5's output
}

DEFAULT_WEIGHT = 5.0        # fallback for a section we've never seen
MIN_SAMPLE_FOR_DERIVED = 5  # below this, prefer MANUAL_OVERRIDES or default
WEIGHT_FLOOR = 5.0
WEIGHT_CEILING = 100.0


def derive_weight(pct_serious: float, occurrences: int, section: str) -> float:
    """
    Step-1 math: turn "what fraction of this section's cases were flagged
    is_serious" into a 5-100 weight. Manual overrides win outright (used
    for rare-but-obviously-severe sections where the sample is too small
    to trust). Otherwise scale the fraction into the weight range.
    """
    section = section.upper()
    if section in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[section]

    if occurrences < MIN_SAMPLE_FOR_DERIVED:
        # Not enough data to trust pct_serious, and no manual override —
        # treat as a low-severity procedural section by default rather
        # than let a 1-case 100%/0% skew things.
        return DEFAULT_WEIGHT

    weight = WEIGHT_FLOOR + pct_serious * (WEIGHT_CEILING - WEIGHT_FLOOR)
    return round(weight, 1)