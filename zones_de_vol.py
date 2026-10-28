# -*- coding: utf-8 -*-
"""Main plugin class for Zones de vol."""

import os
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .dock_widget import ZonesDeVolDockWidget


class ZonesDeVolPlugin:
    """QGIS Plugin implementation for planning drone flight zones."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None
        self.dock_widget = None
        self.menu_name = "&Zones de vol"

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        self.action = QAction(icon, "Zones de vol", self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.setToolTip("Ouvrir le panneau de planification Zones de vol")
        self.action.triggered.connect(self.toggle_dock)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(self.menu_name, self.action)

        # Open the dock automatically on the right side
        self.open_dock()

    def open_dock(self):
        """Create and attach the dock widget on the right side of QGIS."""
        if self.dock_widget is None:
            self.dock_widget = ZonesDeVolDockWidget(
                self.iface,
                self.plugin_dir,
                parent=self.iface.mainWindow(),
            )
            self.dock_widget.visibilityChanged.connect(self._on_dock_visibility_changed)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)

        self.dock_widget.show()
        self.dock_widget.raise_()
        if self.action:
            self.action.setChecked(True)

    def toggle_dock(self, checked):
        """Show or hide the right-side dock widget."""
        if checked:
            self.open_dock()
        elif self.dock_widget is not None:
            self.dock_widget.hide()

    def _on_dock_visibility_changed(self, visible):
        """Keep the toolbar action state synchronized with the dock visibility."""
        if self.action is not None:
            self.action.setChecked(visible)

    def unload(self):
        """Remove the plugin menu item, icon, map tools, and dock widget."""
        if self.dock_widget is not None:
            self.dock_widget.cleanup()
            self.iface.removeDockWidget(self.dock_widget)
            self.dock_widget.deleteLater()
            self.dock_widget = None

        if self.action is not None:
            self.iface.removePluginMenu(self.menu_name, self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None
