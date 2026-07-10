# -*- coding: utf-8 -*-
"""Value-by-Alpha — Processing algorithm."""
from __future__ import annotations

import math

from qgis.core import (
    QgsFeature, QgsFeatureSink, QgsField, QgsFields,
    QgsProcessing, QgsProcessingAlgorithm, QgsProcessingException,
    QgsProcessingParameterFeatureSink, QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField, QgsProcessingParameterNumber,
)
from qgis.PyQt.QtCore import QVariant

from ..core.bivariate_engine import compute_alpha_values
from ._help_mixin import CartoLabHelpMixin


class ValueByAlphaAlgorithm(CartoLabHelpMixin, QgsProcessingAlgorithm):
    INPUT = "INPUT"
    FIELD_COLOUR = "FIELD_COLOUR"
    FIELD_ALPHA = "FIELD_ALPHA"
    ALPHA_MIN = "ALPHA_MIN"
    ALPHA_MAX = "ALPHA_MAX"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        return "value_by_alpha"

    def displayName(self) -> str:
        return "Value-by-Alpha (VbA) Map"

    def group(self) -> str:
        return "Thematic Mapping"

    def groupId(self) -> str:
        return "thematic_mapping"

    def createInstance(self):
        return ValueByAlphaAlgorithm()

    def shortHelpString(self) -> str:
        return (
            "Encode uncertainty/reliability as opacity (alpha channel).\n\n"
            "Primary variable drives colour; secondary reliability variable "
            "controls opacity. High reliability = opaque; low = transparent.\n"
            "Adds 'vba_alpha' (0-255) and 'vba_alpha_pct' (0-100) fields."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT, "Input layer", [QgsProcessing.TypeVectorAnyGeometry]))
        self.addParameter(QgsProcessingParameterField(
            self.FIELD_COLOUR, "Primary variable (colour)", parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Numeric))
        self.addParameter(QgsProcessingParameterField(
            self.FIELD_ALPHA, "Reliability variable (opacity)", parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Numeric))
        self.addParameter(QgsProcessingParameterNumber(
            self.ALPHA_MIN, "Minimum opacity (least reliable)",
            type=QgsProcessingParameterNumber.Integer,
            defaultValue=25, minValue=0, maxValue=255))
        self.addParameter(QgsProcessingParameterNumber(
            self.ALPHA_MAX, "Maximum opacity (most reliable)",
            type=QgsProcessingParameterNumber.Integer,
            defaultValue=255, minValue=0, maxValue=255))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, "VbA output"))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        colour_field = self.parameterAsString(parameters, self.FIELD_COLOUR, context)
        alpha_field = self.parameterAsString(parameters, self.FIELD_ALPHA, context)
        alpha_min = self.parameterAsInt(parameters, self.ALPHA_MIN, context)
        alpha_max = self.parameterAsInt(parameters, self.ALPHA_MAX, context)

        primary_vals = []
        reliability_vals = []
        features_raw = []
        for feat in source.getFeatures():
            pv = feat[colour_field]
            rv = feat[alpha_field]
            pv_ok = pv is not None and math.isfinite(float(pv))
            rv_ok = rv is not None and math.isfinite(float(rv))
            primary_vals.append(float(pv) if pv_ok else 0.0)
            reliability_vals.append(float(rv) if rv_ok else 0.0)
            features_raw.append(feat)

        if not features_raw:
            raise QgsProcessingException("No features in input layer.")

        alpha_values = compute_alpha_values(primary_vals, reliability_vals, alpha_min, alpha_max)

        # Build output schema
        out_fields = QgsFields()
        for f in source.fields():
            out_fields.append(QgsField(f.name(), f.type()))
        out_fields.append(QgsField("vba_alpha", QVariant.Int))
        out_fields.append(QgsField("vba_alpha_pct", QVariant.Int))

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            out_fields, source.wkbType(), source.sourceCrs(),
        )

        total = len(features_raw)
        for i, feat in enumerate(features_raw):
            if feedback.isCanceled():
                break
            attrs = feat.attributes()[:]
            attrs.append(alpha_values[i])
            attrs.append(int(100 * alpha_values[i] / 255))

            new_feat = QgsFeature(out_fields)
            new_feat.setGeometry(feat.geometry())
            new_feat.setAttributes(attrs)
            sink.addFeature(new_feat, QgsFeatureSink.FastInsert)
            feedback.setProgress(int(100 * i / total))

        feedback.pushInfo(
            f"VbA complete. Alpha range [{alpha_min}, {alpha_max}]. "
            "Use 'vba_alpha' to drive layer opacity in symbology."
        )
        return {self.OUTPUT: dest_id}
