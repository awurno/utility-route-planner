import math

import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
import shapely

from settings import Config
from util.write import write_results_to_geopackage


class HexagonGraphBuilder:
    def __init__(self, vectors_for_project_area: gpd.GeoDataFrame):
        self.vectors_for_project_area = vectors_for_project_area

    def build(self):
        graph, max_node = self.build_graph()
        potential_ms_route = self.compute_route(graph, source_node=0, target_node=max_node - 1)

        # Write debug for QGIS
        nodes_gdf, edges_gdf = ox.convert.graph_to_gdfs(graph)
        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, self.vectors_for_project_area, "project_area", overwrite=True
        )
        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, nodes_gdf, "vector_points", overwrite=True
        )
        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, edges_gdf, "vector_edges", overwrite=True
        )
        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, potential_ms_route, "ms_route", overwrite=True
        )

    def build_graph(self) -> nx.MultiGraph:
        # Create a grid of all points within the geometry boundaries
        x_min, y_min, x_max, y_max = self.vectors_for_project_area.total_bounds

        # Compute hexagon height and width for determining centerpoints. Here, we use the flat-top orientation hexagons
        # TODO: should we divide the hexagon width / 2 as each hexagon size is now 2 * cell size?
        hexagon_size = 1

        hexagon_width = 2 * hexagon_size
        hexagon_height = math.sqrt(3) * hexagon_size

        # 0.75 is used to correctly set the offset of the x coordinate of the center, as each hexagon is partially covered
        # by the surrounding tiles
        x_coordinates = np.arange(x_min, x_max, hexagon_width * 0.75)
        y_coordinates = np.arange(y_min, y_max, hexagon_height)

        # For each coordinate, check if within the geometry. If this is the case, add node to the graph
        # TODO: maybe it's faster to create the grid at once based on the bounding box and then remove all points that
        # do not intersect instead of checking for every point
        node_id = 0
        graph = nx.MultiGraph(crs=Config.CRS)
        for x in x_coordinates:
            for y in y_coordinates:
                # Every odd column must be offset by half of the hexagon height to properly determine the vertical
                # position of the hexagon. A column is odd when the distance between the x coordinate and the min_x
                # can be divided by hexagon_width * 0.75
                if ((x - x_min) / (hexagon_width * 0.75)) % 2:
                    y += hexagon_height / 2

                # Check whether the coordinate intersects with at least one geometry vector. If this is the case, add
                # a node to the graph for these coordinates
                intersected_geometries = self.vectors_for_project_area.geometry.contains(shapely.Point(x, y))
                if any(intersected_geometries):
                    instersected_values = self.vectors_for_project_area.loc[
                        intersected_geometries, ["suitability_value", "function"]
                    ]

                    # For now, simply sum suitability values of all intersection points and add it to the graph node
                    suitability_value = instersected_values["suitability_value"].sum()
                    function_label = instersected_values["function"].str.cat(sep=",")
                    graph.add_node(node_id, suitability_value=suitability_value, function=function_label, x=x, y=y)
                    node_id += 1

        for center_node, center_data in graph.nodes(data=True):
            x, y = center_data["x"], center_data["y"]
            neighbour_coordinates = [
                (x, y + hexagon_height),  # Connect center to vertical neighbours
                (
                    # Connect center to top- and bottom-right neighbours
                    x + hexagon_width * 0.75,
                    y + hexagon_height / 2,
                ),
                (x - hexagon_width * 0.75, y + hexagon_height / 2),  # Connect center to top- and bottom-left neighbours
            ]

            # Given the neighbour coordinates, iterate over all nodes in the graph to find the nodes that are close to
            # the calculated coordinates. These nodes are considered as neighbours.
            # TODO: this part is very slow and must be optimized. Maybe we can use axial coordinates instead of
            #  determining neighbours spatially?
            for neighbour_x, neighbour_y in neighbour_coordinates:
                for neighbour_node, neighbor_data in graph.nodes(data=True):
                    if math.isclose(neighbor_data["x"], neighbour_x, abs_tol=1e-2) and math.isclose(
                        neighbor_data["y"], neighbour_y, abs_tol=1e-2
                    ):
                        edge_weight = (center_data["suitability_value"] + neighbor_data["suitability_value"]) / 2
                        graph.add_edge(center_node, neighbour_node, weight=edge_weight)
                        break

        return graph, node_id

    def compute_route(self, graph: nx.MultiGraph, source_node: int, target_node: int) -> shapely.LineString:
        # Compute the shortest path to simulate the potential MS-route calculation. Use the first node-id as start, and
        # final node id as target. Edges with a lower weight are more favourable.
        shortest_path = nx.shortest_path(graph, source=source_node, target=target_node, weight="weight")
        shortest_path_points = [
            shapely.Point(graph.nodes[node_id]["x"], graph.nodes[node_id]["y"]) for node_id in shortest_path
        ]
        shortest_path_line_string = shapely.LineString(shortest_path_points)

        return shortest_path_line_string
