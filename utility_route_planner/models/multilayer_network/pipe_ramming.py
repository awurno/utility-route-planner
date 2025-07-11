# SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#
# SPDX-License-Identifier: Apache-2.0
import numpy as np
import pandas as pd
import shapely
import structlog
import rustworkx as rx
import itertools

from settings import Config
import geopandas as gpd

from utility_route_planner.models.multilayer_network.hexagon_graph.hexagon_utils import convert_hexagon_graph_to_gdfs
from utility_route_planner.util.geo_utilities import osm_graph_to_gdfs
from utility_route_planner.util.write import write_results_to_geopackage

logger = structlog.get_logger(__name__)


class GetPotentialPipeRammingCrossings:
    def __init__(
        self,
        osm_graph: rx.PyGraph,
        cost_surface_graph: rx.PyGraph,
        obstacles: gpd.GeoDataFrame,
        debug: bool = False,
    ):
        self.osm_graph = osm_graph
        self.cost_surface_graph = cost_surface_graph
        # Everything which blocks a possible pipe ramming, or filter on suitability value?
        self.obstacles = obstacles

        # Minimum length of a street segment to be considered for adding pipe ramming crossings.
        self.threshold_edge_length_crossing_m = Config.THRESHOLD_SEGMENT_CROSSING_LENGTH_M
        # Maximum length possible of a pipe ramming crossing.
        self.max_pipe_ramming_length_m = 15
        # Cost surface value below which we consider a crossing suitable.
        self.suitability_value_threshold = 10  # TODO this is a value which includes sidewalk/berm
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
        osm_edges, osm_nodes = self.convert_osm_graph_to_gdfs()  # TODO move to init and put on self?

        # Group the edges into street segments between junctions (node degree > 2).
        osm_nodes, street_segments = self.create_street_segment_groups(osm_nodes, osm_edges)

        # Finds crossings (parallel to the edge!) for junctions.
        self.create_junction_crossings(osm_nodes, street_segments)

        # Find crossings (perpendicular to the edge!) for larger street segments.
        self.get_crossings_per_segment(osm_nodes, street_segments)

        logger.info("Found n crossings.")
        return

    def convert_osm_graph_to_gdfs(self):
        osm_nodes, osm_edges = osm_graph_to_gdfs(self.osm_graph)
        return osm_edges, osm_nodes

    def create_junction_crossings(self, osm_nodes, osm_street_segments):
        # Find the degree of each node in the graph.
        node_degree = {
            i: self.osm_graph.degree(i) for i in self.osm_graph.node_indices() if self.osm_graph.degree(i) > 2
        }
        osm_nodes["degree"] = pd.Series(node_degree, index=osm_nodes.index, dtype=int)
        junctions = osm_nodes[osm_nodes["degree"] > 2]
        if len(junctions) == 0:
            logger.warning("No junctions found to consider for pipe ramming.")
            return
        else:
            logger.info(f"Found {len(junctions)} junctions to consider for pipe ramming.")

        # TODO discuss adding the properties (BGT elements) to the hexagon nodes. That way you can force it to only include sidewalks, ignoring the suitability value.
        cost_surface_nodes = convert_hexagon_graph_to_gdfs(self.cost_surface_graph, edges=False)
        # to_remove = self.mcda_roads[~self.mcda_roads["function"].isin(["fietspand", "voetpad"])]
        # cost_surface_nodes_filtered = cost_surface_nodes.overlay(to_remove, how="difference")
        cost_surface_nodes_filtered = cost_surface_nodes[
            cost_surface_nodes["suitability_value"] < self.suitability_value_threshold
        ]

        # buffer the (concave_hull?) of the grouped nodes equal to the pipe ramming max length, take a bit of margin
        junctions["geometry"] = junctions.buffer(
            self.max_pipe_ramming_length_m + self.max_pipe_ramming_length_m * 0.5, 6
        )

        # Split the buffer with the edges. Each segment should get a connection to the other segment if they share a boundary
        for node_id, junction_node in junctions.iterrows():
            junction_edge_groups = osm_street_segments.loc[self.osm_graph.incident_edges(node_id)].group
            # TODO this will give problems when junctions are very close by each other, i think we better extend the direct incident edges.
            junction_edges = osm_street_segments[osm_street_segments["group"].isin(junction_edge_groups)]

            # First, split the buffered junction by the osm_edges to create the sides to connect.
            line_split_collection = [junction_node.geometry.boundary, *junction_edges.geometry.to_list()]
            merged_lines = shapely.ops.linemerge(line_split_collection)
            border_lines = shapely.ops.unary_union(merged_lines)
            street_sides = [i for i in shapely.ops.polygonize(border_lines)]

            # Second, intersect the hexagon_nodes eligible for creating crossings to each created side.
            street_sides = gpd.GeoDataFrame(street_sides, columns=["geometry"], crs=Config.CRS)
            cost_surface_nodes_junction = cost_surface_nodes_filtered.sjoin(
                street_sides, how="inner", predicate="intersects"
            )
            cost_surface_nodes_junction.rename(columns={"index_right": "idx_street_side"}, inplace=True)

            # Third, check number of sides created and if there are nodes in each side to connect.
            if not len(street_sides) == junction_node.degree:
                logger.warning(
                    f"Node {junction_node['osm_id']} has {junction_node.degree} edges, but {len(street_sides)} polygons were created."
                )
            if not cost_surface_nodes_junction["idx_street_side"].nunique() == junction_node.degree:
                logger.warning("Not all street sides have nodes to connect to.")

            # Check for edges which are almost 180 degrees apart, create straight crossings for those.
            adjacent_edges = osm_street_segments.loc[self.osm_graph.incident_edges(node_id)]
            adjacent_edges["point_a"] = adjacent_edges["geometry"].apply(lambda line: shapely.Point(line.coords[0]))
            adjacent_edges["point_b"] = adjacent_edges["geometry"].apply(lambda line: shapely.Point(line.coords[1]))
            for edge_1, edge_2 in itertools.combinations(adjacent_edges.index, 2):
                # Get the outer points of the edges to compare the angle to.
                if adjacent_edges.loc[edge_1].point_a.equals(osm_nodes.loc[node_id].geometry):
                    a = adjacent_edges.loc[edge_1].point_b
                else:
                    a = adjacent_edges.loc[edge_1].point_a
                if adjacent_edges.loc[edge_2].point_a.equals(osm_nodes.loc[node_id].geometry):
                    b = adjacent_edges.loc[edge_2].point_b
                else:
                    b = adjacent_edges.loc[edge_2].point_a

                # Convert to vectors: from C to A and from C to B
                vec_CA = np.array([a.x - osm_nodes.loc[node_id].geometry.x, a.y - osm_nodes.loc[node_id].geometry.y])
                vec_CB = np.array([b.x - osm_nodes.loc[node_id].geometry.x, b.y - osm_nodes.loc[node_id].geometry.y])

                cos_theta = np.dot(vec_CA, vec_CB) / (np.linalg.norm(vec_CA) * np.linalg.norm(vec_CB))
                angle_rad = np.arccos(np.clip(cos_theta, -1, 1))
                angle_deg = np.degrees(angle_rad)

                print(f"Angle between edges {edge_1} and {edge_2} at junction {node_id}: {angle_deg:.2f} degrees.")

            match junction_node.degree:
                case 3:
                    # T junction, treat sides differently. the | part is less important than the - part.
                    pass
                case 4:
                    # find the segments which belong to each other.
                    outer_points = osm_street_segments.intersection(junction_node.geometry.exterior)
                    outer_points = outer_points[~outer_points.is_empty]
                    junction_edges = osm_street_segments[osm_street_segments.intersects(junction_node.geometry)]

                case _:
                    logger.warning("not implemented")

            # Alternative approach, for each edge from the center node, create a linestring perpendicular to the edge. and move outwards.
            for side_1, side_2 in itertools.combinations(street_sides, 2):
                # Check if the two sides share an edge, if so, we can create a crossing.
                paths = [i for i in shapely.shared_paths(side_1.exterior, side_2.exterior).geoms if not i.is_empty]
                if len(paths) != 0:
                    # get points of the clipped edges which do not intersect the shared path
                    outer_points_subset = outer_points.intersects(shapely.MultiPolygon([side_1, side_2]))
                    outer_points_subset_1 = outer_points[outer_points_subset]
                    outer_points_subset_2 = outer_points_subset_1[~outer_points_subset_1.intersects(paths[0])]
                    if len(outer_points_subset_2) != 2:
                        print("i think this occurs when degree == 3")
                        continue
                    # TODO build crossing from the middle based on self.max_pipe_ramming_length_m?
                    crossing = shapely.LineString(
                        [outer_points_subset_2.iloc[0].geometry, outer_points_subset_2.iloc[1].geometry]
                    )
                    # sweepline approach, first implement the hexagonal grid.
                    print(crossing.length)

        if self.debug:
            out = Config.PATH_GEOPACKAGE_MULTILAYER_NETWORK_OUTPUT
            # Plot hexagons
            write_results_to_geopackage(out, cost_surface_nodes, "pytest_cost_surface_nodes")
            write_results_to_geopackage(out, cost_surface_nodes_filtered, "pytest_cost_surface_filtered")
            # Plot junctions
            write_results_to_geopackage(out, junctions, "pytest_osm_junctions")
            write_results_to_geopackage(out, osm_street_segments, "pytest_osm_streets")
            # Plot an individual junction with its street sides and outer points.
            write_results_to_geopackage(out, junction_edges, "pytest_osm_junction_edges")
            write_results_to_geopackage(out, street_sides, "pytest_street_sides")
            write_results_to_geopackage(out, cost_surface_nodes_junction, "pytest_cost_surface_nodes_junction")

            write_results_to_geopackage(out, a, "pytest_point_a")
            write_results_to_geopackage(out, b, "pytest_point_b")

            write_results_to_geopackage(out, outer_points, "pytest_outer_points")
            write_results_to_geopackage(out, side_1, "pytest_side_1")
            write_results_to_geopackage(out, side_2, "pytest_side_2")
            write_results_to_geopackage(out, outer_points_subset_2, "pytest_nodes_to_connect")

    def create_street_segment_groups(self, nodes, edges) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
        """
        Similar function: https://osmnx.readthedocs.io/en/stable/user-reference.html#osmnx.simplification.simplify_graph
        Publication: https://onlinelibrary.wiley.com/doi/10.1111/tgis.70037
        """
        # Group the edges which are connected by nodes with only 2 edges. We refer to this as a street segment.
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
                Config.PATH_GEOPACKAGE_MULTILAYER_NETWORK_OUTPUT,
                edges.dissolve(by="group"),
                "pytest_edges_with_segment_groups",
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

        for group in crossing_points.index:
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
