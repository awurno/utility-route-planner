import math

import geopandas as gpd
import networkx as nx
import numpy as np
import shapely

from settings import Config
from util.timer import time_function
from util.write import write_results_to_geopackage


class HexagonGraphBuilder:
    def __init__(self, vectors_for_project_area: gpd.GeoDataFrame):
        self.vectors_for_project_area = vectors_for_project_area

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

    def convert_coordinates_to_axial(self, x: float, y: float, size: float):
        # Convert the x and y coordinate to axial coordinates
        q = (2 / 3 * x) / size
        r = (-1 / 3 * x + math.sqrt(3) / 3 * y) / size

        # Convert to cube coordinates
        x = q
        y = r
        z = -x - y

        # Round to nearest integer
        rx, ry, rz = round(x), round(y), round(z)

        # Find the largest rounding error
        x_diff = abs(rx - x)
        y_diff = abs(ry - y)
        z_diff = abs(rz - z)

        # Adjust the coordinate with the largest error to maintain x + y + z = 0
        if x_diff > y_diff and x_diff > z_diff:
            rx = -ry - rz
        elif y_diff > z_diff:
            ry = -rx - rz

        # Axial coordinates are (q = x, r = y)
        return (rx, ry)

    @time_function
    def build_graph(self) -> nx.MultiGraph:
        # Create a grid of all points within the geometry boundaries
        x_min, y_min, x_max, y_max = self.vectors_for_project_area.total_bounds

        # Compute hexagon height and width for determining centerpoints. Here, we use the flat-top orientation hexagons
        # TODO: should we divide the hexagon width / 2 as each hexagon size is now 2 * cell size?
        hexagon_size = 0.5

        hexagon_width = 2 * hexagon_size
        hexagon_height = math.sqrt(3) * hexagon_size

        # 0.75 is used to correctly set the offset of the x coordinate of the center, as each hexagon is partially covered
        # by the surrounding tiles
        x_coordinates = np.arange(x_min, x_max, hexagon_width * 0.75)
        y_coordinates = np.arange(y_min, y_max, hexagon_height)

        # Create a grid given the computed x and y coordinates boundaries
        x_matrix, y_matrix = np.meshgrid(x_coordinates, y_coordinates)

        # Every odd column must be offset by half of the hexagon height to properly determine the vertical
        # position of the hexagon.
        y_matrix[:, ::2] += hexagon_height / 2

        # Combine both matrices to construct shapely Points. Check for every point whether it is within at least one
        # project area vector
        matrix_points = [shapely.Point(x, y) for x, y in zip(x_matrix.ravel(), y_matrix.ravel())]
        mask_outside_project_area = np.array(
            [self.vectors_for_project_area.geometry.contains(point).any() for point in matrix_points]
        )

        # Use masked array to filter out all points outside the project area
        mask_outside_project_area = mask_outside_project_area.reshape(x_matrix.shape)
        x_matrix_masked = np.ma.masked_array(x_matrix, mask=~mask_outside_project_area)
        y_matrix_masked = np.ma.masked_array(y_matrix, mask=~mask_outside_project_area)
        points_within_polygon = [
            shapely.Point(x, y) for x, y in zip(x_matrix_masked.compressed(), y_matrix_masked.compressed())
        ]

        points_gdf = gpd.GeoDataFrame(geometry=points_within_polygon, crs=Config.CRS)
        points_gdf = points_gdf.reset_index(names="node_id")

        # Get suitability value for reach point. Aggregate, as a point can intersect with multiple vectors. For now
        # suitability values are simply summed. First geometry is always used, as it is always the same for an equal
        # node id
        suitability_value_gdf = points_gdf.sjoin_nearest(
            self.vectors_for_project_area[["suitability_value", "geometry"]]
        )
        aggregated_suitability_values = gpd.GeoDataFrame(
            suitability_value_gdf.groupby("node_id")
            .agg({"suitability_value": "sum", "geometry": "first"})
            .reset_index(),
            crs=Config.CRS,
        )

        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, aggregated_suitability_values, "points_series", overwrite=True
        )

        # For each coordinate, check if within the geometry. If this is the case, add node to the graph
        # TODO: maybe it's faster to create the grid at once based on the bounding box and then remove all points that
        # do not intersect instead of checking for every point
        # node_id = 0
        # graph = nx.MultiGraph(crs=Config.CRS)
        # axial_nodes = {}
        # for x in x_coordinates:
        #     for y in y_coordinates:
        #         # Every odd column must be offset by half of the hexagon height to properly determine the vertical
        #         # position of the hexagon. A column is odd when the distance between the x coordinate and the min_x
        #         # can be divided by hexagon_width * 0.75
        #         if ((x - x_min) / (hexagon_width * 0.75)) % 2:
        #             y += hexagon_height / 2
        # #
        #         # Check whether the coordinate intersects with at least one geometry vector. If this is the case, add
        #         # a node to the graph for these coordinates
        #         intersected_geometries = self.vectors_for_project_area.geometry.contains(shapely.Point(x, y))
        #         if any(intersected_geometries):
        #             instersected_values = self.vectors_for_project_area.loc[
        #                 intersected_geometries, ["suitability_value", "function"]
        #             ]
        #
        #             # Convert positions to axial coordinates for determining neighbours later on
        #             # axial_q, axial_r = self.convert_coordinates_to_axial(x, y, hexagon_size)
        #             # axial_nodes[(axial_q, axial_r)] = node_id
        #
        #             # For now, simply sum suitability values of all intersection points and add it to the graph node
        #             # suitability_value = instersected_values["suitability_value"].sum()
        #             # function_label = instersected_values["function"].str.cat(sep=",")
        #             graph.add_node(
        #                 node_id,
        #                 # suitability_value=suitability_value,
        #                 # function=function_label,
        #                 x=x,
        #                 y=y,
        #                 # axial_q=axial_q,
        #                 # axial_r=axial_r,
        #             )
        #             node_id += 1

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

    def compute_route(self, graph: nx.MultiGraph, source_node: int, target_node: int) -> shapely.LineString:
        # Compute the shortest path to simulate the potential MS-route calculation. Use the first node-id as start, and
        # final node id as target. Edges with a lower weight are more favourable.
        shortest_path = nx.shortest_path(graph, source=source_node, target=target_node, weight="weight")
        shortest_path_points = [
            shapely.Point(graph.nodes[node_id]["x"], graph.nodes[node_id]["y"]) for node_id in shortest_path
        ]
        shortest_path_line_string = shapely.LineString(shortest_path_points)

        return shortest_path_line_string
