# -*- coding: utf-8 -*-
"""Bivariate Choropleth — Processing algorithm."""
from __future__ import annotations

from qgis.core import (
    QgsFeatureSink,
    QgsFeature,
    QgsField,
    QgsGraduatedSymbolRenderer,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum,
    QgsRendererRange,
    QgsSymbol,
    QgsVectorLayer,
    QgsProject,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor

from ..core.bivariate_engine import (
    geometric_interval_breaks,
    fisher_jenks_breaks,
    bivariate_colour_matrix,
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
            "into an N×N colour matrix. Each feature is assigned a compound "
            "colour from the bilinear-interpolated legend matrix.\n\n"
            "The output layer retains all source fields plus a 'bivar_class' "
            "string field encoding the (row,col) assignment."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT, "Input layer", [QgsProcessing.TypeVectorAnyGeometry]
            )
        )
        self.addParameter(
            QgsProcessingParameterField(self.FIELD_X, "X-axis variable (column)",
                                         parentLayerParameterName=self.INPUT,
                                         type=QgsProcessingParameterField.Numeric)
        )
        self.addParameter(
            QgsProcessingParameterField(self.FIELD_Y, "Y-axis variable (row)",
                                         parentLayerParameterName=self.INPUT,
                                         type=QgsProcessingParameterField.Numeric)
        )
        self.addParameter(
            QgsProcessingParameterNumber(self.CLASSES, "Grid size (e.g. 4 → 4×4)",
                                          type=QgsProcessingParameterNumber.Integer,
                                          minValue=2, defaultValue=4, maxValue=7)
        )
        self.addParameter(
            QgsProcessingParameterEnum(self.METHOD, "Classification method",
                                        options=[m[0] for m in self.METHODS], defaultValue=0)
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, "Bivariate output")
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        field_x = self.parameterAsString(parameters, self.FIELD_X, context)
        field_y = self.parameterAsString(parameters, self.FIELD_Y, context)
        n_classes = self.parameterAsInt(parameters, self.CLASSES, context)
        method_idx = self.parameterAsEnum(parameters, self.METHOD, context)

        method = self.METHODS[method_idx][1]

        # collect paired values
        x_vals, y_vals = [], []
        for feat in source.getFeatures():
            xv = feat[field_x]
            yv = feat[field_y]
            if xv is not None and yv is not None:
                x_vals.append(float(xv))
                y_vals.append(float(yv))

        if not x_vals:
            raise QgsProcessingException("No valid paired values found.")

        # classify each axis
        classify = geometric_interval_breaks if method == "geometric" else fisher_jenks_breaks
        x_breaks = classify(x_vals, n_classes)
        y_breaks = classify(y_vals, n_classes)

        feedback.pushInfo(
            f"X breaks ({field_x}): {[round(b, 4) for b in x_breaks]}\n"
            f"Y breaks ({field_y}): {[round(b, 4) for b in y_breaks]}"
        )

        # colour matrix
        colour_matrix = bivariate_colour_matrix(n_classes)

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            source.fields(), source.wkbType(), source.sourceCrs(),
        )

        total = source.featureCount() or 1
        for current, feat in enumerate(source.getFeatures()):
            if feedback.isCanceled():
                break
            xv = feat[field_x]
            yv = feat[field_y]
            if xv is None or yv is None:
                col_idx, row_idx = 0, 0
            else:
                col_idx = _break_index(float(xv), x_breaks)
                row_idx = _break_index(float(yv), y_breaks)

            colour = colour_matrix[row_idx][col_idx]

            new_feat = feat.clone()
            new_feat["bivar_x_class"] = col_idx
            new_feat["bivar_y_class"] = row_idx
            new_feat["bivar_class"] = f"({col_idx},{row_idx})"
            sink.addFeature(new_feat, QgsFeatureSink.FastInsert)
            feedback.setProgress(int(100 * current / total))

        return {self.OUTPUT: dest_id}


def _break_index(value: float, breaks: list) -> int:
    for i in range(len(breaks) - 1):
        if breaks[i] <= value < breaks[i + 1]:
            return i
    return len(breaks) - 2
