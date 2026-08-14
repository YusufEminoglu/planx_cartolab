# -*- coding: utf-8 -*-
"""Proportional Symbols — Processing algorithm."""
from __future__ import annotations

from contextlib import suppress

import math

from qgis.core import (
    QgsFeature, QgsFeatureSink, QgsField, QgsFields, QgsProcessing,
    QgsProcessingAlgorithm, QgsProcessingException,
    QgsProcessingParameterBoolean, QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource, QgsProcessingParameterField,
    QgsProcessingParameterNumber, QgsWkbTypes,
)
from qgis.PyQt.QtCore import QVariant

from ..core.utils import safe_float
from ..core import proportional_symbols as ps
from ._help_mixin import CartoLabHelpMixin


class ProportionalSymbolsAlgorithm(CartoLabHelpMixin, QgsProcessingAlgorithm):
    _ICON_NAME = "proportional.png"
    INPUT = "INPUT"
    FIELD = "FIELD"
    MAX_SIZE = "MAX_SIZE"
    MIN_SIZE = "MIN_SIZE"
    FLANNERY = "FLANNERY"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        return "proportional_symbols"

    def displayName(self) -> str:
        return "Proportional Symbols (Flannery)"

    def group(self) -> str:
        return "Thematic Mapping"

    def groupId(self) -> str:
        return "thematic_mapping"

    def createInstance(self):
        return ProportionalSymbolsAlgorithm()

    def shortHelpString(self) -> str:
        return (
            "Convert any vector layer to point symbols sized proportionally to a "
            "numeric field, using Flannery perceptual compensation by default.\n\n"
            "Readers systematically under-estimate circle area; Flannery scaling "
            "(exponent ~0.57) compensates so visual perception matches true data "
            "ratios.\n\n"
            "Outputs point geometries at centroids with 'psym_value' and 'psym_size' "
            "(symbol size in mm) fields, styled automatically with a nested legend."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT, "Input layer", [QgsProcessing.SourceType.TypeVectorAnyGeometry]))
        self.addParameter(QgsProcessingParameterField(
            self.FIELD, "Magnitude field", parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.DataType.Numeric))
        self.addParameter(QgsProcessingParameterNumber(
            self.MAX_SIZE, "Maximum symbol size (mm)",
            type=QgsProcessingParameterNumber.Type.Double, defaultValue=16.0, minValue=1.0))
        self.addParameter(QgsProcessingParameterNumber(
            self.MIN_SIZE, "Minimum symbol size (mm)",
            type=QgsProcessingParameterNumber.Type.Double, defaultValue=2.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterBoolean(
            self.FLANNERY, "Apply Flannery perceptual compensation", defaultValue=True))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, "Proportional symbols output", QgsProcessing.SourceType.TypeVectorPoint))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        field_name = self.parameterAsString(parameters, self.FIELD, context)
        max_size = self.parameterAsDouble(parameters, self.MAX_SIZE, context)
        min_size = self.parameterAsDouble(parameters, self.MIN_SIZE, context)
        flannery = self.parameterAsBool(parameters, self.FLANNERY, context)

        values = []
        features_raw = []
        for feat in source.getFeatures():
            fv = safe_float(feat[field_name])
            if fv is not None:
                values.append(fv)
            features_raw.append(feat)

        if not values:
            raise QgsProcessingException(f"No valid numeric values in field '{field_name}'.")

        v_max = max(values)
        v_min = min(values)

        out_fields = QgsFields()
        for f in source.fields():
            out_fields.append(QgsField(f.name(), f.type()))
        out_fields.append(QgsField("psym_value", QVariant.Double))
        out_fields.append(QgsField("psym_size", QVariant.Double))

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            out_fields, QgsWkbTypes.Type.Point, source.sourceCrs(),
        )

        total = len(features_raw) or 1
        for current, feat in enumerate(features_raw):
            if feedback.isCanceled():
                break
            geom = feat.geometry()
            if geom is None or geom.isEmpty():
                continue
            fv = safe_float(feat[field_name], 0.0)
            size = ps.symbol_size(fv, v_max, max_size, min_size, flannery)
            attrs = feat.attributes()[:]
            attrs.append(fv)
            attrs.append(size)
            nf = QgsFeature(out_fields)
            nf.setGeometry(geom.pointOnSurface())
            nf.setAttributes(attrs)
            sink.addFeature(nf, QgsFeatureSink.Flag.FastInsert)
            feedback.setProgress(int(100 * current / total))

        legend = ps.nice_legend_values(v_min, v_max, 3)
        feedback.pushInfo(
            f"Value range [{v_min:g}, {v_max:g}]. "
            f"Suggested legend circles: {', '.join(f'{v:g}' for v in legend) or 'n/a'}."
        )

        with suppress(Exception):
            out_layer = context.getMapLayer(dest_id)
            if out_layer:
                from qgis.core import QgsMarkerSymbol, QgsSingleSymbolRenderer, QgsProperty
                symbol = QgsMarkerSymbol.createSimple({
                    "name": "circle", "color": "227,142,79,180",
                    "outline_color": "120,66,20,220", "outline_width": "0.3",
                })
                symbol.setDataDefinedSize(QgsProperty.fromField("psym_size"))
                out_layer.setRenderer(QgsSingleSymbolRenderer(symbol))
                out_layer.triggerRepaint()

        return {self.OUTPUT: dest_id}
