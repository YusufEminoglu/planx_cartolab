# -*- coding: utf-8 -*-
"""
Continuous-Area Cartogram Engine.

Diffusion method (Gastner & Newman 2004) — iteratively displaces polygon
boundaries until each region's area is proportional to a chosen variable.

Cross-version compatible with QGIS 3.14+ and QGIS 4.x.
"""
from __future__ import annotations

import math
import re
from typing import List, Tuple, Optional

from qgis.core import (
    QgsFeature, QgsGeometry, QgsVectorLayer,
)


# ---------------------------------------------------------------------------
# WKT coordinate parsing — version-agnostic
# ---------------------------------------------------------------------------

_COORD_RE = re.compile(r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)")


def _extract_wkt_coords(wkt: str) -> List[Tuple[float, float]]:
    """Parse all coordinate pairs from a WKT string in order."""
    return [(float(m.group(1)), float(m.group(2)))
            for m in _COORD_RE.finditer(wkt)]


def _rebuild_wkt(wkt: str, new_coords: List[Tuple[float, float]]) -> str:
    """Replace coordinate pairs in a WKT string with new values."""
    result = []
    last_end = 0
    idx = 0
    for m in _COORD_RE.finditer(wkt):
        if idx >= len(new_coords):
            break
        # copy WKT text before the X coordinate
        result.append(wkt[last_end:m.start(1)])
        # insert new coordinate pair
        nx, ny = new_coords[idx]
        result.append(f"{nx:.12f} {ny:.12f}")
        last_end = m.end(2)
        idx += 1
    # copy any remaining WKT text
    result.append(wkt[last_end:])
    return "".join(result)


# ---------------------------------------------------------------------------
# CartogramFeature — lightweight pickle-able polygon
# ---------------------------------------------------------------------------

class CartogramFeature:
    """Minimal pickle-able polygon representation for parallel processing."""

    __slots__ = (
        "id", "wkt_str", "value", "area", "radius",
        "cx", "cy", "mass", "size_error",
        "coords", "_area_value_ratio",
    )

    def __init__(self, feature_id: int, geometry, value):
        self.id = feature_id
        if geometry is None or (hasattr(geometry, "isNull") and geometry.isNull()):
            raise ValueError(f"Feature {feature_id}: geometry is None or null")
        self.wkt_str = geometry.asWkt()
        self.value = max(float(value or 0.0), 1e-12)
        self.area = 0.0
        self.radius = 0.0
        self.cx = 0.0
        self.cy = 0.0
        self.mass = 0.0
        self.size_error = 1.0
        self.coords: List[Tuple[float, float]] = []
        self._area_value_ratio = 1.0

    @property
    def area_value_ratio(self):
        return self._area_value_ratio

    @area_value_ratio.setter
    def area_value_ratio(self, val):
        self._area_value_ratio = val

    def recompute_properties(self) -> None:
        """Calculate area, radius, and centroid from current WKT."""
        geom = QgsGeometry.fromWkt(self.wkt_str)
        self.area = geom.area()
        self.radius = math.sqrt(self.area / math.pi) if self.area > 0 else 1e-12
        centroid = geom.centroid().asPoint()
        self.cx = centroid.x()
        self.cy = centroid.y()

    def extract_coords(self) -> None:
        """Parse all vertex coordinates from WKT."""
        self.coords = _extract_wkt_coords(self.wkt_str)

    def displace_coords(self, dx: float, dy: float) -> None:
        """Displace all vertices uniformly (used in repulsion step)."""
        self.coords = [(x + dx, y + dy) for x, y in self.coords]

    def writeback_coords(self) -> None:
        """Rebuild WKT from displaced coordinates."""
        self.wkt_str = _rebuild_wkt(self.wkt_str, self.coords)


# ---------------------------------------------------------------------------
# CartogramEngine
# ---------------------------------------------------------------------------

class CartogramEngine:
    """
    Diffusion cartogram transformer.

    Usage::

        engine = CartogramEngine(source_layer, field_name, max_iter=50, max_error=5.0)
        iterations, error = engine.run(feedback=...)
        engine.write_to_layer(output_layer)
    """

    def __init__(
        self,
        source_layer: QgsVectorLayer,
        field_name: str,
        max_iterations: int = 30,
        max_average_error_pct: float = 5.0,
    ):
        self.source = source_layer
        self.field = field_name
        self.max_iter = max_iterations
        self.max_error = 1.0 + max_average_error_pct / 100.0
        self.features: List[CartogramFeature] = []
        self._total_area = 0.0
        self._total_value = 0.0
        self._area_value_ratio = 1.0

    def _load_features(self) -> None:
        for feat in self.source.getFeatures():
            geom = feat.geometry()
            if geom.isEmpty() or geom.isNull():
                continue
            val = feat[self.field]
            if val is None:
                val = 1e-12
            cf = CartogramFeature(feat.id(), geom, float(val))
            cf.recompute_properties()
            cf.extract_coords()
            self.features.append(cf)

        if len(self.features) < 2:
            raise ValueError("Cartogram requires at least 2 valid features.")

        self._total_area = sum(f.area for f in self.features)
        self._total_value = sum(f.value for f in self.features)
        self._area_value_ratio = self._total_area / max(self._total_value, 1e-12)

        for f in self.features:
            f.area_value_ratio = self._area_value_ratio

    def run(self, feedback=None) -> Tuple[int, float]:
        """Execute the diffusion cartogram algorithm. Returns (iterations, avg_error)."""
        self._load_features()
        n = len(self.features)
        damping = 0.25

        for iteration in range(self.max_iter):
            if feedback and feedback.isCanceled():
                break

            # compute masses and size errors
            for f in self.features:
                target_area = f.value * self._area_value_ratio
                if target_area > 0:
                    f.mass = math.sqrt(target_area / math.pi) - f.radius
                else:
                    f.mass = 0.0
                if min(f.area, target_area) > 0:
                    f.size_error = max(f.area, target_area) / min(f.area, target_area)
                else:
                    f.size_error = 1.0

            avg_error = sum(f.size_error for f in self.features) / n

            if feedback:
                progress_pct = int(100 * iteration / self.max_iter)
                feedback.setProgress(progress_pct)
                if iteration % 5 == 0 or avg_error <= self.max_error:
                    feedback.pushInfo(
                        f"Cartogram iter {iteration + 1}/{self.max_iter}, "
                        f"avg error: {(avg_error - 1) * 100:.2f}%"
                    )

            if avg_error <= self.max_error:
                break

            self._diffusion_step(damping)

            # recompute areas from rebuilt WKT
            for f in self.features:
                f.recompute_properties()

        return min(iteration + 1, self.max_iter), avg_error

    def _diffusion_step(self, damping: float) -> None:
        """
        Single diffusion step: each feature's boundary vertices are pushed
        outward (too-small features) or pulled inward (too-large features)
        relative to every other feature's centroid.

        The force from feature j on a vertex of feature i is proportional to
        j.mass * j.radius / distance(vertex_i, centroid_j).
        """
        n = len(self.features)
        for i, f_i in enumerate(self.features):
            new_coords = []
            for vx, vy in f_i.coords:
                fx, fy = 0.0, 0.0
                for j, f_j in enumerate(self.features):
                    if i == j:
                        continue
                    dist = math.hypot(vx - f_j.cx, vy - f_j.cy)
                    if dist < 1e-12:
                        dist = 1e-12
                    # force magnitude decays with distance
                    influence = f_j.mass * f_j.radius * damping / dist
                    fx += influence * (vx - f_j.cx) / dist
                    fy += influence * (vy - f_j.cy) / dist
                new_coords.append((vx + fx, vy + fy))
            f_i.coords = new_coords
            f_i.writeback_coords()

    def write_to_layer(self, output_layer: QgsVectorLayer) -> None:
        """Write distorted geometries into an existing memory layer."""
        lookup = {f.id: f for f in self.features}
        output_layer.startEditing()
        for feat in output_layer.getFeatures():
            if feat.id() in lookup:
                cf = lookup[feat.id()]
                new_geom = QgsGeometry.fromWkt(cf.wkt_str)
                if not new_geom.isNull():
                    output_layer.changeGeometry(feat.id(), new_geom)
        output_layer.commitChanges()
