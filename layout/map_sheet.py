# -*- coding: utf-8 -*-
"""
Auto Map Sheet — one-click publication-ready print layout.

Assembles a complete :class:`QgsPrintLayout` from the current map view:
titled map frame at the current extent, filtered legend, scale bar,
north arrow, optional coordinate grid, neat-line and credits. The result
is added to the project's layout manager so it opens straight in the
Layout Designer.
"""
from __future__ import annotations

from typing import List, Optional

from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtCore import QPointF
from qgis.PyQt.QtGui import QPolygonF
from qgis.core import (
    QgsProject,
    QgsPrintLayout,
    QgsLayoutItemMap,
    QgsLayoutItemLabel,
    QgsLayoutItemLegend,
    QgsLayoutItemScaleBar,
    QgsLayoutItemPicture,
    QgsLayoutItemPolygon,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsLayoutMeasurement,
    QgsUnitTypes,
    QgsRectangle,
    QgsFillSymbol,
)

from ..core.layout_math import page_size_mm
from .layout_utils import unique_layout_name, north_arrow_svg_path

_MM = QgsUnitTypes.LayoutMillimeters
# A real font fallback chain — QFont("A, B") treats the whole string as one
# family name and matches nothing, so use setFamilies() for a true cascade.
_FONT_FAMILIES = ["Inter", "Segoe UI", "Arial", "sans-serif"]


def _font(size: float, bold: bool = False) -> QFont:
    f = QFont()
    f.setFamilies(_FONT_FAMILIES)
    f.setPointSizeF(float(size))
    f.setBold(bold)
    return f


def _resolve_layers(iface, project: QgsProject) -> List:
    """Visible canvas layers if a canvas is available, else all project layers."""
    if iface is not None:
        try:
            canvas_layers = iface.mapCanvas().layers()
            if canvas_layers:
                return list(canvas_layers)
        except Exception:
            pass
    return [
        node.layer()
        for node in project.layerTreeRoot().findLayers()
        if node.isVisible() and node.layer() is not None
    ] or list(project.mapLayers().values())


def _resolve_extent(iface, layers) -> Optional[QgsRectangle]:
    """Current canvas extent if possible, else the combined extent of layers."""
    if iface is not None:
        try:
            ext = iface.mapCanvas().extent()
            if ext is not None and not ext.isEmpty():
                return QgsRectangle(ext)
        except Exception:
            pass
    extent = None
    for layer in layers:
        try:
            le = layer.extent()
        except Exception:
            continue
        if le is None or le.isEmpty():
            continue
        if extent is None:
            extent = QgsRectangle(le)
        else:
            extent.combineExtentWith(le)
    return extent


def create_map_sheet(
    iface=None,
    *,
    layers: Optional[List] = None,
    extent: Optional[QgsRectangle] = None,
    crs=None,
    title: str = "",
    subtitle: str = "",
    credits: str = "",
    page_size: str = "A4",
    landscape: bool = True,
    add_title: bool = True,
    add_legend: bool = True,
    add_scalebar: bool = True,
    add_north_arrow: bool = True,
    add_grid: bool = False,
    add_frame: bool = True,
    layout_name: str = "CartoLab Map Sheet",
    project: Optional[QgsProject] = None,
) -> QgsPrintLayout:
    """
    Build and register a finished map sheet.

    Every element is optional via the ``add_*`` switches. Inputs left as
    ``None`` are resolved from ``iface`` (canvas layers / extent / CRS) so a
    caller can pass just ``iface`` and get a sensible sheet.

    Returns the :class:`QgsPrintLayout`, already added to the project's
    layout manager.
    """
    project = project or QgsProject.instance()
    layers = layers if layers is not None else _resolve_layers(iface, project)
    extent = extent if extent is not None else _resolve_extent(iface, layers)
    if crs is None:
        if iface is not None:
            try:
                crs = iface.mapCanvas().mapSettings().destinationCrs()
            except Exception:
                crs = project.crs()
        else:
            crs = project.crs()

    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(unique_layout_name(project, layout_name))

    page_w, page_h = page_size_mm(page_size, landscape)
    page = layout.pageCollection().page(0)
    page.setPageSize(QgsLayoutSize(page_w, page_h, _MM))

    # --- geometry budget (millimetres) -----------------------------------
    margin = 12.0
    gap = 4.0
    title_h = 16.0 if add_title else 0.0
    legend_w = 58.0 if add_legend else 0.0
    bottom_h = 13.0 if (add_scalebar or credits) else 0.0

    map_x = margin
    map_y = margin + (title_h + gap if add_title else 0.0)
    right_reserve = (legend_w + gap) if add_legend else 0.0
    bottom_reserve = (bottom_h + gap) if bottom_h else 0.0
    map_w = page_w - 2 * margin - right_reserve
    map_h = page_h - map_y - margin - bottom_reserve

    # --- map frame -------------------------------------------------------
    map_item = QgsLayoutItemMap(layout)
    map_item.setId("cartolab_map")
    map_item.attemptResize(QgsLayoutSize(map_w, map_h, _MM))
    map_item.attemptMove(QgsLayoutPoint(map_x, map_y, _MM))
    if crs is not None and crs.isValid():
        map_item.setCrs(crs)
    if extent is not None and not extent.isEmpty():
        map_item.zoomToExtent(extent)
    if layers:
        map_item.setLayers(list(layers))
        map_item.setKeepLayerSet(True)
    if add_frame:
        map_item.setFrameEnabled(True)
        map_item.setFrameStrokeColor(QColor("#333333"))
        map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, _MM))
    layout.addLayoutItem(map_item)

    if add_grid:
        try:
            from .grid_styler import apply_minimalist_grid
            apply_minimalist_grid(layout, map_id="cartolab_map")
        except Exception:
            pass

    # --- title / subtitle ------------------------------------------------
    if add_title:
        text = title or project.title() or "Map"
        label = QgsLayoutItemLabel(layout)
        label.setText(text)
        label.setFont(_font(22, bold=True))
        label.setFontColor(QColor("#1b2733"))
        label.attemptMove(QgsLayoutPoint(margin, margin, _MM))
        label.attemptResize(QgsLayoutSize(page_w - 2 * margin, 10.0, _MM))
        layout.addLayoutItem(label)

        if subtitle:
            sub = QgsLayoutItemLabel(layout)
            sub.setText(subtitle)
            sub.setFont(_font(11))
            sub.setFontColor(QColor("#5a6b78"))
            sub.attemptMove(QgsLayoutPoint(margin, margin + 9.0, _MM))
            sub.attemptResize(QgsLayoutSize(page_w - 2 * margin, 6.0, _MM))
            layout.addLayoutItem(sub)

    # --- legend ----------------------------------------------------------
    if add_legend:
        legend = QgsLayoutItemLegend(layout)
        legend.setLinkedMap(map_item)
        legend.setLegendFilterByMapEnabled(True)
        legend.setAutoUpdateModel(True)
        legend.setResizeToContents(True)
        legend.setTitle("")
        legend.attemptMove(QgsLayoutPoint(map_x + map_w + gap, map_y, _MM))
        legend.attemptResize(QgsLayoutSize(legend_w, map_h, _MM))
        layout.addLayoutItem(legend)

    # --- scale bar -------------------------------------------------------
    if add_scalebar:
        bar = QgsLayoutItemScaleBar(layout)
        bar.setLinkedMap(map_item)
        bar.applyDefaultSettings()
        bar.setStyle("Single Box")
        bar.applyDefaultSize()
        bar.attemptMove(
            QgsLayoutPoint(map_x, map_y + map_h + gap, _MM)
        )
        layout.addLayoutItem(bar)

    # --- north arrow -----------------------------------------------------
    if add_north_arrow:
        _add_north_arrow(layout, map_x + map_w - 16.0, map_y + 4.0)

    # --- credits ---------------------------------------------------------
    if credits:
        cred = QgsLayoutItemLabel(layout)
        cred.setText(credits)
        cred.setFont(_font(8))
        cred.setFontColor(QColor("#7a8a97"))
        cred.attemptResize(QgsLayoutSize(map_w * 0.6, bottom_h, _MM))
        cred.attemptMove(
            QgsLayoutPoint(map_x + map_w * 0.4, map_y + map_h + gap, _MM)
        )
        layout.addLayoutItem(cred)

    project.layoutManager().addLayout(layout)
    layout.refresh()
    return layout


def _add_north_arrow(layout, x: float, y: float, size: float = 13.0) -> None:
    """Add a north-arrow picture; fall back to a drawn arrow if no SVG."""
    svg = north_arrow_svg_path()
    if svg:
        pic = QgsLayoutItemPicture(layout)
        pic.setPicturePath(svg)
        pic.attemptResize(QgsLayoutSize(size, size, _MM))
        pic.attemptMove(QgsLayoutPoint(x, y, _MM))
        layout.addLayoutItem(pic)
        return
    _add_drawn_north_arrow(layout, x, y, size)


def _add_drawn_north_arrow(layout, x: float, y: float, size: float) -> None:
    """Vector fallback: a filled triangle plus an 'N' label."""
    half = size / 2.0
    poly = QPolygonF([
        QPointF(x + half, y),
        QPointF(x + size, y + size),
        QPointF(x + half, y + size * 0.72),
        QPointF(x, y + size),
    ])
    arrow = QgsLayoutItemPolygon(poly, layout)
    sym = QgsFillSymbol.createSimple({
        "color": "#1b2733", "outline_color": "#1b2733", "outline_width": "0.2",
    })
    arrow.setSymbol(sym)
    layout.addLayoutItem(arrow)

    label = QgsLayoutItemLabel(layout)
    label.setText("N")
    label.setFont(_font(9, bold=True))
    label.adjustSizeToText()
    label.attemptMove(QgsLayoutPoint(x + half - 2.0, y - 5.0, _MM))
    layout.addLayoutItem(label)
