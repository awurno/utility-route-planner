# SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#
# SPDX-License-Identifier: Apache-2.0
import networkx as nx
import osmnx as ox
import structlog

logger = structlog.get_logger(__name__)


class OSMGraphPreprocessor:
    def __init__(self, graph: nx.MultiGraph):
        self.graph = graph

    def preprocess_graph(self) -> nx.MultiGraph:
        self.graph = ox.convert.to_undirected(self.graph)
        max_edge_id = self._remove_duplicate_edges_and_add_edge_id_and_length_properties()
        self._set_unused_id_nodes_and_unused_id_edges(max_edge_id)

        return self.graph

    def _remove_duplicate_edges_and_add_edge_id_and_length_properties(self) -> int:
        """
        After removing duplicate edges, OSM graphs occasionally contain duplicate edges. These duplicates are removed.
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

    def _set_unused_id_nodes_and_unused_id_edges(self, max_edge_id: int):
        self.graph.graph["unused_osm_id_nodes"] = max(set(self.graph.nodes)) + 1
        self.graph.graph["unused_osm_id_edges"] = max_edge_id + 1
