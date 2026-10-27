import pytest
from qgis.core import QgsCategorizedSymbolRenderer, QgsProject
from qgis.PyQt.QtGui import QColor

from .helpers import carre, module

zm_mod = module("source.zoneManager")
ZoneManager = zm_mod.ZoneManager
COUCHE_NOM = zm_mod.COUCHE_NOM
Zone = module("source.zone").Zone


def aires_par_type(couche):
    return {f["type"]: f.geometry().area() for f in couche.getFeatures()}


@pytest.fixture
def zm(qgs):
    return ZoneManager()


# --- Initialisation et couche ---

def test_init(zm):
    assert zm.priorities == {"ban": 4, "fly": 3, "buffer": 1, "cont": 2}
    assert zm.layer is not None
    assert QgsProject.instance().mapLayer(zm.layer_id) is not None


def test_champs_de_la_couche(zm):
    noms = {champ.name() for champ in zm.layer.fields()}
    assert {"id", "type", "priority"} <= noms


def test_style_categorise_par_type(zm):
    rendu = zm.layer.renderer()
    assert isinstance(rendu, QgsCategorizedSymbolRenderer)
    assert rendu.classAttribute() == "type"
    assert {c.value() for c in rendu.categories()} == {"ban", "fly", "buffer", "cont"}


def test_creer_couche_remplace_l_ancienne(zm):
    ancien_id = zm.layer_id

    zm.creer_couche()

    assert zm.layer_id != ancien_id
    assert QgsProject.instance().mapLayer(ancien_id) is None
    assert len(QgsProject.instance().mapLayersByName(COUCHE_NOM)) == 1


def test_supprimer_couche(zm):
    zm.supprimer_couche()

    assert zm.layer is None
    assert zm.layer_id is None
    assert QgsProject.instance().mapLayersByName(COUCHE_NOM) == []


def test_supprimer_couche_deux_fois(zm):
    zm.supprimer_couche()
    zm.supprimer_couche()  # ne doit pas lever d'exception


def test_couche_presente(zm):
    assert zm._couche_presente()

    QgsProject.instance().removeMapLayer(zm.layer_id)

    assert not zm._couche_presente()


def test_appliquer_style_peut_etre_rappele(zm):
    zm.appliquer_style()
    assert len(zm.layer.renderer().categories()) == 4


# --- ajouter_zone : cas simples ---

@pytest.mark.parametrize("type_zone, priorite", [
    ("ban", 4), ("fly", 3), ("cont", 2), ("buffer", 1),
])
def test_ajouter_zone_applique_la_priorite(zm, type_zone, priorite):
    zm.ajouter_zone(Zone(carre(10), type=type_zone))

    feats = list(zm.layer.getFeatures())
    assert len(feats) == 1
    assert feats[0]["type"] == type_zone
    assert feats[0]["priority"] == priorite


def test_ajouter_zone_type_invalide(zm, capsys):
    zm.ajouter_zone(Zone(carre(10), type="inconnu"))

    assert zm.layer.featureCount() == 0
    assert "invalide" in capsys.readouterr().out


def test_ajouter_zone_geometrie_invalide(zm, capsys):
    zm.ajouter_zone(Zone(carre(10)[:2], type="fly"))

    assert zm.layer.featureCount() == 0
    assert "géométrie invalide" in capsys.readouterr().out


def test_ajouter_zone_recree_la_couche_si_absente(zm):
    QgsProject.instance().removeMapLayer(zm.layer_id)

    zm.ajouter_zone(Zone(carre(10), type="fly"))

    assert zm._couche_presente()
    assert zm.layer.featureCount() == 1


def test_ajouter_zones_adjacentes_sans_chevauchement(zm):
    zm.ajouter_zone(Zone(carre(10, 5, 5), type="fly"))
    zm.ajouter_zone(Zone(carre(10, 25, 5), type="buffer"))

    aires = aires_par_type(zm.layer)
    assert aires["fly"] == pytest.approx(100)
    assert aires["buffer"] == pytest.approx(100)


# --- ajouter_zone : priorités et découpes ---

def test_zone_basse_priorite_decoupee_par_zone_haute(zm):
    zm.ajouter_zone(Zone(carre(10, 5, 5), type="fly"))
    zm.ajouter_zone(Zone(carre(10, 10, 10), type="buffer"))

    aires = aires_par_type(zm.layer)
    assert aires["fly"] == pytest.approx(100)
    assert aires["buffer"] == pytest.approx(75)  # 100 moins le recouvrement de 25


def test_zone_haute_priorite_decoupe_zone_existante(zm):
    zm.ajouter_zone(Zone(carre(10, 10, 10), type="buffer"))
    zm.ajouter_zone(Zone(carre(10, 5, 5), type="fly"))

    aires = aires_par_type(zm.layer)
    assert aires["fly"] == pytest.approx(100)
    assert aires["buffer"] == pytest.approx(75)


def test_zone_basse_priorite_entierement_recouverte_est_ignoree(zm):
    zm.ajouter_zone(Zone(carre(10, 5, 5), type="fly"))
    zm.ajouter_zone(Zone(carre(4, 5, 5), type="buffer"))

    assert zm.layer.featureCount() == 1
    assert aires_par_type(zm.layer).keys() == {"fly"}


def test_meme_priorite_remplace_la_zone_existante(zm):
    zm.ajouter_zone(Zone(carre(10), type="fly"))
    zm.ajouter_zone(Zone(carre(10), type="fly"))

    assert zm.layer.featureCount() == 1
    assert aires_par_type(zm.layer)["fly"] == pytest.approx(100)
