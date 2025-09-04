# SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#
# SPDX-License-Identifier: Apache-2.0

import pytest
import geopandas as gpd
import shapely

from settings import Config
from utility_route_planner.util.write import reset_geopackage


@pytest.fixture
def setup_mcda_lcpa_testing(monkeypatch):
    reset_geopackage(Config.PATH_GEOPACKAGE_LCPA_OUTPUT)
    reset_geopackage(Config.PATH_GEOPACKAGE_MCDA_OUTPUT, truncate=False)
    monkeypatch.setattr(Config, "DEBUG", True)


@pytest.fixture
def single_criterion_vectors() -> gpd.GeoDataFrame:
    def __vectors(max_value: int, min_value: int, no_data: int) -> gpd.GeoDataFrame:
        return gpd.GeoDataFrame(
            data=[
                # These layers all overlap each other.
                [1, shapely.Polygon([[174872, 451093], [174870, 451082], [174876, 451081], [174872, 451093]])],
                [10, shapely.Polygon([[174872, 451093], [174870, 451082], [174876, 451081], [174872, 451093]])],
                [10, shapely.Polygon([[174872, 451093], [174870, 451082], [174876, 451081], [174872, 451093]])],
                [1, shapely.Polygon([[174872, 451093], [174870, 451082], [174876, 451081], [174872, 451093]])],
                # One larger partly overlapping polygon with a unique value.
                [
                    5,
                    shapely.Polygon([[174872, 451093], [174870, 451082], [174876, 451081], [174872, 451093]]).buffer(
                        50
                    ),
                ],
                # These values should be reset to the min/max of the intermediate raster values
                [
                    min_value - 1000,
                    shapely.Polygon([[175091, 450919], [175091, 450911], [175105, 450911], [175091, 450919]]),
                ],
                [
                    max_value + 1000,
                    shapely.Polygon([[175012, 450920], [175011, 450907], [175019, 450906], [175012, 450920]]),
                ],
                # This value is equal to no-data and should be reset to a "safe" value (+1 it)
                [no_data, shapely.Polygon([[174917, 450965], [174937, 450962], [174916, 450952], [174917, 450965]])],
            ],
            geometry="geometry",
            crs=Config.CRS,
            columns=["suitability_value", "geometry"],
        )

    return __vectors
