# -*- coding: utf-8 -*-
"""Value-by-Alpha — Processing algorithm."""
from __future__ import annotations

from qgis.core import (
    QgsFeatureSink,
    QgsField,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterNumber,
)
from qgis.PyQt.QtCore import QVariant

from ..core.bivariate_engine import compute_alpha_values


class ValueByAlphaAlgorithm(QgsProcessingAlgorithm):
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
            "The primary variable determines the colour (hue), while the "
            "secondary reliability variable controls opacity:\n"
            "  - High reliability → opaque, visually dominant\n"
            "  - Low reliability → transparent, fades into background\n\n"
            "This prevents misleading conclusions from low-confidence data "
            "(e.g. small sample sizes, high standard error, model uncertainty)."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(self.INPUT, "Input layer", [QgsProcessing.TypeVectorAnyGeometry])
        )
        self.addParameter(
            QgsProcessingParameterField(self.FIELD_COLOUR, "Primary variable (colour)",
                                         parentLayerParameterName=self.INPUT,
                                         type=QgsProcessingParameterField.Numeric)
        )
        self.addParameter(
            QgsProcessingParameterField(self.FIELD_ALPHA, "Reliability variable (opacity)",
                                         parentLayerParameterName=self.INPUT,
                                         type=QgsProcessingParameterField.Numeric)
        )
        self.addParameter(
            QgsProcessingParameterNumber(self.ALPHA_MIN, "Minimum opacity (least reliable)",
                                          type=QgsProcessingParameterNumber.Integer,
                                          defaultValue=25, minValue=0, maxValue=255)
        )
        self.addParameter(
            QgsProcessingParameterNumber(self.ALPHA_MAX, "Maximum opacity (most reliable)",
                                          type=QgsProcessingParameterNumber.Integer,
                                          defaultValue=255, minValue=0, maxValue=255)
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, "VbA output")
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        colour_field = self.parameterAsString(parameters, self.FIELD_COLOUR, context)
        alpha_field = self.parameterAsString(parameters, self.FIELD_ALPHA, context)
        alpha_min = self.parameterAsInt(parameters, self.ALPHA_MIN, context)
        alpha_max = self.parameterAsInt(parameters, self.ALPHA_MAX, context)

        # gather values
        primary_vals, reliability_vals = [], []
        features_data = []
        for feat in source.getFeatures():
            pv = feat[colour_field]
            rv = feat[alpha_field]
            if pv is not None and rv is not None:
                primary_vals.append(float(pv))
                reliability_vals.append(float(rv))
            else:
                primary_vals.append(0.0)
                reliability_vals.append(0.0)
            features_data.append(feat)

        if not primary_vals:
            raise QgsProcessingException("No valid values found.")

        alpha_values = compute_alpha_values(primary_vals, reliability_vals, alpha_min, alpha_max)

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            source.fields(), source.wkbType(), source.sourceCrs(),
        )

        total = len(features_data)
        for i, feat in enumerate(features_data):
            if feedback.isCanceled():
                break
            new_feat = feat.clone()
            new_feat["vba_alpha"] = alpha_values[i]
            new_feat["vba_alpha_pct"] = int(100 * alpha_values[i] / 255)
            sink.addFeature(new_feat, QgsFeatureSink.FastInsert)
            feedback.setProgress(int(100 * i / total))

        feedback.pushInfo(
            f"VbA processing complete. Alpha range: [{alpha_min}, {alpha_max}].\n"
            f"Use the 'vba_alpha' field to drive layer opacity in the symbology panel."
        )
        return {self.OUTPUT: dest_id}
