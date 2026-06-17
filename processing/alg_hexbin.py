# -*- coding: utf-8 -*-
"""Hexbin Aggregation — Processing algorithm."""
from __future__ import annotations

import math

from qgis.core import (
    QgsFeature, QgsFeatureSink, QgsField, QgsFields, QgsGeometry, QgsPointXY,
    QgsProcessing, QgsProcessingAlgorithm, QgsProcessingException,
    QgsProcessingParameterEnum, QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource, QgsProcessingParameterField,
    QgsProcessingParameterNumber, QgsWkbTypes,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor

from ..core.hexgrid import point_to_cell, cell_center, hex_vertices


class HexbinAlgorithm(QgsProcessingAlgorithm):
    INPUT = "INPUT"
    CELL_SIZE = "CELL_SIZE"
    WEIGHT = "WEIGHT"
    STAT = "STAT"
    OUTPUT = "OUTPUT"

    STATS = [("Count", "count"), ("Sum of weight", "sum"), ("Mean of weight", "mean")]

    def name(self) -> str:
        return "hexbin_aggregate"

    def displayName(self) -> str:
        return "Hexbin Aggregation"

    def group(self) -> str:
        return "Aggregation"

    def groupId(self) -> str:
        return "aggregation"

    def createInstance(self):
        return HexbinAlgorithm()

    def shortHelpString(self) -> str:
        return (
            "Aggregate a point layer into a pointy-top hexagonal grid. Only hexagons "
            "that actually contain points are emitted, so dense scatter plots become "
            "a clean, overplot-free density surface.\n\n"
            "Statistic: count of points, sum of a weight field, or mean of a weight "
            "field. Output carries hex_count, hex_sum and hex_mean and is graduated "
            "on the chosen statistic.\n\n"
            "Cell size is the hexagon radius in the layer's map units."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT, "Input point layer", [QgsProcessing.TypeVectorPoint]))
        self.addParameter(QgsProcessingParameterNumber(
            self.CELL_SIZE, "Hexagon radius (map units)",
            type=QgsProcessingParameterNumber.Double, defaultValue=1000.0, minValue=1e-9))
        self.addParameter(QgsProcessingParameterField(
            self.WEIGHT, "Weight field (for sum / mean)", parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Numeric, optional=True))
        self.addParameter(QgsProcessingParameterEnum(
            self.STAT, "Statistic", options=[s[0] for s in self.STATS], defaultValue=0))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, "Hexbin output", QgsProcessing.TypeVectorPolygon))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        size = self.parameterAsDouble(parameters, self.CELL_SIZE, context)
        weight_field = self.parameterAsString(parameters, self.WEIGHT, context)
        stat = self.STATS[self.parameterAsEnum(parameters, self.STAT, context)][1]

        if stat in ("sum", "mean") and not weight_field:
            raise QgsProcessingException(
                f"Statistic '{stat}' needs a weight field. Pick one or use 'Count'.")

        # bin points
        bins = {}  # (q, r) -> [count, sum_weight]
        total = source.featureCount() or 1
        for current, feat in enumerate(source.getFeatures()):
            if feedback.isCanceled():
                break
            geom = feat.geometry()
            if geom is None or geom.isEmpty():
                continue
            pt = geom.centroid().asPoint()
            cell = point_to_cell(pt.x(), pt.y(), size)
            w = 1.0
            if weight_field:
                try:
                    w = float(feat[weight_field])
                except (TypeError, ValueError):
                    w = float("nan")
                if not math.isfinite(w):
                    # skip non-finite weights for sum/mean, but still count
                    w = None
            entry = bins.setdefault(cell, [0, 0.0])
            entry[0] += 1
            if w is not None:
                entry[1] += w
            feedback.setProgress(int(50 * current / total))

        out_fields = QgsFields()
        out_fields.append(QgsField("hex_q", QVariant.Int))
        out_fields.append(QgsField("hex_r", QVariant.Int))
        out_fields.append(QgsField("hex_count", QVariant.Int))
        out_fields.append(QgsField("hex_sum", QVariant.Double))
        out_fields.append(QgsField("hex_mean", QVariant.Double))

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            out_fields, QgsWkbTypes.Polygon, source.sourceCrs(),
        )

        stat_field = {"count": "hex_count", "sum": "hex_sum", "mean": "hex_mean"}[stat]
        stat_values = []
        n_cells = len(bins) or 1
        for idx, ((q, r), (count, wsum)) in enumerate(bins.items()):
            cx, cy = cell_center(q, r, size)
            ring = [QgsPointXY(x, y) for (x, y) in hex_vertices(cx, cy, size)]
            ring.append(ring[0])
            nf = QgsFeature(out_fields)
            nf.setGeometry(QgsGeometry.fromPolygonXY([ring]))
            mean = wsum / count if count else 0.0
            nf.setAttributes([q, r, count, wsum, mean])
            sink.addFeature(nf, QgsFeatureSink.FastInsert)
            stat_values.append(count if stat == "count" else (wsum if stat == "sum" else mean))
            feedback.setProgress(50 + int(50 * idx / n_cells))

        feedback.pushInfo(f"Aggregated {total} points into {len(bins)} hexagons (statistic: {stat}).")

        try:
            out_layer = context.getMapLayer(dest_id)
            if out_layer and stat_values:
                _apply_graduated(out_layer, stat_field, min(stat_values), max(stat_values))
        except Exception:
            pass

        return {self.OUTPUT: dest_id}


def _apply_graduated(layer, field, vmin, vmax):
    """Apply a 5-class viridis-ish graduated renderer on ``field``."""
    from qgis.core import (
        QgsGraduatedSymbolRenderer, QgsRendererRange, QgsSymbol,
    )
    colours = [
        QColor("#440154"), QColor("#3b528b"), QColor("#21918c"),
        QColor("#5ec962"), QColor("#fde725"),
    ]
    n = len(colours)
    span = (vmax - vmin) or 1.0
    ranges = []
    for i in range(n):
        lo = vmin + span * i / n
        hi = vmin + span * (i + 1) / n
        sym = QgsSymbol.defaultSymbol(layer.geometryType())
        sym.setColor(colours[i])
        sym.setOpacity(0.9)
        ranges.append(QgsRendererRange(lo, hi, sym, f"{lo:.2f} – {hi:.2f}"))
    renderer = QgsGraduatedSymbolRenderer(field, ranges)
    renderer.setMode(QgsGraduatedSymbolRenderer.Custom)
    layer.setRenderer(renderer)
    layer.triggerRepaint()
