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
) -> None:
    """
    Insert a bivariate colour-matrix legend into a QGIS Print Layout.

    Renders the legend as an embedded SVG picture item.
    """
    matrix = bivariate_colour_matrix(grid_size)
    hex_matrix = [[c.name() for c in row] for row in matrix]

    html = build_bivariate_legend_html(x_label, y_label, hex_matrix)

    # write a temp SVG (the HTML embed flow needs a browser;
    # for layout we render a pure-SVG variant)
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
    """Build a standalone SVG legend for layout embedding."""
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
