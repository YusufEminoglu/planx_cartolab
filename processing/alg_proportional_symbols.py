# -*- coding: utf-8 -*-
"""Proportional Symbols — Processing algorithm."""
from __future__ import annotations

import math

from qgis.core import (
    QgsFeature, QgsFeatureSink, QgsField, QgsFields, QgsProcessing,
    QgsProcessingAlgorithm, QgsProcessingException,
    QgsProcessingParameterBoolean, QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource, QgsProcessingParameterField,
    QgsProcessingParameterNumber, QgsWkbTypes,
)
from qgis.PyQt.QtCore import QVariant

from ..core.proportional_symbols import symbol_size, nice_legend_values
from ._help_mixin import CartoLabHelpMixin


class ProportionalSymbolsAlgorithm(QgsProcessingAlgorithm, CartoLabHelpMixin):
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
            "Place a point at each feature whose symbol size is proportional to a "
            "numeric field.\n\n"
            "Flannery compensation (size = value ** 0.5716) corrects the fact that "
            "readers under-estimate circle area, so big values are not perceived as "
            "too small. Disable it for true area-proportional scaling.\n\n"
            "Adds a 'psym_size' field (mm) used as data-defined marker size, and "
            "prints suggested nested-legend values."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT, "Input layer", [QgsProcessing.TypeVectorAnyGeometry]))
        self.addParameter(QgsProcessingParameterField(
            self.FIELD, "Magnitude field", parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Numeric))
        self.addParameter(QgsProcessingParameterNumber(
            self.MAX_SIZE, "Maximum symbol size (mm)",
            type=QgsProcessingParameterNumber.Double, defaultValue=12.0, minValue=0.1))
        self.addParameter(QgsProcessingParameterNumber(
            self.MIN_SIZE, "Minimum symbol size (mm)",
            type=QgsProcessingParameterNumber.Double, defaultValue=1.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterBoolean(
            self.FLANNERY, "Apply Flannery perceptual compensation", defaultValue=True))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, "Proportional symbols output", QgsProcessing.TypeVectorPoint))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        field_name = self.parameterAsString(parameters, self.FIELD, context)
        max_size = self.parameterAsDouble(parameters, self.MAX_SIZE, context)
        min_size = self.parameterAsDouble(parameters, self.MIN_SIZE, context)
        flannery = self.parameterAsBool(parameters, self.FLANNERY, context)

        features_raw = []
        values = []
        for feat in source.getFeatures():
            v = feat[field_name]
            try:
                fv = float(v)
            except (TypeError, ValueError):
                fv = None
            if fv is not None and math.isfinite(fv):
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
            out_fields, QgsWkbTypes.Point, source.sourceCrs(),
        )

        total = len(features_raw) or 1
        for current, feat in enumerate(features_raw):
            if feedback.isCanceled():
                break
            geom = feat.geometry()
            if geom is None or geom.isEmpty():
                continue
            try:
                fv = float(feat[field_name])
            except (TypeError, ValueError):
                fv = 0.0
            size = symbol_size(fv, v_max, max_size, min_size, flannery)
            attrs = feat.attributes()[:]
            attrs.append(fv if math.isfinite(fv) else None)
            attrs.append(size)
            nf = QgsFeature(out_fields)
            nf.setGeometry(geom.pointOnSurface())
            nf.setAttributes(attrs)
            sink.addFeature(nf, QgsFeatureSink.FastInsert)
            feedback.setProgress(int(100 * current / total))

        legend = nice_legend_values(v_min, v_max, 3)
        feedback.pushInfo(
            f"Value range [{v_min:g}, {v_max:g}]. "
            f"Suggested legend circles: {', '.join(f'{v:g}' for v in legend) or 'n/a'}."
        )

        try:
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
        except Exception:
            pass

        return {self.OUTPUT: dest_id}
