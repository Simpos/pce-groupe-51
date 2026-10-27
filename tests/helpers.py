"""Accès aux modules du plugin, quel que soit le nom de son dossier."""
import importlib
import os
import sys

from qgis.core import QgsPointXY

PLUGIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
PKG = os.path.basename(PLUGIN_DIR)
PARENT_DIR = os.path.dirname(PLUGIN_DIR)

if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)


def module(nom: str):
    """Importe un module du plugin, par exemple module('source.zone')."""
    return importlib.import_module(f"{PKG}.{nom}")


def carre(cote: float = 2.0, cx: float = 0.0, cy: float = 0.0) -> list[QgsPointXY]:
    """Quatre sommets d'un carré de côté `cote`, centré sur (cx, cy)."""
    h = cote / 2
    return [
        QgsPointXY(cx - h, cy - h),
        QgsPointXY(cx + h, cy - h),
        QgsPointXY(cx + h, cy + h),
        QgsPointXY(cx - h, cy + h),
    ]


def distances_au_centre(zone, centre=(0.0, 0.0)) -> list[float]:
    """Distance de chaque sommet de la zone au centre donné."""
    import math
    return [math.hypot(p.x() - centre[0], p.y() - centre[1]) for p in zone.points]
