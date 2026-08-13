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
        grid = main_map.grids().addGrid("PlanXCoordGrid")

    if grid is None:
        return False

    grid.setEnabled(True)
    grid.setStyle(QgsLayoutItemMapGrid.GridStyle.Cross)
    grid.setIntervalX(interval_m)
    grid.setIntervalY(interval_m)
    grid.setFrameStyle(QgsLayoutItemMapGrid.FrameStyle.Zebra)
    grid.setFrameWidth(2.0)

    if show_annotations and hasattr(grid, "setAnnotationEnabled"):
        grid.setAnnotationEnabled(True)
        grid.setAnnotationDisplay(
            QgsLayoutItemMapGrid.DisplayMode.ShowAll,
            QgsLayoutItemMapGrid.BorderSide.Left,
        )
        grid.setAnnotationDisplay(
            QgsLayoutItemMapGrid.DisplayMode.ShowAll,
            QgsLayoutItemMapGrid.BorderSide.Bottom,
        )

    main_map.updateBoundingRect()
    layout.refresh()
    return True
