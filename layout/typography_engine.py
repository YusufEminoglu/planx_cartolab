# -*- coding: utf-8 -*-
"""
Typography engine — Enforce consistent font hierarchy across layouts.

Provides Swiss Modernism, Academic Serif, Technical Blueprint, and Warm Editorial
typography hierarchies for all label items in QGIS Print Layouts.
"""
from __future__ import annotations

from typing import Dict, Tuple

try:
    from qgis.core import QgsLayout, QgsLayoutItemLabel
    from qgis.PyQt.QtGui import QFont, QColor
except ImportError:
    QgsLayout = QgsLayoutItemLabel = QFont = QColor = None


TYPOGRAPHY_PRESETS: Dict[str, Dict[str, any]] = {
    "swiss_modern": {
        "name": "Swiss Modernism",
        "title_family": "Inter, Segoe UI, Arial, sans-serif",
        "body_family": "Inter, Segoe UI, Arial, sans-serif",
        "mono_family": "IBM Plex Mono, Consolas, monospace",
        "title_color": "#0f172a",
        "body_color": "#334155",
        "subtitle_color": "#64748b",
    },
    "academic_serif": {
        "name": "Academic Journal",
        "title_family": "Merriweather, Georgia, Times New Roman, serif",
        "body_family": "Georgia, Times New Roman, serif",
        "mono_family": "Courier New, monospace",
        "title_color": "#1e293b",
        "body_color": "#334155",
        "subtitle_color": "#475569",
    },
    "technical_blueprint": {
        "name": "Technical Blueprint",
        "title_family": "IBM Plex Mono, Consolas, Roboto Mono, monospace",
        "body_family": "IBM Plex Mono, Consolas, monospace",
        "mono_family": "Consolas, monospace",
        "title_color": "#0f766e",
        "body_color": "#134e4a",
        "subtitle_color": "#0d9488",
    },
    "warm_editorial": {
        "name": "Warm Editorial",
        "title_family": "Palatino, Georgia, serif",
        "body_family": "Palatino Linotype, Georgia, serif",
        "mono_family": "Consolas, monospace",
        "title_color": "#292524",
        "body_color": "#44403c",
        "subtitle_color": "#78716c",
    },
}


def apply_typography_hierarchy(layout: QgsLayout, preset: str = "swiss_modern") -> bool:
    """
    Apply a typography hierarchy preset to all label items in the print layout.
    """
    if layout is None or QgsLayoutItemLabel is None:
        return False

    config = TYPOGRAPHY_PRESETS.get(preset.lower(), TYPOGRAPHY_PRESETS["swiss_modern"])
    title_fam = config["title_family"].split(",")[0].strip()
    body_fam = config["body_family"].split(",")[0].strip()
    mono_fam = config["mono_family"].split(",")[0].strip()

    title_col = QColor(config["title_color"]) if QColor else None
    body_col = QColor(config["body_color"]) if QColor else None
    sub_col = QColor(config["subtitle_color"]) if QColor else None

    for item in layout.items():
        if not isinstance(item, QgsLayoutItemLabel):
            continue
        font = item.font()
        item_id_lower = (item.id() or "").lower()
        text_lower = (item.text() or "").lower()

        if "mono" in item_id_lower or "code" in item_id_lower:
            font.setFamily(mono_fam)
            font.setPointSize(max(8, font.pointSize()))
            if hasattr(QFont, "Weight"):
                font.setWeight(QFont.Weight.Normal)
            if body_col:
                item.setFontColor(body_col)
        elif font.pointSize() >= 16 or "title" in item_id_lower:
            font.setFamily(title_fam)
            if hasattr(QFont, "Weight"):
                font.setWeight(QFont.Weight.Bold)
            if title_col:
                item.setFontColor(title_col)
        elif "subtitle" in item_id_lower or "source" in text_lower or font.pointSize() <= 9:
            font.setFamily(body_fam)
            if hasattr(QFont, "Weight"):
                font.setWeight(QFont.Weight.Normal)
            if sub_col:
                item.setFontColor(sub_col)
        else:
            font.setFamily(body_fam)
            if hasattr(QFont, "Weight"):
                font.setWeight(QFont.Weight.Normal)
            if body_col:
                item.setFontColor(body_col)

        item.setFont(font)
        item.adjustSizeToText()

    layout.refresh()
    return True


def apply_swiss_typography(layout: QgsLayout) -> bool:
    """Apply default Swiss Modernism typography."""
    return apply_typography_hierarchy(layout, preset="swiss_modern")
