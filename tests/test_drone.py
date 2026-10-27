import pytest

from .helpers import module

Drone = module("source.drone").Drone
File_managing = module("source.file_managing").File_managing


def test_init_et_getters():
    d = Drone("UX", 25000.0, 15.0, "fixed_wing", 20.0)

    assert d.get_name() == "UX"
    assert d.get_radio_dist() == 25000.0
    assert d.get_air_speed() == 15.0
    assert d.get_drone_type() == "fixed_wing"
    assert d.get_buffer_dist() == 20.0


def test_init_accepte_none():
    d = Drone("UX", None, None, "fixed_wing", None)
    assert d.get_radio_dist() is None
    assert d.get_buffer_dist() is None


def test_modify_drone():
    d = Drone("A", 1.0, 2.0, "x", 3.0)

    d.modify_drone("B", 4.0, 5.0, "y", 6.0)

    assert (d.get_name(), d.get_radio_dist(), d.get_air_speed(),
            d.get_drone_type(), d.get_buffer_dist()) == ("B", 4.0, 5.0, "y", 6.0)


def test_nouveau_drone_ecrit_le_fichier(tmp_path):
    chemin = tmp_path / "UX.txt"

    d = Drone.nouveau_drone(str(chemin), "UX", 25000.0, None, "fixed_wing", 20.0)

    assert isinstance(d, Drone)
    assert chemin.exists()
    relu = File_managing.read(str(chemin))
    assert relu.get_name() == "UX"
    assert relu.get_radio_dist() == 25000.0
    assert relu.get_air_speed() is None


def test_nouveau_drone_refuse_un_fichier_existant(tmp_path):
    chemin = tmp_path / "UX.txt"
    chemin.write_text("contenu", encoding="utf-8")

    with pytest.raises(FileExistsError):
        Drone.nouveau_drone(str(chemin), "UX", 1.0, 1.0, "x", 1.0)

    assert chemin.read_text(encoding="utf-8") == "contenu"


def test_nouveau_drone_respecte_la_sous_classe(tmp_path):
    class DroneSpecial(Drone):
        pass

    d = DroneSpecial.nouveau_drone(str(tmp_path / "s.txt"), "S", 1.0, 1.0, "x", 1.0)

    assert isinstance(d, DroneSpecial)


def test_repr():
    texte = repr(Drone("UX", 1.0, None, "fixed_wing", 2.0))

    assert "UX" in texte
    assert "fixed_wing" in texte
    assert "None" in texte
