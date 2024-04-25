# TODO tests for running MCDA + LCPA
import pytest
import shapely

from settings import Config
from src.models.lcpa.lcpa_engine import LcpaUtilityRouteEngine
from src.models.mcda.mcda_engine import McdaCostSurfaceEngine
from src.util.write import reset_geopackage, write_results_to_geopackage


@pytest.fixture
def setup_mcda_lcpa_testing():
    reset_geopackage(Config.PATH_LCPA_GEOPACKAGE)
    reset_geopackage(Config.PATH_OUTPUT_MCDA_GEOPACKAGE)


def test_mcda_lcpa_chain(monkeypatch, setup_mcda_lcpa_testing):
    monkeypatch.setattr(Config, "DEBUG", True)
    # preset = load_preset("preset_benchmark_raw")
    mcda_engine = McdaCostSurfaceEngine("preset_benchmark_raw")
    mcda_engine.preprocess_vectors()
    path_suitability_raster = mcda_engine.preprocess_rasters(mcda_engine.processed_vectors)

    lcpa_engine = LcpaUtilityRouteEngine()
    lcpa_engine.get_lcpa_route(
        path_suitability_raster,
        mcda_engine.raster_preset.general.project_area_geometry,
        shapely.LineString([(174896.9, 451130.5), (175279.79, 450519.61)]),
    )
    write_results_to_geopackage(Config.PATH_LCPA_GEOPACKAGE, lcpa_engine.lcpa_result, "utility_route_result")


def test_mcda_lcpa_chain_with_(monkeypatch, setup_mcda_lcpa_testing):
    pass
