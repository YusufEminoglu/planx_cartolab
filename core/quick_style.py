# -*- coding: utf-8 -*-
"""
Classification helpers for Quick Style.

Pure logic (no ``qgis`` import): compute class-break edges for graduated
rendering. Returns ``n + 1`` monotonic edges ``[min, ..., max]`` so callers can
pair them into ``n`` ranges. The geometric-interval method lives in
``bivariate_engine``; this module adds quantile and equal-interval.
"""
from __future__ import annotations

import math
from typing import List

QUANTILE = "quantile"
EQUAL = "equal"
GEOMETRIC = "geometric"


def _clean(values) -> List[float]:
    return sorted(float(v) for v in values if v is not None)


def quantile_breaks(values, n: int) -> List[float]:
    """``n + 1`` edges placing an equal count of features in each class."""
    xs = _clean(values)
    if not xs or n < 1:
        return []
    if xs[0] == xs[-1]:
        return [xs[0], xs[-1]]
    edges = [xs[0]]
    last = len(xs) - 1
    for i in range(1, n):
        idx = (i / n) * last
        lo = int(math.floor(idx))
        hi = min(lo + 1, last)
        frac = idx - lo
        edges.append(xs[lo] + (xs[hi] - xs[lo]) * frac)
    edges.append(xs[-1])
    return edges


def equal_interval_breaks(values, n: int) -> List[float]:
    """``n + 1`` evenly-spaced edges between the data min and max."""
    xs = _clean(values)
    if not xs or n < 1:
        return []
    lo, hi = xs[0], xs[-1]
    if lo == hi:
        return [lo, hi]
    return [lo + (hi - lo) * i / n for i in range(n + 1)]


def dedupe_edges(edges: List[float]) -> List[float]:
    """Drop consecutive duplicate edges so no zero-width class is produced."""
    out: List[float] = []
    for e in edges:
        if not out or e > out[-1]:
            out.append(e)
    return out


def edges_to_ranges(edges):
    """Turn ``n + 1`` edges into ``n`` ``(lower, upper)`` pairs."""
    clean = dedupe_edges(edges)
    return [(clean[i], clean[i + 1]) for i in range(len(clean) - 1)]
