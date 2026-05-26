# -*- coding: utf-8 -*-
"""
CartoLab Dock — Multi-tab panel with Swiss-typography styling.

Provides quick-access controls for all CartoLab modules:
  - Bivariate classification
  - Cartogram generation
  - Ridge map creation
  - Value-by-Alpha settings
  - Isometric layout stacking
"""
from __future__ import annotations

import os

from qgis.PyQt.QtWidgets import (
    QDockWidget, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QListWidget, QTextEdit,
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont

from qgis.core import QgsProject, QgsMapLayer


class CartoLabDock(QDockWidget):
    """Main dockable panel for CartoLab."""

    def __init__(self, iface, parent=None):
        super().__init__("CartoLab", parent)
        self.iface = iface
        self.setObjectName("CartoLabDock")
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setMinimumWidth(320)

        # central tab widget
        self.tabs = QTabWidget()
        self.setWidget(self.tabs)

        self._build_bivariate_tab()
        self._build_cartogram_tab()
        self._build_ridge_tab()
        self._build_vba_tab()
        self._build_isometric_tab()

    # -------------------------------------------------------------------
    def _make_group(self, title: str) -> QGroupBox:
        gb = QGroupBox(title)
        font = QFont("Inter, Segoe UI", 9, QFont.Bold)
        gb.setFont(font)
        gb.setStyleSheet(
            "QGroupBox { border: 1px solid #ccc; border-radius: 6px; margin-top: 8px; padding: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }"
        )
        return gb

    # -------------------------------------------------------------------
    # BIVARIATE TAB
    # -------------------------------------------------------------------
    def _build_bivariate_tab(self) -> None:
        w = QWidget()
        lyt = QVBoxLayout(w)

        gb = self._make_group("Bivariate Choropleth")
        gl = QVBoxLayout(gb)

        self.bivar_layer_cb = QComboBox()
        self.bivar_layer_cb.setToolTip("Select input polygon layer")
        self._populate_layer_combo(self.bivar_layer_cb)
        gl.addWidget(QLabel("Layer:"))
        gl.addWidget(self.bivar_layer_cb)

        self.bivar_field_x = QComboBox()
        gl.addWidget(QLabel("X-axis variable:"))
        gl.addWidget(self.bivar_field_x)

        self.bivar_field_y = QComboBox()
        gl.addWidget(QLabel("Y-axis variable:"))
        gl.addWidget(self.bivar_field_y)

        self.bivar_classes = QSpinBox()
        self.bivar_classes.setRange(2, 7)
        self.bivar_classes.setValue(4)
        gl.addWidget(QLabel("Grid size (N×N):"))
        gl.addWidget(self.bivar_classes)

        btn = QPushButton("Generate Bivariate Map")
        btn.clicked.connect(self._on_bivariate)
        gl.addWidget(btn)
        lyt.addWidget(gb)
        lyt.addStretch()
        self.tabs.addTab(w, "Bivariate")

    # -------------------------------------------------------------------
    # CARTOGRAM TAB
    # -------------------------------------------------------------------
    def _build_cartogram_tab(self) -> None:
        w = QWidget()
        lyt = QVBoxLayout(w)

        gb = self._make_group("Diffusion Cartogram")
        gl = QVBoxLayout(gb)

        self.carto_layer_cb = QComboBox()
        self._populate_layer_combo(self.carto_layer_cb)
        gl.addWidget(QLabel("Polygon layer:"))
        gl.addWidget(self.carto_layer_cb)

        self.carto_field = QComboBox()
        gl.addWidget(QLabel("Area-representation field:"))
        gl.addWidget(self.carto_field)

        self.carto_iter = QSpinBox()
        self.carto_iter.setRange(1, 200)
        self.carto_iter.setValue(30)
        gl.addWidget(QLabel("Max iterations:"))
        gl.addWidget(self.carto_iter)

        self.carto_error = QDoubleSpinBox()
        self.carto_error.setRange(0.1, 100.0)
        self.carto_error.setValue(5.0)
        gl.addWidget(QLabel("Max avg error (%):"))
        gl.addWidget(self.carto_error)

        btn = QPushButton("Compute Cartogram")
        btn.clicked.connect(self._on_cartogram)
        gl.addWidget(btn)
        lyt.addWidget(gb)
        lyt.addStretch()
        self.tabs.addTab(w, "Cartogram")

    # -------------------------------------------------------------------
    # RIDGE MAP TAB
    # -------------------------------------------------------------------
    def _build_ridge_tab(self) -> None:
        w = QWidget()
        lyt = QVBoxLayout(w)

        gb = self._make_group("Ridge Map (Joyplot)")
        gl = QVBoxLayout(gb)

        self.ridge_raster_cb = QComboBox()
        gl.addWidget(QLabel("Raster layer:"))
        gl.addWidget(self.ridge_raster_cb)
        self._populate_raster_combo(self.ridge_raster_cb)

        self.ridge_lines = QSpinBox()
        self.ridge_lines.setRange(5, 500)
        self.ridge_lines.setValue(60)
        gl.addWidget(QLabel("Scanlines:"))
        gl.addWidget(self.ridge_lines)

        self.ridge_scale = QDoubleSpinBox()
        self.ridge_scale.setRange(0.01, 100.0)
        self.ridge_scale.setValue(1.0)
        self.ridge_scale.setDecimals(2)
        gl.addWidget(QLabel("Vertical exaggeration:"))
        gl.addWidget(self.ridge_scale)

        self.ridge_smooth = QSpinBox()
        self.ridge_smooth.setRange(0, 20)
        self.ridge_smooth.setValue(2)
        gl.addWidget(QLabel("Smoothing passes:"))
        gl.addWidget(self.ridge_smooth)

        btn = QPushButton("Generate Ridge Lines")
        btn.clicked.connect(self._on_ridge)
        gl.addWidget(btn)
        lyt.addWidget(gb)
        lyt.addStretch()
        self.tabs.addTab(w, "Ridge Map")

    # -------------------------------------------------------------------
    # VALUE-BY-ALPHA TAB
    # -------------------------------------------------------------------
    def _build_vba_tab(self) -> None:
        w = QWidget()
        lyt = QVBoxLayout(w)

        gb = self._make_group("Value-by-Alpha")
        gl = QVBoxLayout(gb)

        self.vba_layer_cb = QComboBox()
        self._populate_layer_combo(self.vba_layer_cb)
        gl.addWidget(QLabel("Layer:"))
        gl.addWidget(self.vba_layer_cb)

        self.vba_colour_field = QComboBox()
        gl.addWidget(QLabel("Primary (colour) field:"))
        gl.addWidget(self.vba_colour_field)

        self.vba_alpha_field = QComboBox()
        gl.addWidget(QLabel("Reliability (alpha) field:"))
        gl.addWidget(self.vba_alpha_field)

        self.vba_alpha_min = QSpinBox()
        self.vba_alpha_min.setRange(0, 255)
        self.vba_alpha_min.setValue(25)
        gl.addWidget(QLabel("Min opacity:"))
        gl.addWidget(self.vba_alpha_min)

        self.vba_alpha_max = QSpinBox()
        self.vba_alpha_max.setRange(0, 255)
        self.vba_alpha_max.setValue(255)
        gl.addWidget(QLabel("Max opacity:"))
        gl.addWidget(self.vba_alpha_max)

        btn = QPushButton("Apply VbA")
        btn.clicked.connect(self._on_vba)
        gl.addWidget(btn)
        lyt.addWidget(gb)
        lyt.addStretch()
        self.tabs.addTab(w, "VbA")

    # -------------------------------------------------------------------
    # ISOMETRIC TAB
    # -------------------------------------------------------------------
    def _build_isometric_tab(self) -> None:
        w = QWidget()
        lyt = QVBoxLayout(w)

        gb = self._make_group("Isometric Layout Stacker")
        gl = QVBoxLayout(gb)

        self.iso_layers_list = QListWidget()
        self.iso_layers_list.setSelectionMode(QListWidget.MultiSelection)
        gl.addWidget(QLabel("Select layers (bottom → top):"))
        gl.addWidget(self.iso_layers_list)
        self._populate_layer_list(self.iso_layers_list)

        self.iso_spacing = QDoubleSpinBox()
        self.iso_spacing.setRange(5, 200)
        self.iso_spacing.setValue(18)
        gl.addWidget(QLabel("Layer spacing (mm):"))
        gl.addWidget(self.iso_spacing)

        btn = QPushButton("Create Isometric Layout")
        btn.clicked.connect(self._on_isometric)
        gl.addWidget(btn)
        lyt.addWidget(gb)
        lyt.addStretch()
        self.tabs.addTab(w, "Isometric")

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------
    def _populate_layer_combo(self, combo: QComboBox) -> None:
        combo.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == QgsMapLayer.VectorLayer:
                combo.addItem(layer.name(), layer.id())

    def _populate_raster_combo(self, combo: QComboBox) -> None:
        combo.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == QgsMapLayer.RasterLayer:
                combo.addItem(layer.name(), layer.id())

    def _populate_layer_list(self, lst: QListWidget) -> None:
        lst.clear()
        for layer in QgsProject.instance().mapLayers().values():
            lst.addItem(layer.name())

    # -------------------------------------------------------------------
    # Action handlers — launch Processing algorithms
    # -------------------------------------------------------------------
    def _on_bivariate(self) -> None:
        from qgis import processing
        processing.execAlgorithmDialog("planx_cartolab:bivariate_choropleth", {})

    def _on_cartogram(self) -> None:
        from qgis import processing
        processing.execAlgorithmDialog("planx_cartolab:compute_cartogram", {})

    def _on_ridge(self) -> None:
        from qgis import processing
        processing.execAlgorithmDialog("planx_cartolab:ridge_map", {})

    def _on_vba(self) -> None:
        from qgis import processing
        processing.execAlgorithmDialog("planx_cartolab:value_by_alpha", {})

    def _on_isometric(self) -> None:
        selected = [item.text() for item in self.iso_layers_list.selectedItems()]
        if not selected:
            self.iface.messageBar().pushWarning("CartoLab", "Select at least two layers.")
            return
        layers = []
        for name in selected:
            for layer in QgsProject.instance().mapLayers().values():
                if layer.name() == name:
                    layers.append(layer)
                    break
        from ..layout.isometric_stacker import create_isometric_stack_layout
        create_isometric_stack_layout(
            layers, base_spacing_mm=self.iso_spacing.value()
        )
        self.iface.messageBar().pushSuccess("CartoLab", "Isometric layout created.")
