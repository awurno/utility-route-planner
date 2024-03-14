import pytest
import shapely

from src.models.lcpa.lcpa_main import get_lcpa_utility_route
from settings import Config
from src.util.write import reset_geopackage
import geopandas as gpd


@pytest.fixture
def setup_monkeypatch_debug(monkeypatch):
    reset_geopackage(Config.PATH_LCPA_GEOPACKAGE)
    monkeypatch.setattr(Config, "DEBUG", True)


@pytest.mark.usefixtures("setup_monkeypatch_debug")
class TestUtilityRoutes:
    def test_get_utility_route_small_area(self):
        lcpa_engine = get_lcpa_utility_route(
            path_raster=Config.PATH_EXAMPLE_RASTER_1,
            utility_route_sketch=shapely.LineString([(193077.740, 466510.697), (193031.551, 466474.721)]),
        )

        # Check that the input points are present in the result.
        for route_point in lcpa_engine.route_model.route_points.geometry.tolist():
            assert lcpa_engine.lcpa_result.dwithin(route_point, Config.RASTER_CELL_SIZE)

    def test_get_utility_route_small_area_with_project_area(self):
        project_area = gpd.read_file(Config.PATH_PROJECT_AREA_ROAD_CROSSING).iloc[0].geometry
        lcpa_engine = get_lcpa_utility_route(
            path_raster=Config.PATH_EXAMPLE_RASTER_1,
            utility_route_sketch=shapely.LineString([(193077.740, 466510.697), (193031.551, 466474.721)]),
            project_area=project_area,
        )

        for route_point in lcpa_engine.route_model.route_points.geometry.tolist():
            assert lcpa_engine.lcpa_result.dwithin(route_point, Config.RASTER_CELL_SIZE)

    def test_get_utility_route_with_intermediate_stops_small_area(self):
        project_area = gpd.read_file(Config.PATH_PROJECT_AREA_ROAD_CROSSING).iloc[0].geometry
        lcpa_engine = get_lcpa_utility_route(
            path_raster=Config.PATH_EXAMPLE_RASTER_1,
            utility_route_sketch=shapely.LineString(
                [(193077.740, 466510.697), (193043.338, 466490.707), (193055.374, 466489.049), (193031.551, 466474.721)]
            ),
            project_area=project_area,
        )

        for route_point in lcpa_engine.route_model.route_points.geometry.tolist():
            assert lcpa_engine.lcpa_result.dwithin(route_point, Config.RASTER_CELL_SIZE)

    def test_get_utility_route_larger_area_with_project_area(self):
        project_area = gpd.read_file(Config.PATH_PROJECT_AREA).iloc[0].geometry
        lcpa_engine = get_lcpa_utility_route(
            path_raster=Config.PATH_EXAMPLE_RASTER_1,
            utility_route_sketch=shapely.LineString([(193077.740, 466510.697), (193383.28, 466452.02)]),
            project_area=project_area,
        )

        for route_point in lcpa_engine.route_model.route_points.geometry.tolist():
            assert lcpa_engine.lcpa_result.dwithin(route_point, Config.RASTER_CELL_SIZE)
