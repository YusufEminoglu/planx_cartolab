# -*- coding: utf-8 -*-
"""PlanX CartoLab — Main plugin (Processing provider + production dashboard + annotation tool)."""
from __future__ import annotations

import os

from qgis.core import Qgis, QgsApplication
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
        self.action_25d = None
        self.action_annotate = None
        self.dialog = None
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
        icon_path = os.path.join(icon_dir, "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        # Dashboard action
        self.action_dashboard = QAction(icon, "CartoLab Dashboard", self.iface.mainWindow())
        self.action_dashboard.triggered.connect(self.open_dashboard)
        self.iface.addToolBarIcon(self.action_dashboard)
        self.iface.addPluginToMenu("&PlanX CartoLab", self.action_dashboard)

        # 2.5D styling panel action
        self.action_25d = QAction(icon, "2.5D Styling Panel", self.iface.mainWindow())
        self.action_25d.triggered.connect(self.open_25d_panel)
        self.iface.addPluginToMenu("&PlanX CartoLab", self.action_25d)

        # Annotation tool action
        bivar_icon_path = os.path.join(icon_dir, "bivariate.png")
        annotate_icon = QIcon(bivar_icon_path) if os.path.exists(bivar_icon_path) else icon
        self.action_annotate = QAction(annotate_icon, "Inspect Features (Radar Chart)",
                                        self.iface.mainWindow())
        self.action_annotate.setCheckable(True)
        self.action_annotate.toggled.connect(self._toggle_annotation_tool)
        self.iface.addPluginToMenu("&PlanX CartoLab", self.action_annotate)

    def open_dashboard(self) -> None:
        if self.dialog is None:
            from .ui.cartolab_dashboard import CartoLabDashboard
            self.dialog = CartoLabDashboard(self.iface, self.iface.mainWindow())
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

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
            try:
                self.iface.mapCanvas().unsetMapTool(self.annotation_tool)
            except Exception:
                pass
        if self.iface:
            if self.action_dashboard:
                self.iface.removePluginMenu("&PlanX CartoLab", self.action_dashboard)
                self.iface.removeToolBarIcon(self.action_dashboard)
            if self.action_25d:
                self.iface.removePluginMenu("&PlanX CartoLab", self.action_25d)
            if self.action_annotate:
                self.iface.removePluginMenu("&PlanX CartoLab", self.action_annotate)
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
