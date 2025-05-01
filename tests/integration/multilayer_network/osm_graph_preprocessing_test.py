# SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#
# SPDX-License-Identifier: Apache-2.0
import pytest
from settings import Config
from networkx import MultiDiGraph, MultiGraph
from pyproj import CRS
from shapely import LineString

from utility_route_planner.util.osm_graph_preprocessing import OSMGraphPreprocessor


class TestOSMGraphPreprocessor:
    @pytest.fixture
    def unprocessed_directed_graph(self):
        graph = MultiDiGraph()
        graph.graph["crs"] = CRS(Config.CRS)

        # Two-way edges between node 0 and 1
        graph.add_edge(0, 1, 0, osmid=0, geometry=LineString([(0, 0), (0, 1)]))
        graph.add_edge(1, 0, 0, osmid=1, geometry=LineString([(0, 1), (0, 0)]))

        # Oneway edge from node 1 to 2
        graph.add_edge(1, 2, 0, osmid=2, geometry=LineString([(0, 1), (0, 2)]))

        return graph

    def test_graph_is_made_undirected(self, unprocessed_directed_graph: MultiDiGraph):
        graph_preprocessor = OSMGraphPreprocessor(unprocessed_directed_graph)
        preprocessed_graph = graph_preprocessor.preprocess_graph()

        assert not preprocessed_graph.is_directed()
        assert preprocessed_graph.number_of_edges() == 2

        self.check_graph_properties(preprocessed_graph)

    @pytest.fixture
    def graph_with_duplicate_edges(self) -> MultiDiGraph:
        graph = MultiDiGraph()
        graph.graph["crs"] = CRS(Config.CRS)

        # Two duplicate edges (having a distinct key) between nodes 0 and 1
        graph.add_edge(0, 1, 0, osmid=0, geometry=LineString([(0, 0), (0, 1)]))
        graph.add_edge(0, 1, 1, osmid=1, geometry=LineString([(0, 0), (0, 1)]))

        # One edge between nodes 1 and 2
        graph.add_edge(1, 2, 0, osmid=2, geometry=LineString([(0, 1), (0, 2)]))

        return graph

    def test_duplicate_edges_are_removed(self, graph_with_duplicate_edges: MultiDiGraph):
        graph_preprocessor = OSMGraphPreprocessor(graph_with_duplicate_edges)
        preprocessed_graph = graph_preprocessor.preprocess_graph()

        # For all edges in the preprocessed graph, the key should be 0. Keys > 0 imply duplicate edges
        assert preprocessed_graph.number_of_edges() == 2
        for _, _, key in preprocessed_graph.edges(keys=True):
            assert key == 0

        self.check_graph_properties(preprocessed_graph)

    @staticmethod
    def check_graph_properties(graph: MultiGraph):
        previous_edge_id = 0
        for u, v, edge_data in graph.edges(data=True):
            assert edge_data["edge_id"] > previous_edge_id
            previous_edge_id = edge_data["edge_id"]
            assert edge_data["length"] == edge_data["geometry"].length
