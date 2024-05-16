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
    @pytest.mark.parametrize(
        "utility_route_sketch",
        [
            [(174753.97, 451038.03), (175775.00, 450411.52)],
            [(174998.02, 451155.50), (174815.78, 450568.64), (175775.00, 450411.52)],
        ],
    )
    def test_get_utility_routes(self, utility_route_sketch):
        lcpa_engine = get_lcpa_utility_route(
            path_raster=Config.PATH_EXAMPLE_RASTER_EDE,
            utility_route_sketch=shapely.LineString(utility_route_sketch),
        )

        # Check that the input points are present in the result.
        for route_point in lcpa_engine.route_model.route_points.geometry.tolist():
            assert lcpa_engine.lcpa_result.dwithin(route_point, Config.RASTER_CELL_SIZE)

    @pytest.mark.parametrize(
        "utility_route_sketch",
        [
            [(174972.16, 450998.87), (175089.39, 450889.53)],
            [(174966.75, 450896.42), (174968.96, 450846.43), (174912.32, 450837.07)],
        ],
    )
    def test_get_utility_route_with_smaller_project_area(self, utility_route_sketch):
        project_area = gpd.read_file(Config.PATH_PROJECT_AREA_EDE_COMPONISTENBUURT).iloc[0].geometry.buffer(-200)
        lcpa_engine = get_lcpa_utility_route(
            path_raster=Config.PATH_EXAMPLE_RASTER_EDE,
            utility_route_sketch=shapely.LineString(utility_route_sketch),
            project_area=project_area,
        )

        for route_point in lcpa_engine.route_model.route_points.geometry.tolist():
            assert lcpa_engine.lcpa_result.dwithin(route_point, Config.RASTER_CELL_SIZE)

    @pytest.mark.parametrize(
        "utility_route_sketch",
        [
            [(174922.17, 450595.98), (175106.38, 450753.59)],  # start in no data, end valid
            [(174770.47, 450766.39), (174933.99, 450615.68)],  # start in valid, end in no data
            [(174841.39, 450793.98), (174941.87, 450635.38), (175199.96, 450783.14)],  # start valid, invalid, end valid
        ],
    )
    def test_invalid_utility_route_outside_raster(self, utility_route_sketch):
        with pytest.raises(ValueError):
            get_lcpa_utility_route(
                path_raster=Config.PATH_EXAMPLE_RASTER_EDE,
                utility_route_sketch=shapely.LineString(utility_route_sketch),
            )


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
            # Diagonals need to be at least 2 wide to block a path.
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
