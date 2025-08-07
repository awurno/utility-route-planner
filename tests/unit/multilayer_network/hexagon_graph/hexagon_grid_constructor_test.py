# SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#
# SPDX-License-Identifier: Apache-2.0

import math
import geopandas as gpd
import numpy as np
import pytest
import shapely

from settings import Config
from utility_route_planner.models.mcda.load_mcda_preset import RasterPreset, load_preset
from utility_route_planner.models.multilayer_network.hexagon_graph.hexagon_grid_constructor import (
    HexagonalGridConstructor,
)


class TestConstructHexagonalGridForBoundingBox:
    @pytest.fixture()
    def square_project_area(self) -> shapely.Polygon:
        return shapely.Polygon(
            [
                shapely.Point(0, 0),
                shapely.Point(5, 0),
                shapely.Point(5, 5),
                shapely.Point(0, 5),
                shapely.Point(0, 0),
            ]
        )

    @pytest.fixture()
    def triangular_project_area(self) -> shapely.Polygon:
        return shapely.Polygon(
            [
                shapely.Point(0, 0),
                shapely.Point(4, 0),
                shapely.Point(2, 4),
                shapely.Point(0, 0),
            ]
        )

    @pytest.fixture()
    def preprocessed_vectors(self) -> dict[str, gpd.GeoDataFrame]:
        return {"test": gpd.GeoDataFrame()}

    @pytest.fixture()
    def raster_preset(self) -> RasterPreset:
        return load_preset(
            Config.RASTER_PRESET_NAME_BENCHMARK,
            Config.PYTEST_PATH_GEOPACKAGE_MCDA,
            gpd.read_file(Config.PYTEST_PATH_GEOPACKAGE_MCDA, layer=Config.PYTEST_LAYER_NAME_PROJECT_AREA)
            .iloc[0]
            .geometry,
        )

    @pytest.fixture()
    def grid_constructor(
        self, raster_preset: RasterPreset, preprocessed_vectors: dict[str, gpd.GeoDataFrame]
    ) -> HexagonalGridConstructor:
        hexagon_size = 0.5
        return HexagonalGridConstructor(raster_preset, preprocessed_vectors, hexagon_size)

    def test_square_project_area(
        self, grid_constructor: HexagonalGridConstructor, square_project_area: shapely.Polygon
    ):
        result = grid_constructor.construct_hexagonal_grid_for_bounding_box(square_project_area)

        coordinates = result.geometry.get_coordinates()
        x_coordinates = coordinates["x"].values.reshape(6, 7)
        y_coordinates = coordinates["y"].values.reshape(6, 7)

        hexagon_size = grid_constructor.hexagon_size
        self.check_grid_bounding_box(hexagon_size, square_project_area, x_coordinates, y_coordinates)
        self.check_grid_spacing(hexagon_size, x_coordinates, y_coordinates)

    def test_triangular_project_area(
        self, grid_constructor: HexagonalGridConstructor, triangular_project_area: shapely.Polygon
    ):
        result = grid_constructor.construct_hexagonal_grid_for_bounding_box(triangular_project_area)
        coordinates = result.geometry.get_coordinates()
        x_coordinates = coordinates["x"].values.reshape(5, 6)
        y_coordinates = coordinates["y"].values.reshape(5, 6)

        self.check_grid_spacing(grid_constructor.hexagon_size, x_coordinates, y_coordinates)

        hexagon_size = grid_constructor.hexagon_size
        self.check_grid_bounding_box(hexagon_size, triangular_project_area, x_coordinates, y_coordinates)
        self.check_grid_spacing(hexagon_size, x_coordinates, y_coordinates)

    @staticmethod
    def check_grid_bounding_box(
        hexagon_size: float, project_area: shapely.Polygon, x_coordinates: np.ndarray, y_coordinates: np.ndarray
    ):
        """
        Verifies that all coordinates are within or on the border of the project area polygon bounding box. At this stage,
        the grid should be equal to the square equal to the bounding box, independent of the shape of the project area polygon.
        """
        exptected_x_min, exptected_y_min, exptected_x_max, exptected_y_max = project_area.bounds

        assert pytest.approx(exptected_x_min) == x_coordinates.min()
        assert exptected_x_max >= x_coordinates.max() >= (exptected_x_max - hexagon_size)
        assert pytest.approx(exptected_y_min) == y_coordinates.min()
        assert exptected_y_max >= y_coordinates.max() >= (exptected_y_max - hexagon_size)

    @staticmethod
    def check_grid_spacing(hexagon_size: float, x_coordinates: np.ndarray, y_coordinates: np.ndarray):
        # Set expected spacing between hexagon points based on known equations.
        expected_horizontal_spacing = 3 / 2 * hexagon_size
        expected_vertical_spacing = math.sqrt(3) * hexagon_size

        # Verify that spacing between x-coordinates of hexagon center points equals the expected horizontal spacing
        x_spacing = np.diff(x_coordinates, axis=1)
        assert all(x_space == pytest.approx(expected_horizontal_spacing, abs=1e-4) for x_space in x_spacing)

        # Verify that spacing between y-coordinates of hexagon center points equals the expected vertical spacing
        y_vertical_spacing = np.diff(y_coordinates, axis=0)
        assert all(y_space == pytest.approx(expected_vertical_spacing, abs=1e-4) for y_space in y_vertical_spacing)

        # Verify that y-coordinates of horizontally neighbouring hexagon center points are 1/2 of the expected vertical spacing
        # separated from each other. This is due to alternating offset of neighbouring hexagon points.
        y_horizontal_spacing = np.diff(y_coordinates, axis=1)
        assert all(
            y_space == pytest.approx(expected_vertical_spacing / 2, abs=1e-4)
            for y_space in np.abs(y_horizontal_spacing)
        )

        # As every even column is offset by 1/2 the hexagon height, the horizontal spacing should always be negative. For
        # all odd columns, the sign should be positive
        signs = np.sign(y_horizontal_spacing)
        assert all(sign == -1 for sign in signs[:, ::2].flatten())
        assert all(sign == 1 for sign in signs[:, 1::2].flatten())
