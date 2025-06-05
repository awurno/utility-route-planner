# SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#
# SPDX-License-Identifier: Apache-2.0
import pytest
import geopandas as gpd
import rustworkx as rx
import shapely

from settings import Config
from utility_route_planner.util.graph_utilities import create_edge_info
from utility_route_planner.models.mcda.mcda_engine import McdaCostSurfaceEngine
from utility_route_planner.models.multilayer_network.pipe_ramming import GetPotentialPipeRammingCrossings
from utility_route_planner.util.geo_utilities import get_empty_geodataframe
from utility_route_planner.models.multilayer_network.osm_graph_preprocessing import OSMGraphPreprocessor, NodeInfo
from utility_route_planner.util.write import reset_geopackage


class TestPipeRamming:
    @pytest.fixture
    def setup_pipe_ramming_example_polygon(self, load_osm_graph_pickle):
        project_area = (
            gpd.read_file(Config.PYTEST_PATH_GEOPACKAGE_MCDA, layer=Config.PYTEST_LAYER_NAME_PROJECT_AREA)
            .iloc[0]
            .geometry
        )

        osm_graph_preprocessor = OSMGraphPreprocessor(load_osm_graph_pickle)
        osm_graph_preprocessed = osm_graph_preprocessor.preprocess_graph()

        mcda_engine = McdaCostSurfaceEngine(
            Config.RASTER_PRESET_NAME_BENCHMARK, Config.PYTEST_PATH_GEOPACKAGE_MCDA, project_area
        )
        mcda_engine.preprocess_vectors()

        return osm_graph_preprocessed, mcda_engine

    def test_simplify_graph(self):
        osm_graph = rx.PyGraph()
        node1 = NodeInfo(osm_id=1, geometry=shapely.Point(0, 0))
        node2 = NodeInfo(osm_id=2, geometry=shapely.Point(1, 0))
        node3 = NodeInfo(osm_id=3, geometry=shapely.Point(1, -1))
        node4 = NodeInfo(osm_id=4, geometry=shapely.Point(1, -2))
        node5 = NodeInfo(osm_id=5, geometry=shapely.Point(2, 0))
        node6 = NodeInfo(osm_id=6, geometry=shapely.Point(3, 0))
        node7 = NodeInfo(osm_id=7, geometry=shapely.Point(3, 1))
        node8 = NodeInfo(osm_id=8, geometry=shapely.Point(4, 1))
        node9 = NodeInfo(osm_id=9, geometry=shapely.Point(4, 0))
        node10 = NodeInfo(osm_id=10, geometry=shapely.Point(5, 0))
        node11 = NodeInfo(osm_id=11, geometry=shapely.Point(6, 1))
        node12 = NodeInfo(osm_id=12, geometry=shapely.Point(6, -1))

        edge1 = create_edge_info(100, node1, node2)
        edge2 = create_edge_info(101, node2, node3)
        edge3 = create_edge_info(102, node3, node4)
        edge4 = create_edge_info(103, node2, node5)
        edge5 = create_edge_info(104, node5, node6)
        edge6 = create_edge_info(105, node6, node7)
        edge7 = create_edge_info(106, node7, node8)
        edge8 = create_edge_info(107, node8, node9)
        edge9 = create_edge_info(108, node6, node9)
        edge10 = create_edge_info(109, node9, node10)
        edge11 = create_edge_info(110, node10, node11)
        edge12 = create_edge_info(111, node10, node12)
        edge13 = create_edge_info(112, node11, node12)

        node_ids = osm_graph.add_nodes_from(
            [node1, node2, node3, node4, node5, node6, node7, node8, node9, node10, node11, node12]
        )
        (
            node1.node_id,
            node2.node_id,
            node3.node_id,
            node4.node_id,
            node5.node_id,
            node6.node_id,
            node7.node_id,
            node8.node_id,
            node9.node_id,
            node10.node_id,
            node11.node_id,
            node12.node_id,
        ) = node_ids
        edges_to_add = [
            (node1.node_id, node2.node_id, edge1),
            (node2.node_id, node3.node_id, edge2),
            (node3.node_id, node4.node_id, edge3),
            (node2.node_id, node5.node_id, edge4),
            (node5.node_id, node6.node_id, edge5),
            (node6.node_id, node7.node_id, edge6),
            (node7.node_id, node8.node_id, edge7),
            (node8.node_id, node9.node_id, edge8),
            (node6.node_id, node9.node_id, edge9),
            (node9.node_id, node10.node_id, edge10),
            (node10.node_id, node11.node_id, edge11),
            (node10.node_id, node12.node_id, edge12),
            (node11.node_id, node12.node_id, edge13),
        ]
        for edge_index, edge in enumerate(edges_to_add, start=0):
            node_a, node_b, edge_info = edge
            edge_info.edge_id = edge_index
            osm_graph.add_edge(node_a, node_b, edge_info)

        # Enable debug for visual debugging in QGIS.
        crossings = GetPotentialPipeRammingCrossings(
            osm_graph, get_empty_geodataframe(), get_empty_geodataframe(), debug=True
        )
        nodes, edges = crossings.group_graph_segments()

        # Do a sanity check on the grouped edges and nodes.
        assert len(edges) == osm_graph.num_edges()
        assert len(nodes) == osm_graph.num_nodes()

        # Check that the edges are grouped correctly.
        assert edges["group"].nunique() == 7

        group_100 = edges.loc[edges["osm_id"] == 100, "group"].iloc[0]
        assert (edges["group"] == group_100).sum() == 1

        group_101 = edges.loc[edges["osm_id"] == 101, "group"].iloc[0]
        group_102 = edges.loc[edges["osm_id"] == 102, "group"].iloc[0]
        assert group_101 == group_102
        assert (edges["group"] == group_101).sum() == 2

        group_103 = edges.loc[edges["osm_id"] == 103, "group"].iloc[0]
        group_104 = edges.loc[edges["osm_id"] == 104, "group"].iloc[0]
        assert group_103 == group_104
        assert (edges["group"] == group_103).sum() == 2

        group_105 = edges.loc[edges["osm_id"] == 105, "group"].iloc[0]
        group_106 = edges.loc[edges["osm_id"] == 106, "group"].iloc[0]
        group_107 = edges.loc[edges["osm_id"] == 107, "group"].iloc[0]
        assert group_105 == group_106 == group_107
        assert (edges["group"] == group_105).sum() == 3

        group_108 = edges.loc[edges["osm_id"] == 108, "group"].iloc[0]
        assert (edges["group"] == group_108).sum() == 1

        group_109 = edges.loc[edges["osm_id"] == 109, "group"].iloc[0]
        assert (edges["group"] == group_109).sum() == 1

        group_110 = edges.loc[edges["osm_id"] == 110, "group"].iloc[0]
        group_111 = edges.loc[edges["osm_id"] == 111, "group"].iloc[0]
        group_112 = edges.loc[edges["osm_id"] == 112, "group"].iloc[0]
        assert group_110 == group_111 == group_112
        assert (edges["group"] == group_110).sum() == 3

    def test_find_road_crossings(self, setup_pipe_ramming_example_polygon):
        reset_geopackage(Config.PATH_GEOPACKAGE_MULTILAYER_NETWORK_OUTPUT, truncate=False)
        osm_graph, mcda_engine = setup_pipe_ramming_example_polygon

        obstacles = mcda_engine.processed_vectors["pand"]  # can be expanded with water, trees.
        roads = mcda_engine.processed_vectors["wegdeel"]
        crossings = GetPotentialPipeRammingCrossings(osm_graph, roads, obstacles)
        nodes, edges = crossings.get_crossings()
