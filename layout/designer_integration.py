# -*- coding: utf-8 -*-
"""
PlanX CartoLab — Print Layout Designer Window Integration.

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
    from qgis.PyQt.QtCore import QUrl
    from qgis.PyQt.QtGui import QDesktopServices, QIcon
    from qgis.PyQt.QtWidgets import (
        QAction,
        QFileDialog,
        QMenu,
        QMessageBox,
        QToolBar,
    )
except ImportError:
    QgsProject = None
    QUrl = QDesktopServices = QIcon = QAction = QFileDialog = QMenu = QMessageBox = QToolBar = None







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
    """Attach PlanX CartoLab toolbar & menu inside a QgsLayoutDesignerInterface window."""
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


def _get_designer_layout(designer):
    """Retrieve the QgsLayout from a designer instance safely."""
    if hasattr(designer, "layout"):
        return designer.layout()
    if hasattr(designer, "currentLayout"):
        return designer.currentLayout()
    if hasattr(designer, "masterLayout"):
        return designer.masterLayout()
    return None
