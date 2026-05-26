# -*- coding: utf-8 -*-
"""Adaptive Geometric Interval Classification — Processing algorithm."""
from __future__ import annotations

from qgis.core import (
    QgsFeatureSink,
    QgsField,
    QgsGraduatedSymbolRenderer,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProcessingParameterEnum,
    QgsRendererRange,
    QgsSymbol,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor

from ..core.bivariate_engine import (
    geometric_interval_breaks,
    head_tail_breaks,
    fisher_jenks_breaks,
)


class GeometricIntervalAlgorithm(QgsProcessingAlgorithm):
    INPUT = "INPUT"
    FIELD = "FIELD"
    CLASSES = "CLASSES"
    METHOD = "METHOD"
    OUTPUT_COL = "OUTPUT_COL"
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
            "Classify a numeric field using one of three advanced algorithms:\n"
            "  - Adaptive Geometric Interval (GIC): optimal for skewed continuous data\n"
            "  - Head/Tail Breaks: for heavy-tailed / power-law distributions\n"
            "  - Fisher-Jenks: natural breaks minimising within-class variance\n\n"
            "Output includes a graduated-renderer memory layer."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(self.INPUT, "Input layer", [QgsProcessing.TypeVectorAnyGeometry])
        )
        self.addParameter(
            QgsProcessingParameterField(self.FIELD, "Field to classify",
                                         parentLayerParameterName=self.INPUT,
                                         type=QgsProcessingParameterField.Numeric)
        )
        self.addParameter(
            QgsProcessingParameterNumber(self.CLASSES, "Number of classes",
                                          type=QgsProcessingParameterNumber.Integer,
                                          minValue=2, defaultValue=5, maxValue=20)
        )
        self.addParameter(
            QgsProcessingParameterEnum(self.METHOD, "Classification method",
                                        options=[m[0] for m in self.METHODS],
                                        defaultValue=0)
        )
        self.addParameter(
            QgsProcessingParameterString(self.OUTPUT_COL, "Output classification field",
                                          defaultValue="gic_class")
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, "Classified output")
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        field_name = self.parameterAsString(parameters, self.FIELD, context)
        n_classes = self.parameterAsInt(parameters, self.CLASSES, context)
        method_idx = self.parameterAsEnum(parameters, self.METHOD, context)
        output_col = self.parameterAsString(parameters, self.OUTPUT_COL, context)

        method = self.METHODS[method_idx][1]

        # harvest values
        values = [feat[field_name] for feat in source.getFeatures()
                  if feat[field_name] is not None]
        if not values:
            raise QgsProcessingException(f"No valid values in field '{field_name}'.")

        feedback.pushInfo(f"Classifying {len(values)} values using {method} into {n_classes} classes.")

        # run selected classifier
        if method == "geometric":
            breaks = geometric_interval_breaks(values, n_classes)
        elif method == "head_tail":
            breaks = head_tail_breaks(values)
        elif method == "fisher_jenks":
            breaks = fisher_jenks_breaks(values, n_classes)
        else:
            raise QgsProcessingException(f"Unknown method: {method}")

        feedback.pushInfo(f"Breaks: {[round(b, 4) for b in breaks]}")

        # create output sink
        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            source.fields(), source.wkbType(), source.sourceCrs(),
        )

        # build colour ramp (Viridis)
        colours = _viridis_colours(len(breaks) - 1)

        # classify & write features
        total = source.featureCount() or 1
        for current, feat in enumerate(source.getFeatures()):
            if feedback.isCanceled():
                break
            val = feat[field_name]
            class_idx = 0
            if val is not None:
                for i in range(len(breaks) - 1):
                    if breaks[i] <= val < breaks[i + 1]:
                        class_idx = i
                        break
            new_feat = feat.clone()
            new_feat[output_col] = class_idx
            sink.addFeature(new_feat, QgsFeatureSink.FastInsert)
            feedback.setProgress(int(100 * current / total))

        return {self.OUTPUT: dest_id}


def _viridis_colours(n: int) -> list:
    """Return n interpolated Viridis colours."""
    base = [
        QColor("#440154"), QColor("#482878"), QColor("#3e4989"),
        QColor("#31688e"), QColor("#26828e"), QColor("#1f9e89"),
        QColor("#35b779"), QColor("#6ece58"), QColor("#b5de2b"),
        QColor("#fde725"),
    ]
    if n <= len(base):
        return base[:n]
    result = []
    for i in range(n):
        frac = i / max(n - 1, 1) * (len(base) - 1)
        lo, hi = int(frac), min(int(frac) + 1, len(base) - 1)
        t = frac - lo
        r = int(base[lo].red() + t * (base[hi].red() - base[lo].red()))
        g = int(base[lo].green() + t * (base[hi].green() - base[lo].green()))
        b = int(base[lo].blue() + t * (base[hi].blue() - base[lo].blue()))
        result.append(QColor(r, g, b))
    return result
