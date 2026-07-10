# -*- coding: utf-8 -*-
"""Adaptive Geometric Interval Classification — Processing algorithm."""
from __future__ import annotations

import math

from qgis.core import (
    QgsClassificationCustom, QgsFeature, QgsFeatureSink, QgsField, QgsFields,
    QgsGraduatedSymbolRenderer, QgsProcessing, QgsProcessingAlgorithm,
    QgsProcessingException, QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource, QgsProcessingParameterField,
    QgsProcessingParameterNumber, QgsProcessingParameterEnum,
    QgsRendererRange, QgsSymbol,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor

from ..core.bivariate_engine import (
    geometric_interval_breaks, head_tail_breaks, fisher_jenks_breaks,
)
from ._help_mixin import CartoLabHelpMixin


class GeometricIntervalAlgorithm(CartoLabHelpMixin, QgsProcessingAlgorithm):
    INPUT = "INPUT"
    FIELD = "FIELD"
    CLASSES = "CLASSES"
    METHOD = "METHOD"
    OUTPUT = "OUTPUT"

    METHODS = [
        ("Adaptive Geometric Interval (GIC)", "geometric"),
        ("Head/Tail Breaks", "head_tail"),
        ("Fisher-Jenks Natural Breaks", "fisher_jenks"),
    ]

    def name(self) -> str:
        return "geometric_interval_classification"

    def displayName(self) -> str:
        return "Advanced Classification (GIC / Head-Tail / Fisher-Jenks)"

    def group(self) -> str:
        return "Classification"

    def groupId(self) -> str:
        return "classification"

    def createInstance(self):
        return GeometricIntervalAlgorithm()

    def shortHelpString(self) -> str:
        return (
            "Classify a numeric field using one of three advanced algorithms.\n\n"
            "  - Adaptive GIC: optimal for skewed continuous data\n"
            "  - Head/Tail Breaks: for heavy-tailed / power-law distributions\n"
            "  - Fisher-Jenks: natural breaks minimising within-class variance\n\n"
            "Adds a 'gic_class' integer field (0-based class index) to the output."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT, "Input layer", [QgsProcessing.TypeVectorAnyGeometry]))
        self.addParameter(QgsProcessingParameterField(
            self.FIELD, "Field to classify", parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Numeric))
        self.addParameter(QgsProcessingParameterNumber(
            self.CLASSES, "Number of classes", type=QgsProcessingParameterNumber.Integer,
            minValue=2, defaultValue=5, maxValue=20))
        self.addParameter(QgsProcessingParameterEnum(
            self.METHOD, "Classification method",
            options=[m[0] for m in self.METHODS], defaultValue=0))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, "Classified output"))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        field_name = self.parameterAsString(parameters, self.FIELD, context)
        n_classes = self.parameterAsInt(parameters, self.CLASSES, context)
        method_idx = self.parameterAsEnum(parameters, self.METHOD, context)
        method = self.METHODS[method_idx][1]

        values = []
        features_raw = []
        for feat in source.getFeatures():
            val = feat[field_name]
            if val is not None and math.isfinite(float(val)):
                values.append(float(val))
                features_raw.append(feat)

        if not values:
            raise QgsProcessingException(f"No valid numeric values in field '{field_name}'.")

        feedback.pushInfo(f"Classifying {len(values)} values using {method} into {n_classes} classes.")

        if method == "geometric":
            breaks = geometric_interval_breaks(values, n_classes)
        elif method == "head_tail":
            breaks = head_tail_breaks(values)
        elif method == "fisher_jenks":
            breaks = fisher_jenks_breaks(values, n_classes)
        else:
            raise QgsProcessingException(f"Unknown method: {method}")

        feedback.pushInfo(f"Breaks: {[round(b, 4) for b in breaks]}")

        # Build output field schema
        out_fields = QgsFields()
        for f in source.fields():
            out_fields.append(QgsField(f.name(), f.type()))
        out_fields.append(QgsField("gic_class", QVariant.Int))
        out_fields.append(QgsField("gic_label", QVariant.String))

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            out_fields, source.wkbType(), source.sourceCrs(),
        )

        labels = ["Very Low", "Low", "Medium", "High", "Very High"]
        total = len(features_raw)
        for current, feat in enumerate(features_raw):
            if feedback.isCanceled():
                break
            val = float(feat[field_name])
            class_idx = 0
            for i in range(len(breaks) - 1):
                if breaks[i] <= val < breaks[i + 1]:
                    class_idx = i
                    break
            # build attributes: copy original + append classification
            attrs = feat.attributes()[:]
            attrs.append(class_idx)
            label = labels[class_idx] if class_idx < len(labels) else f"Class {class_idx + 1}"
            attrs.append(label)

            new_feat = QgsFeature(out_fields)
            new_feat.setGeometry(feat.geometry())
            new_feat.setAttributes(attrs)
            sink.addFeature(new_feat, QgsFeatureSink.FastInsert)
            feedback.setProgress(int(100 * current / total))

        # Apply graduated symbology
        try:
            out_layer = context.getMapLayer(dest_id)
            if out_layer:
                colours = [
                    QColor("#440154"), QColor("#3b528b"), QColor("#21918c"),
                    QColor("#5ec962"), QColor("#fde725"),
                ]
                ranges = []
                for i in range(len(breaks) - 1):
                    sym = QgsSymbol.defaultSymbol(out_layer.geometryType())
                    col = colours[min(i, len(colours) - 1)]
                    sym.setColor(col)
                    sym.setOpacity(0.85)
                    label = f"{breaks[i]:.2f} – {breaks[i+1]:.2f}"
                    ranges.append(QgsRendererRange(breaks[i], breaks[i+1], sym, label))
                renderer = QgsGraduatedSymbolRenderer("gic_class", ranges)
                renderer.setClassificationMethod(QgsClassificationCustom())
                out_layer.setRenderer(renderer)
                out_layer.triggerRepaint()
        except Exception as exc:
            feedback.pushInfo(f"Renderer styling skipped (cosmetic): {exc}")

        return {self.OUTPUT: dest_id}
