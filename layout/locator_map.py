# -*- coding: utf-8 -*-
"""
PlanX CartoLab — Layout Locator / Inset Map Decorator.

Provides automated locator map inset creation for QGIS Print Layouts.
"""
from __future__ import annotations

from typing import Optional

try:
    from qgis.core import (
        QgsLayout,
        QgsLayoutItemMap,
        QgsLayoutItemMapOverview,
        QgsLayoutPoint,
        QgsLayoutSize,
        QgsUnitTypes,
    )
except ImportError:
    QgsLayout = QgsLayoutItemMap = QgsLayoutItemMapOverview = QgsUnitTypes = None

_MM = QgsUnitTypes.LayoutUnit.LayoutMillimeters if QgsUnitTypes else 0


def add_locator_inset_map(
    layout: QgsLayout,
    main_map: Optional[QgsLayoutItemMap] = None,
    position: tuple = (15.0, 15.0),
    size_mm: tuple = (45.0, 45.0),
) -> Optional[QgsLayoutItemMap]:
    """
    Insert a secondary locator inset map frame into the layout linked to the primary map extent.
    """
    if layout is None or QgsLayoutItemMap is None:
        return None

    # Find primary map item if not provided
    if main_map is None:
        for item in layout.items():
            if isinstance(item, QgsLayoutItemMap):
                main_map = item
                break

    # Create secondary locator map item
    inset_map = QgsLayoutItemMap(layout)
    inset_map.attemptMove(QgsLayoutPoint(position[0], position[1], _MM))
    inset_map.attemptResize(QgsLayoutSize(size_mm[0], size_mm[1], _MM))
    inset_map.setFrameEnabled(True)

    if main_map is not None:
        # Scale inset map out 5x for context
        inset_map.setExtent(main_map.extent())
        inset_map.zoomByFactor(5.0)

        # Add extent overview rectangle linking inset map to main map
        if hasattr(inset_map, "overviews"):
            overview = inset_map.overviews().addOverview("MainMapOverview")
            if overview:
                overview.setLinkedMap(main_map)
                overview.setEnabled(True)

    layout.addLayoutItem(inset_map)
    layout.refresh()
    return inset_map
