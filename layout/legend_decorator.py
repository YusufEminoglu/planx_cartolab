# -*- coding: utf-8 -*-
"""Bivariate matrix legend generator for QGIS Layouts."""
from __future__ import annotations

import os
from qgis.core import (
    QgsLayoutItemPicture,
    QgsLayout,
    QgsLayoutPoint,
    QgsUnitTypes,
)
from qgis.PyQt.QtCore import QRectF

from ..core.bivariate_engine import bivariate_colour_matrix
from ..core.html_graph_factory import build_bivariate_legend_html


def add_bivariate_legend_to_layout(
    layout: QgsLayout,
    x_label: str = "Variable X →",
    y_label: str = "Variable Y →",
    grid_size: int = 4,
    position: tuple = (10, 10),
    size_mm: tuple = (60, 60),
    color_ll: str = "#e8e8e8",
    color_lh: str = "#5ab4ac",
    color_hl: str = "#d8b365",
    color_hh: str = "#8c510a",
    legend_type: str = "diamond",
) -> None:
    """
    Insert a bivariate colour-matrix legend into a QGIS Print Layout.

    Renders the legend as an embedded SVG picture item.
    """
    matrix = bivariate_colour_matrix(grid_size, color_ll, color_lh, color_hl, color_hh)

    if legend_type == "diamond":
        svg = _svg_bivariate_diamond_legend(x_label, y_label, matrix)
    else:
        svg = _svg_bivariate_legend(x_label, y_label, matrix)

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False, mode="w", encoding="utf-8") as f:
        f.write(svg)
        tmp_path = f.name

    pic = QgsLayoutItemPicture(layout)
    pic.setPicturePath(tmp_path)
    pic.setReferencePoint(QgsLayoutItemPicture.UpperLeft)
    pic.attemptMove(QgsLayoutPoint(position[0], position[1], QgsUnitTypes.LayoutMillimeters))
    pic.attemptResize(QRectF(0, 0, size_mm[0], size_mm[1]))

    layout.addLayoutItem(pic)
    # note: temp file deletion deferred; cleaned by OS eventually


def _svg_bivariate_legend(
    x_label: str, y_label: str, matrix: list, cell: int = 36
) -> str:
    """Build a standalone SVG legend for layout embedding (Square Grid)."""
    n = len(matrix)
    w, h = n * cell, n * cell
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w + 36}" height="{h + 36}">',
        f'<g transform="translate(24, 6)">',
    ]
    for ri, row in enumerate(matrix):
        for ci, col in enumerate(row):
            svg_parts.append(
                f'<rect x="{ci * cell}" y="{ri * cell}" '
                f'width="{cell}" height="{cell}" fill="{col.name()}" '
                f'stroke="#fff" stroke-width="1"/>'
            )
    svg_parts.append(
        f'<text x="{w / 2}" y="{h + 18}" text-anchor="middle" '
        f'font-family="Inter,sans-serif" font-size="10" fill="#333">{x_label}</text>'
    )
    svg_parts.append(
        f'<text x="-10" y="{h / 2}" text-anchor="middle" '
        f'font-family="Inter,sans-serif" font-size="10" fill="#333" '
        f'transform="rotate(-90, -10, {h / 2})">{y_label}</text>'
    )
    svg_parts.append("</g></svg>")
    return "\n".join(svg_parts)


def _svg_bivariate_diamond_legend(
    x_label: str, y_label: str, matrix: list, half_w: int = 24, half_h: int = 14
) -> str:
    """Build a standalone SVG legend for layout embedding (Diamond shape)."""
    n = len(matrix)
    padding = 40
    W = 2 * (n - 1) * half_w + 2 * padding
    H = 2 * (n - 1) * half_h + 2 * padding

    offset_x = (n - 1) * half_w + padding
    offset_y = (n - 1) * half_h + padding

    import math
    angle = math.degrees(math.atan2(half_h, half_w))

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">',
        f'<g>',
    ]

    for ri in range(n):
        for ci in range(n):
            col = matrix[ri][ci]
            cx = offset_x + (ci - ri) * half_w
            cy = offset_y + ((n - 1) - (ci + ri)) * half_h

            p1_x, p1_y = cx, cy - half_h
            p2_x, p2_y = cx + half_w, cy
            p3_x, p3_y = cx, cy + half_h
            p4_x, p4_y = cx - half_w, cy

            svg_parts.append(
                f'<polygon points="{p1_x},{p1_y} {p2_x},{p2_y} {p3_x},{p3_y} {p4_x},{p4_y}" '
                f'fill="{col.name()}" stroke="#ffffff" stroke-width="1"/>'
            )

    svg_parts.append(
        f'<text x="{W/2}" y="{padding - 8}" text-anchor="middle" '
        f'font-family="Inter,sans-serif" font-size="9" font-weight="bold" fill="#555">High-High</text>'
    )
    svg_parts.append(
        f'<text x="{W/2}" y="{H - padding + 16}" text-anchor="middle" '
        f'font-family="Inter,sans-serif" font-size="9" font-weight="bold" fill="#555">Low-Low</text>'
    )
    svg_parts.append(
        f'<text x="{padding - 8}" y="{H/2 + 3}" text-anchor="end" '
        f'font-family="Inter,sans-serif" font-size="9" font-weight="bold" fill="#555">Low-High</text>'
    )
    svg_parts.append(
        f'<text x="{W - padding + 8}" y="{H/2 + 3}" text-anchor="start" '
        f'font-family="Inter,sans-serif" font-size="9" font-weight="bold" fill="#555">High-Low</text>'
    )

    x_c = W/2 + (n - 1) * half_w / 2 + 10
    y_c = H - padding + 14 - (n - 1) * half_h / 2
    svg_parts.append(
        f'<text x="{x_c}" y="{y_c}" text-anchor="middle" '
        f'font-family="Inter,sans-serif" font-size="10" font-weight="bold" fill="#333" '
        f'transform="rotate({-angle:.2f}, {x_c}, {y_c})">{x_label}</text>'
    )

    y_c_x = W/2 - (n - 1) * half_w / 2 - 10
    y_c_y = H - padding + 14 - (n - 1) * half_h / 2
    svg_parts.append(
        f'<text x="{y_c_x}" y="{y_c_y}" text-anchor="middle" '
        f'font-family="Inter,sans-serif" font-size="10" font-weight="bold" fill="#333" '
        f'transform="rotate({angle:.2f}, {y_c_x}, {y_c_y})">{y_label}</text>'
    )

    svg_parts.append("</g></svg>")
    return "\n".join(svg_parts)
