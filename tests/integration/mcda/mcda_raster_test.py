import pytest
import geopandas as gpd
import rasterio
import rasterio.sample
import shapely
import numpy as np

from settings import Config
from src.models.mcda.exceptions import RasterCellSizeTooSmall
from src.models.mcda.mcda_rasterizing import rasterize_vector_data


def test_rasterize_vector_data_cell_size_error():
    with pytest.raises(RasterCellSizeTooSmall):
        project_area = gpd.read_file(Config.PATH_PROJECT_AREA_EDE_COMPONISTENBUURT).iloc[0].geometry
        rasterize_vector_data("temp", project_area, gpd.GeoDataFrame(), 500000)


def test_rasterize_different_order():
    gdf = gpd.GeoDataFrame(
        data=[
            # These layers all overlap each other.
            [1, shapely.Polygon([[174872, 451093], [174870, 451082], [174876, 451081], [174872, 451093]])],
            [10, shapely.Polygon([[174872, 451093], [174870, 451082], [174876, 451081], [174872, 451093]])],
            [10, shapely.Polygon([[174872, 451093], [174870, 451082], [174876, 451081], [174872, 451093]])],
            [1, shapely.Polygon([[174872, 451093], [174870, 451082], [174876, 451081], [174872, 451093]])],
            # One larger partly overlapping polygon with a unique value.
            [5, shapely.Polygon([[174872, 451093], [174870, 451082], [174876, 451081], [174872, 451093]]).buffer(50)],
        ],
        geometry="geometry",
        crs=Config.CRS,
        columns=["suitability_value", "geometry"],
    )
    sort_asc = gdf.sort_values("suitability_value", ascending=True)
    sort_desc = gdf.sort_values("suitability_value", ascending=False)

    gdfs_to_rasterize = [gdf, sort_desc, sort_asc]
    for gdf in gdfs_to_rasterize:
        rasterized_gdf = rasterize_vector_data(
            "pytest_",
            "test_rasterize",
            gpd.read_file(Config.PATH_PROJECT_AREA_EDE_COMPONISTENBUURT).iloc[0].geometry,
            gdf,
            0.5,
        )
        with rasterio.open(rasterized_gdf, "r") as out:
            result = out.read(1)
            unique_values = np.unique(result)
            assert set(unique_values) == {0, 5, 10}
            # Check that the overlapping part has the highest value
            values = list(
                rasterio.sample.sample_gen(
                    out, [[174872.396, 451084.460], [174868.573, 451086.020], [174985.83, 451101.57], [0, 0]]
                )
            )
            assert values[0][0] == 10  # middle of the overlapping part
            assert values[1][0] == 5  # just next to the polygon
            assert values[2][0] == 0  # outside the polygons
            assert values[3][0] == 0  # outside the project area
