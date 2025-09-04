#  SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#  #
#  SPDX-License-Identifier: Apache-2.0
import geopandas as gpd
import geopandas.testing
import pandas as pd
import pytest
import shapely

from settings import Config
from utility_route_planner.models.multilayer_network.hexagon_graph.hexagon_edge_generator import HexagonEdgeGenerator
from utility_route_planner.util.write import write_results_to_geopackage


class TestHexagonEdgeGenerator:
    @pytest.fixture()
    def hexagonal_grid(self) -> gpd.GeoDataFrame:
        return gpd.GeoDataFrame(
            data=[
                [-233233, 637464, 10, 174924.804, 451067.279],
                [-233233, 637465, 10, 174924.804, 451068.145],
                [-233236, 637465, 10, 174927.054, 451066.846],
                [-233234, 637464, 10, 174925.554, 451066.846],
                [-233237, 637466, 20, 174927.804, 451067.279],
                [-233235, 637465, 20, 174926.304, 451067.279],
                [-233234, 637465, 20, 174925.554, 451067.712],
                [-233236, 637466, 20, 174927.054, 451067.712],
                [-233237, 637467, 30, 174927.804, 451068.145],
                [-233235, 637466, 30, 174926.304, 451068.145],
                [-233234, 637466, 30, 174925.554, 451068.578],
                [-233236, 637467, 30, 174927.054, 451068.578],
            ],
            columns=["axial_q", "axial_r", "suitability_value", "x", "y"],
        )

    def test_generate_edges(self, hexagonal_grid: gpd.GeoDataFrame, debug: bool = False):
        """
        This test can be understood most easily by setting debug=True and inspecting the results in QGis.
        """
        generator = HexagonEdgeGenerator(hexagonal_grid)
        vertical_edges, left_edges, right_edges = [*generator.generate()]

        self.verify_vertical_edges(vertical_edges)
        self.verify_left_edges(left_edges)
        self.verify_right_edges(right_edges)

        if debug:
            hexagon_points = gpd.GeoDataFrame(
                geometry=gpd.points_from_xy(hexagonal_grid["x"], hexagonal_grid["y"]), crs=Config.CRS
            )
            write_results_to_geopackage(
                Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, hexagon_points, "graph_test_nodes", overwrite=True
            )
            write_results_to_geopackage(
                Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, vertical_edges, "graph_test_vertical_edges", overwrite=True
            )
            write_results_to_geopackage(
                Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, left_edges, "graph_test_left_edges", overwrite=True
            )
            write_results_to_geopackage(
                Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, right_edges, "graph_test_right_edges", overwrite=True
            )

    def verify_vertical_edges(self, vertical_edges_result: gpd.GeoDataFrame):
        expected_edges = gpd.GeoDataFrame(
            data=[
                [0, 1, 10.0],
                [2, 7, 15.0],
                [3, 6, 15.0],
                [4, 8, 25.0],
                [5, 9, 25.0],
                [6, 10, 25.0],
                [7, 11, 25.0],
            ],
            geometry=[
                shapely.LineString([shapely.Point(174924.804, 451067.279), shapely.Point(174924.804, 451068.145)]),
                shapely.LineString([shapely.Point(174927.054, 451066.846), shapely.Point(174927.054, 451067.712)]),
                shapely.LineString([shapely.Point(174925.554, 451066.846), shapely.Point(174925.554, 451067.712)]),
                shapely.LineString([shapely.Point(174927.804, 451067.279), shapely.Point(174927.804, 451068.145)]),
                shapely.LineString([shapely.Point(174926.304, 451067.279), shapely.Point(174926.304, 451068.145)]),
                shapely.LineString([shapely.Point(174925.554, 451067.712), shapely.Point(174925.554, 451068.578)]),
                shapely.LineString([shapely.Point(174927.054, 451067.712), shapely.Point(174927.054, 451068.578)]),
            ],
            columns=["node_id_source", "node_id_target", "weight"],
            crs=Config.CRS,
        )
        # Edge lengths must be tested separately, as geopandas does not allow float tolerance
        expected_lengths = pd.Series([0.866, 0.866, 0.866, 0.866, 0.866, 0.866, 0.866], name="length")

        gpd.testing.assert_geodataframe_equal(
            expected_edges, vertical_edges_result[["node_id_source", "node_id_target", "weight", "geometry"]]
        )
        pd.testing.assert_series_equal(expected_lengths, vertical_edges_result["length"], atol=0.01)

    def verify_left_edges(self, left_edges_result: gpd.GeoDataFrame):
        expected_edges = gpd.GeoDataFrame(
            data=[
                [0, 3, 10.0],
                [1, 6, 15.0],
                [5, 2, 15.0],
                [6, 5, 20.0],
                [7, 4, 20.0],
                [9, 7, 25.0],
                [10, 9, 30.0],
                [11, 8, 30.0],
            ],
            geometry=[
                shapely.LineString([shapely.Point(174924.804, 451067.279), shapely.Point(174925.554, 451066.846)]),
                shapely.LineString([shapely.Point(174924.804, 451068.145), shapely.Point(174925.554, 451067.712)]),
                shapely.LineString([shapely.Point(174926.304, 451067.279), shapely.Point(174927.054, 451066.846)]),
                shapely.LineString([shapely.Point(174925.554, 451067.712), shapely.Point(174926.304, 451067.279)]),
                shapely.LineString([shapely.Point(174927.054, 451067.712), shapely.Point(174927.804, 451067.279)]),
                shapely.LineString([shapely.Point(174926.304, 451068.145), shapely.Point(174927.054, 451067.712)]),
                shapely.LineString([shapely.Point(174925.554, 451068.578), shapely.Point(174926.304, 451068.145)]),
                shapely.LineString([shapely.Point(174927.054, 451068.578), shapely.Point(174927.804, 451068.145)]),
            ],
            columns=["node_id_source", "node_id_target", "weight"],
            crs=Config.CRS,
        )
        # Edge lengths must be tested separately, as geopandas does not allow float tolerance
        expected_lengths = pd.Series([0.866, 0.866, 0.866, 0.866, 0.866, 0.866, 0.866, 0.866], name="length")

        gpd.testing.assert_geodataframe_equal(
            expected_edges, left_edges_result[["node_id_source", "node_id_target", "weight", "geometry"]]
        )
        pd.testing.assert_series_equal(expected_lengths, left_edges_result["length"], atol=0.01)

    def verify_right_edges(self, right_edges_result: gpd.GeoDataFrame):
        expected_edges = gpd.GeoDataFrame(
            data=[
                [4, 2, 15.0],
                [5, 3, 15.0],
                [6, 0, 15.0],
                [7, 5, 20.0],
                [8, 7, 25.0],
                [9, 6, 25.0],
                [10, 1, 20.0],
                [11, 9, 30.0],
            ],
            geometry=[
                shapely.LineString([shapely.Point(174927.804, 451067.279), shapely.Point(174927.054, 451066.846)]),
                shapely.LineString([shapely.Point(174926.304, 451067.279), shapely.Point(174925.554, 451066.846)]),
                shapely.LineString([shapely.Point(174925.554, 451067.712), shapely.Point(174924.804, 451067.279)]),
                shapely.LineString([shapely.Point(174927.054, 451067.712), shapely.Point(174926.304, 451067.279)]),
                shapely.LineString([shapely.Point(174927.804, 451068.145), shapely.Point(174927.054, 451067.712)]),
                shapely.LineString([shapely.Point(174926.304, 451068.145), shapely.Point(174925.554, 451067.712)]),
                shapely.LineString([shapely.Point(174925.554, 451068.578), shapely.Point(174924.804, 451068.145)]),
                shapely.LineString([shapely.Point(174927.054, 451068.578), shapely.Point(174926.304, 451068.145)]),
            ],
            columns=["node_id_source", "node_id_target", "weight"],
            crs=Config.CRS,
        )
        # Edge lengths must be tested separately, as geopandas does not allow float tolerance
        expected_lengths = pd.Series([0.866, 0.866, 0.866, 0.866, 0.866, 0.866, 0.866, 0.866], name="length")

        gpd.testing.assert_geodataframe_equal(
            expected_edges, right_edges_result[["node_id_source", "node_id_target", "weight", "geometry"]]
        )
        pd.testing.assert_series_equal(expected_lengths, right_edges_result["length"], atol=0.01)
