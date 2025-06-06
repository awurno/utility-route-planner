#  SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#  #
#  SPDX-License-Identifier: Apache-2.0
from typing import Iterator

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from settings import Config


class HexagonEdgeGenerator:
    def __init__(self, hexagonal_grid: gpd.GeoDataFrame):
        self.hexagonal_grid = hexagonal_grid

    def generate(self) -> Iterator[gpd.GeoDataFrame]:
        q, r = self.hexagonal_grid["axial_q"], self.hexagonal_grid["axial_r"]

        vertical_q, vertical_r = q, r + 1
        left_q, left_r = q - 1, r
        right_q, right_r = q + 1, r - 1

        for neighbour_q, neighbour_r in [
            (vertical_q, vertical_r),
            (left_q, left_r),
            (right_q, right_r),
        ]:
            yield self.get_neighbouring_edges(neighbour_q, neighbour_r)

    def get_neighbouring_edges(self, neighbour_q: pd.Series, neighbour_r: pd.Series) -> gpd.GeoDataFrame:
        neighbour_candidates = pd.concat([neighbour_q, neighbour_r], axis=1)

        neighbours = pd.merge(
            neighbour_candidates.reset_index(names="node_id_source"),
            self.hexagonal_grid[["axial_q", "axial_r"]].reset_index(names="node_id_target"),
            how="inner",
            on=["axial_q", "axial_r"],
        )

        neighbours["weight"] = (
            self.hexagonal_grid.loc[neighbours["node_id_source"], "suitability_value"].values
            + self.hexagonal_grid.loc[neighbours["node_id_target"], "suitability_value"].values
        ) / 2

        line_string_coords = np.stack(
            [
                self.hexagonal_grid.loc[neighbours["node_id_source"], ["x", "y"]].values,
                self.hexagonal_grid.loc[neighbours["node_id_target"], ["x", "y"]].values,
            ],
            axis=1,
        )
        edge_line_strings = shapely.linestrings(line_string_coords)
        neighbours = gpd.GeoDataFrame(neighbours, geometry=edge_line_strings, crs=Config.CRS)
        neighbours["length"] = neighbours.geometry.length

        return neighbours[["node_id_source", "node_id_target", "length", "geometry", "weight"]]
