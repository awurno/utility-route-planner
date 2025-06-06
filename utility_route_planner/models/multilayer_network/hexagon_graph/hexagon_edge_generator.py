#  SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#  #
#  SPDX-License-Identifier: Apache-2.0
from typing import Iterator

import geopandas as gpd
import pandas as pd


class HexagonEdgeGenerator:
    def __init__(self, hexagonal_grid: gpd.GeoDataFrame):
        self.hexagonal_grid = hexagonal_grid

    def generate(self) -> Iterator[Iterator[tuple[int, int, float]]]:
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

    def get_neighbouring_edges(
        self, neighbour_q: pd.Series, neighbour_r: pd.Series
    ) -> Iterator[tuple[int, int, float]]:
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

        return neighbours[["node_id_source", "node_id_target", "weight"]].itertuples(index=False)
