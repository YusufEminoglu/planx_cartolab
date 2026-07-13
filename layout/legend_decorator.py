# -*- coding: utf-8 -*-
"""
Bivariate colour-matrix legend for QGIS print layouts.

Renders the legend as *native* layout items (rectangles or diamonds plus
text), grouped so it drags as one unit. Unlike an embedded SVG this leaves
no temporary files behind and stays fully editable in the Layout Designer.
"""
from __future__ import annotations

from typing import List

from qgis.PyQt.QtCore import QPointF
from qgis.PyQt.QtGui import QColor, QFont, QPolygonF
from qgis.core import (
    QgsLayout,
    QgsLayoutItemGroup,
    QgsLayoutItemLabel,
    QgsLayoutItemPolygon,
    QgsLayoutItemShape,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsUnitTypes,
    QgsFillSymbol,
)

from ..core.bivariate_engine import bivariate_colour_matrix

_MM = QgsUnitTypes.LayoutUnit.LayoutMillimeters


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
    return layout.groupItems(items)


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
