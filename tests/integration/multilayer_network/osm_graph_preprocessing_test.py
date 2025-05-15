# SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#
# SPDX-License-Identifier: Apache-2.0
import pytest
import rustworkx as rx
import pickle

from settings import Config
from networkx import MultiDiGraph, MultiGraph
from pyproj import CRS
import shapely

from utility_route_planner.util.osm_graph_preprocessing import OSMGraphPreprocessor, NodeInfo


class TestOSMGraphPreprocessor:
    @pytest.fixture
    def unprocessed_directed_graph(self):
        graph = MultiDiGraph()
        graph.graph["crs"] = CRS(Config.CRS)

        graph.add_node(0, osmid=0, x=0, y=0)
        graph.add_node(1, osmid=1, x=0, y=1)
        graph.add_node(2, osmid=2, x=0, y=-2)

        # Two-way edges between node 0 and 1
        graph.add_edge(0, 1, 0, osmid=0, geometry=shapely.LineString([(0, 0), (0, 1)]), length=1)
        graph.add_edge(1, 0, 0, osmid=1, geometry=shapely.LineString([(0, 1), (0, 0)]), length=1)

        # Oneway edge from node 0 to 2
        graph.add_edge(0, 2, 0, osmid=2, geometry=shapely.LineString([(0, 0), (0, -2)]), length=2)

        return graph

    @pytest.fixture
    def pytest_osm_graph_pickle(self, refresh_example_graph=False) -> MultiGraph:
        # Option to refresh to example osm graph.
        if refresh_example_graph:
            import geopandas as gpd
            from utility_route_planner.util.osm_graph_downloader import OSMGraphDownloader

            project_area = (
                gpd.read_file(Config.PYTEST_PATH_GEOPACKAGE_MCDA, layer=Config.PYTEST_LAYER_NAME_PROJECT_AREA)
                .iloc[0]
                .geometry
            )
            osm_graph_downloader = OSMGraphDownloader(project_area, 50)
            project_area_graph = osm_graph_downloader.download_graph()

            with open(Config.PYTEST_OSM_GRAPH_PICKLE, "wb") as file:
                pickle.dump(project_area_graph, file)

        with open(Config.PYTEST_OSM_GRAPH_PICKLE, "rb") as file:
            osm_graph = pickle.load(file)
        return osm_graph

    def test_graph_is_made_undirected(self, unprocessed_directed_graph: MultiDiGraph):
        graph_preprocessor = OSMGraphPreprocessor(unprocessed_directed_graph)
        preprocessed_graph = graph_preprocessor.preprocess_graph()

        assert isinstance(preprocessed_graph, rx.PyGraph)
        assert preprocessed_graph.num_edges() == 2

        self.check_graph_properties(preprocessed_graph, graph_preprocessor.nx_graph)

    def test_duplicate_edges_are_removed(self, unprocessed_directed_graph: MultiDiGraph):
        # Add duplicate edge
        unprocessed_directed_graph.add_edge(0, 1, 1, osmid=0, geometry=shapely.LineString([(0, 0), (0, 1)]), length=1)
        graph_preprocessor = OSMGraphPreprocessor(unprocessed_directed_graph)
        preprocessed_graph = graph_preprocessor.preprocess_graph()

        # For all edges in the preprocessed graph, the key should be 0. Keys > 0 imply duplicate edges
        assert preprocessed_graph.num_edges() == 2

        self.check_graph_properties(preprocessed_graph, graph_preprocessor.nx_graph)

    def test_osm_pickle(self, pytest_osm_graph_pickle: MultiGraph):
        graph_preprocessor = OSMGraphPreprocessor(pytest_osm_graph_pickle)
        preprocessed_graph = graph_preprocessor.preprocess_graph()

        self.check_graph_properties(preprocessed_graph, graph_preprocessor.nx_graph)

    def test_invalid_input(self):
        with pytest.raises(TypeError):
            OSMGraphPreprocessor(None).preprocess_graph()
        graph = MultiDiGraph()
        with pytest.raises(ValueError):
            OSMGraphPreprocessor(graph).preprocess_graph()
        graph.add_node(0, osmid=0, geometry=shapely.LineString([(0, 0), (0, 1)]))
        with pytest.raises(ValueError):
            OSMGraphPreprocessor(graph).preprocess_graph()

    @staticmethod
    def check_graph_properties(rx_graph: rx.PyGraph, nx_graph: MultiGraph):
        assert nx_graph.number_of_nodes() == rx_graph.num_nodes()
        assert nx_graph.number_of_edges() == rx_graph.num_edges()

        nx_nodes = nx_graph.nodes(data=True)
        for rx_node in rx_graph.nodes():
            # Check if the properties of the node are the same as the nx_graph
            assert isinstance(rx_node, NodeInfo)
            assert nx_nodes[rx_node.osm_id].get("x") == rx_node.geometry.x
            assert nx_nodes[rx_node.osm_id].get("y") == rx_node.geometry.y

            # Check if we have the same edges as neighbours in both graphs
            rx_adjacent_edges = rx_graph.adj(rx_node.node_id)
            nx_adjacent_edges = nx_graph.edges(rx_node.osm_id, data=True)
            assert len(rx_adjacent_edges) == len(nx_adjacent_edges)

            # Check if the edge properties are the same
            nx_edge_props = set((i[2]["geometry"], i[2]["length"], i[2]["osmid"]) for i in nx_adjacent_edges)
            rx_edge_props = set(
                (rx_edge.geometry, rx_edge.length, rx_edge.osm_id) for rx_edge in rx_adjacent_edges.values()
            )
            assert rx_edge_props == nx_edge_props
