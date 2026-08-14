# -*- coding: utf-8 -*-
"""
PlanX CartoLab — Automated Multi-Page Map Book & Atlas Builder.

Configures QGIS Print Layout Atlas engine for automatic serial map sheet production:
coverage layer binding, dynamic title expressions, page counters, and auto-centering map frames.
"""
from __future__ import annotations

from typing import Optional

try:
    from qgis.core import (
        QgsLayout,
        QgsLayoutItemLabel,
        QgsLayoutItemMap,
        QgsLayoutPoint,
        QgsLayoutSize,
        QgsUnitTypes,
        QgsVectorLayer,
    )
    from qgis.PyQt.QtGui import QFont, QColor
except ImportError:
    QgsLayout = QgsLayoutItemLabel = QgsLayoutItemMap = QgsLayoutPoint = QgsLayoutSize = QgsUnitTypes = QgsVectorLayer = QFont = QColor = None


def setup_layout_atlas(
    layout: QgsLayout,
    coverage_layer: QgsVectorLayer,
    name_field: str = "",
    margin_percent: float = 10.0,
) -> bool:
    """
    Configure the layout's Atlas engine with dynamic titles, page counters, and auto-framing.
    """
    if layout is None or coverage_layer is None or QgsLayoutItemMap is None:
        return False

    atlas = layout.atlas()
    if atlas is None:
        return False

    # 1. Configure Atlas Engine
    atlas.setEnabled(True)
    atlas.setCoverageLayer(coverage_layer)

    if name_field and name_field in [f.name() for f in coverage_layer.fields()]:
        atlas.setPageNameExpression(f'"{name_field}"')
        atlas_title_expr = f'[% "{name_field}" %]'
    else:
        atlas.setPageNameExpression("concat('Sheet ', @atlas_featurenumber)")
        atlas_title_expr = "[% @atlas_pagename %]"

    # 2. Find and link primary map frame
    main_map: Optional[QgsLayoutItemMap] = None
    for item in layout.items():
        if isinstance(item, QgsLayoutItemMap):
            main_map = item
            break

    if main_map is not None:
        main_map.setAtlasDriven(True)
        _AutoScaling = getattr(getattr(QgsLayoutItemMap, "AtlasScalingMode", QgsLayoutItemMap), "Auto", getattr(QgsLayoutItemMap, "Auto", 0))
        main_map.setAtlasScalingMode(_AutoScaling)
        main_map.setAtlasMargin(margin_percent / 100.0)

    # 3. Add Dynamic Title & Page Counter labels if not already present
    _Mm = getattr(getattr(QgsUnitTypes, "LayoutUnit", QgsUnitTypes), "LayoutMillimeters", getattr(QgsUnitTypes, "LayoutMillimeters", 0))
    page = layout.pageCollection().page(0)
    page_w = page.pageSize().width() if page else 297.0
    page_h = page.pageSize().height() if page else 210.0

    # Dynamic Atlas Title Label
    has_atlas_title = any(isinstance(it, QgsLayoutItemLabel) and "atlas" in it.text().lower() for it in layout.items())
    if not has_atlas_title:
        lbl_title = QgsLayoutItemLabel(layout)
        lbl_title.setText(f"Map Series: {atlas_title_expr}")
        if QFont is not None:
            lbl_title.setFont(QFont("Inter, Segoe UI", 16, QFont.Weight.Bold))
        if QColor is not None:
            lbl_title.setFontColor(QColor("#0f172a"))
        lbl_title.attemptMove(QgsLayoutPoint(12.0, 10.0, _Mm))
        lbl_title.attemptResize(QgsLayoutSize(page_w - 90.0, 12.0, _Mm))
        layout.addLayoutItem(lbl_title)

    # Dynamic Page Counter (e.g. Sheet 1 of 24)
    has_counter = any(isinstance(it, QgsLayoutItemLabel) and "@atlas_featurenumber" in it.text() for it in layout.items())
    if not has_counter:
        lbl_counter = QgsLayoutItemLabel(layout)
        lbl_counter.setText("Sheet [% @atlas_featurenumber %] of [% @atlas_totalfeatures %]")
        if QFont is not None:
            lbl_counter.setFont(QFont("Inter, Segoe UI", 10, QFont.Weight.DemiBold))
        if QColor is not None:
            lbl_counter.setFontColor(QColor("#64748b"))
        lbl_counter.attemptMove(QgsLayoutPoint(page_w - 75.0, 12.0, _Mm))
        lbl_counter.attemptResize(QgsLayoutSize(63.0, 8.0, _Mm))
        layout.addLayoutItem(lbl_counter)

    layout.refresh()
    return True
