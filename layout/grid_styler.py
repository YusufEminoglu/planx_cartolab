# -*- coding: utf-8 -*-
"""Minimalist grid styler for layout coordinate grids."""
from __future__ import annotations

from qgis.core import (
    QgsLayoutItemMap,
    QgsLayoutItemMapGrid,
    QgsLayout,
    QgsProject,
)
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import Qt


def apply_minimalist_grid(
    layout: QgsLayout,
    map_item_id: str = "",
    interval_x: float = 500.0,
    interval_y: float = 500.0,
) -> None:
    """
    Apply a minimalist thin-line coordinate grid to a map item.

    Produces a subtle crossed-hair (+) style grid with light grey lines,
    suitable for academic publication figures.
    """
    # find map item
    map_item = None
    if map_item_id:
        map_item = layout.itemById(map_item_id)
    if not map_item:
        for item in layout.items():
            if isinstance(item, QgsLayoutItemMap):
                map_item = item
                break
    if not map_item:
        return

    grid = QgsLayoutItemMapGrid("CartoLabGrid", map_item)
    grid.setIntervalX(interval_x)
    grid.setIntervalY(interval_y)
    grid.setEnabled(True)

    # frame style: no frame, only internal crosses
    grid.setFrameStyle(QgsLayoutItemMapGrid.Zebra)  # actually we want minimal
    grid.setFramePenSize(0.0)
    grid.setFrameEnabled(False)

    # grid lines: thin, light grey
    grid.setGridLineColor(QColor("#cccccc"))
    grid.setGridLinePenSize(0.2)
    grid.setGridLineStyle(Qt.SolidLine)

    # annotation
    grid.setAnnotationEnabled(True)
    grid.setAnnotationPrecision(0)
    grid.setAnnotationFontColor(QColor("#666666"))
    grid.setAnnotationFrameDistance(2.0)

    map_item.grids().addGrid(grid)
    layout.refresh()


def create_cross_grid_style(
    grid: QgsLayoutItemMapGrid,
    colour: str = "#999999",
    line_width: float = 0.15,
) -> None:
    """Configure an existing grid to draw subtle inner crosses (not full gridlines)."""
    grid.setGridLineColor(QColor(colour))
    grid.setGridLinePenSize(line_width)
    grid.setGridLineStyle(Qt.DashLine)
    grid.setAnnotationEnabled(True)
