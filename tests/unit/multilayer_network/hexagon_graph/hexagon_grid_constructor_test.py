# SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#
# SPDX-License-Identifier: Apache-2.0

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
        hexagon_width, hexagon_height = 0.75, 0.866

        # Test number of points (based on size of project area)

        # Test spacing between points (based on equation?)
        coordinates = result.geometry.get_coordinates()
        x_coordinates = coordinates["x"].values.reshape(6, 7)
        y_coordinates = coordinates["y"].values.reshape(6, 7)

        x_spacing = np.diff(x_coordinates, axis=1)
        assert all(x_space == pytest.approx(hexagon_width, abs=1e-4) for x_space in x_spacing)

        y_spacing = np.diff(y_coordinates, axis=0)
        assert all(y_space == pytest.approx(hexagon_height, abs=1e-4) for y_space in y_spacing)
