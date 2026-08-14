# -*- coding: utf-8 -*-
"""
PlanX CartoLab — Layout Coordinate Grid Decorator.

Provides automated coordinate grid and graticule annotation styling for QGIS Print Layout map frames.
"""
from __future__ import annotations

from typing import Optional

try:
    from qgis.core import (
        QgsLayout,
        QgsLayoutItemMap,
        QgsLayoutItemMapGrid,
        QgsUnitTypes,
    )
except ImportError:
    QgsLayout = QgsLayoutItemMap = QgsLayoutItemMapGrid = QgsUnitTypes = None


def apply_coordinate_grid_decorator(
    layout: QgsLayout,
    main_map: Optional[QgsLayoutItemMap] = None,
    interval_m: float = 1000.0,
    show_annotations: bool = True,
) -> bool:
    """
    Apply a publication-ready coordinate grid with frame borders and coordinate labels to the layout's primary map frame.
    """
    if layout is None or QgsLayoutItemMap is None or QgsLayoutItemMapGrid is None:
        return False

    if main_map is None:
        for item in layout.items():
            if isinstance(item, QgsLayoutItemMap):
                main_map = item
                break

    if main_map is None:
        return False

    # Get or create grid
    grid = None
    if main_map.grids().size() > 0:
        grid = main_map.grids().grid(0)
    else:
        grid = QgsLayoutItemMapGrid("PlanXCoordGrid", main_map)
        main_map.grids().addGrid(grid)

    if grid is None:
        return False

    grid.setEnabled(True)
    _Cross = getattr(getattr(QgsLayoutItemMapGrid, "GridStyle", QgsLayoutItemMapGrid), "Cross", getattr(QgsLayoutItemMapGrid, "Cross", 1))
    grid.setStyle(_Cross)
    grid.setIntervalX(interval_m)
    grid.setIntervalY(interval_m)
    _Zebra = getattr(getattr(QgsLayoutItemMapGrid, "FrameStyle", QgsLayoutItemMapGrid), "Zebra", getattr(QgsLayoutItemMapGrid, "Zebra", 1))
    grid.setFrameStyle(_Zebra)
    grid.setFrameWidth(2.0)

    if show_annotations and hasattr(grid, "setAnnotationEnabled"):
        grid.setAnnotationEnabled(True)
        _ShowAll = getattr(getattr(QgsLayoutItemMapGrid, "DisplayMode", QgsLayoutItemMapGrid), "ShowAll", getattr(QgsLayoutItemMapGrid, "ShowAll", 0))
        _Left = getattr(getattr(QgsLayoutItemMapGrid, "BorderSide", QgsLayoutItemMapGrid), "Left", getattr(QgsLayoutItemMapGrid, "Left", 0))
        _Bottom = getattr(getattr(QgsLayoutItemMapGrid, "BorderSide", QgsLayoutItemMapGrid), "Bottom", getattr(QgsLayoutItemMapGrid, "Bottom", 2))
        grid.setAnnotationDisplay(_ShowAll, _Left)
        grid.setAnnotationDisplay(_ShowAll, _Bottom)

    main_map.updateBoundingRect()
    layout.refresh()
    return True
