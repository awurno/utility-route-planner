#  SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#  #
#  SPDX-License-Identifier: Apache-2.0

import math

import geopandas as gpd
import numpy as np
import rustworkx as rx
import shapely

from settings import Config
from utility_route_planner.util.timer import time_function


def get_hexagon_width_and_height(hexagon_size: float) -> tuple[float, float]:
    """
    Compute hexagon width and height, given the provided size of the hexagon. In this calculation, width and height are
    computed for a flat-top oriented hexagon.

    source: https://www.redblobgames.com/grids/hexagons/#basics

    :param hexagon_size: size of hexagon described by the inner circle of the hexagon that touches the edges
    """

    hexagon_width = 2 * hexagon_size
    hexagon_height = math.sqrt(3) * hexagon_size

    return hexagon_width, hexagon_height


@time_function
def convert_hexagon_graph_to_gdfs(hexagon_graph: rx.PyGraph) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    nodes = hexagon_graph.nodes()

    nodes_gdf = gpd.GeoDataFrame.from_dict(dict(nodes), orient="index")
    nodes_gdf = nodes_gdf.set_geometry(gpd.points_from_xy(nodes_gdf["x"], nodes_gdf["y"], crs=Config.CRS))

    edges_gdf = gpd.GeoDataFrame(hexagon_graph.weighted_edge_list(), columns=["u", "v", "weight"])
    u_coords = nodes_gdf.loc[edges_gdf["u"], ["x", "y"]].values
    v_coords = nodes_gdf.loc[edges_gdf["v"], ["x", "y"]].values

    # Stack u and v coordinates on axis 1 to get correct linestring coordinate format: [[u_x, u_y], [v_x, v_y]]
    line_string_coords = np.stack([u_coords, v_coords], axis=1)
    edge_line_strings = shapely.linestrings(line_string_coords)

    edges_gdf = edges_gdf.set_geometry(edge_line_strings, crs=Config.CRS)

    return nodes_gdf, edges_gdf
