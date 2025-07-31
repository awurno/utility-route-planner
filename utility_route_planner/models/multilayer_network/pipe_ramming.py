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
from utility_route_planner.util.geo_utilities import osm_graph_to_gdfs, get_empty_geodataframe, get_angle_between_points
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
        self.osm_nodes, self.osm_edges = osm_graph_to_gdfs(osm_graph)
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

        # Group the edges into street segments between junctions (node degree > 2).
        self.create_street_segment_groups()

        # Finds crossings (parallel to the edge!) for junctions.
        junctions, suitable_cost_surface_nodes_to_cross = self.prepare_junction_crossings()
        if not junctions.empty:
            for node_id, junction_node in junctions.iterrows():
                self.get_crossing_for_junction(suitable_cost_surface_nodes_to_cross, node_id, junction_node)

        # Find crossings (perpendicular to the edge!) for larger street segments.
        self.get_crossings_per_segment()

        logger.info("Found n crossings.")
        return

    def create_street_segment_groups(self):
        """
        Similar function: https://osmnx.readthedocs.io/en/stable/user-reference.html#osmnx.simplification.simplify_graph
        Publication: https://onlinelibrary.wiley.com/doi/10.1111/tgis.70037
        """
        # Group the edges which are connected by nodes with only 2 edges. We refer to this as a street segment.
        node_degree = {i: self.osm_graph.degree(i) for i in self.osm_graph.node_indices()}
        # Initialize all edges with a unique group number, then start merging adjacent edges.
        self.osm_edges["group"] = pd.Series(range(len(self.osm_edges)), index=self.osm_edges.index)

        seen_nodes = set()
        for edge_group_nr, (node_id, degree) in enumerate(node_degree.items(), start=len(self.osm_edges) + 1):
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

            self.osm_edges.loc[edges_to_group, "group"] = edge_group_nr

        logger.info(f"{len(self.osm_edges)} edges were grouped into {self.osm_edges['group'].nunique()} segments.")
        # Optionally, we can simplify the graph object by removing the nodes and merging the edges to 1 EdgeInfo.

        if self.debug:
            write_results_to_geopackage(
                Config.PATH_GEOPACKAGE_MULTILAYER_NETWORK_OUTPUT, self.osm_nodes, "pytest_nodes"
            )
            write_results_to_geopackage(
                Config.PATH_GEOPACKAGE_MULTILAYER_NETWORK_OUTPUT, self.osm_edges, "pytest_edges"
            )
            write_results_to_geopackage(
                Config.PATH_GEOPACKAGE_MULTILAYER_NETWORK_OUTPUT,
                self.osm_edges.dissolve(by="group"),
                "pytest_edges_with_segment_groups",
            )

    def prepare_junction_crossings(self):
        node_degree = {i: self.osm_graph.degree(i) for i in self.osm_graph.node_indices()}
        self.osm_nodes["degree"] = pd.Series(node_degree, index=self.osm_nodes.index, dtype=int)
        junctions = self.osm_nodes[self.osm_nodes["degree"] > 2]
        if len(junctions) == 0:
            logger.warning("No junctions found to consider for pipe ramming.")
            return get_empty_geodataframe(), get_empty_geodataframe()
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
        junctions["geometry"] = junctions.buffer(self.max_pipe_ramming_length_m + 1)

        if self.debug:
            out = Config.PATH_GEOPACKAGE_MULTILAYER_NETWORK_OUTPUT
            # Plot hexagons
            write_results_to_geopackage(out, cost_surface_nodes, "pytest_cost_surface_nodes")
            write_results_to_geopackage(out, cost_surface_nodes_filtered, "pytest_cost_surface_filtered")
            # Plot junctions
            write_results_to_geopackage(out, junctions, "pytest_osm_junctions")
            write_results_to_geopackage(out, self.osm_edges, "pytest_osm_streets")

        return junctions, cost_surface_nodes_filtered

    def get_crossing_for_junction(self, cost_surface_nodes_filtered, node_id, junction_node):
        # Create rectangles which simulate potential crossings.
        minx, miny, maxx, maxy = junction_node.geometry.bounds
        boxes = [shapely.box(x, miny, min(x + 1, maxx), maxy) for x in np.arange(minx, maxx, 1)]
        center_outer_point = shapely.Point(self.osm_nodes.loc[node_id].geometry.x, maxy)
        grid_rectangles = gpd.GeoDataFrame(data=boxes, columns=["geometry"], crs=Config.CRS)
        grid_rectangles["distance_to_junction_center"] = grid_rectangles.distance(self.osm_nodes.loc[node_id].geometry)

        # Check for edges which are almost 180 degrees apart, create straight crossings for those.
        adjacent_edges = self.osm_edges.loc[self.osm_graph.incident_edges(node_id)]
        adjacent_edges = adjacent_edges.clip(junction_node.geometry)
        adjacent_edges["point_a"] = adjacent_edges["geometry"].apply(lambda line: shapely.Point(line.coords[0]))
        adjacent_edges["point_b"] = adjacent_edges["geometry"].apply(lambda line: shapely.Point(line.coords[1]))
        adjacent_edges["point_inner"] = self.osm_graph.get_node_data(node_id).geometry
        adjacent_edges["point_outer"] = adjacent_edges["geometry"].apply(
            lambda line: shapely.Point(line.coords[1])
            if shapely.Point(line.coords[0]).equals(self.osm_graph.get_node_data(node_id).geometry)
            else shapely.Point(line.coords[0])
        )
        adjacent_edges["group"] = range(len(adjacent_edges))
        for idx_edge_1, idx_edge_2 in itertools.combinations(adjacent_edges.index, 2):
            angle_degree = get_angle_between_points(
                adjacent_edges.loc[idx_edge_1].point_outer,
                adjacent_edges.loc[idx_edge_2].point_outer,
                self.osm_nodes.loc[node_id].geometry,
            )
            if 170 <= angle_degree <= 190:
                # TODO take mean
                # We do not cover the scenario that three or more edges are almost 180 degrees apart.
                adjacent_edges.at[idx_edge_2, "group"] = adjacent_edges.at[idx_edge_1, "group"]
            logger.debug(
                f"Angle between edges {idx_edge_1} and {idx_edge_2} at junction {node_id}: {angle_degree:.2f} degrees."
            )

        # Get angle to the center point of the junction.
        adjacent_edges["degree_grid"] = adjacent_edges.apply(
            lambda row: get_angle_between_points(
                row["point_outer"], center_outer_point, self.osm_nodes.loc[node_id].geometry
            ),
            axis=1,
        )

        # TODO this will give problems when junctions are very close by each other, i think we better extend the direct incident edges.
        junction_edge_groups = self.osm_edges.loc[self.osm_graph.incident_edges(node_id)].group
        junction_edges = self.osm_edges[self.osm_edges["group"].isin(junction_edge_groups)]

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

        # TODO iterate over groups
        for idx_edge, row in adjacent_edges.iterrows():
            grid_copy = grid_rectangles.copy()
            grid_rotated = grid_copy.rotate(row.degree_grid, origin=self.osm_nodes.loc[node_id].geometry)
            grid_copy["geometry"] = grid_rotated
            tst = cost_surface_nodes_junction.sjoin(grid_copy, predicate="intersects", how="left")
            potential = tst.groupby(by="index_right", axis=0)["idx_street_side"].nunique()
            combinations = tst.groupby(by="index_right", axis=0)["idx_street_side"].unique()
            # TODO split combinations into seperate columns at start? Then join to gdf grid.
            potential = pd.DataFrame({"potential": potential, "combinations": combinations})
            potential = grid_copy.loc[potential[potential > 1].index]

            # get the one closest to the center point of the junction

        if self.debug:
            out = Config.PATH_GEOPACKAGE_MULTILAYER_NETWORK_OUTPUT
            write_results_to_geopackage(out, junction_node.geometry, "pytest_junction")
            write_results_to_geopackage(
                out,
                adjacent_edges[["osm_id", "length", "group", "degree_grid", "geometry"]],
                "pytest_junction_adjacent_edges",
            )
            write_results_to_geopackage(
                out,
                adjacent_edges[["osm_id", "length", "group", "point_outer"]],
                "pytest_junction_adjacent_outer_point",
            )

            write_results_to_geopackage(out, grid_rectangles, "pytest_rotation_grid")
            write_results_to_geopackage(out, grid_copy, "pytest_rotation_grid")
            write_results_to_geopackage(out, potential, "pytest_potential_crossings")

            # Plot an individual junction with its street sides and outer points.
            write_results_to_geopackage(out, junction_edges, "pytest_osm_junction_edges")
            write_results_to_geopackage(out, street_sides, "pytest_street_sides")
            write_results_to_geopackage(out, cost_surface_nodes_filtered, "pytest_cost_surface_nodes_junction")

    def get_crossings_per_segment(self):
        """
        Create perpendicular crossings for long street segments when there are no obstacles in the way.
        """
        logger.info("Finding crossings in grouped edges and nodes.")

        # Get road crossings for only long segments.
        merged_segments = self.osm_edges.dissolve(by="group")
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
        write_results_to_geopackage(Config.PATH_GEOPACKAGE_MULTILAYER_NETWORK_OUTPUT, self.osm_edges, "pytest_edges")
        write_results_to_geopackage(Config.PATH_GEOPACKAGE_MULTILAYER_NETWORK_OUTPUT, self.osm_nodes, "pytest_nodes")
