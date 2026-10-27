from unittest.mock import MagicMock

import pytest
from qgis.core import QgsCoordinateReferenceSystem, QgsPointXY
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtGui import QCloseEvent, QShowEvent

from .helpers import carre, module

dlg_mod = module("flying_areas_dialog")
FlyingAreasDialog = dlg_mod.FlyingAreasDialog
PointManager = module("source.pointManager").PointManager
ZoneManager = module("source.zoneManager").ZoneManager

DRONE_VALIDE = "Test\n100\nnull\nfixed_wing\n20\n"
DRONE_SANS_BUFFER = "Test\n100\nnull\nfixed_wing\nnull\n"


def ecrire_drone(dossier, nom, contenu):
    (dossier / nom).write_text(contenu, encoding="utf-8")


def messages_avertissement(iface_mock):
    """Textes passés à messageBar().pushWarning()."""
    return [appel.args[1] for appel in iface_mock.messageBar().pushWarning.call_args_list]


@pytest.fixture
def canvas(qgs):
    c = QgsMapCanvas()
    c.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:2154"))
    return c


@pytest.fixture
def iface_mock(canvas, monkeypatch):
    mock = MagicMock()
    mock.mapCanvas.return_value = canvas
    monkeypatch.setattr(dlg_mod, "iface", mock)
    return mock


@pytest.fixture
def dossier_drones(tmp_path, monkeypatch):
    monkeypatch.setattr(dlg_mod, "DOSSIER_DRONES", str(tmp_path))
    return tmp_path


@pytest.fixture
def dialog(qgs, iface_mock, dossier_drones):
    d = FlyingAreasDialog()
    yield d
    d.close()
    d.deleteLater()


# --- Initialisation ---

def test_init_cree_les_gestionnaires(dialog, canvas):
    assert isinstance(dialog.zone_manager, ZoneManager)
    assert isinstance(dialog.point_manager, PointManager)
    assert dialog.point_manager.canvas is canvas
    assert dialog.drones == {}


def test_init_bornes_des_curseurs(dialog):
    assert dialog.AltiVol.minimum() == 0 and dialog.AltiVol.maximum() == 1000
    assert dialog.VitVol.minimum() == 0 and dialog.VitVol.maximum() == 1000
    assert dialog.DensPop.minimum() == 0 and dialog.DensPop.maximum() == 1000000


# --- showEvent / closeEvent ---

def test_show_event_active_l_outil_de_clic(dialog, canvas):
    dialog.showEvent(QShowEvent())

    assert canvas.mapTool() is dialog.point_manager


def test_close_event_nettoie_les_gestionnaires(dialog):
    dialog.point_manager = MagicMock()
    dialog.zone_manager = MagicMock()

    dialog.closeEvent(QCloseEvent())

    dialog.point_manager.desactiver.assert_called_once()
    dialog.zone_manager.supprimer_couche.assert_called_once()


# --- charger_drones ---

def test_charger_drones_lit_les_txt_valides(dialog, dossier_drones, iface_mock):
    ecrire_drone(dossier_drones, "Test.txt", DRONE_VALIDE)
    ecrire_drone(dossier_drones, "Autre.txt", DRONE_SANS_BUFFER)  # lisible, nom "Test"
    ecrire_drone(dossier_drones, "notes.md", "ignoré")
    ecrire_drone(dossier_drones, "casse.txt", "trois\nlignes\nseulement")

    dialog.charger_drones()

    noms = [dialog.ChoixDrone.itemText(i) for i in range(dialog.ChoixDrone.count())]
    assert noms == ["Test", "Test"]
    assert "Test" in dialog.drones
    assert any("casse.txt" in m for m in messages_avertissement(iface_mock))


def test_charger_drones_ne_duplique_pas_la_liste(dialog, dossier_drones):
    ecrire_drone(dossier_drones, "Test.txt", DRONE_VALIDE)

    dialog.charger_drones()
    dialog.charger_drones()

    assert dialog.ChoixDrone.count() == 1


def test_charger_drones_dossier_absent(dialog, monkeypatch, iface_mock):
    monkeypatch.setattr(dlg_mod, "DOSSIER_DRONES", "dossier_inexistant_xyz")

    dialog.charger_drones()

    assert dialog.ChoixDrone.count() == 0
    assert dialog.drones == {}
    assert any("introuvable" in m for m in messages_avertissement(iface_mock))


# --- lancer_calcul ---

def test_lancer_calcul_sans_drone(dialog, iface_mock):
    dialog.lancer_calcul()

    assert any("Aucun drone" in m for m in messages_avertissement(iface_mock))


def test_lancer_calcul_mode_point_sans_point(dialog, dossier_drones, iface_mock):
    ecrire_drone(dossier_drones, "Test.txt", DRONE_VALIDE)
    dialog.charger_drones()
    dialog.ChoixMode.setCurrentIndex(0)

    dialog.lancer_calcul()

    assert any("point de départ" in m for m in messages_avertissement(iface_mock))


def test_lancer_calcul_mode_point_succes(dialog, dossier_drones):
    ecrire_drone(dossier_drones, "Test.txt", DRONE_VALIDE)
    dialog.charger_drones()
    dialog.ChoixMode.setCurrentIndex(0)
    dialog.point_manager.points = [QgsPointXY(348000, 6683000)]

    dialog.lancer_calcul()

    types = {f["type"] for f in dialog.zone_manager.layer.getFeatures()}
    assert types == {"fly", "cont", "buffer"}
    assert dialog.point_manager.points == []


def test_lancer_calcul_donnees_drone_incompletes(dialog, dossier_drones, iface_mock):
    ecrire_drone(dossier_drones, "Test.txt", DRONE_SANS_BUFFER)
    dialog.charger_drones()
    dialog.ChoixMode.setCurrentIndex(0)
    dialog.point_manager.points = [QgsPointXY(348000, 6683000)]

    dialog.lancer_calcul()

    assert any("incomplètes" in m for m in messages_avertissement(iface_mock))
    assert len(dialog.point_manager.points) == 1  # points conservés après échec


def test_lancer_calcul_mode_zone_trop_peu_de_points(dialog, dossier_drones, iface_mock):
    ecrire_drone(dossier_drones, "Test.txt", DRONE_VALIDE)
    dialog.charger_drones()
    dialog.ChoixMode.setCurrentIndex(1)
    dialog.point_manager.points = [QgsPointXY(0, 0), QgsPointXY(1, 1)]

    dialog.lancer_calcul()

    assert any("au moins 3" in m for m in messages_avertissement(iface_mock))


def test_lancer_calcul_mode_zone_succes(dialog, dossier_drones):
    ecrire_drone(dossier_drones, "Test.txt", DRONE_VALIDE)
    dialog.charger_drones()
    dialog.ChoixMode.setCurrentIndex(1)
    dialog.point_manager.points = carre(10, 348005, 6683005)

    dialog.lancer_calcul()

    aires = {f["type"]: f.geometry().area() for f in dialog.zone_manager.layer.getFeatures()}
    assert set(aires) == {"fly", "cont", "buffer"}
    assert aires["fly"] == pytest.approx(100.0)


# --- _construire_zone_vol ---

def test_construire_zone_vol_mode_point(dialog):
    dialog.ChoixMode.setCurrentIndex(0)
    points = [QgsPointXY(1, 1), QgsPointXY(348000, 6683000)]

    zone = dialog._construire_zone_vol(points)

    assert zone.type == "fly" and zone.priority == 3
    assert len(zone.points) == dlg_mod.NB_SOMMETS_ZONE_VOL
    centre = zone.barycenter()  # le dernier point cliqué sert de centre
    assert centre.x() == pytest.approx(348000, abs=0.01)
    assert centre.y() == pytest.approx(6683000, abs=0.01)


def test_construire_zone_vol_mode_point_sans_point(dialog, iface_mock):
    dialog.ChoixMode.setCurrentIndex(0)

    assert dialog._construire_zone_vol([]) is None
    assert messages_avertissement(iface_mock)


def test_construire_zone_vol_mode_zone(dialog):
    dialog.ChoixMode.setCurrentIndex(1)
    points = [QgsPointXY(0, 0), QgsPointXY(10, 0), QgsPointXY(0, 10)]

    zone = dialog._construire_zone_vol(points)

    assert zone.type == "fly"
    assert [(p.x(), p.y()) for p in zone.points] == [(0, 0), (10, 0), (0, 10)]


def test_construire_zone_vol_mode_zone_insuffisant(dialog, iface_mock):
    dialog.ChoixMode.setCurrentIndex(1)

    assert dialog._construire_zone_vol([QgsPointXY(0, 0)]) is None
    assert messages_avertissement(iface_mock)


# --- Boutons ---

def test_fermer_plugin_remet_les_curseurs_a_zero(dialog):
    dialog.show()
    dialog.AltiVol.setValue(500)
    dialog.VitVol.setValue(300)
    dialog.DensPop.setValue(1000)

    dialog.fermer_plugin()

    assert dialog.AltiVol.value() == 0
    assert dialog.VitVol.value() == 0
    assert dialog.DensPop.value() == 0
    assert not dialog.isVisible()


def test_ouvrir_seconde_fenetre(dialog, monkeypatch):
    classe = MagicMock()
    monkeypatch.setattr(dlg_mod, "SecondWindow", classe)

    dialog.ouvrir_seconde_fenetre()

    classe.assert_called_once_with(None)
    dialog.second_window.show.assert_called_once()


def test_accept_ne_fait_rien(dialog):
    assert dialog.accept() is None


def test_avertir_utilise_la_barre_de_messages(dialog, iface_mock):
    dialog._avertir("Un message")

    iface_mock.messageBar().pushWarning.assert_called_with("Zones de vol", "Un message")
