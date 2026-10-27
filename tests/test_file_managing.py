import os

import pytest

from .helpers import module

File_managing = module("source.file_managing").File_managing
Drone = module("source.drone").Drone

CONTENU_VALIDE = "Delair UX11\n25000\nnull\nfixed_wing\nnull"


def ecrire(tmp_path, contenu, nom="d.txt"):
    chemin = tmp_path / nom
    chemin.write_text(contenu, encoding="utf-8")
    return str(chemin)


# --- read ---

def test_read_lit_les_5_lignes(tmp_path):
    drone = File_managing.read(ecrire(tmp_path, CONTENU_VALIDE))

    assert drone.get_name() == "Delair UX11"
    assert drone.get_radio_dist() == 25000.0
    assert drone.get_air_speed() is None
    assert drone.get_drone_type() == "fixed_wing"
    assert drone.get_buffer_dist() is None


def test_read_accepte_un_saut_de_ligne_final(tmp_path):
    drone = File_managing.read(ecrire(tmp_path, CONTENU_VALIDE + "\n"))
    assert drone.get_drone_type() == "fixed_wing"


def test_read_lignes_insuffisantes(tmp_path):
    with pytest.raises(ValueError, match="5 lignes attendues"):
        File_managing.read(ecrire(tmp_path, "a\nb\nc"))


def test_read_valeur_numerique_invalide(tmp_path):
    with pytest.raises(ValueError):
        File_managing.read(ecrire(tmp_path, "a\nabc\nnull\nx\nnull"))


def test_read_fichier_absent(tmp_path):
    with pytest.raises(OSError):
        File_managing.read(str(tmp_path / "absent.txt"))


# --- write ---

def test_write_format_exact(tmp_path):
    chemin = tmp_path / "w.txt"

    File_managing.write(Drone("UX", 25000.0, None, "fixed_wing", 20.0), str(chemin))

    assert chemin.read_text(encoding="utf-8").splitlines() == [
        "UX", "25000.0", "null", "fixed_wing", "20.0",
    ]


def test_write_puis_read_aller_retour(tmp_path):
    chemin = str(tmp_path / "rt.txt")
    original = Drone("UX", 25000.0, 15.0, "fixed_wing", None)

    File_managing.write(original, chemin)
    relu = File_managing.read(chemin)

    assert (relu.get_name(), relu.get_radio_dist(), relu.get_air_speed(),
            relu.get_drone_type(), relu.get_buffer_dist()) == \
           ("UX", 25000.0, 15.0, "fixed_wing", None)


# --- delete ---

def test_delete_supprime_le_fichier(tmp_path):
    chemin = ecrire(tmp_path, CONTENU_VALIDE)

    File_managing.delete(chemin)

    assert not os.path.exists(chemin)


def test_delete_fichier_absent(tmp_path):
    with pytest.raises(FileNotFoundError):
        File_managing.delete(str(tmp_path / "absent.txt"))


# --- modify_* ---

@pytest.mark.parametrize("methode, attribut, valeur", [
    ("modify_air_speed", "air_speed", 12.5),
    ("modify_radio_dist", "radio_dist", 3000.0),
    ("modify_drone_type", "drone_type", "multirotor"),
    ("modify_buffer_dist", "buffer_dist", 50.0),
])
def test_modify_met_a_jour_l_objet_et_le_fichier(tmp_path, methode, attribut, valeur):
    chemin = str(tmp_path / "m.txt")
    drone = Drone("UX", 1.0, 2.0, "fixed_wing", 3.0)
    File_managing.write(drone, chemin)

    getattr(File_managing, methode)(drone, valeur, chemin)

    assert getattr(drone, attribut) == valeur
    assert getattr(File_managing.read(chemin), attribut) == valeur
