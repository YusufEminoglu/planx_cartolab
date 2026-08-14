# -*- coding: utf-8 -*-
"""PlanX CartoLab — Main plugin (Processing provider + production dashboard + annotation tool)."""
from __future__ import annotations

import os
from contextlib import suppress

from qgis.core import Qgis, QgsApplication
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .processing.cartolab_provider import CartoLabProvider


IS_QGIS4 = int(getattr(Qgis, "QGIS_VERSION_INT", 0)) >= 40000


class PlanXCartoLab:
    """Top-level QGIS plugin: toolbar icon + menu + Processing provider + dashboard + annotation tool."""

    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.action_dashboard = None
        self.action_quick_style = None
        self.action_layout = None
        self.action_25d = None
        self.action_annotate = None
        self.action_welcome = None
        self.dialog = None
        self.welcome = None
        self.annotation_tool = None

    def initProcessing(self) -> None:
        if self.provider is not None:
            return
        self.provider = CartoLabProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self) -> None:
        self.initProcessing()
        if not self.iface:
            return

        icon_dir = os.path.join(os.path.dirname(__file__), "icons")
        def _icon(name):
            p = os.path.join(icon_dir, name)
            return QIcon(p) if os.path.exists(p) else QIcon(os.path.join(icon_dir, "icon.png"))

        # 1. Main Dashboard action
        self.action_dashboard = QAction(_icon("icon.png"), "PlanX CartoLab Studio", self.iface.mainWindow())
        self.action_dashboard.setToolTip("Open PlanX CartoLab Production Console")
        self.action_dashboard.triggered.connect(self.open_dashboard)
        self.iface.addToolBarIcon(self.action_dashboard)
        self.iface.addPluginToMenu("&PlanX CartoLab", self.action_dashboard)

        # 2. Symbology & Quick Style action
        self.action_quick_style = QAction(_icon("style.png"), "Quick Style Symbology Studio", self.iface.mainWindow())
        self.action_quick_style.setToolTip("Open Quick Style & Bivariate Symbology Studio")
        self.action_quick_style.triggered.connect(self.open_quick_style)
        self.iface.addToolBarIcon(self.action_quick_style)
        self.iface.addPluginToMenu("&PlanX CartoLab", self.action_quick_style)

        # 3. Layout Automation Studio action
        self.action_layout = QAction(_icon("layout.png"), "Print Layout Automation Studio", self.iface.mainWindow())
        self.action_layout.setToolTip("Open Print Layout Automation & Auto Map Sheet")
        self.action_layout.triggered.connect(self.open_layout_studio)
        self.iface.addToolBarIcon(self.action_layout)
        self.iface.addPluginToMenu("&PlanX CartoLab", self.action_layout)

        # 4. 2.5D styling panel action
        self.action_25d = QAction(_icon("isometric.png"), "2.5D Building Extrusion Panel", self.iface.mainWindow())
        self.action_25d.setToolTip("Apply 2.5D Isometric Building Extrusions & Lighting Presets")
        self.action_25d.triggered.connect(self.open_25d_panel)
        self.iface.addPluginToMenu("&PlanX CartoLab", self.action_25d)

        # 5. Annotation / Inspector tool action
        self.action_annotate = QAction(_icon("inspector.png"), "Inspect Features (Radar Chart)", self.iface.mainWindow())
        self.action_annotate.setToolTip("Inspect attributes and radar chart on map click")
        self.action_annotate.setCheckable(True)
        self.action_annotate.toggled.connect(self._toggle_annotation_tool)
        self.iface.addToolBarIcon(self.action_annotate)
        self.iface.addPluginToMenu("&PlanX CartoLab", self.action_annotate)

        # 6. Welcome / sample-map action (onboarding entry)
        self.action_welcome = QAction(_icon("compass.png"), "Welcome & Sample Datasets", self.iface.mainWindow())
        self.action_welcome.triggered.connect(self.open_welcome)
        self.iface.addPluginToMenu("&PlanX CartoLab", self.action_welcome)

        # First run only: greet the user shortly after startup completes.
        QTimer.singleShot(1200, self._maybe_show_welcome)

        # Print Layout Designer window integration (attach dock toolbar & menu to layout windows)
        with suppress(Exception):
            from .layout.designer_integration import setup_designer_integration
            setup_designer_integration(self.iface)

    def _maybe_show_welcome(self) -> None:
        with suppress(Exception):
            from .ui.onboarding import should_show
            if should_show():
                self.open_welcome()

    def open_welcome(self) -> None:
        from .ui.onboarding import WelcomeDialog
        self.welcome = WelcomeDialog(self.iface, self.iface.mainWindow())
        self.welcome.show()
        self.welcome.raise_()
        self.welcome.activateWindow()

    def open_dashboard(self) -> None:
        if self.dialog is None:
            from .ui.cartolab_dashboard import CartoLabDashboard
            self.dialog = CartoLabDashboard(self.iface, self.iface.mainWindow())
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def open_quick_style(self) -> None:
        self.open_dashboard()
        if self.dialog and hasattr(self.dialog, "nav_sidebar"):
            self.dialog.nav_sidebar.setCurrentRow(0)

    def open_layout_studio(self) -> None:
        self.open_dashboard()
        if self.dialog and hasattr(self.dialog, "nav_sidebar"):
            self.dialog.nav_sidebar.setCurrentRow(1)

    def open_25d_panel(self) -> None:
        self.open_dashboard()
        if self.dialog and hasattr(self.dialog, "show_25d_panel"):
            self.dialog.show_25d_panel()

    def _toggle_annotation_tool(self, checked: bool) -> None:
        if checked:
            from .ui.floating_annotation import FloatingAnnotationTool
            canvas = self.iface.mapCanvas()
            self.annotation_tool = FloatingAnnotationTool(self.iface, canvas)
            canvas.setMapTool(self.annotation_tool)
        else:
            self.iface.mapCanvas().unsetMapTool(
                self.annotation_tool if self.annotation_tool else None
            )

    def unload(self) -> None:
        # unset map tool if active
        if self.annotation_tool:
            with suppress(Exception):
                self.iface.mapCanvas().unsetMapTool(self.annotation_tool)
        if self.iface:
            for act in (
                self.action_dashboard,
                self.action_quick_style,
                self.action_layout,
                self.action_25d,
                self.action_annotate,
                self.action_welcome,
            ):
                if act:
                    self.iface.removePluginMenu("&PlanX CartoLab", act)
                    self.iface.removeToolBarIcon(act)
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
