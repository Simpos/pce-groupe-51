import math

import pytest
from qgis.core import QgsGeometry, QgsPointXY
from qgis.PyQt.QtGui import QColor

from .helpers import carre, distances_au_centre, module

Zone = module("source.zone").Zone


# --- Construction ---

def test_valeurs_par_defaut():
    zone = Zone()
    assert zone.points == []
    assert zone.color == QColor("red")
    assert zone.priority == -1
    assert zone.type == "default_type"


def test_listes_par_defaut_non_partagees():
    a, b = Zone(), Zone()
    a.add_point(QgsPointXY(0, 0))
    assert b.points == []


def test_add_point():
    zone = Zone()
    zone.add_point(QgsPointXY(1, 2))
    assert len(zone.points) == 1
    assert zone.points[0].x() == 1


# --- geometrie / is_valid / intersect ---

def test_geometrie_none_si_moins_de_3_sommets():
    assert Zone([QgsPointXY(0, 0), QgsPointXY(1, 1)]).geometrie() is None


def test_geometrie_ferme_l_anneau():
    geom = Zone(carre()).geometrie()
    assert isinstance(geom, QgsGeometry)
    anneau = geom.asPolygon()[0]
    assert len(anneau) == 5
    assert anneau[0] == anneau[-1]


def test_geometrie_ne_double_pas_un_anneau_deja_ferme():
    anneau = Zone(carre() + [carre()[0]]).geometrie().asPolygon()[0]
    assert len(anneau) == 5


def test_geometrie_ne_modifie_pas_les_sommets():
    zone = Zone(carre())
    zone.geometrie()
    assert len(zone.points) == 4


def test_is_valid_carre():
    assert Zone(carre()).is_valid()


def test_is_valid_polygone_croise():
    noeud = [QgsPointXY(0, 0), QgsPointXY(2, 2), QgsPointXY(2, 0), QgsPointXY(0, 2)]
    assert not Zone(noeud).is_valid()


def test_is_valid_sans_geometrie():
    assert not Zone([QgsPointXY(0, 0)]).is_valid()


def test_intersect_zones_qui_se_chevauchent():
    assert Zone(carre(2)).intersect(Zone(carre(2, cx=1, cy=0)))


def test_intersect_zones_disjointes():
    assert not Zone(carre(2)).intersect(Zone(carre(2, cx=10, cy=0)))


def test_intersect_avec_zone_sans_geometrie():
    assert not Zone(carre(2)).intersect(Zone([]))


def test_repr():
    assert repr(Zone([QgsPointXY(1, 2)])) == "Zone([(1.00, 2.00)])"


# --- barycentre / normalize ---

def test_barycentre_zone_vide():
    p = Zone().barycenter()
    assert (p.x(), p.y()) == (0, 0)


def test_barycentre_carre_decentre():
    p = Zone(carre(2, cx=5, cy=-3)).barycenter()
    assert p.x() == pytest.approx(5)
    assert p.y() == pytest.approx(-3)


def test_normalize_ramene_a_longueur_1():
    p = QgsPointXY(3, 4)
    Zone().normalize(p)
    assert p.x() == pytest.approx(0.6)
    assert p.y() == pytest.approx(0.8)


# --- expand_zone / expand_self ---

def test_expand_zone_repousse_les_sommets():
    agrandie = Zone(carre(2)).expand_zone(1.0)
    assert isinstance(agrandie, Zone)
    for d in distances_au_centre(agrandie):
        assert d == pytest.approx(math.sqrt(2) + 1)


def test_expand_zone_ne_modifie_pas_l_original():
    zone = Zone(carre(2))
    avant = [(p.x(), p.y()) for p in zone.points]
    zone.expand_zone(5.0)
    assert [(p.x(), p.y()) for p in zone.points] == avant


def test_expand_zone_expansion_nulle():
    zone = Zone(carre(2))
    agrandie = zone.expand_zone(0.0)
    for p, q in zip(zone.points, agrandie.points):
        assert (q.x(), q.y()) == pytest.approx((p.x(), p.y()))


def test_expand_zone_sommets_confondus_avec_le_barycentre():
    zone = Zone([QgsPointXY(1, 1)] * 3)
    agrandie = zone.expand_zone(5.0)
    assert all((p.x(), p.y()) == (1, 1) for p in agrandie.points)


def test_expand_self_modifie_la_zone_courante():
    zone = Zone()
    base = Zone(carre(2))

    zone.expand_self(base, 1.0)

    for d in distances_au_centre(zone):
        assert d == pytest.approx(math.sqrt(2) + 1)
    assert len(base.points) == 4


# --- create_zone_from_point ---

def test_create_zone_from_point_carre():
    zone = Zone()
    zone.create_zone_from_point(QgsPointXY(0, 0), 1.0, 4)

    attendu = [(-1, 1), (-1, -1), (1, -1), (1, 1)]
    assert len(zone.points) == 4
    for p, (ex, ey) in zip(zone.points, attendu):
        assert p.x() == pytest.approx(ex)
        assert p.y() == pytest.approx(ey)


def test_create_zone_from_point_nombre_de_sommets_et_rayon():
    zone = Zone()
    zone.create_zone_from_point(QgsPointXY(0, 0), 1.0, 30)

    assert len(zone.points) == 30
    for d in distances_au_centre(zone):
        assert d == pytest.approx(math.sqrt(2), abs=1e-3)


def test_create_zone_from_point_decale_le_centre():
    zone = Zone()
    zone.create_zone_from_point(QgsPointXY(100, 200), 1.0, 4)
    assert zone.barycenter().x() == pytest.approx(100)
    assert zone.barycenter().y() == pytest.approx(200)


def test_create_zone_from_point_remplace_les_sommets():
    zone = Zone(carre(10))
    zone.create_zone_from_point(QgsPointXY(0, 0), 1.0, 4)
    assert len(zone.points) == 4


# --- copy ---

def test_copy_copie_les_attributs():
    original = Zone(carre(), QColor("blue"), 2, "cont")
    copie = original.copy()

    assert copie.color == QColor("blue")
    assert copie.priority == 2
    assert copie.type == "cont"
    assert len(copie.points) == 4


def test_copy_n_est_pas_lie_a_l_original():
    original = Zone(carre())
    copie = original.copy()

    copie.add_point(QgsPointXY(9, 9))

    assert copie.points is not original.points
    assert len(original.points) == 4
