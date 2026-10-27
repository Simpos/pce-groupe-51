import os
from unittest.mock import MagicMock

import pytest
from qgis.PyQt.QtCore import Qt

from .helpers import module

fa_mod = module("flying_areas")
FlyingAreas = fa_mod.FlyingAreas


@pytest.fixture
def iface():
    mock = MagicMock()
    mock.mainWindow.return_value = None  # évite un parent MagicMock pour QAction
    return mock


@pytest.fixture
def plugin(qgs, iface):
    return FlyingAreas(iface)


# --- __init__ et tr ---

def test_init(plugin, iface):
    assert plugin.iface is iface
    assert plugin.actions == []
    assert plugin.menu == "&Zones de vol"
    assert plugin.first_start is None
    assert os.path.isdir(plugin.plugin_dir)


def test_tr_renvoie_le_message(plugin):
    assert plugin.tr("abc") == "abc"


# --- add_action ---

def test_add_action_ajoute_menu_et_barre_d_outils(plugin, iface):
    callback = MagicMock()

    action = plugin.add_action(
        "", "Texte", callback, status_tip="aide", whats_this="quoi", parent=None
    )

    iface.addToolBarIcon.assert_called_once_with(action)
    iface.addPluginToMenu.assert_called_once_with(plugin.menu, action)
    assert action in plugin.actions
    assert action.statusTip() == "aide"
    assert action.whatsThis() == "quoi"

    action.trigger()
    callback.assert_called_once()


def test_add_action_sans_menu_ni_barre(plugin, iface):
    action = plugin.add_action(
        "", "Texte", MagicMock(), enabled_flag=False,
        add_to_menu=False, add_to_toolbar=False, parent=None,
    )

    iface.addToolBarIcon.assert_not_called()
    iface.addPluginToMenu.assert_not_called()
    assert not action.isEnabled()
    assert action in plugin.actions


# --- initGui ---

def test_init_gui_cree_une_action(plugin, iface):
    plugin.initGui()

    assert len(plugin.actions) == 1
    iface.addPluginToMenu.assert_called_once()
    assert plugin.first_start is True


# --- run ---

def test_run_cree_le_dialogue_une_seule_fois(plugin, iface, monkeypatch):
    dialogue = MagicMock()
    classe = MagicMock(return_value=dialogue)
    monkeypatch.setattr(fa_mod, "FlyingAreasDialog", classe)

    plugin.run()
    plugin.run()

    assert classe.call_count == 1
    iface.addDockWidget.assert_called_once_with(Qt.RightDockWidgetArea, dialogue)
    assert dialogue.show.call_count == 2
    assert dialogue.raise_.call_count == 2


def test_run_recree_le_dialogue_si_supprime(plugin, monkeypatch):
    classe = MagicMock(return_value=MagicMock())
    monkeypatch.setattr(fa_mod, "FlyingAreasDialog", classe)

    plugin.dlg = None
    plugin.run()

    assert classe.call_count == 1


# --- unload ---

def test_unload_retire_menu_et_icones(plugin, iface):
    plugin.initGui()
    plugin.unload()

    iface.removePluginMenu.assert_called_once()
    iface.removeToolBarIcon.assert_called_once()


def test_unload_ferme_le_dialogue(plugin, iface):
    dialogue = MagicMock()
    plugin.dlg = dialogue

    plugin.unload()

    dialogue.close.assert_called_once()
    iface.removeDockWidget.assert_called_once_with(dialogue)
    dialogue.deleteLater.assert_called_once()
    assert plugin.dlg is None


def test_unload_sans_dialogue(plugin):
    plugin.unload()  # ne doit pas lever d'exception
