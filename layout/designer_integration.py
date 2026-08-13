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
        QLineEdit,
        QMenu,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QTabWidget,
        QToolBar,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    QgsProject = None
    Qt = QUrl = QDesktopServices = QIcon = QAction = QComboBox = QDockWidget = QDoubleSpinBox = QFileDialog = QFormLayout = QGroupBox = QHBoxLayout = QLabel = QLineEdit = QMenu = QMessageBox = QPushButton = QScrollArea = QTabWidget = QToolBar = QVBoxLayout = QWidget = None




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
    """Attach PlanX CartoLab embedded studio dock panel inside a QgsLayoutDesignerInterface window."""
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

    # 1. Create 1 Embedded Dock Panel inside Print Layout Window
    dock = create_cartolab_layout_dock(iface, designer, main_win)
    dock.setWindowIcon(icon)
    with suppress(Exception):
        if hasattr(designer, "addDockWidget"):
            designer.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        elif hasattr(main_win, "addDockWidget"):
            main_win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    # 2. Add single PlanX CartoLab Menu item to Designer MenuBar (No extra top toolbar)
    with suppress(Exception):
        menubar = main_win.menuBar()
        if menubar:
            menu = QMenu("&PlanX CartoLab", menubar)
            act_toggle = dock.toggleViewAction()
            act_toggle.setText("Show/Hide CartoLab Studio Panel")
            act_toggle.setIcon(icon)
            menu.addAction(act_toggle)
            menubar.addMenu(menu)


def create_cartolab_layout_dock(iface, designer, parent_win) -> QDockWidget:
    """Create embedded CartoLab Layout Studio Dock Widget for the layout designer."""
    dock = QDockWidget("CartoLab Layout Studio", parent_win)
    dock.setObjectName("CartoLabLayoutStudioDock")
    dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

    container = QWidget()
    main_lyt = QVBoxLayout(container)
    main_lyt.setContentsMargins(4, 4, 4, 4)
    main_lyt.setSpacing(6)

    tabs = QTabWidget()
    tabs.setStyleSheet("""
        QTabWidget::pane {
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            background: #ffffff;
        }
        QTabBar::tab {
            background: #f1f5f9;
            color: #334155;
            padding: 6px 10px;
            font-weight: 600;
            font-size: 11px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background: #ffffff;
            color: #2563eb;
            border-bottom: 2px solid #2563eb;
        }
        QPushButton {
            background-color: #2563eb;
            color: white;
            border-radius: 4px;
            padding: 6px 12px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #1d4ed8;
        }
    """)

    # -----------------------------------------------------------------
    # TAB 1: Canvas & Grid
    # -----------------------------------------------------------------
    tab_canvas = QWidget()
    lyt_canvas = QVBoxLayout(tab_canvas)
    lyt_canvas.setContentsMargins(8, 8, 8, 8)
    lyt_canvas.setSpacing(10)

    gb_theme = QGroupBox("Paper Canvas Theme")
    fl_theme = QFormLayout(gb_theme)
    theme_combo = QComboBox()
    theme_combo.addItem("Architectural Blueprint", "blueprint")
    theme_combo.addItem("Vintage Sepia Atlas", "sepia_atlas")
    theme_combo.addItem("Modern Swiss Minimalist", "swiss_modern")
    fl_theme.addRow("Theme:", theme_combo)
    btn_apply_theme = QPushButton("Apply Canvas Theme")

    def _apply_theme():
        layout = _get_designer_layout(designer)
        if not layout:
            return
        try:
            from .paper_themes import apply_paper_theme
            tkey = theme_combo.currentData()
            if apply_paper_theme(layout, tkey):
                if hasattr(iface, "messageBar"):
                    iface.messageBar().pushSuccess("CartoLab", f"Applied '{theme_combo.currentText()}' paper theme.")
        except Exception as exc:
            QMessageBox.critical(parent_win, "Paper Theme Error", str(exc))

    btn_apply_theme.clicked.connect(_apply_theme)
    fl_theme.addRow(btn_apply_theme)
    lyt_canvas.addWidget(gb_theme)

    gb_typo = QGroupBox("Swiss Typography & Grid")
    fl_typo = QFormLayout(gb_typo)
    btn_dock_typo = QPushButton("📏 Apply Swiss Typography & Grid")

    def _dock_typo():
        layout = _get_designer_layout(designer)
        if not layout:
            return
        try:
            from .typography_engine import apply_swiss_typography
            apply_swiss_typography(layout)
            if hasattr(iface, "messageBar"):
                iface.messageBar().pushSuccess("CartoLab", "Swiss typography hierarchy applied.")
        except Exception as exc:
            QMessageBox.critical(parent_win, "Swiss Typography", str(exc))

    btn_dock_typo.clicked.connect(_dock_typo)
    fl_typo.addRow(btn_dock_typo)

    btn_dock_title = QPushButton("🏛️ Add Publication Title Block")

    def _dock_title():
        layout = _get_designer_layout(designer)
        if not layout:
            return
        try:
            from .title_block import add_publication_title_block
            add_publication_title_block(layout)
            if hasattr(iface, "messageBar"):
                iface.messageBar().pushSuccess("CartoLab", "Publication title block added to layout.")
        except Exception as exc:
            QMessageBox.critical(parent_win, "Title Block Error", str(exc))

    btn_dock_title.clicked.connect(_dock_title)
    fl_typo.addRow(btn_dock_title)

    lyt_canvas.addWidget(gb_typo)
    lyt_canvas.addStretch()

    tabs.addTab(tab_canvas, "🎨 Canvas & Grid")


    # -----------------------------------------------------------------
    # TAB 2: Decorators (Bivariate, Scale Bar, North Arrow)
    # -----------------------------------------------------------------
    tab_dec = QWidget()
    lyt_dec = QVBoxLayout(tab_dec)
    lyt_dec.setContentsMargins(8, 8, 8, 8)
    lyt_dec.setSpacing(10)

    gb_bivar = QGroupBox("Bivariate Legend")
    fl_bivar = QFormLayout(gb_bivar)

    palette_combo = QComboBox()
    palette_combo.addItem("Teal-Brown", ("#e8e8e8", "#5ab4ac", "#d8b365", "#8c510a"))
    palette_combo.addItem("Purple-Green", ("#e8e8e8", "#7fbf7b", "#af8dc3", "#762a83"))
    palette_combo.addItem("Blue-Orange", ("#e8e8e8", "#fdae61", "#abd9e9", "#2c7bb6"))
    palette_combo.addItem("Pink-Green", ("#e8e8e8", "#a1d76a", "#e9a3c9", "#c51b7d"))
    fl_bivar.addRow("Palette:", palette_combo)

    shape_combo = QComboBox()
    shape_combo.addItem("Diamond", "diamond")
    shape_combo.addItem("Square", "square")
    fl_bivar.addRow("Shape:", shape_combo)

    title_input = QLineEdit()
    title_input.setPlaceholderText("Bivariate Relationship")
    fl_bivar.addRow("Title:", title_input)

    btn_add_bivar = QPushButton("Add Bivariate Legend")

    def _add_bivar():
        layout = _get_designer_layout(designer)
        if not layout:
            return
        colors = palette_combo.currentData()
        ltype = shape_combo.currentData()
        ltitle = title_input.text().strip() or "Bivariate Legend"
        try:
            from .legend_decorator import add_bivariate_legend
            add_bivariate_legend(layout, colors=colors, legend_type=ltype, title=ltitle)
            if hasattr(iface, "messageBar"):
                iface.messageBar().pushSuccess("CartoLab", f"Custom bivariate legend '{ltitle}' added.")
        except Exception as exc:
            QMessageBox.critical(parent_win, "Bivariate Legend", str(exc))

    btn_add_bivar.clicked.connect(_add_bivar)
    fl_bivar.addRow(btn_add_bivar)
    lyt_dec.addWidget(gb_bivar)

    gb_map_elem = QGroupBox("Map Elements")
    fl_elem = QFormLayout(gb_map_elem)

    btn_dock_scalebar = QPushButton("📏 Add Scale Bar")

    def _dock_scalebar():
        layout = _get_designer_layout(designer)
        if not layout:
            return
        try:
            from .legend_decorator import add_scalebar_to_layout
            add_scalebar_to_layout(layout)
            if hasattr(iface, "messageBar"):
                iface.messageBar().pushSuccess("CartoLab", "Scale bar added to layout.")
        except Exception as exc:
            QMessageBox.critical(parent_win, "Scale Bar Error", str(exc))

    btn_dock_scalebar.clicked.connect(_dock_scalebar)
    fl_elem.addRow(btn_dock_scalebar)

    btn_dock_north = QPushButton("🧭 Add North Arrow")

    def _dock_north():
        layout = _get_designer_layout(designer)
        if not layout:
            return
        try:
            from .legend_decorator import add_north_arrow_to_layout
            add_north_arrow_to_layout(layout)
            if hasattr(iface, "messageBar"):
                iface.messageBar().pushSuccess("CartoLab", "North arrow added to layout.")
        except Exception as exc:
            QMessageBox.critical(parent_win, "North Arrow Error", str(exc))

    btn_dock_north.clicked.connect(_dock_north)
    fl_elem.addRow(btn_dock_north)

    btn_dock_legend_style = QPushButton("📊 Style Legend (Publication Clean)")

    def _dock_legend_style():
        layout = _get_designer_layout(designer)
        if not layout:
            return
        try:
            from .legend_styler import style_layout_legend
            style_layout_legend(layout)
            if hasattr(iface, "messageBar"):
                iface.messageBar().pushSuccess("CartoLab", "Publication legend styling applied.")
        except Exception as exc:
            QMessageBox.critical(parent_win, "Legend Style Error", str(exc))

    btn_dock_legend_style.clicked.connect(_dock_legend_style)
    fl_elem.addRow(btn_dock_legend_style)

    btn_dock_locator = QPushButton("📍 Add Locator / Inset Map")

    def _dock_locator():
        layout = _get_designer_layout(designer)
        if not layout:
            return
        try:
            from .locator_map import add_locator_inset_map
            add_locator_inset_map(layout)
            if hasattr(iface, "messageBar"):
                iface.messageBar().pushSuccess("CartoLab", "Locator inset map frame added to layout.")
        except Exception as exc:
            QMessageBox.critical(parent_win, "Locator Map Error", str(exc))

    btn_dock_locator.clicked.connect(_dock_locator)
    fl_elem.addRow(btn_dock_locator)

    btn_dock_grid = QPushButton("🌐 Apply Coordinate Grid")

    def _dock_grid():
        layout = _get_designer_layout(designer)
        if not layout:
            return
        try:
            from .coordinate_grid import apply_coordinate_grid_decorator
            apply_coordinate_grid_decorator(layout)
            if hasattr(iface, "messageBar"):
                iface.messageBar().pushSuccess("CartoLab", "Coordinate grid applied to layout map.")
        except Exception as exc:
            QMessageBox.critical(parent_win, "Coordinate Grid Error", str(exc))

    btn_dock_grid.clicked.connect(_dock_grid)
    fl_elem.addRow(btn_dock_grid)


    lyt_dec.addWidget(gb_map_elem)

    lyt_dec.addStretch()

    tabs.addTab(tab_dec, "💎 Decorators")

    # -----------------------------------------------------------------
    # TAB 3: 3D Perspective & Quick Export
    # -----------------------------------------------------------------
    tab_exp = QWidget()
    lyt_exp = QVBoxLayout(tab_exp)
    lyt_exp.setContentsMargins(8, 8, 8, 8)
    lyt_exp.setSpacing(10)

    gb_iso = QGroupBox("2.5D Isometric Stack")
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
    lyt_exp.addWidget(gb_iso)

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
    lyt_exp.addWidget(gb_exp)
    lyt_exp.addStretch()

    tabs.addTab(tab_exp, "⚡ 3D & Export")

    main_lyt.addWidget(tabs)
    dock.setWidget(container)
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
