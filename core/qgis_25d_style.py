# -*- coding: utf-8 -*-
"""Native QGIS 2.5D styling helpers for PlanX CartoLab."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict


POLYGON_GEOMETRY = 2
HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
HEIGHT_MODE_HEIGHT = "height"
HEIGHT_MODE_FLOOR_COUNT = "floor_count"
HEIGHT_MODES = (HEIGHT_MODE_HEIGHT, HEIGHT_MODE_FLOOR_COUNT)
FLOOR_FIELD_TOKENS = ("kat", "floor", "storey", "story", "level")


STYLE_25D_PRESETS: Dict[str, dict] = {
    "warm_civic": {
        "label": "Warm Civic",
        "roof": "#f2cf96",
        "wall": "#b36f43",
        "shadow": "#202833",
        "shadow_spread": 3.5,
    },
    "cool_slate": {
        "label": "Cool Slate",
        "roof": "#d7e4e8",
        "wall": "#607d8b",
        "shadow": "#14242b",
        "shadow_spread": 4.0,
    },
    "limestone_teal": {
        "label": "Limestone and Teal",
        "roof": "#eadfc8",
        "wall": "#4f8f8a",
        "shadow": "#1f2933",
        "shadow_spread": 3.0,
    },
    "night_copper": {
        "label": "Night Copper",
        "roof": "#d89b6a",
        "wall": "#6f4a58",
        "shadow": "#090d16",
        "shadow_spread": 5.0,
    },
}


@dataclass(frozen=True)
class Style25DConfig:
    """Serializable configuration for one CartoLab 2.5D renderer."""

    height_field: str
    preset: str = "warm_civic"
    roof_color: str = "#f2cf96"
    wall_color: str = "#b36f43"
    shadow_color: str = "#202833"
    angle: float = 110.0
    height_scale: float = 1.0
    max_height: float = 0.0
    stepped: bool = False
    step_height: float = 3.5
    shadow_enabled: bool = True
    shadow_spread: float = 3.5
    wall_shading: bool = True
    height_mode: str = HEIGHT_MODE_HEIGHT
    floor_height: float = 3.5


def preset_config(height_field: str, preset_key: str = "warm_civic") -> Style25DConfig:
    preset = STYLE_25D_PRESETS.get(preset_key, STYLE_25D_PRESETS["warm_civic"])
    return Style25DConfig(
        height_field=height_field,
        preset=preset_key if preset_key in STYLE_25D_PRESETS else "warm_civic",
        roof_color=preset["roof"],
        wall_color=preset["wall"],
        shadow_color=preset["shadow"],
        shadow_spread=float(preset["shadow_spread"]),
    )


def normalise_hex_color(value: str, fallback: str) -> str:
    value = (value or "").strip()
    if HEX_COLOR_RE.match(value):
        return value.lower()
    return fallback.lower()


def quote_field_name(field_name: str) -> str:
    if not field_name or not field_name.strip():
        raise ValueError("A height field is required.")
    return '"' + field_name.replace('"', '""') + '"'


def looks_like_floor_count_field(field_name: str) -> bool:
    clean = (field_name or "").strip().lower().replace(" ", "_")
    return any(token in clean for token in FLOOR_FIELD_TOKENS)


def format_number(value: float) -> str:
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.6f}".rstrip("0").rstrip(".")


def build_height_expression(config: Style25DConfig) -> str:
    """Build the expression evaluated by QGIS as @qgis_25d_height."""
    field_expr = f"coalesce(to_real({quote_field_name(config.height_field)}), 0)"
    scale_parts = []
    if config.height_mode == HEIGHT_MODE_FLOOR_COUNT:
        scale_parts.append(max(float(config.floor_height), 0.01))
    scale_parts.append(max(float(config.height_scale), 0.01))

    expr = field_expr
    for factor in scale_parts:
        expr = f"({expr}) * {format_number(factor)}"

    if config.stepped:
        step = max(float(config.step_height), 0.01)
        expr = f"round(({expr}) / {format_number(step)}) * {format_number(step)}"

    expr = f"(CASE WHEN ({expr}) < 0 THEN 0 ELSE ({expr}) END)"
    if config.max_height and config.max_height > 0:
        max_height = format_number(config.max_height)
        expr = f"(CASE WHEN ({expr}) > {max_height} THEN {max_height} ELSE ({expr}) END)"
    return expr


def build_order_by_expression(angle_variable: str = "@qgis_25d_angle") -> str:
    return (
        "distance(@geometry, translate(@map_extent_center, "
        f"1000 * @map_extent_width * cos(radians({angle_variable} + 180)), "
        f"1000 * @map_extent_width * sin(radians({angle_variable} + 180))))"
    )


def build_style_summary(layer_name: str, config: Style25DConfig) -> str:
    preset_label = STYLE_25D_PRESETS.get(config.preset, {}).get("label", config.preset)
    mode_label = "floor count" if config.height_mode == HEIGHT_MODE_FLOOR_COUNT else "height"
    lines = [
        "PlanX CartoLab 2.5D style applied",
        f"Layer: {layer_name}",
        f"Height field: {config.height_field}",
        f"Height source: {mode_label}",
        f"Height expression: {build_height_expression(config)}",
        f"Preset: {preset_label}",
        f"Angle: {format_number(config.angle)} degrees",
        f"Roof color: {config.roof_color}",
        f"Wall color: {config.wall_color}",
        f"Shadow: {'enabled' if config.shadow_enabled else 'disabled'}",
    ]
    if config.height_mode == HEIGHT_MODE_FLOOR_COUNT:
        lines.append(f"Floor height: {format_number(config.floor_height)} map units")
    if config.height_scale != 1.0:
        lines.append(f"Vertical scale: {format_number(config.height_scale)}x")
    if config.stepped:
        lines.append(f"Stepped extrusion: {format_number(config.step_height)} map units")
    if config.max_height and config.max_height > 0:
        lines.append(f"Maximum height clamp: {format_number(config.max_height)} map units")
    return "\n".join(lines)


def field_is_numeric(field) -> bool:
    if hasattr(field, "isNumeric"):
        try:
            return bool(field.isNumeric())
        except Exception:
            pass
    type_name = ""
    if hasattr(field, "typeName"):
        try:
            type_name = str(field.typeName()).lower()
        except Exception:
            type_name = ""
    return any(token in type_name for token in ("int", "real", "double", "float", "decimal", "numeric"))


def apply_25d_renderer(layer, config: Style25DConfig) -> str:
    """Apply a native Qgs25DRenderer to a loaded polygon layer."""
    if layer is None:
        raise ValueError("Select a polygon layer before applying the 2.5D style.")
    if not hasattr(layer, "geometryType") or layer.geometryType() != POLYGON_GEOMETRY:
        raise ValueError("The 2.5D style requires a polygon layer.")

    fields = layer.fields()
    lookup = fields.lookupField(config.height_field) if hasattr(fields, "lookupField") else fields.indexOf(config.height_field)
    if lookup < 0:
        raise ValueError(f"Height field not found: {config.height_field}")

    from qgis.core import Qgs25DRenderer, QgsExpressionContextUtils
    from qgis.PyQt.QtGui import QColor

    renderer = Qgs25DRenderer()
    renderer.setRoofColor(QColor(config.roof_color))
    renderer.setWallColor(QColor(config.wall_color))

    if hasattr(renderer, "setShadowColor"):
        renderer.setShadowColor(QColor(config.shadow_color))
    if hasattr(renderer, "setShadowEnabled"):
        renderer.setShadowEnabled(bool(config.shadow_enabled))
    if hasattr(renderer, "setShadowSpread"):
        renderer.setShadowSpread(float(config.shadow_spread))
    if hasattr(renderer, "setWallShadingEnabled"):
        renderer.setWallShadingEnabled(bool(config.wall_shading))

    QgsExpressionContextUtils.setLayerVariable(layer, "qgis_25d_angle", format_number(config.angle))
    QgsExpressionContextUtils.setLayerVariable(layer, "qgis_25d_height", build_height_expression(config))
    QgsExpressionContextUtils.setLayerVariable(layer, "planx_cartolab_25d_preset", config.preset)

    layer.setCustomProperty("planx_cartolab/25d_height_field", config.height_field)
    layer.setCustomProperty("planx_cartolab/25d_preset", config.preset)
    layer.setCustomProperty("planx_cartolab/25d_angle", float(config.angle))
    layer.setCustomProperty("planx_cartolab/25d_height_scale", float(config.height_scale))
    layer.setCustomProperty("planx_cartolab/25d_height_mode", config.height_mode)
    layer.setCustomProperty("planx_cartolab/25d_floor_height", float(config.floor_height))
    layer.setCustomProperty("planx_cartolab/25d_step_height", float(config.step_height))
    layer.setCustomProperty("planx_cartolab/25d_max_height", float(config.max_height))

    layer.setRenderer(renderer)
    layer.triggerRepaint()
    return build_style_summary(layer.name(), config)
