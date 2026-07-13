# -*- coding: utf-8 -*-
"""Quick Style — one-click graduated or categorized renderer with a good palette."""
from __future__ import annotations

from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingOutputString,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterField,
    QgsProcessingParameterNumber,
    QgsProcessingParameterVectorLayer,
    QgsSymbol,
    QgsRendererRange,
    QgsRendererCategory,
    QgsGraduatedSymbolRenderer,
    QgsCategorizedSymbolRenderer,
)

from ..core import palettes as pal
from ..core import quick_style as qs
from ..core.bivariate_engine import geometric_interval_breaks
from ._help_mixin import CartoLabHelpMixin

_MODE_AUTO, _MODE_GRAD, _MODE_CAT = 0, 1, 2
_METHODS = [
    ("Quantile (equal count)", qs.QUANTILE),
    ("Equal interval", qs.EQUAL),
    ("Geometric interval", qs.GEOMETRIC),
]
# Ordered palette list: sequential, then diverging, then qualitative.
_PALETTES = pal.ordered_names()
_MAX_CATS = 100


class QuickStyleAlgorithm(CartoLabHelpMixin, QgsProcessingAlgorithm):
    INPUT = "INPUT"
    FIELD = "FIELD"
    MODE = "MODE"
    CLASSES = "CLASSES"
    METHOD = "METHOD"
    PALETTE = "PALETTE"
    REVERSE = "REVERSE"
    OUTLINE = "OUTLINE"
    SUMMARY = "SUMMARY"

    def name(self) -> str:
        return "quick_style"

    def displayName(self) -> str:
        return "Quick Style (auto choropleth / categories)"

    def group(self) -> str:
        return "Quick Style"

    def groupId(self) -> str:
        return "quick_style"

    def createInstance(self):
        return QuickStyleAlgorithm()

    def shortHelpString(self) -> str:
        return (
            "Style any vector layer in one step. Pick a field and a colour "
            "palette (ColorBrewer or the colour-blind-safe viridis family) and "
            "CartoLab applies a graduated renderer for numeric fields or a "
            "categorized renderer for text fields, with quantile, equal-interval "
            "or geometric-interval class breaks. The renderer is applied to the "
            "selected layer in place."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.INPUT, "Vector layer"))
        self.addParameter(QgsProcessingParameterField(
            self.FIELD, "Field to style", parentLayerParameterName=self.INPUT))
        self.addParameter(QgsProcessingParameterEnum(
            self.MODE, "Style as",
            options=["Auto (numeric -> graduated, text -> categories)",
                     "Graduated (numeric)", "Categorized (unique values)"],
            defaultValue=_MODE_AUTO))
        self.addParameter(QgsProcessingParameterNumber(
            self.CLASSES, "Number of classes (graduated)",
            type=QgsProcessingParameterNumber.Integer,
            defaultValue=5, minValue=2, maxValue=12))
        self.addParameter(QgsProcessingParameterEnum(
            self.METHOD, "Class break method (graduated)",
            options=[m[0] for m in _METHODS], defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(
            self.PALETTE, "Colour palette", options=_PALETTES,
            defaultValue=_PALETTES.index(pal.default_palette(pal.SEQUENTIAL))))
        self.addParameter(QgsProcessingParameterBoolean(
            self.REVERSE, "Reverse palette", defaultValue=False))
        self.addParameter(QgsProcessingParameterBoolean(
            self.OUTLINE, "Thin white outline", defaultValue=True))
        self.addOutput(QgsProcessingOutputString(self.SUMMARY, "Style summary"))

    def processAlgorithm(self, parameters, context, feedback):
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException("Select a valid vector layer.")
        field = self.parameterAsString(parameters, self.FIELD, context)
        mode = self.parameterAsEnum(parameters, self.MODE, context)
        classes = self.parameterAsInt(parameters, self.CLASSES, context)
        method = _METHODS[self.parameterAsEnum(parameters, self.METHOD, context)][1]
        palette = _PALETTES[self.parameterAsEnum(parameters, self.PALETTE, context)]
        reverse = self.parameterAsBool(parameters, self.REVERSE, context)
        outline = self.parameterAsBool(parameters, self.OUTLINE, context)

        idx = layer.fields().indexOf(field)
        if idx < 0:
            raise QgsProcessingException(f"Field '{field}' not found.")
        is_numeric = layer.fields().at(idx).isNumeric()

        if mode == _MODE_AUTO:
            mode = _MODE_GRAD if is_numeric else _MODE_CAT
        if mode == _MODE_GRAD and not is_numeric:
            raise QgsProcessingException(
                f"Field '{field}' is not numeric; choose Categorized instead.")

        if mode == _MODE_GRAD:
            summary = self._graduated(layer, field, classes, method, palette,
                                      reverse, outline)
        else:
            summary = self._categorized(layer, field, palette, reverse, outline,
                                        feedback)

        layer.triggerRepaint()
        feedback.pushInfo(summary)
        return {self.SUMMARY: summary}

    # -- helpers ----------------------------------------------------------

    def _symbol(self, layer, hex_color, outline):
        sym = QgsSymbol.defaultSymbol(layer.geometryType())
        sym.setColor(QColor(hex_color))
        if outline:
            try:
                sl = sym.symbolLayer(0)
                if hasattr(sl, "setStrokeColor"):
                    sl.setStrokeColor(QColor("#ffffff"))
                if hasattr(sl, "setStrokeWidth"):
                    sl.setStrokeWidth(0.2)
            except Exception:
                pass
        return sym

    def _colors(self, palette, n, reverse):
        cols = pal.get_palette(palette, n)
        return list(reversed(cols)) if reverse else cols

    def _graduated(self, layer, field, classes, method, palette, reverse, outline):
        values = [f[field] for f in layer.getFeatures() if f[field] is not None]
        if not values:
            raise QgsProcessingException(f"Field '{field}' has no numeric values.")
        if method == qs.QUANTILE:
            edges = qs.quantile_breaks(values, classes)
        elif method == qs.EQUAL:
            edges = qs.equal_interval_breaks(values, classes)
        else:
            edges = geometric_interval_breaks(values, classes)
        ranges_lh = qs.edges_to_ranges(edges)
        if not ranges_lh:
            # Degenerate field (a single distinct value): one class is still
            # a valid, if plain, map — better than failing outright.
            v = values[0]
            ranges_lh = [(v, v)]
        colors = self._colors(palette, len(ranges_lh), reverse)
        ranges = []
        for (lo, hi), col in zip(ranges_lh, colors):
            label = f"{lo:.4g} - {hi:.4g}"
            ranges.append(QgsRendererRange(lo, hi, self._symbol(layer, col, outline), label))
        layer.setRenderer(QgsGraduatedSymbolRenderer(field, ranges))
        return (f"Quick Style: graduated '{field}' into {len(ranges)} classes "
                f"({method}) with palette '{palette}'"
                f"{' (colour-blind safe)' if pal.is_colorblind_safe(palette) else ''}.")

    def _categorized(self, layer, field, palette, reverse, outline, feedback):
        seen = []
        for f in layer.getFeatures():
            v = f[field]
            if v is not None and v not in seen:
                seen.append(v)
                if len(seen) > _MAX_CATS:
                    break
        cats = sorted(seen, key=lambda x: str(x))
        if not cats:
            raise QgsProcessingException(f"Field '{field}' has no values.")
        if len(cats) >= _MAX_CATS:
            feedback.pushInfo(
                f"Field has many unique values; styling the first {_MAX_CATS}.")
        colors = self._colors(palette, len(cats), reverse)
        categories = []
        for value, col in zip(cats, colors):
            categories.append(
                QgsRendererCategory(value, self._symbol(layer, col, outline), str(value)))
        layer.setRenderer(QgsCategorizedSymbolRenderer(field, categories))
        return (f"Quick Style: categorized '{field}' into {len(categories)} "
                f"classes with palette '{palette}'.")
