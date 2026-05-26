# -*- coding: utf-8 -*-
"""Bivariate Choropleth — Processing algorithm."""
from __future__ import annotations

import math

from qgis.core import (
    QgsFeature, QgsFeatureSink, QgsField, QgsFields,
    QgsProcessing, QgsProcessingAlgorithm, QgsProcessingException,
    QgsProcessingParameterFeatureSink, QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField, QgsProcessingParameterNumber,
    QgsProcessingParameterEnum,
)
from qgis.PyQt.QtCore import QVariant

from ..core.bivariate_engine import (
    geometric_interval_breaks, fisher_jenks_breaks, bivariate_colour_matrix,
)


class BivariateChoroplethAlgorithm(QgsProcessingAlgorithm):
    INPUT = "INPUT"
    FIELD_X = "FIELD_X"
    FIELD_Y = "FIELD_Y"
    CLASSES = "CLASSES"
    METHOD = "METHOD"
    OUTPUT = "OUTPUT"

    METHODS = [("Geometric Interval", "geometric"), ("Fisher-Jenks", "fisher_jenks")]

    def name(self) -> str:
        return "bivariate_choropleth"

    def displayName(self) -> str:
        return "Bivariate Choropleth Map"

    def group(self) -> str:
        return "Thematic Mapping"

    def groupId(self) -> str:
        return "thematic_mapping"

    def createInstance(self):
        return BivariateChoroplethAlgorithm()

    def shortHelpString(self) -> str:
        return (
            "Create a bivariate choropleth map by classifying two numeric fields "
            "into an NxN colour matrix.\n\n"
            "Output adds three fields: bivar_x_class (int), bivar_y_class (int), "
            "bivar_class (string). Use bivar_class for symbology."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT, "Input layer", [QgsProcessing.TypeVectorAnyGeometry]))
        self.addParameter(QgsProcessingParameterField(
            self.FIELD_X, "X-axis variable (column)", parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Numeric))
        self.addParameter(QgsProcessingParameterField(
            self.FIELD_Y, "Y-axis variable (row)", parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Numeric))
        self.addParameter(QgsProcessingParameterNumber(
            self.CLASSES, "Grid size (e.g. 4 = 4x4)", type=QgsProcessingParameterNumber.Integer,
            minValue=2, defaultValue=4, maxValue=7))
        self.addParameter(QgsProcessingParameterEnum(
            self.METHOD, "Classification method",
            options=[m[0] for m in self.METHODS], defaultValue=0))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, "Bivariate output"))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        field_x = self.parameterAsString(parameters, self.FIELD_X, context)
        field_y = self.parameterAsString(parameters, self.FIELD_Y, context)
        n_classes = self.parameterAsInt(parameters, self.CLASSES, context)
        method_idx = self.parameterAsEnum(parameters, self.METHOD, context)
        method = self.METHODS[method_idx][1]

        # collect paired values
        x_vals, y_vals = [], []
        features_raw = []
        for feat in source.getFeatures():
            xv = feat[field_x]
            yv = feat[field_y]
            if xv is not None and yv is not None and math.isfinite(float(xv)) and math.isfinite(float(yv)):
                x_vals.append(float(xv))
                y_vals.append(float(yv))
                features_raw.append(feat)

        if not x_vals:
            raise QgsProcessingException("No valid paired numeric values found.")

        classify_fn = geometric_interval_breaks if method == "geometric" else fisher_jenks_breaks
        x_breaks = classify_fn(x_vals, n_classes)
        y_breaks = classify_fn(y_vals, n_classes)

        feedback.pushInfo(
            f"X breaks ({field_x}): {[round(b, 4) for b in x_breaks]}\n"
            f"Y breaks ({field_y}): {[round(b, 4) for b in y_breaks]}"
        )

        # Build output schema with bivariate fields
        out_fields = QgsFields()
        for f in source.fields():
            out_fields.append(QgsField(f.name(), f.type()))
        out_fields.append(QgsField("bivar_x_class", QVariant.Int))
        out_fields.append(QgsField("bivar_y_class", QVariant.Int))
        out_fields.append(QgsField("bivar_class", QVariant.String))

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            out_fields, source.wkbType(), source.sourceCrs(),
        )

        total = len(features_raw)
        for current, feat in enumerate(features_raw):
            if feedback.isCanceled():
                break
            col_idx = _break_index(float(feat[field_x]), x_breaks)
            row_idx = _break_index(float(feat[field_y]), y_breaks)

            attrs = feat.attributes()[:]
            attrs.append(col_idx)
            attrs.append(row_idx)
            attrs.append(f"({col_idx},{row_idx})")

            new_feat = QgsFeature(out_fields)
            new_feat.setGeometry(feat.geometry())
            new_feat.setAttributes(attrs)
            sink.addFeature(new_feat, QgsFeatureSink.FastInsert)
            feedback.setProgress(int(100 * current / total))

        return {self.OUTPUT: dest_id}


def _break_index(value: float, breaks: list) -> int:
    for i in range(len(breaks) - 1):
        if breaks[i] <= value < breaks[i + 1]:
            return i
    return len(breaks) - 2
