# -*- coding: utf-8 -*-
"""Choropleth Normalization & Rates — Processing algorithm."""
from __future__ import annotations

from qgis.core import (
    QgsFeature, QgsFeatureSink, QgsField, QgsFields, QgsGraduatedSymbolRenderer,
    QgsProcessing, QgsProcessingAlgorithm, QgsProcessingException,
    QgsProcessingParameterEnum, QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource, QgsProcessingParameterField,
    QgsProcessingParameterNumber, QgsRendererRange, QgsSymbol,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor

from ..core import normalize as nm
from ._help_mixin import CartoLabHelpMixin


class NormalizeFieldAlgorithm(QgsProcessingAlgorithm, CartoLabHelpMixin):
    INPUT = "INPUT"
    FIELD = "FIELD"
    METHOD = "METHOD"
    DENOMINATOR = "DENOMINATOR"
    SCALE = "SCALE"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        return "normalize_field"

    def displayName(self) -> str:
        return "Choropleth Normalization & Rates"

    def group(self) -> str:
        return "Data Preparation"

    def groupId(self) -> str:
        return "data_preparation"

    def createInstance(self):
        return NormalizeFieldAlgorithm()

    def shortHelpString(self) -> str:
        return (
            "Turn a raw field into a map-ready value before choropleth "
            "classification. Mapping a raw count as colour is the classic error "
            "(it just redraws population); normalise first.\n\n"
            "  - Rate: numerator / denominator x scale (e.g. cases per 100k)\n"
            "  - Z-score / Robust z (median-MAD): standardise for comparison\n"
            "  - Min-max: rescale to 0-1\n"
            "  - Percentile rank: 0-100 position in the distribution\n"
            "  - Log (base 10): tame heavy right tails\n\n"
            "Writes a 'norm_value' field and a 'norm_method' tag, and graduates "
            "the output on the new value."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT, "Input layer", [QgsProcessing.TypeVectorAnyGeometry]))
        self.addParameter(QgsProcessingParameterField(
            self.FIELD, "Value field (numerator)", parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Numeric))
        self.addParameter(QgsProcessingParameterEnum(
            self.METHOD, "Method", options=[m[0] for m in nm.METHODS], defaultValue=0))
        self.addParameter(QgsProcessingParameterField(
            self.DENOMINATOR, "Denominator field (Rate only)",
            parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Numeric, optional=True))
        self.addParameter(QgsProcessingParameterNumber(
            self.SCALE, "Rate scale (e.g. 1000, 100000)",
            type=QgsProcessingParameterNumber.Double, defaultValue=1.0, minValue=1e-12))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, "Normalized output"))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        field_name = self.parameterAsString(parameters, self.FIELD, context)
        method = nm.METHODS[self.parameterAsEnum(parameters, self.METHOD, context)][1]
        denom_field = self.parameterAsString(parameters, self.DENOMINATOR, context)
        scale = self.parameterAsDouble(parameters, self.SCALE, context)

        if method == "rate" and not denom_field:
            raise QgsProcessingException(
                "The Rate method needs a denominator field (e.g. population).")

        features_raw = list(source.getFeatures())
        numerators = [f[field_name] for f in features_raw]

        if method == "rate":
            denominators = [f[denom_field] for f in features_raw]
            norm = nm.rate(numerators, denominators, scale)
        elif method == "zscore":
            norm = nm.z_scores(numerators)
        elif method == "robust_z":
            norm = nm.robust_z(numerators)
        elif method == "minmax":
            norm = nm.min_max(numerators)
        elif method == "percentile":
            norm = nm.percentile_rank(numerators)
        elif method == "log":
            norm = nm.log_scale(numerators)
        else:
            raise QgsProcessingException(f"Unknown method: {method}")

        out_fields = QgsFields()
        for f in source.fields():
            out_fields.append(QgsField(f.name(), f.type()))
        out_fields.append(QgsField("norm_value", QVariant.Double))
        out_fields.append(QgsField("norm_method", QVariant.String))

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            out_fields, source.wkbType(), source.sourceCrs(),
        )

        valid_values = []
        total = len(features_raw) or 1
        for i, feat in enumerate(features_raw):
            if feedback.isCanceled():
                break
            val = norm[i]
            attrs = feat.attributes()[:]
            attrs.append(float(val) if val is not None else None)
            attrs.append(method)
            nf = QgsFeature(out_fields)
            nf.setGeometry(feat.geometry())
            nf.setAttributes(attrs)
            sink.addFeature(nf, QgsFeatureSink.FastInsert)
            if val is not None:
                valid_values.append(float(val))
            feedback.setProgress(int(100 * i / total))

        n_null = len(features_raw) - len(valid_values)
        feedback.pushInfo(
            f"Normalised {len(valid_values)} features via '{method}'. "
            f"{n_null} left null (missing / zero denominator)."
        )

        try:
            out_layer = context.getMapLayer(dest_id)
            if out_layer and valid_values:
                _apply_graduated(out_layer, "norm_value", min(valid_values), max(valid_values))
        except Exception as exc:
            feedback.pushInfo(f"Normalize renderer styling skipped (cosmetic): {exc}")

        return {self.OUTPUT: dest_id}


def _apply_graduated(layer, field, vmin, vmax):
    from qgis.core import QgsClassificationCustom
    colours = [
        QColor("#fde725"), QColor("#5ec962"), QColor("#21918c"),
        QColor("#3b528b"), QColor("#440154"),
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
        ranges.append(QgsRendererRange(lo, hi, sym, f"{lo:.3f} – {hi:.3f}"))
    renderer = QgsGraduatedSymbolRenderer(field, ranges)
    renderer.setClassificationMethod(QgsClassificationCustom())
    layer.setRenderer(renderer)
    layer.triggerRepaint()
