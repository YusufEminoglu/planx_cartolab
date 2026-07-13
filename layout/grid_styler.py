# -*- coding: utf-8 -*-
"""Minimalist coordinate-grid styler for print layouts."""
from __future__ import annotations

from typing import Optional

from qgis.core import QgsLayoutItemMapGrid, QgsLayout, QgsLineSymbol
from qgis.PyQt.QtGui import QColor

from ..core.layout_math import nice_interval
from .layout_utils import find_map_item

GRID_ID = "CartoLabGrid"


def apply_minimalist_grid(
    layout: QgsLayout,
    map_id: str = "",
    interval_x: Optional[float] = None,
    interval_y: Optional[float] = None,
    target_divisions: int = 8,
) -> bool:
    """
    Apply a subtle thin-line coordinate grid to a map item.

    Idempotent: re-running replaces the previous CartoLab grid instead of
    stacking duplicates, so the dashboard button can be pressed repeatedly.
    When the intervals are not given they are derived from the map's current
    extent (``nice_interval``) so the grid reads well at any scale or CRS.

    Returns ``True`` when a grid was applied, ``False`` when the layout has
    no map frame.
    """
    map_item = find_map_item(layout, map_id)
    if map_item is None:
        return False

    # Derive rounded intervals from the current extent when not supplied.
    if interval_x is None or interval_y is None:
        extent = map_item.extent()
        span = max(extent.width(), extent.height()) if extent else 0.0
        auto = nice_interval(span, target_divisions)
        if auto <= 0:
            auto = (span / 5.0) if span > 0 else 1000.0
        interval_x = auto if interval_x is None else interval_x
        interval_y = auto if interval_y is None else interval_y

    # Drop any previous CartoLab grid so repeated runs stay idempotent.
    # Grids are addressed by an auto-generated UUID id(), not their name,
    # so match on the name we assign and remove by id.
    stack = map_item.grids()
    for existing in list(stack.asList()):
        if existing.name() == GRID_ID:
            stack.removeGrid(existing.id())

    grid = QgsLayoutItemMapGrid(GRID_ID, map_item)
    grid.setEnabled(True)
    grid.setUnits(QgsLayoutItemMapGrid.GridUnit.MapUnit)
    grid.setIntervalX(interval_x)
    grid.setIntervalY(interval_y)

    # No frame — a minimal academic look with only interior lines + labels.
    grid.setFrameStyle(QgsLayoutItemMapGrid.FrameStyle.NoFrame)
    grid.setLineSymbol(QgsLineSymbol.createSimple({"color": "#c8c8c8", "width": "0.2"}))

    grid.setAnnotationEnabled(True)
    grid.setAnnotationPrecision(0)
    grid.setAnnotationFontColor(QColor("#666666"))
    grid.setAnnotationFrameDistance(2.0)

    map_item.grids().addGrid(grid)
    map_item.updateBoundingRect()
    layout.refresh()
    return True
