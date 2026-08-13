# -*- coding: utf-8 -*-
"""
PlanX CartoLab — Print Layout Designer Window Integration & Embedded Studio Dock.

Hooks directly into QGIS QgsLayoutDesignerInterface instances so that users
have access to CartoLab cartographic tools, presets, decorators, and 1-click
export & open right inside the QGIS Print Layout Designer window.
"""
from __future__ import annotations

import os
from contextlib import suppress
from typing import Optional

try:
    from qgis.core import QgsProject
    from qgis.PyQt.QtCore import Qt, QUrl
    from qgis.PyQt.QtGui import QDesktopServices, QIcon
    from qgis.PyQt.QtWidgets import (
        QAction,
        QComboBox,
        QDockWidget,
        QDoubleSpinBox,
        QFileDialog,
        QFormLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QMenu,
        QMessageBox,
        QPushButton,
        QToolBar,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    QgsProject = None
    Qt = QUrl = QDesktopServices = QIcon = QAction = QComboBox = QDockWidget = QDoubleSpinBox = QFileDialog = QFormLayout = QGroupBox = QHBoxLayout = QLabel = QMenu = QMessageBox = QPushButton = QToolBar = QVBoxLayout = QWidget = None


_INTEGRATED_DESIGNERS = set()


def setup_designer_integration(iface) -> None:
    """Connect to layoutDesignerOpened signal and attach to active designers."""
    if not iface:
        return

    def _on_opened(designer):
        attach_cartolab_to_designer(iface, designer)

    with suppress(Exception):
        if hasattr(iface, "layoutDesignerOpened"):
            iface.layoutDesignerOpened.connect(_on_opened)

    # Attach to existing open layout designers
    with suppress(Exception):
        if hasattr(iface, "layoutDesigners"):
            for designer in iface.layoutDesigners():
                attach_cartolab_to_designer(iface, designer)


def attach_cartolab_to_designer(iface, designer) -> None:
    """Attach PlanX CartoLab toolbar, menu, and embedded dock panel inside a QgsLayoutDesignerInterface window."""
    if designer is None or id(designer) in _INTEGRATED_DESIGNERS:
        return
    _INTEGRATED_DESIGNERS.add(id(designer))

    main_win = None
    with suppress(Exception):
        if hasattr(designer, "view") and hasattr(designer.view(), "window"):
            main_win = designer.view().window()
        elif hasattr(designer, "mainWindow"):
            main_win = designer.mainWindow()

    if main_win is None:
        return

    icon_dir = os.path.join(os.path.dirname(__file__), "..", "icons")
    icon_path = os.path.join(icon_dir, "icon.png")
    icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

    # 1. Create Toolbar inside Layout Designer
    toolbar = QToolBar("PlanX CartoLab", main_win)
    toolbar.setObjectName("PlanXCartoLabLayoutToolbar")

    # Action 1: Add Bivariate Legend
    act_bivar = QAction(icon, "💎 Bivariate Legend", main_win)
    act_bivar.setToolTip("Add a Bivariate Legend overlay (Teal-Brown 3x3) to the layout")

    def _on_bivar():
        layout = _get_designer_layout(designer)
        if not layout:
            return
        try:
            from .legend_decorator import add_bivariate_legend
            add_bivariate_legend(
                layout=layout,
                colors=("#e8e8e8", "#5ab4ac", "#d8b365", "#8c510a"),
                legend_type="diamond",
            )
            if hasattr(iface, "messageBar"):
                iface.messageBar().pushSuccess("CartoLab", "Bivariate legend added to layout.")
        except Exception as exc:
            QMessageBox.critical(main_win, "Bivariate Legend", str(exc))

    act_bivar.triggered.connect(_on_bivar)
    toolbar.addAction(act_bivar)

    # Action 2: Apply Swiss Typography & Grid
    act_typo = QAction(icon, "📏 Swiss Typography & Grid", main_win)
    act_typo.setToolTip("Apply clean Swiss typography hierarchy and grid structure to map labels & frames")

    def _on_typo():
        layout = _get_designer_layout(designer)
        if not layout:
            return
        try:
            from .typography_engine import apply_swiss_typography
            apply_swiss_typography(layout)
            if hasattr(iface, "messageBar"):
                iface.messageBar().pushSuccess("CartoLab", "Swiss typography applied to layout.")
        except Exception as exc:
            QMessageBox.critical(main_win, "Swiss Typography", str(exc))

    act_typo.triggered.connect(_on_typo)
    toolbar.addAction(act_typo)

    # Action 3: Isometric Layer Stack
    act_iso = QAction(icon, "📐 Isometric Stack", main_win)
    act_iso.setToolTip("Stack active vector layers with isometric perspective rendering")

    def _on_iso():
        layout = _get_designer_layout(designer)
        if not layout:
            return
        if not QgsProject or not QgsProject.instance():
            return
        layers = [lyr for lyr in QgsProject.instance().mapLayers().values() if hasattr(lyr, "geometryType")]
        if len(layers) < 2:
            QMessageBox.warning(main_win, "Isometric Stack", "At least 2 layers are required in the project.")
            return
        try:
            from .isometric_stacker import stack_layers_isometrically
            stack_layers_isometrically(
                layout=layout,
                layers=layers[:3],
                tilt_angle=30.0,
                heading=100.0,
            )
            if hasattr(iface, "messageBar"):
                iface.messageBar().pushSuccess("CartoLab", "Isometric layer stack built in layout.")
        except Exception as exc:
            QMessageBox.critical(main_win, "Isometric Stack", str(exc))

    act_iso.triggered.connect(_on_iso)
    toolbar.addAction(act_iso)

    toolbar.addSeparator()

    # Action 4: Quick Export & Open (PNG/PDF/SVG)
    act_export = QAction(icon, "⚡ Export & Open ↗", main_win)
    act_export.setToolTip("Export layout to 300 DPI image/PDF and open immediately in system viewer")

    def _on_export():
        layout = _get_designer_layout(designer)
        if not layout:
            return
        safe = "".join(c if c.isalnum() else "_" for c in layout.name())
        default = os.path.join(os.path.expanduser("~"), f"{safe}.png")
        path, _ = QFileDialog.getSaveFileName(
            main_win, "Export Layout (300 DPI)", default, "PNG Image (*.png);;PDF Document (*.pdf);;SVG Vector (*.svg)")
        if not path:
            return
        try:
            from .layout_utils import export_layout
            success = export_layout(layout, path, dpi=300)
            if success and os.path.exists(path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
                if hasattr(iface, "messageBar"):
                    iface.messageBar().pushSuccess("CartoLab", f"Exported & Opened: {path}")
        except Exception as exc:
            QMessageBox.critical(main_win, "Export Layout", str(exc))

    act_export.triggered.connect(_on_export)
    toolbar.addAction(act_export)

    main_win.addToolBar(toolbar)

    # 2. Add PlanX CartoLab Menu to Designer MenuBar
    with suppress(Exception):
        menubar = main_win.menuBar()
        if menubar:
            menu = QMenu("&PlanX CartoLab", menubar)
            menu.addAction(act_bivar)
            menu.addAction(act_typo)
            menu.addAction(act_iso)
            menu.addSeparator()
            menu.addAction(act_export)
            menubar.addMenu(menu)

    # 3. Add Embedded Dock Panel inside Print Layout Window
    with suppress(Exception):
        dock = create_cartolab_layout_dock(iface, designer, main_win)
        if hasattr(designer, "addDockWidget"):
            designer.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        elif hasattr(main_win, "addDockWidget"):
            main_win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)


def create_cartolab_layout_dock(iface, designer, parent_win) -> QDockWidget:
    """Create embedded CartoLab Layout Studio Dock Widget for the layout designer."""
    dock = QDockWidget("CartoLab Layout Studio", parent_win)
    dock.setObjectName("CartoLabLayoutStudioDock")
    dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

    w = QWidget()
    lyt = QVBoxLayout(w)
    lyt.setContentsMargins(8, 8, 8, 8)
    lyt.setSpacing(10)

    # Section 1: Quick Decorators
    gb_dec = QGroupBox("Quick Decorators")
    fl_dec = QFormLayout(gb_dec)
    
    palette_combo = QComboBox()
    palette_combo.addItem("Teal-Brown", ("#e8e8e8", "#5ab4ac", "#d8b365", "#8c510a"))
    palette_combo.addItem("Purple-Green", ("#e8e8e8", "#7fbf7b", "#af8dc3", "#762a83"))
    palette_combo.addItem("Blue-Orange", ("#e8e8e8", "#fdae61", "#abd9e9", "#2c7bb6"))
    palette_combo.addItem("Pink-Green", ("#e8e8e8", "#a1d76a", "#e9a3c9", "#c51b7d"))
    fl_dec.addRow("Bivar Palette:", palette_combo)

    shape_combo = QComboBox()
    shape_combo.addItem("Diamond", "diamond")
    shape_combo.addItem("Square", "square")
    fl_dec.addRow("Legend Shape:", shape_combo)

    btn_add_bivar = QPushButton("Add Bivariate Legend")
    def _add_bivar():
        layout = _get_designer_layout(designer)
        if not layout:
            return
        colors = palette_combo.currentData()
        ltype = shape_combo.currentData()
        try:
            from .legend_decorator import add_bivariate_legend
            add_bivariate_legend(layout, colors=colors, legend_type=ltype)
            if hasattr(iface, "messageBar"):
                iface.messageBar().pushSuccess("CartoLab", "Custom bivariate legend added.")
        except Exception as exc:
            QMessageBox.critical(parent_win, "Bivariate Legend", str(exc))

    btn_add_bivar.clicked.connect(_add_bivar)
    fl_dec.addRow(btn_add_bivar)
    lyt.addWidget(gb_dec)

    # Section 2: Isometric Stacking Controls
    gb_iso = QGroupBox("Isometric Perspective")
    fl_iso = QFormLayout(gb_iso)
    
    tilt_spin = QDoubleSpinBox()
    tilt_spin.setRange(0, 89)
    tilt_spin.setValue(30.0)
    tilt_spin.setSuffix(" °")
    fl_iso.addRow("Tilt Angle:", tilt_spin)

    heading_spin = QDoubleSpinBox()
    heading_spin.setRange(0, 359)
    heading_spin.setValue(100.0)
    heading_spin.setSuffix(" °")
    fl_iso.addRow("Heading Angle:", heading_spin)

    btn_apply_iso = QPushButton("Apply Isometric Perspective")
    def _apply_iso():
        layout = _get_designer_layout(designer)
        if not layout or not QgsProject or not QgsProject.instance():
            return
        layers = [lyr for lyr in QgsProject.instance().mapLayers().values() if hasattr(lyr, "geometryType")]
        if len(layers) < 2:
            QMessageBox.warning(parent_win, "Isometric Stack", "Need at least 2 layers.")
            return
        try:
            from .isometric_stacker import stack_layers_isometrically
            stack_layers_isometrically(layout, layers[:3], tilt_angle=tilt_spin.value(), heading=heading_spin.value())
            if hasattr(iface, "messageBar"):
                iface.messageBar().pushSuccess("CartoLab", "Isometric stack applied.")
        except Exception as exc:
            QMessageBox.critical(parent_win, "Isometric Stack", str(exc))

    btn_apply_iso.clicked.connect(_apply_iso)
    fl_iso.addRow(btn_apply_iso)
    lyt.addWidget(gb_iso)

    # Section 3: Quick Export & Open
    gb_exp = QGroupBox("Quick Export")
    fl_exp = QFormLayout(gb_exp)

    dpi_combo = QComboBox()
    dpi_combo.addItem("150 DPI (Draft)", 150)
    dpi_combo.addItem("300 DPI (Publication)", 300)
    dpi_combo.addItem("600 DPI (Ultra)", 600)
    dpi_combo.setCurrentIndex(1)
    fl_exp.addRow("Quality:", dpi_combo)

    btn_dock_export = QPushButton("⚡ Export & Open ↗")
    def _dock_export():
        layout = _get_designer_layout(designer)
        if not layout:
            return
        dpi = dpi_combo.currentData()
        safe = "".join(c if c.isalnum() else "_" for c in layout.name())
        default = os.path.join(os.path.expanduser("~"), f"{safe}.png")
        path, _ = QFileDialog.getSaveFileName(parent_win, "Export Layout", default, "PNG Image (*.png);;PDF Document (*.pdf);;SVG Vector (*.svg)")
        if not path:
            return
        try:
            from .layout_utils import export_layout
            if export_layout(layout, path, dpi=int(dpi)) and os.path.exists(path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
                if hasattr(iface, "messageBar"):
                    iface.messageBar().pushSuccess("CartoLab", f"Exported & Opened: {path}")
        except Exception as exc:
            QMessageBox.critical(parent_win, "Export Error", str(exc))

    btn_dock_export.clicked.connect(_dock_export)
    fl_exp.addRow(btn_dock_export)
    lyt.addWidget(gb_exp)

    lyt.addStretch()
    dock.setWidget(w)
    return dock


def _get_designer_layout(designer):
    """Retrieve the QgsLayout from a designer instance safely."""
    if hasattr(designer, "layout"):
        return designer.layout()
    if hasattr(designer, "currentLayout"):
        return designer.currentLayout()
    if hasattr(designer, "masterLayout"):
        return designer.masterLayout()
    return None
