import math

import geopandas as gpd
import networkx as nx
import osmnx as ox
import numpy as np
import pandas as pd
import shapely
import structlog

from settings import Config
from util.timer import time_function
from util.write import write_results_to_geopackage

logger = structlog.get_logger(__name__)


class HexagonGraphBuilder:
    def __init__(self, vectors_for_project_area: gpd.GeoDataFrame):
        self.vectors_for_project_area = vectors_for_project_area
        self.hexagon_size = 0.5  # TODO pass as param
        self.graph = nx.MultiGraph(crs=Config.CRS)

    def build(self):
        self.build_graph()
        # potential_ms_route = self.compute_route(graph, source_node=0, target_node=max_node - 1)

        # Write debug for QGIS
        # nodes_gdf, edges_gdf = ox.convert.graph_to_gdfs(graph)
        # write_results_to_geopackage(
        #     Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, self.vectors_for_project_area, "project_area", overwrite=True
        # )
        # write_results_to_geopackage(
        #     Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, nodes_gdf, "vector_points", overwrite=True
        # )
        # write_results_to_geopackage(
        #     Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, edges_gdf, "vector_edges", overwrite=True
        # )
        # write_results_to_geopackage(
        #     Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, potential_ms_route, "ms_route", overwrite=True
        # )

    def convert_coordinates_to_axial(self, x, y, size: float):
        """
        Used algorithms as provided by:
        - coordinate to hex: https://www.redblobgames.com/grids/hexagons/#pixel-to-hex
        - rounding hex correctly: https://observablehq.com/@jrus/hexround (via redblobgames)
        """
        # Convert x- and y-coordinates to axial
        q = (2 / 3 * x) / size
        r = (-1 / 3 * x + np.sqrt(3) / 3 * y) / size

        # Convert coordinates to integers and correct rounding errors
        xgrid = np.round(q).astype(np.int32)
        ygrid = np.round(r).astype(np.int32)

        q_diff = q - xgrid
        r_diff = r - ygrid

        mask = np.abs(q_diff) > np.abs(r_diff)
        xgrid[mask] = xgrid[mask] + np.round(q_diff[mask] + 0.5 * r_diff[mask])
        ygrid[~mask] = ygrid[~mask] + np.round(r_diff[~mask] + 0.5 * q_diff[~mask])

        return xgrid, ygrid

    @time_function
    def build_graph(self) -> nx.MultiGraph:
        # Compute hexagon height and width for determining centerpoints. Here, we use the flat-top orientation hexagons
        hexagon_width = 2 * self.hexagon_size
        hexagon_height = math.sqrt(3) * self.hexagon_size
        hexagon_points = self.determine_hexagon_center_points(hexagon_width, hexagon_height)
        hexagon_points = gpd.GeoDataFrame(
            pd.concat([hexagon_points, hexagon_points.get_coordinates()], axis=1), geometry="geometry"
        )

        nodes = hexagon_points[["axial_q", "axial_r", "x", "y"]].to_dict(orient="index").items()
        self.graph.add_nodes_from(nodes)
        self.determine_neighbours(hexagon_points)

        nodes_gdf, edges_gdf = ox.convert.graph_to_gdfs(self.graph)
        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, nodes_gdf, "graph_nodes", overwrite=True
        )
        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, edges_gdf, "graph_edges", overwrite=True
        )

        return self.graph

        # edges = set()
        # for (q, r), source_node in axial_nodes.items():
        #     top = (q, r - 1)
        #     top_left = (q - 1, r)
        #     top_right = (q + 1, r - 1)
        #     bottom_left = (q - 1, r + 1)
        #     bottom_right = (q + 1, r)
        #     bottom = (q, r + 1)

        # neighbour_positions = [top, top_left, top_right, bottom_left, bottom_right, bottom]
        # neighbour_edges = {(source_node, axial_nodes[n_q, n_r]) for (n_q, n_r) in neighbour_positions if (n_q, n_r) in axial_nodes}
        #     edges = edges.union(neighbour_edges)
        #
        # graph.add_edges_from(edges)

        # for dq, dr in [top, top_left, top_right, bottom_left, bottom_right, bottom]:
        #     if (dq, dr) in axial_nodes:
        #         source_node = axial_nodes[(q, r)]
        #         neighbour_node = axial_nodes[(dq, dr)]
        #         graph.add_edge(source_node, neighbour_node)

        #     pass
        #
        # for center_node, center_data in graph.nodes(data=True):
        #     x, y = center_data["x"], center_data["y"]
        #     neighbour_coordinates = [
        #         (x, y + hexagon_height),  # Connect center to vertical neighbours
        #         (
        #             # Connect center to top- and bottom-right neighbours
        #             x + hexagon_width * 0.75,
        #             y + hexagon_height / 2,
        #         ),
        #         (x - hexagon_width * 0.75, y + hexagon_height / 2),  # Connect center to top- and bottom-left neighbours
        #     ]
        #
        #     # Given the neighbour coordinates, iterate over all nodes in the graph to find the nodes that are close to
        #     # the calculated coordinates. These nodes are considered as neighbours.
        #     # TODO: this part is very slow and must be optimized. Maybe we can use axial coordinates instead of
        #     #  determining neighbours spatially?
        #     for neighbour_x, neighbour_y in neighbour_coordinates:
        #         for neighbour_node, neighbor_data in graph.nodes(data=True):
        #             if math.isclose(neighbor_data["x"], neighbour_x, abs_tol=1e-2) and math.isclose(
        #                 neighbor_data["y"], neighbour_y, abs_tol=1e-2
        #             ):
        #                 edge_weight = (center_data["suitability_value"] + neighbor_data["suitability_value"]) / 2
        #                 graph.add_edge(center_node, neighbour_node, weight=edge_weight)
        #                 break

        # return graph, node_id

    def determine_hexagon_center_points(self, hexagon_width: float, hexagon_height: float) -> gpd.GeoDataFrame:
        bounding_box_grid = self.get_grid_for_bounding_box(hexagon_width, hexagon_height)

        # For each point in the generated matrix, check whether it is within the project area using spatial join.
        points_within_project_area = gpd.sjoin(
            bounding_box_grid,
            self.vectors_for_project_area[["suitability_value", "geometry"]],
            predicate="within",
            how="inner",
        ).set_index("node_id")

        # Sum suitability values in case multiple vectors overlap
        aggregated_suitability_values = points_within_project_area.groupby("node_id").agg({"suitability_value": "sum"})

        # Join location afterwards, as this is faster than picking the first one within the aggregation step
        hexagon_points = gpd.GeoDataFrame(
            aggregated_suitability_values.join(
                points_within_project_area["geometry"], how="left", lsuffix="l", rsuffix="r"
            ),
            geometry="geometry",
        )
        # Remove duplicate points, as a point could have joined multiple vector which results in duplicate rows within
        # the right dataframe.
        hexagon_points = hexagon_points[~hexagon_points.index.duplicated()]

        x, y = np.split(hexagon_points.get_coordinates().values, 2, axis=1)
        hexagon_points["axial_q"], hexagon_points["axial_r"] = self.convert_coordinates_to_axial(
            x.flatten(), y.flatten(), size=self.hexagon_size
        )
        return hexagon_points

    def get_grid_for_bounding_box(self, hexagon_width: float, hexagon_height: float) -> gpd.GeoDataFrame:
        # Create a grid of all points within the geometry boundaries
        x_min, y_min, x_max, y_max = self.vectors_for_project_area.total_bounds

        # 0.75 is used to correctly set the offset of the x coordinate of the center, as each hexagon is partially covered
        # by the surrounding tiles
        x_coordinates = np.arange(x_min, x_max, hexagon_width * 0.75)
        y_coordinates = np.arange(y_min, y_max, hexagon_height)
        x_matrix, y_matrix = np.meshgrid(x_coordinates, y_coordinates)

        # Every odd column must be offset by half of the hexagon height to properly determine the vertical
        # position of the hexagon.
        y_matrix[:, ::2] += hexagon_height / 2

        # Combine both matrices to construct shapely Points. Check for every point whether it is within at least one
        # project area vector
        bounding_box_grid = gpd.GeoDataFrame(
            geometry=gpd.points_from_xy(x_matrix.ravel(), y_matrix.ravel()), crs=Config.CRS
        )
        return bounding_box_grid.reset_index(names="node_id")

    def determine_neighbours(self, hexagon_points: gpd.GeoDataFrame):
        q, r = hexagon_points["axial_q"], hexagon_points["axial_r"]

        top_q, top_r = q, r + 1
        top_left_q, top_left_r = q - 1, r
        top_right_q, top_right_r = q + 1, r
        bottom_left_q, bottom_left_r = q - 1, r
        bottom_right_q, bottom_right_r = q + 1, r - 1
        bottom_q, bottom_r = q, r - 1

        for neighbour_q, neighbour_r in [
            (top_q, top_r),
            (top_left_q, top_left_r),
            (top_right_q, top_right_r),
            (bottom_left_q, bottom_left_r),
            (bottom_right_q, bottom_right_r),
            (bottom_q, bottom_r),
        ]:
            neighbour_candidates = pd.concat([neighbour_q, neighbour_r], axis=1)

            # Filter out not-existing neighbours and add the edges to the graph
            top_neighbours = pd.merge(
                neighbour_candidates.reset_index(names="node_id_source"),
                hexagon_points[["axial_q", "axial_r"]].reset_index(names="node_id_target"),
                how="inner",
                on=["axial_q", "axial_r"],
            )
            edges = top_neighbours[["node_id_source", "node_id_target"]].itertuples(index=False)
            self.graph.add_edges_from(edges)

        # top_left_q, top_left_r = q - 1, r
        # top_right_q, top_right_q = q + 1, r - 1
        # bottom_left_q, bottom_left_r = q - 1, r + 1
        # bottom_right_q, bottom_right_r = q + 1, r
        # bottom_q, bottom_r = q, r + 1

    def compute_route(self, graph: nx.MultiGraph, source_node: int, target_node: int) -> shapely.LineString:
        # Compute the shortest path to simulate the potential MS-route calculation. Use the first node-id as start, and
        # final node id as target. Edges with a lower weight are more favourable.
        shortest_path = nx.shortest_path(graph, source=source_node, target=target_node, weight="weight")
        shortest_path_points = [
            shapely.Point(graph.nodes[node_id]["x"], graph.nodes[node_id]["y"]) for node_id in shortest_path
        ]
        shortest_path_line_string = shapely.LineString(shortest_path_points)

        return shortest_path_line_string
