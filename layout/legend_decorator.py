# -*- coding: utf-8 -*-
"""
Bivariate colour-matrix legend for QGIS print layouts.

Renders the legend as *native* layout items (rectangles or diamonds plus
text), grouped so it drags as one unit. Unlike an embedded SVG this leaves
no temporary files behind and stays fully editable in the Layout Designer.
"""
from __future__ import annotations

from typing import List

try:
    from qgis.PyQt.QtCore import QPointF
    from qgis.PyQt.QtGui import QColor, QFont, QPolygonF
    from qgis.core import (
        QgsLayout,
        QgsLayoutItemGroup,
        QgsLayoutItemLabel,
        QgsLayoutItemPolygon,
        QgsLayoutItemShape,
        QgsLayoutItemScaleBar,
        QgsLayoutItemPicture,
        QgsLayoutItemMap,
        QgsLayoutPoint,
        QgsLayoutSize,
        QgsUnitTypes,
        QgsFillSymbol,
    )
    _MM = QgsUnitTypes.LayoutUnit.LayoutMillimeters
except ImportError:
    QPointF = QColor = QFont = QPolygonF = QgsLayout = QgsLayoutItemGroup = QgsLayoutItemLabel = QgsLayoutItemPolygon = QgsLayoutItemShape = QgsLayoutItemScaleBar = QgsLayoutItemPicture = QgsLayoutItemMap = QgsLayoutPoint = QgsLayoutSize = QgsUnitTypes = QgsFillSymbol = None
    _MM = 0



from ..core.bivariate_engine import bivariate_colour_matrix



def add_bivariate_legend_to_layout(
    layout: QgsLayout,
    x_label: str = "Variable X",
    y_label: str = "Variable Y",
    grid_size: int = 4,
    position: tuple = (12.0, 12.0),
    size_mm: tuple = (46.0, 46.0),
    color_ll: str = "#e8e8e8",
    color_lh: str = "#5ab4ac",
    color_hl: str = "#d8b365",
    color_hh: str = "#8c510a",
    legend_type: str = "diamond",
) -> QgsLayoutItemGroup:
    """
    Insert a bivariate colour-matrix legend built from native layout items.

    Returns the :class:`QgsLayoutItemGroup` holding the legend so callers can
    reposition or delete it as a whole.
    """
    matrix = bivariate_colour_matrix(grid_size, color_ll, color_lh, color_hl, color_hh)
    if legend_type == "square":
        items = _build_square(layout, matrix, position, size_mm, x_label, y_label)
    else:
        items = _build_diamond(layout, matrix, position, size_mm, x_label, y_label)

    if hasattr(layout, "groupItems") and items:
        grp = layout.groupItems(items)
        if grp:
            return grp
    return items
def add_bivariate_legend(
    layout: QgsLayout,
    colors: tuple = None,
    legend_type: str = "diamond",
    title: str = "Bivariate Legend",
    x_label: str = "Variable X",
    y_label: str = "Variable Y",
    **kwargs,
) -> QgsLayoutItemGroup:
    """Convenience wrapper for add_bivariate_legend_to_layout."""
    if colors and len(colors) >= 4:
        cll, clh, chl, chh = colors[0], colors[1], colors[2], colors[3]
    else:
        cll, clh, chl, chh = "#e8e8e8", "#5ab4ac", "#d8b365", "#8c510a"
    return add_bivariate_legend_to_layout(
        layout,
        x_label=x_label,
        y_label=y_label,
        color_ll=cll,
        color_lh=clh,
        color_hl=chl,
        color_hh=chh,
        legend_type=legend_type,
        **kwargs,
    )



def _fill(color: QColor) -> QgsFillSymbol:
    return QgsFillSymbol.createSimple({
        "color": color.name(),
        "outline_color": "#ffffff",
        "outline_width": "0.25",
    })


def _label(layout, text: str, x: float, y: float, size: int = 8,
           bold: bool = False, rotation: float = 0.0) -> QgsLayoutItemLabel:
    lbl = QgsLayoutItemLabel(layout)
    lbl.setText(text)
    f = QFont()
    f.setFamilies(["Inter", "Segoe UI", "Arial", "sans-serif"])
    f.setPointSize(size)
    f.setBold(bold)
    lbl.setFont(f)
    lbl.setFontColor(QColor("#333333"))
    lbl.adjustSizeToText()
    if rotation:
        lbl.setItemRotation(rotation)
    lbl.attemptMove(QgsLayoutPoint(x, y, _MM))
    layout.addLayoutItem(lbl)
    return lbl


def _build_square(layout, matrix, position, size_mm, x_label, y_label) -> List:
    n = len(matrix)
    x0, y0 = position
    cell = min(size_mm[0], size_mm[1]) / float(n)
    items: List = []
    for ri, row in enumerate(matrix):
        for ci, col in enumerate(row):
            shape = QgsLayoutItemShape(layout)
            shape.setShapeType(QgsLayoutItemShape.Shape.Rectangle)
            shape.attemptResize(QgsLayoutSize(cell, cell, _MM))
            # matrix row 0 is the high-Y row; draw it at the top
            shape.attemptMove(QgsLayoutPoint(x0 + ci * cell, y0 + ri * cell, _MM))
            shape.setSymbol(_fill(col))
            layout.addLayoutItem(shape)
            items.append(shape)
    grid_h = n * cell
    items.append(_label(layout, x_label, x0, y0 + grid_h + 1.5, size=8, bold=True))
    items.append(_label(layout, y_label, x0 - 3.0, y0 + grid_h,
                        size=8, bold=True, rotation=270.0))
    return items


def _build_diamond(layout, matrix, position, size_mm, x_label, y_label) -> List:
    n = len(matrix)
    half_w = size_mm[0] / (2.0 * n)
    half_h = size_mm[1] / (2.0 * n)
    x0, y0 = position
    offset_x = x0 + (n - 1) * half_w + half_w
    offset_y = y0 + half_h + 6.0
    items: List = []

    for ri in range(n):
        for ci in range(n):
            col = matrix[ri][ci]
            cx = offset_x + (ci - ri) * half_w
            cy = offset_y + ((n - 1) - (ci + ri)) * half_h
            poly = QPolygonF([
                QPointF(cx, cy - half_h),
                QPointF(cx + half_w, cy),
                QPointF(cx, cy + half_h),
                QPointF(cx - half_w, cy),
            ])
            diamond = QgsLayoutItemPolygon(poly, layout)
            diamond.setSymbol(_fill(col))
            layout.addLayoutItem(diamond)
            items.append(diamond)

    cx_mid = offset_x
    items.append(_label(layout, "High", cx_mid - 4.0, offset_y - half_h - 5.0,
                        size=7, bold=True))
    items.append(_label(layout, "Low", cx_mid - 3.0,
                        offset_y + (n - 1) * 2 * half_h + half_h + 1.0,
                        size=7, bold=True))
    items.append(_label(layout, x_label, offset_x + (n - 1) * half_w + 2.0,
                        offset_y + (n - 1) * half_h, size=8, bold=True))
    items.append(_label(layout, y_label, x0 - 2.0,
                        offset_y + (n - 1) * half_h, size=8, bold=True,
                        rotation=0.0))
    return items


def add_scalebar_to_layout(
    layout: QgsLayout,
    map_item: QgsLayoutItemMap = None,
    position: tuple = (15.0, 15.0),
    style_name: str = "Single Box",
) -> QgsLayoutItemScaleBar:
    """Add a native scalebar item to the layout attached to the primary map frame."""
    scalebar = QgsLayoutItemScaleBar(layout)
    if map_item is None:
        for item in layout.items():
            if isinstance(item, QgsLayoutItemMap):
                map_item = item
                break
    if map_item is not None:
        scalebar.setLinkedMap(map_item)
    scalebar.setStyle(style_name)
    scalebar.setUnits(QgsUnitTypes.DistanceUnit.DistanceKilometers)
    scalebar.setNumberOfSegments(2)
    scalebar.setUnitsPerSegment(1.0)
    scalebar.attemptMove(QgsLayoutPoint(position[0], position[1], _MM))
    layout.addLayoutItem(scalebar)
    return scalebar


def add_north_arrow_to_layout(
    layout: QgsLayout,
    position: tuple = (15.0, 15.0),
    size_mm: tuple = (16.0, 16.0),
) -> QgsLayoutItemPolygon:
    """Add a clean north arrow motif to the layout."""
    x0, y0 = position
    w, h = size_mm
    cx = x0 + w / 2.0
    poly = QPolygonF([
        QPointF(cx, y0),
        QPointF(x0 + w, y0 + h),
        QPointF(cx, y0 + h * 0.75),
        QPointF(x0, y0 + h),
    ])
    arrow = QgsLayoutItemPolygon(poly, layout)
    arrow.setSymbol(_fill(QColor("#0f172a")))
    layout.addLayoutItem(arrow)
    return arrow

