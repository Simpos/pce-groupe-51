from unittest.mock import MagicMock

import pytest
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsPointXY,
    QgsProject,
    QgsWkbTypes,
)
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtCore import QPoint, Qt

from .helpers import module

PointManager = module("source.pointManager").PointManager


@pytest.fixture
def canvas(qgs):
    c = QgsMapCanvas()
    c.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:2154"))
    return c


@pytest.fixture
def pm(canvas):
    return PointManager(canvas)


def evenement(bouton, modificateurs=Qt.NoModifier):
    ev = MagicMock()
    ev.button.return_value = bouton
    ev.modifiers.return_value = modificateurs
    ev.pos.return_value = QPoint(0, 0)
    return ev


def fixer_position(monkeypatch, pm, x, y):
    """Remplace la conversion écran -> carte par une position fixe."""
    monkeypatch.setattr(pm, "toMapCoordinates", lambda pos: QgsPointXY(x, y))


# --- Initialisation ---

def test_init(pm, canvas):
    assert pm.canvas is canvas
    assert pm.couche is None
    assert pm.couche_id is None
    assert pm.points == []
    assert pm.crs_cible.authid() == "EPSG:2154"


# --- Couche mémoire ---

def test_create_point_layer(pm):
    couche = pm.create_point_layer()

    assert couche.name() == "Points posés"
    assert couche.geometryType() == QgsWkbTypes.PointGeometry
    assert couche.crs().authid() == "EPSG:2154"
    assert QgsProject.instance().mapLayer(couche.id()) is not None
    assert pm.couche_id == couche.id()


def test_couche_presente(pm):
    assert not pm._couche_presente()

    pm.create_point_layer()
    assert pm._couche_presente()

    QgsProject.instance().removeMapLayer(pm.couche_id)
    assert not pm._couche_presente()


# --- activer / desactiver ---

def test_activer_cree_la_couche_et_active_l_outil(pm, canvas):
    pm.activer()

    assert pm.couche is not None
    assert canvas.mapTool() is pm


def test_activer_ne_duplique_pas_la_couche(pm):
    pm.activer()
    premier_id = pm.couche_id

    pm.activer()

    assert pm.couche_id == premier_id
    assert len(QgsProject.instance().mapLayersByName("Points posés")) == 1


def test_desactiver(pm, canvas):
    pm.activer()
    pm.points.append(QgsPointXY(0, 0))

    pm.desactiver()

    assert canvas.mapTool() is None
    assert pm.couche is None
    assert pm.couche_id is None
    assert pm.points == []
    assert QgsProject.instance().mapLayersByName("Points posés") == []


def test_desactiver_sans_couche(pm):
    pm.desactiver()  # ne doit pas lever d'exception


# --- ajouter_point / vider ---

def test_ajouter_point_cree_la_couche_si_absente(pm):
    pm.ajouter_point(QgsPointXY(348000, 6683000))

    assert pm.couche is not None
    assert pm.couche.featureCount() == 1
    assert len(pm.points) == 1


def test_ajouter_plusieurs_points(pm):
    for x in (1, 2, 3):
        pm.ajouter_point(QgsPointXY(x, x))

    assert pm.couche.featureCount() == 3
    assert len(pm.points) == 3


def test_ajouter_point_stocke_la_geometrie(pm):
    pm.ajouter_point(QgsPointXY(348000, 6683000))

    geom = list(pm.couche.getFeatures())[0].geometry().asPoint()
    assert geom.x() == pytest.approx(348000)
    assert geom.y() == pytest.approx(6683000)


def test_vider_garde_la_couche(pm):
    pm.ajouter_point(QgsPointXY(1, 1))

    pm.vider()

    assert pm.points == []
    assert pm.couche.featureCount() == 1


# --- Saisie à la souris ---

def test_ctrl_clic_gauche_ajoute_un_point(pm, monkeypatch):
    fixer_position(monkeypatch, pm, 1000.0, 2000.0)

    pm.canvasReleaseEvent(evenement(Qt.LeftButton, Qt.ControlModifier))

    assert len(pm.points) == 1
    assert (pm.points[0].x(), pm.points[0].y()) == (1000.0, 2000.0)


def test_clic_gauche_sans_ctrl_est_ignore(pm, monkeypatch):
    fixer_position(monkeypatch, pm, 1000.0, 2000.0)

    pm.canvasReleaseEvent(evenement(Qt.LeftButton, Qt.NoModifier))

    assert pm.points == []


def test_clic_droit_desactive_l_outil(pm, canvas):
    pm.activer()

    pm.canvasReleaseEvent(evenement(Qt.RightButton))

    assert canvas.mapTool() is None


def test_autre_bouton_est_ignore(pm, monkeypatch):
    fixer_position(monkeypatch, pm, 1.0, 1.0)

    pm.canvasReleaseEvent(evenement(Qt.MiddleButton, Qt.ControlModifier))

    assert pm.points == []


# --- Conversion de CRS ---

def test_vers_crs_cible_identique(pm):
    p = pm._vers_crs_cible(QgsPointXY(348000, 6683000))
    assert p.x() == pytest.approx(348000)
    assert p.y() == pytest.approx(6683000)


def test_vers_crs_cible_depuis_wgs84(pm, canvas):
    canvas.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:4326"))

    # Coordonnées WGS84 proches de Nantes
    p = pm._vers_crs_cible(QgsPointXY(-1.55, 47.22))

    assert 100_000 < p.x() < 1_200_000
    assert 6_000_000 < p.y() < 7_200_000
