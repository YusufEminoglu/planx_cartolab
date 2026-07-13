# -*- coding: utf-8 -*-
"""Bivariate Choropleth — Processing algorithm."""
from __future__ import annotations

import math

from qgis.core import (
    QgsFeature, QgsFeatureSink, QgsField, QgsFields,
    QgsProcessing, QgsProcessingAlgorithm, QgsProcessingException,
    QgsProcessingParameterFeatureSink, QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField, QgsProcessingParameterNumber,
    QgsProcessingParameterEnum, QgsProcessingLayerPostProcessorInterface,
    QgsProcessingParameterColor,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor

from ..core.bivariate_engine import (
    geometric_interval_breaks, fisher_jenks_breaks, bivariate_colour_matrix,
)
from ._help_mixin import CartoLabHelpMixin


class BivariateSymbologyPostProcessor(QgsProcessingLayerPostProcessorInterface):
    """Post-processor to automatically apply the bivariate NxN style to the output layer."""

    def __init__(self, n_classes: int, color_ll: str, color_lh: str, color_hl: str, color_hh: str):
        super().__init__()
        self.n_classes = n_classes
        self.color_ll = color_ll
        self.color_lh = color_lh
        self.color_hl = color_hl
        self.color_hh = color_hh

    def postProcessLayer(self, layer, context, feedback) -> None:
        if not layer:
            return

        from qgis.PyQt.QtGui import QColor
        from qgis.core import QgsCategorizedSymbolRenderer, QgsRendererCategory, QgsSymbol

        matrix = bivariate_colour_matrix(self.n_classes, self.color_ll, self.color_lh, self.color_hl, self.color_hh)
        categories = []

        for r in range(self.n_classes):
            for c in range(self.n_classes):
                val = f"({c},{r})"
                color = matrix[r][c]

                # Human-readable labels:
                label_parts = [f"X:{c+1}, Y:{r+1}"]
                if r == 0 and c == 0:
                    label_parts.append("(Low-Low)")
                elif r == 0 and c == self.n_classes - 1:
                    label_parts.append("(High-Low)")
                elif r == self.n_classes - 1 and c == 0:
                    label_parts.append("(Low-High)")
                elif r == self.n_classes - 1 and c == self.n_classes - 1:
                    label_parts.append("(High-High)")
                label = " ".join(label_parts)

                symbol = QgsSymbol.defaultSymbol(layer.geometryType())
                if symbol:
                    symbol.setColor(color)
                    # For polygon layers, use clean semi-transparent white outlines
                    if layer.geometryType() == 2:
                        for idx in range(symbol.symbolLayerCount()):
                            sl = symbol.symbolLayer(idx)
                            if hasattr(sl, 'setStrokeColor'):
                                sl.setStrokeColor(QColor(255, 255, 255, 140))
                            if hasattr(sl, 'setStrokeWidth'):
                                sl.setStrokeWidth(0.2)

                    cat = QgsRendererCategory(val, symbol, label)
                    categories.append(cat)

        renderer = QgsCategorizedSymbolRenderer("bivar_class", categories)
        layer.setRenderer(renderer)
        layer.triggerRepaint()


class BivariateChoroplethAlgorithm(CartoLabHelpMixin, QgsProcessingAlgorithm):
    INPUT = "INPUT"
    FIELD_X = "FIELD_X"
    FIELD_Y = "FIELD_Y"
    CLASSES = "CLASSES"
    METHOD = "METHOD"
    COLOR_LL = "COLOR_LL"
    COLOR_LH = "COLOR_LH"
    COLOR_HL = "COLOR_HL"
    COLOR_HH = "COLOR_HH"
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
            "bivar_class (string). The output layer is automatically styled with "
            "the computed bivariate colour matrix."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT, "Input layer", [QgsProcessing.SourceType.TypeVectorAnyGeometry]))
        self.addParameter(QgsProcessingParameterField(
            self.FIELD_X, "X-axis variable (column)", parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.DataType.Numeric))
        self.addParameter(QgsProcessingParameterField(
            self.FIELD_Y, "Y-axis variable (row)", parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.DataType.Numeric))
        self.addParameter(QgsProcessingParameterNumber(
            self.CLASSES, "Grid size (e.g. 4 = 4x4)", type=QgsProcessingParameterNumber.Type.Integer,
            minValue=2, defaultValue=4, maxValue=7))
        self.addParameter(QgsProcessingParameterEnum(
            self.METHOD, "Classification method",
            options=[m[0] for m in self.METHODS], defaultValue=0))
        self.addParameter(QgsProcessingParameterColor(
            self.COLOR_LL, "Low X - Low Y Colour", defaultValue=QColor("#e8e8e8")
        ))
        self.addParameter(QgsProcessingParameterColor(
            self.COLOR_LH, "Low X - High Y Colour", defaultValue=QColor("#5ab4ac")
        ))
        self.addParameter(QgsProcessingParameterColor(
            self.COLOR_HL, "High X - Low Y Colour", defaultValue=QColor("#d8b365")
        ))
        self.addParameter(QgsProcessingParameterColor(
            self.COLOR_HH, "High X - High Y Colour", defaultValue=QColor("#8c510a")
        ))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, "Bivariate output"))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        field_x = self.parameterAsString(parameters, self.FIELD_X, context)
        field_y = self.parameterAsString(parameters, self.FIELD_Y, context)
        n_classes = self.parameterAsInt(parameters, self.CLASSES, context)
        method_idx = self.parameterAsEnum(parameters, self.METHOD, context)
        method = self.METHODS[method_idx][1]

        color_ll_q = self.parameterAsColor(parameters, self.COLOR_LL, context)
        color_lh_q = self.parameterAsColor(parameters, self.COLOR_LH, context)
        color_hl_q = self.parameterAsColor(parameters, self.COLOR_HL, context)
        color_hh_q = self.parameterAsColor(parameters, self.COLOR_HH, context)

        color_ll = color_ll_q.name()
        color_lh = color_lh_q.name()
        color_hl = color_hl_q.name()
        color_hh = color_hh_q.name()

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
            sink.addFeature(new_feat, QgsFeatureSink.Flag.FastInsert)
            feedback.setProgress(int(100 * current / total))

        # Register post-processor for automatic layer styling
        try:
            if context.willLoadLayerOnCompletion(dest_id):
                layer_details = context.layerToLoadOnCompletionDetails(dest_id)
                layer_details.setPostProcessor(BivariateSymbologyPostProcessor(n_classes, color_ll, color_lh, color_hl, color_hh))
            elif context.willLoadLayerOnCompletion(self.OUTPUT):
                layer_details = context.layerToLoadOnCompletionDetails(self.OUTPUT)
                layer_details.setPostProcessor(BivariateSymbologyPostProcessor(n_classes, color_ll, color_lh, color_hl, color_hh))
        except Exception as exc:
            feedback.pushWarning(f"Could not apply automatic bivariate symbology: {exc}")

        return {self.OUTPUT: dest_id}


def _break_index(value: float, breaks: list) -> int:
    for i in range(len(breaks) - 1):
        if breaks[i] <= value < breaks[i + 1]:
            return i
    return len(breaks) - 2
