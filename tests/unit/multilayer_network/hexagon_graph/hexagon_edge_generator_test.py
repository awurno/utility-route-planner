#  SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#  #
#  SPDX-License-Identifier: Apache-2.0
import geopandas as gpd
import geopandas.testing
import pytest
import shapely

from settings import Config
from utility_route_planner.models.multilayer_network.hexagon_graph.hexagon_edge_generator import HexagonEdgeGenerator


class TestHexagonEdgeGenerator:
    @pytest.fixture()
    def hexagonal_grid(self) -> gpd.GeoDataFrame:
        return gpd.GeoDataFrame(
            data=[
                [0, 2, 10.0, 0, 4],
                [-1, 1, 8.0, -1, 3],
                [1, 2, 8.0, 1, 3],
                [0, 1, 10.0, 0, 2],
                [-1, 0, 8.0, -1, 1],
                [1, 1, 8.0, 1, 1],
                [0, 0, 10.0, 0, 0],
                [-1, -1, 8.0, -1, -1],
                [1, 0, 8.0, 1, -1],
                [0, -1, 10.0, 0, -2],
                [-1, -2, 8.0, -1, -3],
                [1, -1, 8.0, 1, -3],
                [0, -2, 10.0, 0, -4],
                [-2, -1, 20.0, -2, 0],
                [2, 1, 20.0, 2, 0],
                [-2, -2, 20.0, -2, -2],
                [2, 0, 20.0, 2, -2],
            ],
            columns=["axial_q", "axial_r", "suitability_value", "x", "y"],
        )

    def test_get_vertical_edges(self, hexagonal_grid: gpd.GeoDataFrame):
        generator = HexagonEdgeGenerator(hexagonal_grid)

        vertical_edges, left_edges, right_edges = [*generator.generate()]

        self.verify_vertical_edges(vertical_edges)
        self.verify_left_edges(left_edges)
        self.verify_right_edges(right_edges)

    def verify_vertical_edges(self, vertical_edges_result: gpd.GeoDataFrame):
        expected_edges = gpd.GeoDataFrame(
            data=[
                [3, 0, 2.0, 10.0],
                [4, 1, 2.0, 8.0],
                [5, 2, 2.0, 8.0],
                [6, 3, 2.0, 10.0],
                [7, 4, 2.0, 8.0],
                [8, 5, 2.0, 8.0],
                [9, 6, 2.0, 10.0],
                [10, 7, 2.0, 8.0],
                [11, 8, 2.0, 8.0],
                [12, 9, 2.0, 10.0],
                [15, 13, 2.0, 20.0],
                [16, 14, 2.0, 20.0],
            ],
            geometry=[
                shapely.LineString([shapely.Point(0, 2), shapely.Point(0, 4)]),
                shapely.LineString([shapely.Point(-1, 1), shapely.Point(-1, 3)]),
                shapely.LineString([shapely.Point(1, 1), shapely.Point(1, 3)]),
                shapely.LineString([shapely.Point(0, 0), shapely.Point(0, 2)]),
                shapely.LineString([shapely.Point(-1, -1), shapely.Point(-1, 1)]),
                shapely.LineString([shapely.Point(1, -1), shapely.Point(1, 1)]),
                shapely.LineString([shapely.Point(0, -2), shapely.Point(0, 0)]),
                shapely.LineString([shapely.Point(-1, -3), shapely.Point(-1, -1)]),
                shapely.LineString([shapely.Point(1, -3), shapely.Point(1, -1)]),
                shapely.LineString([shapely.Point(0, -4), shapely.Point(0, -2)]),
                shapely.LineString([shapely.Point(-2, -2), shapely.Point(-2, 0)]),
                shapely.LineString([shapely.Point(2, -2), shapely.Point(2, 0)]),
            ],
            columns=["node_id_source", "node_id_target", "length", "weight"],
            crs=Config.CRS,
        )
        gpd.testing.assert_geodataframe_equal(expected_edges, vertical_edges_result)

    def verify_left_edges(self, left_edges_result: gpd.GeoDataFrame):
        pass

    def verify_right_edges(self, right_edges_result: gpd.GeoDataFrame):
        pass
