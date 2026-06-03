# -*- coding: utf-8 -*-
"""Apply native QGIS 2.5D building styling."""
from __future__ import annotations

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingOutputString,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterField,
    QgsProcessingParameterNumber,
    QgsProcessingParameterVectorLayer,
)

from ..core.qgis_25d_style import (
    STYLE_25D_PRESETS,
    Style25DConfig,
    apply_25d_renderer,
    preset_config,
)


class Building25DStyleAlgorithm(QgsProcessingAlgorithm):
    INPUT = "INPUT"
    HEIGHT_FIELD = "HEIGHT_FIELD"
    PRESET = "PRESET"
    ANGLE = "ANGLE"
    HEIGHT_SCALE = "HEIGHT_SCALE"
    MAX_HEIGHT = "MAX_HEIGHT"
    STEPPED = "STEPPED"
    STEP_HEIGHT = "STEP_HEIGHT"
    SHADOW_ENABLED = "SHADOW_ENABLED"
    SHADOW_SPREAD = "SHADOW_SPREAD"
    WALL_SHADING = "WALL_SHADING"
    SUMMARY = "SUMMARY"

    PRESET_KEYS = list(STYLE_25D_PRESETS.keys())

    def name(self) -> str:
        return "building_25d_style"

    def displayName(self) -> str:
        return "Apply 2.5D Building Style"

    def group(self) -> str:
        return "2.5D Styling"

    def groupId(self) -> str:
        return "25d_styling"

    def createInstance(self):
        return Building25DStyleAlgorithm()

    def shortHelpString(self) -> str:
        return (
            "Apply a polished native QGIS 2.5D renderer to a loaded polygon layer. "
            "The selected height field drives the extrusion, while CartoLab controls "
            "the roof colour, wall colour, shadow, viewing angle, optional height "
            "clamp, and optional stepped extrusion."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.INPUT, "Polygon layer", [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterField(
            self.HEIGHT_FIELD,
            "Height field",
            parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Numeric,
        ))
        self.addParameter(QgsProcessingParameterEnum(
            self.PRESET,
            "Visual preset",
            options=[STYLE_25D_PRESETS[k]["label"] for k in self.PRESET_KEYS],
            defaultValue=0,
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.ANGLE,
            "Projection angle in degrees",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=110.0,
            minValue=0.0,
            maxValue=359.0,
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.HEIGHT_SCALE,
            "Height scale multiplier",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=1.0,
            minValue=0.01,
            maxValue=100.0,
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.MAX_HEIGHT,
            "Maximum rendered height, 0 for no clamp",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.0,
            minValue=0.0,
            maxValue=1000000.0,
        ))
        self.addParameter(QgsProcessingParameterBoolean(
            self.STEPPED,
            "Snap heights to stepped floors",
            defaultValue=False,
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.STEP_HEIGHT,
            "Step height in map units",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=3.5,
            minValue=0.01,
            maxValue=100000.0,
        ))
        self.addParameter(QgsProcessingParameterBoolean(
            self.SHADOW_ENABLED,
            "Enable soft shadow",
            defaultValue=True,
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.SHADOW_SPREAD,
            "Shadow spread in map units",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=3.5,
            minValue=0.0,
            maxValue=100000.0,
        ))
        self.addParameter(QgsProcessingParameterBoolean(
            self.WALL_SHADING,
            "Enable directional wall shading",
            defaultValue=True,
        ))
        self.addOutput(QgsProcessingOutputString(self.SUMMARY, "Style summary"))

    def processAlgorithm(self, parameters, context, feedback):
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        height_field = self.parameterAsString(parameters, self.HEIGHT_FIELD, context)
        preset_idx = self.parameterAsEnum(parameters, self.PRESET, context)
        preset_key = self.PRESET_KEYS[preset_idx] if 0 <= preset_idx < len(self.PRESET_KEYS) else "warm_civic"

        base = preset_config(height_field, preset_key)
        config = Style25DConfig(
            height_field=height_field,
            preset=preset_key,
            roof_color=base.roof_color,
            wall_color=base.wall_color,
            shadow_color=base.shadow_color,
            angle=self.parameterAsDouble(parameters, self.ANGLE, context),
            height_scale=self.parameterAsDouble(parameters, self.HEIGHT_SCALE, context),
            max_height=self.parameterAsDouble(parameters, self.MAX_HEIGHT, context),
            stepped=self.parameterAsBool(parameters, self.STEPPED, context),
            step_height=self.parameterAsDouble(parameters, self.STEP_HEIGHT, context),
            shadow_enabled=self.parameterAsBool(parameters, self.SHADOW_ENABLED, context),
            shadow_spread=self.parameterAsDouble(parameters, self.SHADOW_SPREAD, context),
            wall_shading=self.parameterAsBool(parameters, self.WALL_SHADING, context),
        )

        try:
            summary = apply_25d_renderer(layer, config)
        except Exception as exc:
            raise QgsProcessingException(str(exc))

        feedback.pushInfo(summary)
        return {self.SUMMARY: summary}
