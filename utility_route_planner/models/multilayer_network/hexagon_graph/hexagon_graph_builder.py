# SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#
# SPDX-License-Identifier: Apache-2.0

import geopandas as gpd
import networkx as nx
import structlog

from models.multilayer_network.hexagon_graph.hexagon_edge_generator import HexagonEdgeGenerator
from utility_route_planner.models.multilayer_network.hexagon_graph.hexagon_grid_constructor import (
    HexagonalGridConstructor,
)
from settings import Config
from util.timer import time_function

logger = structlog.get_logger(__name__)


class HexagonGraphBuilder:
    def __init__(self, vectors_for_project_area: gpd.GeoDataFrame, hexagon_size: float):
        self.vectors_for_project_area = vectors_for_project_area
        self.hexagon_size = hexagon_size
        self.graph = nx.MultiGraph(crs=Config.CRS)

    @time_function
    def build_graph(self) -> nx.MultiGraph:
        grid_constructor = HexagonalGridConstructor(self.vectors_for_project_area, self.hexagon_size)
        hexagonal_grid = grid_constructor.construct_grid()

        nodes = hexagonal_grid[["suitability_value", "axial_q", "axial_r", "x", "y"]].to_dict(orient="index").items()
        self.graph.add_nodes_from(nodes)

        hexagon_edge_generator = HexagonEdgeGenerator(hexagonal_grid)
        for edges in hexagon_edge_generator.generate():
            self.graph.add_weighted_edges_from(edges)

        return self.graph
