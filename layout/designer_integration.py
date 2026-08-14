# -*- coding: utf-8 -*-
"""
PlanX CartoLab — Print Layout Designer Window Integration & Embedded Studio Dock.

Hooks directly into QGIS QgsLayoutDesignerInterface instances so that users
have access to CartoLab cartographic tools, presets, decorators, and 1-click
export & open right inside the QGIS Print Layout Designer window.
"""
from __future__ import annotations

import math
import os
from contextlib import suppress
from typing import Optional

try:
    from qgis.core import QgsProject, QgsLayoutItemMap
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
    QgsProject = QgsLayoutItemMap = None
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

    # Clean up any existing CartoLab dock widgets in this designer window
    with suppress(Exception):
        for existing in main_win.findChildren(QDockWidget):
            if existing.objectName() == "CartoLabLayoutStudioDock":
                main_win.removeDockWidget(existing)
                existing.deleteLater()

    icon_dir = os.path.join(os.path.dirname(__file__), "..", "icons")
    icon_path = os.path.join(icon_dir, "icon.png")
    icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

    # 1. Create 1 Embedded Dock Panel inside Print Layout Window
    dock = create_cartolab_layout_dock(iface, designer, main_win)
    dock.setWindowIcon(icon)
    _RightDock = getattr(getattr(Qt, "DockWidgetArea", Qt), "RightDockWidgetArea", getattr(Qt, "RightDockWidgetArea", 2))
    with suppress(Exception):
        if hasattr(designer, "addDockWidget"):
            designer.addDockWidget(_RightDock, dock)
        elif hasattr(main_win, "addDockWidget"):
            main_win.addDockWidget(_RightDock, dock)

    # 2. Add single PlanX CartoLab Menu item and QToolBar Action Button
    with suppress(Exception):
        act_toggle = dock.toggleViewAction()
        act_toggle.setText("PlanX CartoLab Studio")
        act_toggle.setIcon(icon)
        act_toggle.setCheckable(True)

        menubar = main_win.menuBar()
        if menubar:
            menu = QMenu("&PlanX CartoLab", menubar)
            menu.addAction(act_toggle)
            menubar.addMenu(menu)

        # Add toggle action directly to the Print Layout Designer's primary toolbar
        toolbars = main_win.findChildren(QToolBar)
        target_tb = None
        for tb in toolbars:
            tb_name = tb.objectName().lower()
            if "layout" in tb_name or "main" in tb_name:
                target_tb = tb
                break
        if target_tb is None and toolbars:
            target_tb = toolbars[0]
        if target_tb:
            target_tb.addAction(act_toggle)


def _get_cartolab_icon(name: str = "icon.png") -> QIcon:
    base = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(base, "icons", name)
    if os.path.exists(path):
        return QIcon(path)
    fallback = os.path.join(base, "icons", "icon.png")
    return QIcon(fallback) if os.path.exists(fallback) else QIcon()


def create_cartolab_layout_dock(iface, designer, parent_win) -> QDockWidget:
    """Create embedded CartoLab Layout Studio Dock Widget for the layout designer."""
    dock = QDockWidget("CartoLab Layout Studio", parent_win)
    dock.setObjectName("CartoLabLayoutStudioDock")
    dock.setWindowIcon(_get_cartolab_icon("icon.png"))
    _LeftDock = getattr(getattr(Qt, "DockWidgetArea", Qt), "LeftDockWidgetArea", getattr(Qt, "LeftDockWidgetArea", 1))
    _RightDock = getattr(getattr(Qt, "DockWidgetArea", Qt), "RightDockWidgetArea", getattr(Qt, "RightDockWidgetArea", 2))
    dock.setAllowedAreas(_LeftDock | _RightDock)

    container = QWidget()
    main_lyt = QVBoxLayout(container)
    main_lyt.setContentsMargins(4, 4, 4, 4)
    main_lyt.setSpacing(6)

    tabs = QTabWidget()
    tabs.setStyleSheet("""
        QTabWidget::pane {
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            background: #ffffff;
        }
        QTabBar::tab {
            background: #f1f5f9;
            color: #475569;
            padding: 8px 12px;
            font-weight: 600;
            font-size: 11px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            margin-right: 2px;
            border: 1px solid #e2e8f0;
        }
        QTabBar::tab:selected {
            background: #ffffff;
            color: #0f172a;
            font-weight: 700;
            border-bottom: 2px solid #2563eb;
        }
        QGroupBox {
            font-weight: 700;
            font-size: 12px;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            margin-top: 8px;
            padding: 10px 8px 8px 8px;
            background: #ffffff;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
            color: #0f172a;
        }
        QPushButton {
            background-color: #0f172a;
            color: #ffffff;
            border-radius: 6px;
            padding: 7px 12px;
            font-weight: 600;
            font-size: 11px;
            border: 1px solid #0f172a;
        }
        QPushButton:hover {
            background-color: #1e293b;
            border-color: #1e293b;
        }
        QPushButton#ghost {
            background-color: #ffffff;
            color: #334155;
            border: 1px solid #cbd5e1;
        }
        QPushButton#ghost:hover {
            background-color: #f8fafc;
            color: #0f172a;
        }
        QLineEdit, QComboBox, QDoubleSpinBox {
            background: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 5px;
            padding: 4px 6px;
            color: #0f172a;
            font-size: 11px;
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
    btn_apply_theme.setIcon(_get_cartolab_icon("style.png"))

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
    btn_dock_typo = QPushButton("Apply Swiss Typography")
    btn_dock_typo.setIcon(_get_cartolab_icon("layout.png"))

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

    btn_dock_title = QPushButton("Add Publication Title Block")
    btn_dock_title.setIcon(_get_cartolab_icon("layout.png"))

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

    tabs.addTab(tab_canvas, _get_cartolab_icon("layout.png"), "Canvas & Grid")


    # -----------------------------------------------------------------
    # TAB 2: Decorators (Bivariate, Scale Bar, North Arrow)
    # -----------------------------------------------------------------
    tab_dec = QWidget()
    lyt_dec = QVBoxLayout(tab_dec)
    lyt_dec.setContentsMargins(8, 8, 8, 8)
    lyt_dec.setSpacing(10)

    gb_bivar = QGroupBox("Bivariate Legend Settings")
    fl_bivar = QFormLayout(gb_bivar)

    xlabel_input = QLineEdit("Variable X")
    fl_bivar.addRow("X Axis Label:", xlabel_input)

    ylabel_input = QLineEdit("Variable Y")
    fl_bivar.addRow("Y Axis Label:", ylabel_input)

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

    btn_add_bivar = QPushButton("Add Bivariate Legend")
    btn_add_bivar.setIcon(_get_cartolab_icon("bivariate.png"))

    def _add_bivar():
        layout = _get_designer_layout(designer)
        if not layout:
            return
        colors = palette_combo.currentData()
        ltype = shape_combo.currentData()
        x_lbl = xlabel_input.text().strip() or "Variable X"
        y_lbl = ylabel_input.text().strip() or "Variable Y"
        try:
            from .legend_decorator import add_bivariate_legend
            add_bivariate_legend(layout, colors=colors, legend_type=ltype, x_label=x_lbl, y_label=y_lbl)
            if hasattr(iface, "messageBar"):
                iface.messageBar().pushSuccess("CartoLab", f"Bivariate legend added ({x_lbl} vs {y_lbl}).")
        except Exception as exc:
            QMessageBox.critical(parent_win, "Bivariate Legend Error", str(exc))

    btn_add_bivar.clicked.connect(_add_bivar)
    fl_bivar.addRow(btn_add_bivar)

    btn_update_bivar = QPushButton("Update Selected Legend in Layout")
    btn_update_bivar.setIcon(_get_cartolab_icon("bivariate.png"))

    def _update_bivar():
        layout = _get_designer_layout(designer)
        if not layout:
            return
        selected = layout.selectedItems()
        if not selected:
            QMessageBox.information(parent_win, "Update Legend", "Please select a bivariate legend group in the layout canvas first.")
            return

        # Record position of first selected item in layout mm coordinates
        first = selected[0]
        pos_x, pos_y = 12.0, 12.0  # fallback default
        with suppress(Exception):
            if hasattr(first, "positionWithUnits"):
                pt = first.positionWithUnits()
                pos_x = pt.x()
                pos_y = pt.y()
            elif hasattr(first, "pos"):
                # pos() returns scene points; approximate as mm
                pos_x = first.pos().x()
                pos_y = first.pos().y()

        # Remove selected items using the correct PyQGIS method
        for item in list(selected):
            with suppress(Exception):
                layout.removeLayoutItem(item)

        colors = palette_combo.currentData()
        ltype = shape_combo.currentData()
        x_lbl = xlabel_input.text().strip() or "Variable X"
        y_lbl = ylabel_input.text().strip() or "Variable Y"
        try:
            from .legend_decorator import add_bivariate_legend
            add_bivariate_legend(layout, colors=colors, legend_type=ltype, position=(pos_x, pos_y), x_label=x_lbl, y_label=y_lbl)
            if hasattr(iface, "messageBar"):
                iface.messageBar().pushSuccess("CartoLab", "Bivariate legend updated in-place.")
        except Exception as exc:
            QMessageBox.critical(parent_win, "Update Legend Error", str(exc))

    btn_update_bivar.clicked.connect(_update_bivar)
    fl_bivar.addRow(btn_update_bivar)
    lyt_dec.addWidget(gb_bivar)

    gb_map_elem = QGroupBox("Map Elements & Motifs")
    fl_elem = QFormLayout(gb_map_elem)

    scalebar_combo = QComboBox()
    scalebar_combo.addItem("Single Box", "Single Box")
    scalebar_combo.addItem("Double Box", "Double Box")
    scalebar_combo.addItem("Line Ticks", "Line Ticks")
    scalebar_combo.addItem("Stepped Box", "Stepped Box")
    fl_elem.addRow("Scalebar Style:", scalebar_combo)

    btn_dock_scalebar = QPushButton("Add Executive Scale Bar")
    btn_dock_scalebar.setIcon(_get_cartolab_icon("layout.png"))

    def _dock_scalebar():
        layout = _get_designer_layout(designer)
        if not layout:
            return
        try:
            from .legend_decorator import add_scalebar_to_layout
            sname = scalebar_combo.currentData() or "Single Box"
            add_scalebar_to_layout(layout, style_name=sname)
            if hasattr(iface, "messageBar"):
                iface.messageBar().pushSuccess("CartoLab", f"Executive scale bar '{sname}' added to layout.")
        except Exception as exc:
            QMessageBox.critical(parent_win, "Scale Bar Error", str(exc))

    btn_dock_scalebar.clicked.connect(_dock_scalebar)
    fl_elem.addRow(btn_dock_scalebar)

    north_combo = QComboBox()
    north_combo.addItem("Architectural Compass Rose", "compass_rose")
    north_combo.addItem("Swiss Minimalist Needle", "swiss_minimal")
    north_combo.addItem("Nautical Star 4-Point", "nautical_star")
    fl_elem.addRow("North Arrow Motif:", north_combo)

    btn_dock_north = QPushButton("Add Publication North Arrow")
    btn_dock_north.setIcon(_get_cartolab_icon("compass.png"))

    def _dock_north():
        layout = _get_designer_layout(designer)
        if not layout:
            return
        try:
            from .legend_decorator import add_north_arrow_to_layout
            npreset = north_combo.currentData() or "compass_rose"
            add_north_arrow_to_layout(layout, preset=npreset)
            if hasattr(iface, "messageBar"):
                iface.messageBar().pushSuccess("CartoLab", f"Publication north arrow '{north_combo.currentText()}' added.")
        except Exception as exc:
            QMessageBox.critical(parent_win, "North Arrow Error", str(exc))

    btn_dock_north.clicked.connect(_dock_north)
    fl_elem.addRow(btn_dock_north)

    btn_dock_legend_style = QPushButton("Style Legend (Clean Publication)")
    btn_dock_legend_style.setIcon(_get_cartolab_icon("style.png"))

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

    btn_dock_filter_legend = QPushButton("Filter Legend to Map Extent")
    btn_dock_filter_legend.setObjectName("ghost")
    btn_dock_filter_legend.setIcon(_get_cartolab_icon("style.png"))

    def _dock_filter_legend():
        layout = _get_designer_layout(designer)
        if not layout:
            return
        main_map = None
        for item in layout.items():
            if isinstance(item, QgsLayoutItemMap):
                main_map = item
                break
        if not main_map:
            QMessageBox.warning(parent_win, "Filter Legend", "No map item found in layout.")
            return

        from qgis.core import QgsLayoutItemLegend
        applied = False
        for item in layout.items():
            if isinstance(item, QgsLayoutItemLegend):
                item.setAutoUpdateModel(False)
                if hasattr(item, "setLinkedMap"):
                    item.setLinkedMap(main_map)
                if hasattr(item, "setLegendFilterByMapEnabled"):
                    item.setLegendFilterByMapEnabled(True)
                item.updateLegend()
                applied = True

        if applied:
            layout.refresh()
            if hasattr(iface, "messageBar"):
                iface.messageBar().pushSuccess("CartoLab", "Legend filtered to visible map extent.")
        else:
            QMessageBox.information(parent_win, "Filter Legend", "No legend found in layout.")

    btn_dock_filter_legend.clicked.connect(_dock_filter_legend)
    fl_elem.addRow(btn_dock_filter_legend)

    btn_dock_locator = QPushButton("Add Locator / Inset Map")
    btn_dock_locator.setIcon(_get_cartolab_icon("grid.png"))

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

    lyt_dec.addWidget(gb_map_elem)

    # Dedicated Publication Coordinate Grid Group
    gb_grid = QGroupBox("Publication Coordinate Grid")
    fl_grid = QFormLayout(gb_grid)

    grid_density_combo = QComboBox()
    grid_density_combo.addItem("Standard (5-6 divisions)", (6, 5))
    grid_density_combo.addItem("Coarse / Clean (3-4 divisions)", (4, 3))
    grid_density_combo.addItem("Dense (7-9 divisions)", (8, 6))
    fl_grid.addRow("Grid Density:", grid_density_combo)

    grid_style_combo = QComboBox()
    grid_style_combo.addItem("Solid Lines", "Solid")
    grid_style_combo.addItem("Crosshairs (+)", "Cross")
    grid_style_combo.addItem("Border Ticks Only", "FrameAndAnnotationsOnly")
    fl_grid.addRow("Grid Style:", grid_style_combo)

    grid_frame_combo = QComboBox()
    grid_frame_combo.addItem("Academic Zebra Border", "Zebra")
    grid_frame_combo.addItem("Clean Line Border", "LineBorder")
    grid_frame_combo.addItem("Frame-Free (Minimal)", "NoFrame")
    fl_grid.addRow("Frame Border:", grid_frame_combo)

    btn_dock_grid = QPushButton("Apply Publication Grid")
    btn_dock_grid.setIcon(_get_cartolab_icon("grid.png"))

    def _dock_grid():
        layout = _get_designer_layout(designer)
        if not layout:
            return
        try:
            from .coordinate_grid import apply_coordinate_grid_decorator
            divs = grid_density_combo.currentData() or (6, 5)
            gstyle = grid_style_combo.currentData() or "Solid"
            fstyle = grid_frame_combo.currentData() or "Zebra"
            apply_coordinate_grid_decorator(
                layout,
                target_divisions_x=divs[0],
                target_divisions_y=divs[1],
                grid_style=gstyle,
                frame_style=fstyle,
                show_annotations=True,
            )
            if hasattr(iface, "messageBar"):
                iface.messageBar().pushSuccess("CartoLab", "Publication coordinate grid applied.")
        except Exception as exc:
            QMessageBox.critical(parent_win, "Coordinate Grid Error", str(exc))

    btn_dock_grid.clicked.connect(_dock_grid)
    fl_grid.addRow(btn_dock_grid)

    lyt_dec.addWidget(gb_grid)

    # Smart Map Utilities
    gb_smart = QGroupBox("Smart Map Tools")
    fl_smart = QFormLayout(gb_smart)

    btn_snap_scale = QPushButton("Snap to Standard Scale (1:10k, 1:25k…)")
    btn_snap_scale.setIcon(_get_cartolab_icon("compass.png"))

    def _dock_snap_scale():
        layout = _get_designer_layout(designer)
        if not layout:
            return
        for item in layout.items():
            if isinstance(item, QgsLayoutItemMap):
                curr = item.scale()
                scales = [500, 1000, 2000, 2500, 5000, 10000, 20000, 25000, 50000, 100000, 200000, 250000, 500000, 1000000]
                best = min(scales, key=lambda s: abs(math.log(s) - math.log(max(1.0, curr))))
                item.setScale(best)
                item.updateBoundingRect()
                layout.refresh()
                if hasattr(iface, "messageBar"):
                    iface.messageBar().pushSuccess("CartoLab", f"Map scale snapped to 1:{best:,}")
                return
        QMessageBox.warning(parent_win, "Snap Scale", "No map item found in layout.")

    btn_snap_scale.clicked.connect(_dock_snap_scale)
    fl_smart.addRow(btn_snap_scale)
    lyt_dec.addWidget(gb_smart)

    lyt_dec.addStretch()

    tabs.addTab(tab_dec, _get_cartolab_icon("bivariate.png"), "Decorators")

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
    btn_apply_iso.setIcon(_get_cartolab_icon("isometric.png"))

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

    btn_dock_export = QPushButton("Export & Open ↗")
    btn_dock_export.setIcon(_get_cartolab_icon("layout.png"))

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

    tabs.addTab(tab_exp, _get_cartolab_icon("isometric.png"), "3D & Export")

    main_lyt.addWidget(tabs)
    dock.setWidget(container)
    return dock



def _get_designer_layout(designer):
    """Retrieve the QgsLayout from a designer instance safely."""
    if designer is None:
        return None
    for attr in ("layout", "currentLayout", "masterLayout"):
        if hasattr(designer, attr):
            val = getattr(designer, attr)
            if callable(val):
                res = val()
                if res:
                    return res
            elif val:
                return val
    return None
