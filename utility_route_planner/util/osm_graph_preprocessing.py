# SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#
# SPDX-License-Identifier: Apache-2.0
from dataclasses import dataclass

import networkx as nx
import rustworkx as rx
import osmnx as ox
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class GraphAttributes:
    max_edge_id: int
    max_node_id: int


class OSMGraphPreprocessor:
    def __init__(self, graph: nx.MultiGraph):
        self.graph = graph

    def preprocess_graph(self) -> rx.PyGraph:
        self.graph = ox.convert.to_undirected(self.graph)
        max_edge_id = self._remove_duplicate_edges_and_add_edge_id_and_length_properties()
        rx_graph = self._convert_to_rustworkx(self.graph)
        rx_graph = self._set_unused_id_nodes_and_unused_id_edges(max_edge_id, rx_graph)

        return rx_graph

    def _remove_duplicate_edges_and_add_edge_id_and_length_properties(self) -> int:
        """
        OSM graphs occasionally contain duplicate edges. These duplicates are removed.
        In addition, a unique edge is assigned to each edge for further processing. Given the geometry of an edge,
        the length is set as an edge attribute.

        :return: the number of edges, which is used as the maximum edge id to assign new edges later on
        """
        edges_to_remove = []
        initial_edge_count = len(self.graph.edges)
        edge_count = 1
        for edge_count, (u, v, key) in enumerate(self.graph.edges(keys=True), start=1):
            if key > 0:
                edges_to_remove.append((u, v, key))
            self.graph[u][v][0]["edge_id"] = edge_count
            self.graph[u][v][0]["length"] = self.graph[u][v][0]["geometry"].length
        self.graph.remove_edges_from(edges_to_remove)
        logger.info(f"Removed {initial_edge_count - len(self.graph.edges)} duplicate edges from the graph")

        return edge_count

    def _set_unused_id_nodes_and_unused_id_edges(self, max_edge_id: int, rx_graph: rx.PyGraph):
        rx_graph.attrs = GraphAttributes(max_edge_id=max_edge_id, max_node_id=max(set(self.graph.nodes)) + 1)
        return rx_graph

    @staticmethod
    def _convert_to_rustworkx(graph) -> rx.PyGraph:
        new_graph = rx.PyGraph(multigraph=graph.is_multigraph())
        nodes = list(graph.nodes)
        node_indices = dict(zip(nodes, new_graph.add_nodes_from(nodes)))
        new_graph.add_edges_from([(node_indices[x[0]], node_indices[x[1]], x[2]) for x in graph.edges(data=True)])

        for node, node_index in node_indices.items():
            attributes = graph.nodes[node]
            attributes["osm_id"] = node
            new_graph[node_index] = attributes

        return new_graph
