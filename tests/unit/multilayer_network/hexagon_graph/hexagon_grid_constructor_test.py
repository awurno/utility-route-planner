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


class TestHexagonalGridConstructor:
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

    def test_construct_hexagonal_grid_for_bounding_box_for_square_project_area(
        self, grid_constructor: HexagonalGridConstructor, square_project_area: shapely.Polygon
    ):
        result = grid_constructor.construct_hexagonal_grid_for_bounding_box(square_project_area)

        coordinates = result.geometry.get_coordinates()
        x_coordinates = coordinates["x"].values.reshape(6, 7)
        y_coordinates = coordinates["y"].values.reshape(6, 7)

        # Set expected spacing between hexagon points based on known equations.
        expected_horizontal_spacing = 3 / 2 * grid_constructor.hexagon_size
        expected_vertical_spacing = math.sqrt(3) * grid_constructor.hexagon_size

        # Verify that spacing between x- and y-coordinates satisfy are equal to hexagon heigth and width
        # and do therefore meet hexagon constaints.

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
