# -*- coding: utf-8 -*-
"""
Pure-logic helpers for print-layout automation.

Kept free of any ``qgis`` import so the numeric behaviour (nice grid
intervals, non-colliding names, page geometry) can be unit-tested outside
QGIS. The QGIS-touching layout code lives in the ``layout`` package.
"""
from __future__ import annotations

import math
from typing import Iterable, Tuple

# ISO A-series page sizes in millimetres (portrait: width, height).
PAGE_SIZES_MM = {
    "A4": (210.0, 297.0),
    "A3": (297.0, 420.0),
    "A2": (420.0, 594.0),
    "A1": (594.0, 841.0),
    "A0": (841.0, 1189.0),
}


def nice_number(value: float, round_down: bool = True) -> float:
    """
    Return a "nice" number approximately equal to ``value``.

    Implements Heckbert's *Nice Numbers for Graph Labels*: snap to the
    nearest 1/2/5 × 10ⁿ. With ``round_down`` the nearest nice value is
    returned; otherwise the smallest nice value ``>= value`` is returned.
    """
    if value <= 0 or not math.isfinite(value):
        return 0.0
    exp = math.floor(math.log10(value))
    frac = value / (10 ** exp)
    if round_down:
        if frac < 1.5:
            nice = 1.0
        elif frac < 3.0:
            nice = 2.0
        elif frac < 7.0:
            nice = 5.0
        else:
            nice = 10.0
    else:
        if frac <= 1.0:
            nice = 1.0
        elif frac <= 2.0:
            nice = 2.0
        elif frac <= 5.0:
            nice = 5.0
        else:
            nice = 10.0
    return nice * (10 ** exp)


def nice_interval(span: float, target_divisions: int = 8) -> float:
    """
    Choose a rounded grid interval that splits ``span`` into roughly
    ``target_divisions`` parts.

    Works at any scale (metres, feet or degrees) because it derives the
    interval from the data span rather than a fixed constant — a graticule
    over a 5 km city and one over a 0.05° window both get sensible lines.
    Returns ``0.0`` for a non-positive or non-finite span so callers can
    fall back gracefully.
    """
    if span <= 0 or not math.isfinite(span) or target_divisions < 1:
        return 0.0
    return nice_number(span / float(target_divisions), round_down=True)


def unique_name(existing: Iterable[str], base: str) -> str:
    """
    Return ``base`` if unused, otherwise ``base 2``, ``base 3`` … so a new
    layout never silently overwrites an existing one of the same name.
    """
    taken = set(existing)
    if base not in taken:
        return base
    i = 2
    while f"{base} {i}" in taken:
        i += 1
    return f"{base} {i}"


def page_size_mm(name: str, landscape: bool = True) -> Tuple[float, float]:
    """
    Return ``(width_mm, height_mm)`` for an ISO A-series page name, swapping
    the axes for landscape. Unknown names fall back to A4.
    """
    w, h = PAGE_SIZES_MM.get(str(name).upper(), PAGE_SIZES_MM["A4"])
    if landscape:
        return (h, w)
    return (w, h)
