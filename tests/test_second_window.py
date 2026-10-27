from qgis.PyQt.QtWidgets import QDockWidget

from .helpers import module

SecondWindow = module("second_window").SecondWindow


def test_est_un_dock_widget(qgs):
    assert isinstance(SecondWindow(), QDockWidget)


def test_accept_ferme_la_fenetre(qgs):
    fenetre = SecondWindow()
    fenetre.show()

    fenetre.accept()

    assert not fenetre.isVisible()


def test_reject_ferme_la_fenetre(qgs):
    fenetre = SecondWindow()
    fenetre.show()

    fenetre.reject()

    assert not fenetre.isVisible()
