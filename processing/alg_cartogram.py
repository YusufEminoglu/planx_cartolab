# -*- coding: utf-8 -*-
"""Continuous-Area Cartogram — Processing algorithm."""
from __future__ import annotations

from qgis.core import (
    QgsFeatureSink,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterNumber,
    QgsProcessingOutputNumber,
    QgsVectorLayer,
    QgsWkbTypes,
    QgsFeature,
)
from qgis import processing

from ..core.cartogram_engine import CartogramEngine
from ._help_mixin import CartoLabHelpMixin


class CartogramAlgorithm(CartoLabHelpMixin, QgsProcessingAlgorithm):
    INPUT = "INPUT"
    FIELD = "FIELD"
    MAX_ITERATIONS = "MAX_ITERATIONS"
    MAX_ERROR = "MAX_ERROR"
    ITERATIONS = "ITERATIONS"
    RESIDUAL_ERROR = "RESIDUAL_ERROR"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        return "compute_cartogram"

    def displayName(self) -> str:
        return "Continuous-Area Cartogram (Diffusion)"

    def group(self) -> str:
        return "Cartogram"

    def groupId(self) -> str:
        return "cartogram"

    def createInstance(self):
        return CartogramAlgorithm()

    def shortHelpString(self) -> str:
        return (
            "Distort polygon areas to be proportional to a numeric field "
            "using the diffusion method (Gastner & Newman).\n\n"
            "The algorithm iteratively displaces polygon boundaries until "
            "each region's area represents its field value.  A zero-width "
            "buffer is applied to fix topology issues on exit.\n\n"
            "Requires at least 2 valid polygon features."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT, "Input polygon layer",
                [QgsProcessing.SourceType.TypeVectorPolygon],
            )
        )
        self.addParameter(
            QgsProcessingParameterField(self.FIELD, "Area-representation field",
                                         parentLayerParameterName=self.INPUT,
                                         type=QgsProcessingParameterField.DataType.Numeric)
        )
        self.addParameter(
            QgsProcessingParameterNumber(self.MAX_ITERATIONS, "Max iterations",
                                          type=QgsProcessingParameterNumber.Type.Integer,
                                          defaultValue=30, minValue=1, maxValue=200)
        )
        self.addParameter(
            QgsProcessingParameterNumber(self.MAX_ERROR, "Max average error (%)",
                                          type=QgsProcessingParameterNumber.Type.Double,
                                          defaultValue=5.0, minValue=0.1, maxValue=100.0)
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, "Cartogram output")
        )
        self.addOutput(
            QgsProcessingOutputNumber(self.ITERATIONS, "Iterations run")
        )
        self.addOutput(
            QgsProcessingOutputNumber(self.RESIDUAL_ERROR, "Residual average error (%)")
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        field_name = self.parameterAsStrings(parameters, self.FIELD, context)[0]
        max_iter = self.parameterAsInt(parameters, self.MAX_ITERATIONS, context)
        max_error = self.parameterAsDouble(parameters, self.MAX_ERROR, context)

        feedback.pushInfo(f"Loading input layer with {source.featureCount()} features...")

        # fix geometry with zero-buffer
        feedback.pushInfo("Fixing geometries (zero-width buffer)...")
        buffered_result = processing.run(
            "native:buffer",
            {"INPUT": parameters[self.INPUT], "DISTANCE": 0.0, "OUTPUT": "memory:"},
            context=context, is_child_algorithm=True,
        )
        memory_layer = context.getMapLayer(buffered_result["OUTPUT"])

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            source.fields(), source.wkbType(), source.sourceCrs(),
        )

        # run cartogram engine
        engine = CartogramEngine(memory_layer, field_name, max_iter, max_error)
        iterations, avg_error = engine.run(feedback)

        engine.write_to_layer(memory_layer)

        # final zero-buffer to fix slithers
        feedback.pushInfo("Final cleanup (zero-width buffer)...")
        cleaned = processing.run(
            "native:buffer",
            {"INPUT": memory_layer, "DISTANCE": 0.0, "OUTPUT": "memory:"},
            context=context, is_child_algorithm=True,
        )
        cleaned_layer = context.getMapLayer(cleaned["OUTPUT"])

        for feat in cleaned_layer.getFeatures():
            sink.addFeature(feat, QgsFeatureSink.Flag.FastInsert)

        error_pct = (avg_error - 1.0) * 100.0
        feedback.pushInfo(
            f"Cartogram finished: {iterations} iterations, "
            f"residual error: {error_pct:.2f}%"
        )

        return {
            self.OUTPUT: dest_id,
            self.ITERATIONS: iterations,
            self.RESIDUAL_ERROR: error_pct,
        }
