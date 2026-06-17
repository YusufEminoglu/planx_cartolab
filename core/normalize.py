# -*- coding: utf-8 -*-
"""
Choropleth data-preparation transforms.

Pure-Python (no QGIS imports) so it is unit-testable headless. Every transform
returns a list aligned to the input, with ``None`` where an input value is
missing / non-finite (so the caller can leave those features unclassified).

Mapping a *count* straight onto a choropleth is the classic cartographic error
(it just re-draws population); these transforms turn raw fields into rates and
comparable standardised values.
"""
from __future__ import annotations

import math
from typing import List, Optional

METHODS = [
    ("Rate (numerator / denominator)", "rate"),
    ("Z-score (standardise)", "zscore"),
    ("Robust z-score (median / MAD)", "robust_z"),
    ("Min-max to 0-1", "minmax"),
    ("Percentile rank (0-100)", "percentile"),
    ("Log (base 10)", "log"),
]


def _finite(v) -> bool:
    try:
        return v is not None and math.isfinite(float(v))
    except (TypeError, ValueError):
        return False


def _clean(values) -> List[float]:
    return [float(v) for v in values if _finite(v)]


def mean(values) -> float:
    c = _clean(values)
    return sum(c) / len(c) if c else 0.0


def pstdev(values) -> float:
    c = _clean(values)
    if not c:
        return 0.0
    m = sum(c) / len(c)
    return math.sqrt(sum((v - m) ** 2 for v in c) / len(c))


def median(values) -> float:
    c = sorted(_clean(values))
    n = len(c)
    if n == 0:
        return 0.0
    mid = n // 2
    if n % 2:
        return c[mid]
    return (c[mid - 1] + c[mid]) / 2.0


def z_scores(values) -> List[Optional[float]]:
    m = mean(values)
    sd = pstdev(values)
    if sd == 0:
        return [0.0 if _finite(v) else None for v in values]
    return [((float(v) - m) / sd) if _finite(v) else None for v in values]


def robust_z(values) -> List[Optional[float]]:
    """Median-centred, MAD-scaled z (1.4826 makes MAD ~ stdev for normal data)."""
    med = median(values)
    abs_dev = [abs(float(v) - med) for v in values if _finite(v)]
    mad = median(abs_dev) if abs_dev else 0.0
    if mad == 0:
        return [0.0 if _finite(v) else None for v in values]
    scale = 1.4826 * mad
    return [((float(v) - med) / scale) if _finite(v) else None for v in values]


def min_max(values, lo: float = 0.0, hi: float = 1.0) -> List[Optional[float]]:
    c = _clean(values)
    if not c:
        return [None for _ in values]
    vmin, vmax = min(c), max(c)
    if vmax == vmin:
        return [lo if _finite(v) else None for v in values]
    span = vmax - vmin
    return [
        (lo + (float(v) - vmin) / span * (hi - lo)) if _finite(v) else None
        for v in values
    ]


def percentile_rank(values) -> List[Optional[float]]:
    """0-100 rank: pct of values below each, plus half the ties (mid-rank)."""
    c = _clean(values)
    n = len(c)
    if n == 0:
        return [None for _ in values]
    ordered = sorted(c)
    out: List[Optional[float]] = []
    for v in values:
        if not _finite(v):
            out.append(None)
            continue
        fv = float(v)
        below = sum(1 for x in ordered if x < fv)
        equal = sum(1 for x in ordered if x == fv)
        out.append(100.0 * (below + 0.5 * equal) / n)
    return out


def log_scale(values, base: float = 10.0) -> List[Optional[float]]:
    """Log transform; if any value <= 0 the whole series is shifted to be > 0."""
    c = _clean(values)
    if not c:
        return [None for _ in values]
    vmin = min(c)
    shift = 0.0
    if vmin <= 0:
        shift = -vmin + 1.0
    log_base = math.log(base)
    return [
        (math.log(float(v) + shift) / log_base) if _finite(v) else None
        for v in values
    ]


def rate(numerators, denominators, scale: float = 1.0) -> List[Optional[float]]:
    """Element-wise numerator/denominator * scale; None when either is bad or d==0."""
    out: List[Optional[float]] = []
    for num, den in zip(numerators, denominators):
        if not _finite(num) or not _finite(den) or float(den) == 0.0:
            out.append(None)
        else:
            out.append(float(num) / float(den) * scale)
    return out
