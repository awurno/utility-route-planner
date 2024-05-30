import pytest
import shapely

from main import run_mcda_lcpa
from settings import Config
from utility_route_planner.models.lcpa.lcpa_engine import LcpaUtilityRouteEngine
from utility_route_planner.models.mcda.mcda_engine import McdaCostSurfaceEngine
from utility_route_planner.util.geo_utilities import get_first_last_point_from_linestring
from utility_route_planner.util.write import reset_geopackage, write_results_to_geopackage
import geopandas as gpd


@pytest.fixture
def setup_mcda_lcpa_testing(monkeypatch):
    reset_geopackage(Config.PATH_GEOPACKAGE_LCPA_OUTPUT)
    reset_geopackage(Config.PATH_GEOPACKAGE_MCDA_OUTPUT, truncate=False)
    monkeypatch.setattr(Config, "DEBUG", True)


@pytest.mark.usefixtures("setup_mcda_lcpa_testing")
class TestMcdaLcpaChain:
    @pytest.mark.parametrize(
        "utility_route_sketch",
        (
            [(174896.9, 451130.5), (175279.7, 450519.6)],
            [(174896.9, 451130.5), (174968.1, 450985.7), (174975.1, 450731.1), (175279.7, 450519.6)],
        ),
    )
    def test_mcda_lcpa_chain_pytest_files(self, utility_route_sketch):
        mcda_engine = McdaCostSurfaceEngine(
            "preset_benchmark_raw",
            Config.PATH_GEOPACKAGE_MCDA_PYTEST_EDE,
            gpd.read_file(Config.PATH_PROJECT_AREA_PYTEST_EDE).iloc[0].geometry,
        )
        mcda_engine.preprocess_vectors()
        path_suitability_raster = mcda_engine.preprocess_rasters(mcda_engine.processed_vectors)

        lcpa_engine = LcpaUtilityRouteEngine()
        lcpa_engine.get_lcpa_route(
            path_suitability_raster,
            mcda_engine.raster_preset.general.project_area_geometry,
            shapely.LineString(utility_route_sketch),
        )
        write_results_to_geopackage(Config.PATH_GEOPACKAGE_LCPA_OUTPUT, lcpa_engine.lcpa_result, "utility_route_result")


@pytest.mark.parametrize(
    "path_geopackage, layer_name_project_area, layer_name_utility_route_human_designed",
    [
        # (Config.PATH_GEOPACKAGE_CASE_01, Config.LAYER_NAME_PROJECT_AREA_CASE_01, Config.LAYER_NAME_HUMAN_DESIGNED_ROUTE_CASE_01),
        (
            Config.PATH_GEOPACKAGE_CASE_02,
            Config.LAYER_NAME_PROJECT_AREA_CASE_02,
            Config.LAYER_NAME_HUMAN_DESIGNED_ROUTE_CASE_02,
        ),
        (
            Config.PATH_GEOPACKAGE_CASE_03,
            Config.LAYER_NAME_PROJECT_AREA_CASE_03,
            Config.LAYER_NAME_HUMAN_DESIGNED_ROUTE_CASE_03,
        ),
        (
            Config.PATH_GEOPACKAGE_CASE_04,
            Config.LAYER_NAME_PROJECT_AREA_CASE_04,
            Config.LAYER_NAME_HUMAN_DESIGNED_ROUTE_CASE_04,
        ),
        (
            Config.PATH_GEOPACKAGE_CASE_05,
            Config.LAYER_NAME_PROJECT_AREA_CASE_05,
            Config.LAYER_NAME_HUMAN_DESIGNED_ROUTE_CASE_05,
        ),
    ],
)
def test_mcda_lcpa_chain_case_01(path_geopackage, layer_name_project_area, layer_name_utility_route_human_designed):
    run_mcda_lcpa(
        Config.RASTER_PRESET_NAME_BENCHMARK,
        path_geopackage,
        gpd.read_file(path_geopackage, layer=layer_name_project_area).geometry.iloc[0],
        get_first_last_point_from_linestring(
            gpd.read_file(path_geopackage, layer=layer_name_utility_route_human_designed).geometry.iloc[0]
        ),
    )
