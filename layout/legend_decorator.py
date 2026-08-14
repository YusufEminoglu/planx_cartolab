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
           bold: bool = False, rotation: float = 0.0, color: str = "#0f172a") -> QgsLayoutItemLabel:
    lbl = QgsLayoutItemLabel(layout)
    lbl.setText(text)
    lbl.setBackgroundEnabled(False)
    lbl.setFrameEnabled(False)
    f = QFont()
    f.setFamilies(["Inter", "Segoe UI", "Arial", "sans-serif"])
    f.setPointSize(size)
    f.setBold(bold)
    lbl.setFont(f)
    lbl.setFontColor(QColor(color))
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

    # Optional background card for contrast
    bg_margin = 6.0
    grid_w = n * cell
    grid_h = n * cell

    for ri, row in enumerate(matrix):
        for ci, col in enumerate(row):
            shape = QgsLayoutItemShape(layout)
            shape.setShapeType(QgsLayoutItemShape.Shape.Rectangle)
            shape.attemptResize(QgsLayoutSize(cell, cell, _MM))
            shape.attemptMove(QgsLayoutPoint(x0 + ci * cell, y0 + ri * cell, _MM))
            shape.setSymbol(_fill(col))
            layout.addLayoutItem(shape)
            items.append(shape)

    # High-contrast X & Y axis labels and directional indicators
    items.append(_label(layout, f"{x_label} ➔", x0, y0 + grid_h + 2.0, size=8, bold=True, color="#0f172a"))
    items.append(_label(layout, f"▲ {y_label}", x0 - 2.0, y0 + grid_h - 2.0, size=8, bold=True, rotation=270.0, color="#0f172a"))
    items.append(_label(layout, "Low", x0 - 2.0, y0 + grid_h + 1.0, size=7, bold=False, color="#64748b"))
    items.append(_label(layout, "High", x0 + grid_w - 6.0, y0 + grid_h + 1.0, size=7, bold=False, color="#64748b"))
    return items


def _build_diamond(layout, matrix, position, size_mm, x_label, y_label) -> List:
    n = len(matrix)
    half_w = size_mm[0] / (2.0 * n)
    half_h = size_mm[1] / (2.0 * n)
    x0, y0 = position
    offset_x = x0 + (n - 1) * half_w + half_w
    offset_y = y0 + half_h + 8.0
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
    # Top/bottom/left/right axis labels
    items.append(_label(layout, "High Y ▲", cx_mid - 6.0, offset_y - (n * half_h) - 4.0, size=7, bold=True, color="#0f172a"))
    items.append(_label(layout, "Low Y", cx_mid - 4.0, offset_y + (n * half_h) + 1.0, size=7, bold=False, color="#64748b"))
    items.append(_label(layout, f"{x_label} ➔", offset_x + (n * half_w) - 2.0, offset_y - 2.0, size=8, bold=True, color="#0f172a"))
    items.append(_label(layout, f"▲ {y_label}", x0 - 4.0, offset_y - 2.0, size=8, bold=True, color="#0f172a"))
    return items


def add_scalebar_to_layout(
    layout: QgsLayout,
    map_item: QgsLayoutItemMap = None,
    position: tuple = (15.0, 15.0),
    style_name: str = "Single Box",
    segments: int = 2,
    units_per_segment: float = 1.0,
    unit_label: str = "km",
) -> QgsLayoutItemScaleBar:
    """Add an executive publication-ready scalebar to the layout."""
    if layout is None or QgsLayoutItemScaleBar is None:
        return None

    scalebar = QgsLayoutItemScaleBar(layout)
    if map_item is None:
        for item in layout.items():
            if isinstance(item, QgsLayoutItemMap):
                map_item = item
                break

    if map_item is not None:
        scalebar.setLinkedMap(map_item)

    # Style mapping: "Single Box", "Double Box", "Line Ticks", "Stepped Box"
    STYLE_MAP = {
        "Single Box": "Single Box",
        "Double Box": "Double Box",
        "Line Ticks": "Line Ticks Middle",
        "Line Ticks Middle": "Line Ticks Middle",
        "Stepped Box": "Stepped Line",
        "Stepped Line": "Stepped Line",
    }
    target_style = STYLE_MAP.get(style_name, "Single Box")
    scalebar.setStyle(target_style)

    # Units — safe for both QGIS 3.x (unscoped) and 4.x (scoped)
    _DistKm = getattr(getattr(QgsUnitTypes, "DistanceUnit", QgsUnitTypes), "DistanceKilometers", getattr(QgsUnitTypes, "DistanceKilometers", None))
    if _DistKm is not None:
        scalebar.setUnits(_DistKm)

    scalebar.setNumberOfSegments(max(1, segments))
    scalebar.setUnitsPerSegment(units_per_segment)
    scalebar.setUnitLabel(unit_label)

    scalebar.attemptMove(QgsLayoutPoint(position[0], position[1], _MM))
    layout.addLayoutItem(scalebar)
    layout.refresh()
    return scalebar


def add_north_arrow_to_layout(
    layout: QgsLayout,
    position: tuple = (15.0, 15.0),
    size_mm: tuple = (16.0, 22.0),
    preset: str = "compass_rose",
) -> QgsLayoutItemGroup:
    """
    Insert a publication-ready north arrow motif (Compass Rose, Swiss Minimalist, Nautical Star).
    Returns the grouped layout item containing the compass components.
    """
    if layout is None:
        return None

    x0, y0 = position
    w, h = size_mm
    cx = x0 + w / 2.0
    cy = y0 + h / 2.0
    items = []

    if preset == "swiss_minimal":
        # Ultra-clean thin needle arrow
        poly_l = QPolygonF([QPointF(cx, y0 + 6.0), QPointF(cx - w / 4.0, y0 + h), QPointF(cx, y0 + h * 0.75)])
        poly_r = QPolygonF([QPointF(cx, y0 + 6.0), QPointF(cx + w / 4.0, y0 + h), QPointF(cx, y0 + h * 0.75)])
        p_l = QgsLayoutItemPolygon(poly_l, layout)
        p_l.setSymbol(_fill(QColor("#0f172a")))
        p_r = QgsLayoutItemPolygon(poly_r, layout)
        p_r.setSymbol(_fill(QColor("#94a3b8")))
        layout.addLayoutItem(p_l)
        layout.addLayoutItem(p_r)
        items.extend([p_l, p_r])
        lbl = _label(layout, "N", cx - 2.5, y0, size=9, bold=True)
        items.append(lbl)

    elif preset == "nautical_star":
        # 4-point Nautical Star Compass
        poly_top = QPolygonF([QPointF(cx, y0 + 6.0), QPointF(cx + w / 5.0, cy), QPointF(cx, cy)])
        poly_right = QPolygonF([QPointF(x0 + w, cy), QPointF(cx, cy + h / 5.0), QPointF(cx, cy)])
        poly_bottom = QPolygonF([QPointF(cx, y0 + h), QPointF(cx - w / 5.0, cy), QPointF(cx, cy)])
        poly_left = QPolygonF([QPointF(x0, cy), QPointF(cx, cy - h / 5.0), QPointF(cx, cy)])
        for poly, col in [(poly_top, "#0f172a"), (poly_right, "#475569"), (poly_bottom, "#0f172a"), (poly_left, "#475569")]:
            item = QgsLayoutItemPolygon(poly, layout)
            item.setSymbol(_fill(QColor(col)))
            layout.addLayoutItem(item)
            items.append(item)
        lbl = _label(layout, "N", cx - 2.5, y0, size=9, bold=True)
        items.append(lbl)

    else:
        # Classic 8-Point Compass Rose with dual-facet shading
        facet_left = QPolygonF([QPointF(cx, y0 + 6.0), QPointF(x0, y0 + h), QPointF(cx, y0 + h * 0.8)])
        facet_right = QPolygonF([QPointF(cx, y0 + 6.0), QPointF(x0 + w, y0 + h), QPointF(cx, y0 + h * 0.8)])
        p1 = QgsLayoutItemPolygon(facet_left, layout)
        p1.setSymbol(_fill(QColor("#0f172a")))
        p2 = QgsLayoutItemPolygon(facet_right, layout)
        p2.setSymbol(_fill(QColor("#cbd5e1")))
        layout.addLayoutItem(p1)
        layout.addLayoutItem(p2)
        items.extend([p1, p2])
        lbl = _label(layout, "N", cx - 2.5, y0, size=9, bold=True)
        items.append(lbl)

    if hasattr(layout, "groupItems") and items:
        grp = layout.groupItems(items)
        if grp:
            return grp
    return items
