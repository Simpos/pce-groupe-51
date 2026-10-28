# -*- coding: utf-8 -*-
"""Entry point for the Zones de vol QGIS plugin."""


def classFactory(iface):
    """Load ZonesDeVolPlugin class from file zones_de_vol.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .zones_de_vol import ZonesDeVolPlugin
    return ZonesDeVolPlugin(iface)
