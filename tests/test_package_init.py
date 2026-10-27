import importlib
from unittest.mock import MagicMock

from .helpers import PKG


def test_class_factory_renvoie_le_plugin(qgs):
    pkg = importlib.import_module(PKG)
    FlyingAreas = importlib.import_module(f"{PKG}.flying_areas").FlyingAreas

    plugin = pkg.classFactory(MagicMock())

    assert isinstance(plugin, FlyingAreas)
