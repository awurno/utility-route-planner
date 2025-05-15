# SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#
# SPDX-License-Identifier: Apache-2.0

import geopandas as gpd
import numpy as np
import pandas as pd

from utility_route_planner.models.multilayer_network.hexagon_graph.hexagon_utils import get_hexagon_width_and_height
from settings import Config


class HexagonalGridConstructor:
    def __init__(self, vectors_for_project_area: gpd.GeoDataFrame, hexagon_size: float):
        self.vectors_for_project_area = vectors_for_project_area
        self.hexagon_size = hexagon_size
        self.hexagon_width, self.hexagon_height = get_hexagon_width_and_height(hexagon_size)

    def construct_grid(self) -> gpd.GeoDataFrame:
        hexagonal_grid_bounding_box = self.construct_hexagonal_grid_for_bounding_box()
        hexagonal_grid = self.get_hexagonal_grid_for_project_area(hexagonal_grid_bounding_box)

        hexagonal_grid["axial_q"], hexagonal_grid["axial_r"] = self.convert_cartesian_coordinates_to_axial(
            hexagonal_grid, size=self.hexagon_size
        )
        hexagonal_grid = gpd.GeoDataFrame(
            pd.concat([hexagonal_grid, hexagonal_grid.get_coordinates()], axis=1), geometry="geometry"
        )
        return hexagonal_grid

    def construct_hexagonal_grid_for_bounding_box(self) -> gpd.GeoDataFrame:
        """
        Given the bounding box of the project area, create a hexagonal grid in flat-top orientation.

        :return: GeoDataFrame where each point represents a location on the grid
        """
        x_min, y_min, x_max, y_max = self.vectors_for_project_area.total_bounds

        # 0.75 is used to correctly set the offset of the x coordinate of the center, as each hexagon is partially covered
        # by the surrounding tiles
        x_coordinates = np.arange(x_min, x_max, self.hexagon_width * 0.75)
        y_coordinates = np.arange(y_min, y_max, self.hexagon_height)
        x_matrix, y_matrix = np.meshgrid(x_coordinates, y_coordinates)

        # Every odd column must be offset by half of the hexagon height to properly determine the vertical
        # position of the hexagon.
        y_matrix[:, ::2] += self.hexagon_height / 2

        bounding_box_grid = gpd.GeoDataFrame(
            geometry=gpd.points_from_xy(x_matrix.ravel(), y_matrix.ravel()), crs=Config.CRS
        )
        return bounding_box_grid.reset_index(names="node_id")

    def get_hexagonal_grid_for_project_area(self, bounding_box_grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Given the hexagonal grid for the bounding box of the project area, remove all points that are not within any
        vector polygon that is provided as input. In addition, the suitability value for each point on the grid is
        computed given the vector the point intersects with. In case a point intersects multiple polygons the
        suitability values are summed for now.

        :return: GeoDataFrame containing all points within the project area in combination with aggregated suitability
        values for every point.
        """
        points_within_project_area = gpd.sjoin(
            bounding_box_grid,
            self.vectors_for_project_area[["suitability_value", "geometry"]],
            predicate="within",
            how="inner",
        ).set_index("node_id")

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

        return hexagon_points

    @staticmethod
    def convert_cartesian_coordinates_to_axial(
        hexagon_center_points: gpd.GeoDataFrame, size: float
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        To efficiently determine neighbours to construct a hexagonal graph later on, convert all cartesian coordinates
        to axial coordinates.

        Used algorithms as provided by:
        - coordinate to hex: https://www.redblobgames.com/grids/hexagons/#pixel-to-hex
        - rounding hex correctly: https://observablehq.com/@jrus/hexround (via redblobgames)

        :return: tuple containing q- and r-values as integers in numpy ndarray format
        """
        x, y = np.split(hexagon_center_points.get_coordinates().values, 2, axis=1)

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
