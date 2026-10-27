import math

import pytest
from qgis.core import QgsPointXY
from qgis.PyQt.QtGui import QColor

from .helpers import carre, distances_au_centre, module

ZoneCalculateur = module("source.calculZone").ZoneCalculateur
Zone = module("source.zone").Zone
Drone = module("source.drone").Drone

RACINE2 = math.sqrt(2)  # distance d'un sommet d'un carré de côté 2 au centre


def calculateur_avec_vol(cote: float = 2.0) -> ZoneCalculateur:
    return ZoneCalculateur(flying_area=Zone(carre(cote), QColor("green"), 3, "fly"))


# --- Valeurs par défaut ---

def test_valeurs_par_defaut():
    calc = ZoneCalculateur()
    assert calc.flying_area.type == "fly" and calc.flying_area.priority == 3
    assert calc.buffering_area.type == "buffer" and calc.buffering_area.priority == 1
    assert calc.contingency_area.type == "cont" and calc.contingency_area.priority == 2
    assert len(calc.restricted_area) == 1
    assert calc.restricted_area[0].type == "ban"
    assert calc.param == 0.0
    assert calc.ITER_LIMIT == 10


def test_instances_independantes():
    a, b = ZoneCalculateur(), ZoneCalculateur()
    a.flying_area.add_point(carre(1)[0])

    assert b.flying_area.points == []
    assert a.restricted_area is not b.restricted_area


# --- calculate_areas ---

def test_calculate_areas_contingence_et_buffer():
    calc = calculateur_avec_vol(2)

    calc.calculate_areas(Drone("D", 25.0, None, "fixed_wing", 10.0))

    for d in distances_au_centre(calc.contingency_area):
        assert d == pytest.approx(RACINE2 + 25)
    for d in distances_au_centre(calc.buffering_area):
        assert d == pytest.approx(RACINE2 + 35)


def test_calculate_areas_ne_modifie_pas_la_zone_de_vol():
    calc = calculateur_avec_vol(2)
    avant = distances_au_centre(calc.flying_area)

    calc.calculate_areas(Drone("D", 25.0, None, "fixed_wing", 10.0))

    assert distances_au_centre(calc.flying_area) == pytest.approx(avant)


@pytest.mark.parametrize("radio, buffer", [(None, 10.0), (25.0, None), (None, None)])
def test_calculate_areas_donnees_manquantes(radio, buffer):
    calc = calculateur_avec_vol(2)

    with pytest.raises(ValueError, match="incomplètes"):
        calc.calculate_areas(Drone("UX", radio, None, "fixed_wing", buffer))

    assert calc.contingency_area.points == []
    assert calc.buffering_area.points == []


# --- expansion_algorithm ---

def test_expansion_algorithm_agrandit_la_zone_de_vol():
    calc = calculateur_avec_vol(2)
    calc.ITER_LIMIT = 3

    calc.expansion_algorithm()

    for d in distances_au_centre(calc.flying_area):
        assert d == pytest.approx(RACINE2 + 30)


def test_expansion_algorithm_met_a_jour_contingence_et_buffer():
    calc = calculateur_avec_vol(2)
    calc.ITER_LIMIT = 2

    calc.expansion_algorithm()

    # zone de vol : +20, contingence : +100 de plus, buffer : +100 de plus
    for d in distances_au_centre(calc.contingency_area):
        assert d == pytest.approx(RACINE2 + 120)
    for d in distances_au_centre(calc.buffering_area):
        assert d == pytest.approx(RACINE2 + 220)


def test_expansion_algorithm_sans_iteration():
    calc = calculateur_avec_vol(2)
    calc.ITER_LIMIT = 0
    avant = distances_au_centre(calc.flying_area)

    calc.expansion_algorithm()

    assert distances_au_centre(calc.flying_area) == pytest.approx(avant)

def test_offset_carre_aire_exacte():
    agrandie = Zone(carre(2)).offset_zone(1.0, segments=64)
    assert agrandie.geometrie().area() == pytest.approx(4 + 8 + math.pi, rel=1e-2)


def test_offset_forme_non_convexe_gere_l_encoche():
    # L : le point (1.5, 1.5) est à 0.5 du bord, donc dans la zone élargie
    # le point (2.5, 2.5) est à plus de 1 du L, donc hors de la zone élargie
    l_shape = Zone([QgsPointXY(0, 0), QgsPointXY(4, 0), QgsPointXY(4, 1),
                    QgsPointXY(1, 1), QgsPointXY(1, 4), QgsPointXY(0, 4)])
    geom = l_shape.offset_zone(1.0).geometrie()
    assert geom.isGeosValid()
    assert geom.contains(QgsGeometry.fromPointXY(QgsPointXY(1.5, 1.5)))
    assert not geom.contains(QgsGeometry.fromPointXY(QgsPointXY(2.5, 2.5)))


def test_calculate_areas_zone_contient_la_precedente():
    calc = calculateur_avec_vol(2)
    calc.calculate_areas(Drone("D", 25.0, None, "fixed_wing", 10.0))
    assert calc.contingency_area.geometrie().contains(calc.flying_area.geometrie())
    assert calc.buffering_area.geometrie().contains(calc.contingency_area.geometrie())
