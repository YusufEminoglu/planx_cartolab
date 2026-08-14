# -*- coding: utf-8 -*-
"""
PlanX CartoLab — Core Utilities.

Provides type-safe extraction of numerical values from PyQGIS features and QVariant objects.
"""
from __future__ import annotations

import math
from typing import Any, Optional


def safe_float(val: Any, default: Optional[float] = None) -> Optional[float]:
    """
    Safely convert any input (QVariant, PyQGIS NULL, str, int, float, None)
    to a finite float. Returns `default` if conversion fails or if non-finite (NaN/Inf).
    """
    if val is None:
        return default
    if hasattr(val, "isNull") and val.isNull():
        return default
    if hasattr(val, "value"):
        val = val.value()
    if val is None:
        return default
    try:
        res = float(val)
        return res if math.isfinite(res) else default
    except (ValueError, TypeError):
        return default


def safe_int(val: Any, default: Optional[int] = None) -> Optional[int]:
    """
    Safely convert any input (QVariant, PyQGIS NULL, str, int, float, None)
    to an integer. Returns `default` if conversion fails.
    """
    f = safe_float(val, default=None)
    if f is None:
        return default
    try:
        return int(f)
    except (ValueError, TypeError):
        return default
