#  SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#  #
#  SPDX-License-Identifier: Apache-2.0

import math

import geopandas as gpd
import numpy as np
import pandas as pd
import rustworkx as rx
import shapely
from geopandas import GeoDataFrame

from settings import Config
from utility_route_planner.util.timer import time_function


def get_hexagon_width_and_height(hexagon_size: float) -> tuple[float, float]:
    """
    Compute hexagon width and height, given the provided size of the hexagon. In this calculation, width and height are
    computed for a flat-top oriented hexagon.

    source: https://www.redblobgames.com/grids/hexagons/#basics

    :param hexagon_size: size of hexagon described by the inner circle of the hexagon that touches the edges
    :return: tuple consisting of two floats that represent the width and height of the hexagon
    """

    hexagon_width = 2 * hexagon_size
    hexagon_height = math.sqrt(3) * hexagon_size

    return hexagon_width, hexagon_height


@time_function
def convert_hexagon_graph_to_gdfs(
    hexagon_graph: rx.PyGraph, edges: bool = True
) -> tuple[GeoDataFrame, None] | GeoDataFrame:
    nodes_gdf = gpd.GeoDataFrame(hexagon_graph.nodes(), crs=Config.CRS)

    if edges:
        edge_keys = pd.DataFrame(hexagon_graph.edge_list(), columns=["u", "v"])
        edge_attributes = gpd.GeoDataFrame(hexagon_graph.edges())
        edges_gdf = gpd.GeoDataFrame(pd.concat([edge_keys, edge_attributes], axis=1), crs=Config.CRS)
        u_coords = nodes_gdf.loc[edges_gdf["u"]].get_coordinates().values
        v_coords = nodes_gdf.loc[edges_gdf["v"]].get_coordinates().values

        # Stack u and v coordinates on axis 1 to get correct linestring coordinate format: [[u_x, u_y], [v_x, v_y]]
        line_string_coords = np.stack([u_coords, v_coords], axis=1)
        edge_line_strings = shapely.linestrings(line_string_coords)

        edges_gdf = edges_gdf.set_geometry(edge_line_strings, crs=Config.CRS)
        return nodes_gdf, edges_gdf
    else:
        return nodes_gdf
