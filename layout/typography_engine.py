# -*- coding: utf-8 -*-
"""
Typography engine — Enforce consistent font hierarchy across layouts.

Sets all text items in a QGIS layout to Inter / IBM Plex Mono font stack.
"""
from __future__ import annotations

from qgis.core import QgsLayout, QgsLayoutItemLabel
from qgis.PyQt.QtGui import QFont


FONT_STACK_TITLE = "Inter, Segoe UI, sans-serif"
FONT_STACK_BODY = "Inter, Segoe UI, system-ui, sans-serif"
FONT_STACK_MONO = "IBM Plex Mono, Consolas, monospace"


def apply_typography_hierarchy(layout: QgsLayout) -> None:
    """
    Apply a consistent Swiss-style typography hierarchy to all label
    items in the given QGIS Print Layout.

    Title items (font size >= 16) → Inter Bold
    Body items → Inter Regular
    Monospace items (item id containing 'mono' or 'code') → IBM Plex Mono
    """
    for item in layout.items():
        if not isinstance(item, QgsLayoutItemLabel):
            continue
        font = item.font()
        item_id_lower = item.id().lower()

        if "mono" in item_id_lower or "code" in item_id_lower:
            font.setFamily(FONT_STACK_MONO.split(",")[0])
            font.setPointSize(max(8, font.pointSize()))
            font.setWeight(QFont.Normal)
        elif font.pointSize() >= 16 or "title" in item_id_lower:
            font.setFamily(FONT_STACK_TITLE.split(",")[0])
            font.setWeight(QFont.Bold)
        else:
            font.setFamily(FONT_STACK_BODY.split(",")[0])
            font.setWeight(QFont.Normal)

        item.setFont(font)
        item.adjustSizeToText()
    layout.refresh()
