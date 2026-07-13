# -*- coding: utf-8 -*-
"""
Shared helpers for PlanX CartoLab print-layout automation.

Small, dependency-light utilities used by the map-sheet generator and the
individual decorators (grid, legend, typography, isometric stack): locating
map items, finding a bundled north-arrow SVG, and exporting to PNG/PDF.
"""
from __future__ import annotations

import os
from typing import List, Optional

from qgis.core import (
    QgsApplication,
    QgsLayout,
    QgsLayoutExporter,
    QgsLayoutItemMap,
    QgsProject,
)

from ..core.layout_math import unique_name


def unique_layout_name(project: QgsProject, base: str) -> str:
    """Return a layout name not already present in the project's manager."""
    existing = [lay.name() for lay in project.layoutManager().layouts()]
    return unique_name(existing, base)


def find_map_item(layout: QgsLayout, map_id: str = "") -> Optional[QgsLayoutItemMap]:
    """
    Return a map item from ``layout``.

    Prefers the item whose id matches ``map_id``; otherwise returns the
    first :class:`QgsLayoutItemMap` found, or ``None`` when the layout has no
    map frame.
    """
    if map_id:
        item = layout.itemById(map_id)
        if isinstance(item, QgsLayoutItemMap):
            return item
    for item in layout.items():
        if isinstance(item, QgsLayoutItemMap):
            return item
    return None


def map_items(layout: QgsLayout) -> List[QgsLayoutItemMap]:
    """Return every map item in the layout (draw order not guaranteed)."""
    return [it for it in layout.items() if isinstance(it, QgsLayoutItemMap)]


def north_arrow_svg_path() -> Optional[str]:
    """
    Locate a north-arrow SVG shipped with QGIS.

    Searches :func:`QgsApplication.svgPaths` for the standard
    ``arrows/NorthArrow_*.svg`` set. Returns the first match, or ``None`` so
    callers can fall back to a drawn arrow.
    """
    candidates: List[str] = []
    for base in QgsApplication.svgPaths():
        arrows = os.path.join(base, "arrows")
        if not os.path.isdir(arrows):
            continue
        for fn in sorted(os.listdir(arrows)):
            if fn.lower().startswith("northarrow") and fn.lower().endswith(".svg"):
                candidates.append(os.path.join(arrows, fn))
    # NorthArrow_02 is the clean filled compass; prefer it when present.
    for path in candidates:
        if path.lower().endswith("northarrow_02.svg"):
            return path
    return candidates[0] if candidates else None


def export_layout(layout: QgsLayout, path: str, dpi: int = 300) -> bool:
    """
    Export ``layout`` to PNG or PDF (chosen by the ``path`` extension).

    Returns ``True`` on success. Any pre-existing target file is removed
    first so raster drivers do not refuse to overwrite.
    """
    exporter = QgsLayoutExporter(layout)
    ext = os.path.splitext(path)[1].lower()
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass

    if ext == ".pdf":
        settings = QgsLayoutExporter.PdfExportSettings()
        settings.dpi = dpi
        result = exporter.exportToPdf(path, settings)
    else:
        settings = QgsLayoutExporter.ImageExportSettings()
        settings.dpi = dpi
        result = exporter.exportToImage(path, settings)
    return result == QgsLayoutExporter.Success
