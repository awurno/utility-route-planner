# SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#
# SPDX-License-Identifier: Apache-2.0

import geopandas as gpd
import networkx as nx
import pandas as pd
import structlog

from utility_route_planner.models.multilayer_network.hexagon_graph.hexagon_center_point_constructor import (
    HexagonalGridConstructor,
)
from settings import Config
from util.timer import time_function

logger = structlog.get_logger(__name__)


class HexagonGraphBuilder:
    def __init__(self, vectors_for_project_area: gpd.GeoDataFrame, hexagon_size: float):
        self.center_point_constructor = HexagonalGridConstructor(vectors_for_project_area, hexagon_size)
        self.graph = nx.MultiGraph(crs=Config.CRS)

    @time_function
    def build_graph(self) -> nx.MultiGraph:
        hexagon_center_points = self.center_point_constructor.construct_grid()

        nodes = (
            hexagon_center_points[["suitability_value", "axial_q", "axial_r", "x", "y"]].to_dict(orient="index").items()
        )
        self.graph.add_nodes_from(nodes)
        self.add_hexagons_as_edges_to_graph(hexagon_center_points)

        return self.graph

    @time_function
    def add_hexagons_as_edges_to_graph(self, hexagon_points: gpd.GeoDataFrame):
        q, r = hexagon_points["axial_q"], hexagon_points["axial_r"]

        vertical_q, vertical_r = q, r + 1
        left_q, left_r = q - 1, r
        right_q, right_r = q + 1, r - 1

        for neighbour_q, neighbour_r in [
            (vertical_q, vertical_r),
            (left_q, left_r),
            (right_q, right_r),
        ]:
            neighbours = self.get_neighbouring_edges(hexagon_points, neighbour_q, neighbour_r)
            edges = neighbours[["node_id_source", "node_id_target", "weight"]].itertuples(index=False)
            self.graph.add_weighted_edges_from(edges)

    def get_neighbouring_edges(self, hexagon_points: pd.DataFrame, neighbour_q: pd.Series, neighbour_r: pd.Series):
        neighbour_candidates = pd.concat([neighbour_q, neighbour_r], axis=1)

        # Filter out not-existing neighbours and add the edges to the graph
        neighbours = pd.merge(
            neighbour_candidates.reset_index(names="node_id_source"),
            hexagon_points[["axial_q", "axial_r"]].reset_index(names="node_id_target"),
            how="inner",
            on=["axial_q", "axial_r"],
        )

        neighbours["weight"] = (
            hexagon_points.loc[neighbours["node_id_source"], "suitability_value"].values
            + hexagon_points.loc[neighbours["node_id_target"], "suitability_value"].values
        ) / 2

        return neighbours
