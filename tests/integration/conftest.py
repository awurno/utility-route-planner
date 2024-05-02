import pytest

from settings import Config


@pytest.fixture(autouse=True)
def patch_input_geopackage_for_tests(monkeypatch):
    # Always use this geopackage for the tests unless specified differently.
    monkeypatch.setattr(Config, "PATH_INPUT_MCDA_GEOPACKAGE", Config.BASEDIR / "data/examples/ede.gpkg")
