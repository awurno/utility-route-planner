# SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#
# SPDX-License-Identifier: Apache-2.0

import networkx as nx
import rustworkx as rx
import osmnx as ox
import structlog
import shapely

from models.multilayer_network.graph_datastructures import OSMNodeInfo, EdgeInfo

logger = structlog.get_logger(__name__)


class OSMGraphPreprocessor:
    def __init__(self, nx_graph: nx.MultiGraph):
        self.nx_graph = nx_graph

    def preprocess_graph(self) -> rx.PyGraph:
        self.validate_input()
        logger.info(
            f"Preprocessing NetworkX OSM graph n_nodes: {self.nx_graph.number_of_nodes()} n_edges: {self.nx_graph.number_of_edges()} to Rustworkx."
        )
        self.nx_graph = ox.convert.to_undirected(self.nx_graph)
        self._remove_duplicate_edges_and_add_edge_id_and_length_properties()
        rx_graph = self._convert_to_rustworkx(self.nx_graph)

        return rx_graph

    def _remove_duplicate_edges_and_add_edge_id_and_length_properties(self):
        """
        OSM graphs occasionally contain duplicate edges. These duplicates are removed.
        In addition, a unique edge is assigned to each edge for further processing. Given the geometry of an edge,
        the length is set as an edge attribute.

        :return: the number of edges, which is used as the maximum edge id to assign new edges later on
        """
        edges_to_remove = []
        initial_edge_count = len(self.nx_graph.edges)
        for u, v, key in self.nx_graph.edges(keys=True):
            if key > 0:
                edges_to_remove.append((u, v, key))
            self.nx_graph[u][v][0]["length"] = self.nx_graph[u][v][0]["geometry"].length
        self.nx_graph.remove_edges_from(edges_to_remove)
        logger.info(f"Removed {initial_edge_count - len(self.nx_graph.edges)} duplicate edges from the graph")

    @staticmethod
    def _convert_to_rustworkx(nx_graph) -> rx.PyGraph:
        rx_graph = rx.PyGraph(multigraph=False)

        nodes = list(nx_graph.nodes)
        nx_rx_node_mapping = dict(zip(nodes, rx_graph.add_nodes_from(nodes)))
        rx_graph.add_edges_from(
            [
                (
                    nx_rx_node_mapping[x[0]],
                    nx_rx_node_mapping[x[1]],
                    EdgeInfo(
                        x[2].get("osmid", 0), x[2].get("length", 0), x[2].get("geometry", shapely.LineString()), idx
                    ),
                )
                for idx, x in enumerate(nx_graph.edges(data=True), start=0)
            ]
        )

        for node, node_index in nx_rx_node_mapping.items():
            data = nx_graph.nodes[node]
            info = OSMNodeInfo(node, shapely.Point(data.get("x", 0), data.get("y", 0)), node_index)
            rx_graph[node_index] = info

        return rx_graph

    def validate_input(self):
        if not isinstance(self.nx_graph, nx.MultiGraph):
            raise TypeError("Input graph must be a NetworkX MultiGraph.")
        if self.nx_graph.number_of_edges() == 0:
            raise ValueError("Graph should have edges.")
        if self.nx_graph.number_of_nodes() == 0:
            raise ValueError("Graph should have nodes.")
