# -*- coding: utf-8 -*-
"""
PlanX CartoLab — Layout Paper Themes & Canvas Styling Engine.

Applies artistic paper background colors, border styles, grid color palettes,
and font color schemes directly to QgsLayout pages and layout items.
"""
from __future__ import annotations

from contextlib import suppress
from typing import Dict, Any

try:
    import sip
except ImportError:
    try:
        from qgis.PyQt import sip
    except ImportError:
        sip = None

try:
    from qgis.core import (
        QgsLayout,
        QgsLayoutItemPage,
        QgsLayoutItemLabel,
        QgsLayoutItemShape,
        QgsLayoutItemMap,
        QgsFillSymbol,
    )
    from qgis.PyQt.QtGui import QColor
except ImportError:
    QgsLayout = QgsLayoutItemPage = QgsLayoutItemLabel = QgsLayoutItemShape = QgsLayoutItemMap = QgsFillSymbol = QColor = None


PAPER_THEMES: Dict[str, Dict[str, Any]] = {
    "blueprint": {
        "name": "Architectural Blueprint",
        "bg_color": "#0b2545",
        "text_color": "#e0f2fe",
        "grid_color": "#134074",
        "frame_color": "#38bdf8",
    },
    "sepia_atlas": {
        "name": "Vintage Sepia Atlas",
        "bg_color": "#f4ebd9",
        "text_color": "#3d2612",
        "grid_color": "#d4c5b9",
        "frame_color": "#6e473b",
    },
    "swiss_modern": {
        "name": "Modern Swiss Minimalist",
        "bg_color": "#ffffff",
        "text_color": "#18181b",
        "grid_color": "#e4e4e7",
        "frame_color": "#27272a",
    },
}


def apply_paper_theme(layout: QgsLayout, theme_key: str = "blueprint") -> bool:
    """
    Apply paper background color, label text colors, and grid colors to a layout.
    Returns True if successfully applied. Safe against C++ access violations.
    """
    if layout is None or QgsLayoutItemPage is None:
        return False

    theme = PAPER_THEMES.get(theme_key, PAPER_THEMES["swiss_modern"])
    bg_qcolor = QColor(theme["bg_color"])
    text_qcolor = QColor(theme["text_color"])
    frame_qcolor = QColor(theme["frame_color"])

    # 1. Update Page Item background color safely using new fill symbol
    page_collection = layout.pageCollection()
    if page_collection:
        for page in page_collection.pages():
            if sip and sip.isdeleted(page):
                continue
            if QgsFillSymbol:
                sym = QgsFillSymbol.createSimple({"color": theme["bg_color"], "outline_style": "no"})
                if sym:
                    page.setPageStyleSymbol(sym)

    # 2. Update Label text colors and Shape item stroke colors safely
    items = list(layout.items())
    for item in items:
        if sip and sip.isdeleted(item):
            continue
        with suppress(Exception):
            if isinstance(item, QgsLayoutItemLabel):
                item.setFontColor(text_qcolor)
            elif isinstance(item, QgsLayoutItemMap):
                item.setFrameEnabled(True)
                item.setFrameColor(frame_qcolor)

    with suppress(Exception):
        layout.invalidateCache()
        layout.refresh()
    return True
