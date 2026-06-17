# -*- coding: utf-8 -*-
"""
Dot-density scatter engine.

Pure-Python (no QGIS imports) so it is unit-testable headless and gives the
Processing algorithm a deterministic, hole-aware dot placer.

  - ``dots_for_value``  : how many dots represent a value at a given dots-per-unit
  - ``point_in_polygon``: even-odd ray cast over all rings (holes excluded)
  - ``generate_dots``   : seeded rejection sampling of dots inside a polygon
"""
from __future__ import annotations

import math
import random
from typing import List, Sequence, Tuple

Ring = Sequence[Tuple[float, float]]


def dots_for_value(value, value_per_dot: float, rounding: str = "round") -> int:
    """Number of dots that represent ``value`` when each dot is ``value_per_dot``.

    Non-positive / missing values and a non-positive dot weight yield 0 dots.
    """
    if value is None or value_per_dot is None or value_per_dot <= 0:
        return 0
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0
    if not math.isfinite(v) or v <= 0:
        return 0
    raw = v / float(value_per_dot)
    if rounding == "floor":
        return int(math.floor(raw))
    if rounding == "ceil":
        return int(math.ceil(raw))
    return int(round(raw))


def point_in_polygon(rings: Sequence[Ring], x: float, y: float) -> bool:
    """Even-odd ray-cast containment test across an exterior ring plus holes.

    ``rings[0]`` is the exterior; any further rings are holes. Because the parity
    is accumulated across every edge of every ring, a point falling inside a hole
    correctly reports as *outside* the polygon.
    """
    inside = False
    for ring in rings:
        n = len(ring)
        if n < 3:
            continue
        j = n - 1
        for i in range(n):
            xi, yi = ring[i]
            xj, yj = ring[j]
            if (yi > y) != (yj > y):
                x_cross = (xj - xi) * (y - yi) / (yj - yi) + xi
                if x < x_cross:
                    inside = not inside
            j = i
    return inside


def generate_dots(
    rings: Sequence[Ring],
    bbox: Tuple[float, float, float, float],
    count: int,
    seed: int = 0,
    max_attempts_factor: int = 40,
) -> List[Tuple[float, float]]:
    """Place ``count`` dots uniformly at random inside the polygon.

    Deterministic for a given ``seed`` (so re-runs and cross-process renders are
    identical). Uses rejection sampling against :func:`point_in_polygon`; if the
    polygon is a thin sliver the attempt budget caps the result rather than
    looping forever.
    """
    if count <= 0:
        return []
    xmin, ymin, xmax, ymax = bbox
    if xmax <= xmin or ymax <= ymin:
        return []
    rng = random.Random(seed)
    pts: List[Tuple[float, float]] = []
    max_attempts = max(count * max_attempts_factor, 2000)
    attempts = 0
    while len(pts) < count and attempts < max_attempts:
        attempts += 1
        x = rng.uniform(xmin, xmax)
        y = rng.uniform(ymin, ymax)
        if point_in_polygon(rings, x, y):
            pts.append((x, y))
    return pts
