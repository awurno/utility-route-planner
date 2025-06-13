# SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#
# SPDX-License-Identifier: Apache-2.0
import numpy as np
import pandas as pd
import shapely
import structlog
import rustworkx as rx

from settings import Config
import geopandas as gpd

from utility_route_planner.util.geo_utilities import osm_graph_to_gdfs
from utility_route_planner.util.write import write_results_to_geopackage

logger = structlog.get_logger(__name__)


class GetPotentialPipeRammingCrossings:
    def __init__(
        self, osm_graph: rx.PyGraph, mcda_roads: gpd.GeoDataFrame, obstacles: gpd.GeoDataFrame, debug: bool = False
    ):
        self.osm_graph = osm_graph
        self.mcda_roads = mcda_roads  # add berm?
        self.obstacles = obstacles  # Everything which blocks a possible pipe ramming.

        # Minimum length of a street segment to be considered for adding pipe ramming crossings.
        self.threshold_edge_length_crossing_m = Config.THRESHOLD_SEGMENT_CROSSING_LENGTH_M
        self.debug = debug

    def get_crossings(self):
        """
        Get the crossings for the pipe ramming process.

        We want a road crossing for each segment longer than a certain length.
        For each street segment (set of edges connected by nodes which only have 2 edges) check:
        - Only if crossing the road is expensive (asphalt).
        - If we have enough space between houses somewhere along that edge.
        - Find two cells on the cost-surface which have a low enough cost (sidewalk / berm).
        - Add edges between the two cells with a cost that is lower than just crossing the road.
        Start by checking junctions (nodes with more than 2 edges).
        After this, check the remaining street segments and split them if they are long enough.
        """
        logger.info("Finding road crossings.")

        nodes, street_segments = self.create_street_segment_groups()
        self.get_crossings_per_segment(nodes, street_segments)

        logger.info("Road crossings found.")
        return

    def create_street_segment_groups(self) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
        """
        Similar function: https://osmnx.readthedocs.io/en/stable/user-reference.html#osmnx.simplification.simplify_graph
        Publication: https://onlinelibrary.wiley.com/doi/10.1111/tgis.70037
        """
        # Group the edges which are connected by nodes with only 2 edges. We refer to this as a street segment.
        nodes, edges = osm_graph_to_gdfs(self.osm_graph)
        node_degree = {i: self.osm_graph.degree(i) for i in self.osm_graph.node_indices()}
        # Initialize all edges with a unique group number, then start merging adjacent edges.
        edges["group"] = pd.Series(range(len(edges)), index=edges.index)

        seen_nodes = set()
        for edge_group_nr, (node_id, degree) in enumerate(node_degree.items(), start=len(edges) + 1):
            if degree != 2 and node_id not in seen_nodes:
                continue

            # Get the complete street segment to merge.
            edges_to_group = []
            nodes_to_check = [node_id]
            while nodes_to_check:
                for node_id_2 in nodes_to_check:
                    if node_degree[node_id_2] == 2 and node_id_2 not in seen_nodes:
                        adjacent = self.osm_graph.adj(node_id_2)
                        edges_to_group.extend([edge.edge_id for edge in adjacent.values()])
                        nodes_to_check.extend(list(adjacent.keys()))

                    nodes_to_check.remove(node_id_2)
                    seen_nodes.add(node_id_2)

            edges.loc[edges_to_group, "group"] = edge_group_nr

        logger.info(f"{len(edges)} edges were grouped into {edges['group'].nunique()} segments.")

        if self.debug:
            write_results_to_geopackage(Config.PATH_GEOPACKAGE_MULTILAYER_NETWORK_OUTPUT, nodes, "pytest_nodes")
            write_results_to_geopackage(Config.PATH_GEOPACKAGE_MULTILAYER_NETWORK_OUTPUT, edges, "pytest_edges")
            write_results_to_geopackage(
                Config.PATH_GEOPACKAGE_MULTILAYER_NETWORK_OUTPUT, edges.dissolve(by="group"), "pytest_edges_grouped"
            )

        # Optionally, we can simplify the graph object by removing the nodes and merging the edges to 1 EdgeInfo.
        return nodes, edges

    def get_crossings_per_segment(self, nodes: gpd.GeoDataFrame, street_segments: gpd.GeoDataFrame):
        """
        Find the crossings for the pipe ramming process.
        This is a placeholder for the actual implementation.
        """
        logger.info("Finding crossings in grouped edges and nodes.")

        # Get road crossings for only long segments.
        merged_segments = street_segments.dissolve(by="group")
        merged_segments["length"] = merged_segments.geometry.length
        merged_segments["find_crossings"] = merged_segments["length"] >= self.threshold_edge_length_crossing_m * 2

        # Determine points per segment where crossings can be added.
        crossing_points = merged_segments.loc[merged_segments["find_crossings"]].copy(deep=True)
        crossing_points.geometry = crossing_points.geometry.line_merge()
        crossing_points["geometry"] = crossing_points.geometry.apply(
            lambda geometry: shapely.MultiPoint(
                geometry.interpolate(  # Note that interpolate needs LineStrings for equal intervals, not MultiLinestrings.
                    (
                        # Interval is now between self.threshold_edge_length_crossing_m and self.threshold_edge_length_crossing_m * 2
                        np.linspace(
                            0,
                            geometry.length,
                            int(geometry.length // self.threshold_edge_length_crossing_m),
                            endpoint=False,
                        )[1:]
                    )
                )
            )
        )

        for index, crossing_point in crossing_points.iterrows():
            # split the segment at the crossing point, then buffer the intervals without endcap
            # intersect with obstacles
            # check if there is a perpendicular remaining part in the buffered segment
            print("stahp")

        # TODO: perhaps start with this first and then per segment: Get road crossings per junction?

        # Determine weight

        if self.debug:
            write_results_to_geopackage(
                Config.PATH_GEOPACKAGE_MULTILAYER_NETWORK_OUTPUT, merged_segments, "pytest_merged_segments"
            )
            write_results_to_geopackage(
                Config.PATH_GEOPACKAGE_MULTILAYER_NETWORK_OUTPUT, crossing_points, "pytest_crossing_points"
            )
            write_results_to_geopackage(
                Config.PATH_GEOPACKAGE_MULTILAYER_NETWORK_OUTPUT, self.obstacles, "pytest_obstacles"
            )

    def _write_debug_layers(self):
        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_MULTILAYER_NETWORK_OUTPUT, self.obstacles, "pytest_obstacles"
        )
        write_results_to_geopackage(Config.PATH_GEOPACKAGE_MULTILAYER_NETWORK_OUTPUT, self.mcda_roads, "pytest_roads")
