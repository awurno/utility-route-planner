import pytest
import shapely

from src.models.lcpa.lcpa_datastructures import LcpaInputModel
from src.models.lcpa.lcpa_engine import LcpaUtilityRouteEngine
from src.models.lcpa.lcpa_main import get_lcpa_utility_route
from settings import Config
from src.util.write import reset_geopackage
import geopandas as gpd
import numpy as np


@pytest.fixture
def setup_clean_start(monkeypatch):
    reset_geopackage(Config.PATH_LCPA_GEOPACKAGE)
    monkeypatch.setattr(Config, "DEBUG", True)


@pytest.mark.usefixtures("setup_clean_start")
class TestUtilityRoutes:
    def test_get_utility_route_small_area(self):
        lcpa_engine = get_lcpa_utility_route(
            path_raster=Config.PATH_EXAMPLE_RASTER_APELDOORN,
            utility_route_sketch=shapely.LineString([(193077.740, 466510.697), (193031.551, 466474.721)]),
        )

        # Check that the input points are present in the result.
        for route_point in lcpa_engine.route_model.route_points.geometry.tolist():
            assert lcpa_engine.lcpa_result.dwithin(route_point, Config.RASTER_CELL_SIZE)

    def test_get_utility_route_small_area_with_project_area(self):
        project_area = gpd.read_file(Config.PATH_PROJECT_AREA_APELDOORN_ROAD_CROSSING).iloc[0].geometry
        lcpa_engine = get_lcpa_utility_route(
            path_raster=Config.PATH_EXAMPLE_RASTER_APELDOORN,
            utility_route_sketch=shapely.LineString([(193077.740, 466510.697), (193031.551, 466474.721)]),
            project_area=project_area,
        )

        for route_point in lcpa_engine.route_model.route_points.geometry.tolist():
            assert lcpa_engine.lcpa_result.dwithin(route_point, Config.RASTER_CELL_SIZE)

    def test_get_utility_route_with_intermediate_stops_small_area(self):
        project_area = gpd.read_file(Config.PATH_PROJECT_AREA_APELDOORN_ROAD_CROSSING).iloc[0].geometry
        lcpa_engine = get_lcpa_utility_route(
            path_raster=Config.PATH_EXAMPLE_RASTER_APELDOORN,
            utility_route_sketch=shapely.LineString(
                [(193077.740, 466510.697), (193043.338, 466490.707), (193055.374, 466489.049), (193031.551, 466474.721)]
            ),
            project_area=project_area,
        )

        for route_point in lcpa_engine.route_model.route_points.geometry.tolist():
            assert lcpa_engine.lcpa_result.dwithin(route_point, Config.RASTER_CELL_SIZE)

    def test_get_utility_route_larger_area_with_project_area(self):
        project_area = gpd.read_file(Config.PATH_PROJECT_AREA_APELDOORN_SMALL).iloc[0].geometry
        lcpa_engine = get_lcpa_utility_route(
            path_raster=Config.PATH_EXAMPLE_RASTER_APELDOORN,
            utility_route_sketch=shapely.LineString(
                [(193077.740, 466510.697), (193262.94, 466507.51), (193383.28, 466452.02)]
            ),
            project_area=project_area,
        )

        for route_point in lcpa_engine.route_model.route_points.geometry.tolist():
            assert lcpa_engine.lcpa_result.dwithin(route_point, Config.RASTER_CELL_SIZE)


@pytest.fixture
def setup_lcpa_engine():
    yield LcpaUtilityRouteEngine()


class TestShortestPath:
    @pytest.mark.parametrize(
        "valid_input",
        [
            [
                np.array(
                    [
                        [1, 1, 1, 1, 1],
                        [1, 1, 1, 1, 1],
                        [1, 1, 1, 1, 1],
                        [1, 1, 1, 1, 1],
                        [1, 1, 1, 1, 1],
                    ]
                ),
                [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4)],
            ],
            [
                np.array(
                    [
                        [1, -1, -1, -1, 1],
                        [1, -1, -1, -1, 1],
                        [1, -1, -1, -1, 1],
                        [1, -1, -1, -1, 1],
                        [1, 1, 1, 1, 1],
                    ]
                ),
                [(0, 0), (1, 0), (2, 0), (3, 0), (4, 1), (4, 2), (4, 3), (4, 4)],
            ],
        ],
    )
    def test_get_easy_utility_route(self, setup_lcpa_engine, valid_input):
        lcpa_engine = setup_lcpa_engine
        input_model = LcpaInputModel(
            shapely.LineString([[0, 0], [4, -4]]),  # Note the negative y due to rasters starting from top-left side.
            tuple([0, 1, 0, 0, 0, -1]),
        )
        array, expected_indices = valid_input
        _, indices = lcpa_engine.calculate_least_cost_path(array, input_model)
        assert indices == expected_indices

    # numpy array which is not connected through valid values
    @pytest.mark.parametrize(
        "invalid_input",
        [
            np.array(
                [
                    [1, 1, -1, 1, 1],
                    [1, 1, -1, 1, 1],
                    [1, 1, -1, 1, 1],
                    [1, 1, -1, 1, 1],
                    [1, 1, -1, 1, 1],
                ]
            ),
            # Diagonals need to be at least 2 wide.
            np.array(
                [
                    [1, 1, 1, 1, -1],
                    [1, 1, 1, -1, -1],
                    [1, 1, -1, -1, 1],
                    [1, -1, -1, 1, 1],
                    [-1, -1, 1, 1, 1],
                ]
            ),
        ],
    )
    def test_get_utility_route_which_is_unsolvable_due_to_no_data(self, setup_lcpa_engine, invalid_input):
        lcpa_engine = setup_lcpa_engine

        input_model = LcpaInputModel(
            shapely.LineString([[0, 0], [4, -4]]),  # Note the negative y due to rasters starting from top-left side.
            tuple([0, 1, 0, 0, 0, -1]),
        )
        with pytest.raises(ValueError):
            lcpa_engine.calculate_least_cost_path(invalid_input, input_model)
