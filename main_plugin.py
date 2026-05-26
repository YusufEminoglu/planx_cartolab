# -*- coding: utf-8 -*-
"""PlanX CartoLab — Main plugin orchestrator (Processing provider + dock UI)."""
from __future__ import annotations

import os
from qgis.PyQt.QtWidgets import QAction, QMenu
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsApplication

from .processing.cartolab_provider import CartoLabProvider


class PlanXCartoLab:
    """Top-level QGIS plugin: registers Processing provider and menu/dock."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.provider: CartoLabProvider | None = None
        self.menu: QMenu | None = None
        self.actions: list[QAction] = []
        self.dock = None

    def initGui(self) -> None:
        icon_path = os.path.join(self.plugin_dir, "icons", "icon.png")
        menu_icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        # --- processing provider ---
        self.provider = CartoLabProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

        # --- PlanX sub-menu ---
        self.menu = QMenu("CartoLab", self.iface.mainWindow().menuBar())
        self.menu.menuAction().setIcon(menu_icon)

        # find or create parent PlanX menu
        parent_menu = None
        for action in self.iface.mainWindow().menuBar().actions():
            if action.text() == "PlanX":
                parent_menu = action.menu()
                break
        if parent_menu:
            parent_menu.addMenu(self.menu)
        else:
            self.iface.mainWindow().menuBar().addMenu(self.menu)

        self._add_action("cartolab_dock", "CartoLab Panel", self._toggle_dock, "bivariate.png")

    def _add_action(self, key: str, label: str, callback, icon_name: str) -> None:
        icon_path = os.path.join(self.plugin_dir, "icons", icon_name)
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        action = QAction(icon, label, self.iface.mainWindow())
        action.triggered.connect(callback)
        self.menu.addAction(action)
        self.actions.append(action)

    def _toggle_dock(self) -> None:
        if self.dock is None:
            from .ui.cartolab_dock import CartoLabDock
            self.dock = CartoLabDock(self.iface)
            self.iface.addDockWidget(2, self.dock)  # Qt.RightDockWidgetArea
        self.dock.setVisible(not self.dock.isVisible())

    def unload(self) -> None:
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
        if self.menu:
            self.iface.mainWindow().menuBar().removeAction(self.menu.menuAction())
        for action in self.actions:
            self.menu.removeAction(action)
        self.actions.clear()
        if self.dock:
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None
