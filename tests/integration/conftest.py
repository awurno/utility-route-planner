import pytest

from settings import Config


@pytest.fixture(autouse=True)
def patch_input_geopackage_for_tests(monkeypatch):
    # Always use this geopackage for the tests unless specified differently.
    monkeypatch.setattr(Config, "PATH_GEOPACKAGE_MCDA_PYTEST_EDE", Config.BASEDIR / "data/examples/ede.gpkg")
    # TODO do we still need this now that we just give it as an argument?
