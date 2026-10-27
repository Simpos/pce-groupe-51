import os

# Doit être défini avant la création de QApplication : pas besoin d'écran
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from qgis.core import QgsApplication, QgsProject


@pytest.fixture(scope="session", autouse=True)
def qgs():
    """Initialise QGIS une seule fois pour toute la session de tests."""
    app = QgsApplication([], True)
    app.initQgis()
    yield app
    app.exitQgis()


@pytest.fixture(autouse=True)
def projet_propre():
    """Retire toutes les couches du projet après chaque test."""
    yield
    QgsProject.instance().removeAllMapLayers()
