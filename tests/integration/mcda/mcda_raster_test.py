import pytest
import geopandas as gpd
import rasterio
import rasterio.sample
import shapely
import numpy as np

from settings import Config
from src.models.mcda.exceptions import RasterCellSizeTooSmall, InvalidSuitabilityRasterInput, InvalidGroupValue
from src.models.mcda.mcda_rasterizing import rasterize_vector_data, sum_rasters


def test_rasterize_vector_data_cell_size_error():
    with pytest.raises(RasterCellSizeTooSmall):
        project_area = gpd.read_file(Config.PATH_PROJECT_AREA_EDE_COMPONISTENBUURT).iloc[0].geometry
        rasterize_vector_data("temp", project_area, gpd.GeoDataFrame(), 500000)


def test_rasterize_single_criterion(monkeypatch):
    max_value = 100
    min_value = -120
    monkeypatch.setattr(Config, "INTERMEDIATE_RASTER_VALUE_LIMIT_LOWER", min_value)
    monkeypatch.setattr(Config, "INTERMEDIATE_RASTER_VALUE_LIMIT_UPPER", max_value)
    gdf = gpd.GeoDataFrame(
        data=[
            # These layers all overlap each other.
            [1, shapely.Polygon([[174872, 451093], [174870, 451082], [174876, 451081], [174872, 451093]])],
            [10, shapely.Polygon([[174872, 451093], [174870, 451082], [174876, 451081], [174872, 451093]])],
            [10, shapely.Polygon([[174872, 451093], [174870, 451082], [174876, 451081], [174872, 451093]])],
            [1, shapely.Polygon([[174872, 451093], [174870, 451082], [174876, 451081], [174872, 451093]])],
            # One larger partly overlapping polygon with a unique value.
            [5, shapely.Polygon([[174872, 451093], [174870, 451082], [174876, 451081], [174872, 451093]]).buffer(50)],
            # These values should be reset to the min/max of the intermediate raster values
            [-9999, shapely.Polygon([[175091, 450919], [175091, 450911], [175105, 450911], [175091, 450919]])],
            [9999, shapely.Polygon([[175012, 450920], [175011, 450907], [175019, 450906], [175012, 450920]])],
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
            assert set(unique_values) == {min_value, 0, 5, 10, max_value}
            # Check that the overlapping part has the highest value
            values = list(
                rasterio.sample.sample_gen(
                    out,
                    [
                        [174872.396, 451084.460],
                        [174868.573, 451086.020],
                        [174985.83, 451101.57],
                        [0, 0],
                        [175013, 450909],
                        [175094, 450913],
                    ],
                )
            )
            assert values[0][0] == 10  # middle of the overlapping part
            assert values[1][0] == 5  # just next to the polygon
            assert values[2][0] == 0  # outside the polygons
            assert values[3][0] == 0  # outside the project area
            assert values[4][0] == max_value  # max value
            assert values[5][0] == min_value  # min value


def test_sum_rasters(monkeypatch, debug=False):
    intermediate_max_value = 1000
    intermediate_min_value = -1000
    monkeypatch.setattr(Config, "INTERMEDIATE_RASTER_VALUE_LIMIT_LOWER", intermediate_min_value)
    monkeypatch.setattr(Config, "INTERMEDIATE_RASTER_VALUE_LIMIT_UPPER", intermediate_max_value)
    final_max_value = 126
    final_min_value = 1
    monkeypatch.setattr(Config, "FINAL_RASTER_VALUE_LIMIT_LOWER", final_min_value)
    monkeypatch.setattr(Config, "FINAL_RASTER_VALUE_LIMIT_UPPER", final_max_value)
    # 4 rasters:
    # 1. group a - partial overlap
    criterion_a_1 = gpd.GeoDataFrame(
        data=[
            # These layers all overlap each other.
            [1, shapely.Polygon([[174872, 451093], [174870, 451082], [174876, 451081], [174872, 451093]])],
            [10, shapely.Polygon([[174872, 451093], [174870, 451082], [174876, 451081], [174872, 451093]])],
            # One larger partly overlapping polygon with a unique value.
            [5, shapely.Polygon([[174872, 451093], [174870, 451082], [174876, 451081], [174872, 451093]]).buffer(50)],
            # These values should be reset to the min/max of the intermediate raster values
            [-9999, shapely.Polygon([[175091, 450919], [175091, 450911], [175105, 450911], [175091, 450919]])],
            [9999, shapely.Polygon([[175012, 450920], [175011, 450907], [175019, 450906], [175012, 450920]])],
        ],
        geometry="geometry",
        crs=Config.CRS,
        columns=["suitability_value", "geometry"],
    )
    # 2. group a - partial overlap
    criterion_a_2 = gpd.GeoDataFrame(
        data=[
            # Overlaps criterion a 1 with a higher value
            [50, shapely.Polygon([[174797, 451107], [174944, 451090], [174807, 451129], [174797, 451107]])],
        ],
        geometry="geometry",
        crs=Config.CRS,
        columns=["suitability_value", "geometry"],
    )
    # 3. group b - partial overlap
    criterion_b_1 = gpd.GeoDataFrame(
        data=[
            # Overlaps criterion a 1 with a higher value
            [20, shapely.Point([174813.28, 451113.88])],
            [1000, shapely.Point([174870.46, 451051.07])],
            [-20, shapely.Point([175013.310, 450910.294])],
            [-1, shapely.Polygon([[175087, 450911], [175107, 450912], [175087, 450915], [175087, 450911]])],
        ],
        geometry="geometry",
        crs=Config.CRS,
        columns=["suitability_value", "geometry"],
    )
    # 4. group b - overlaps criterion b1 and a1
    criterion_b_2 = gpd.GeoDataFrame(
        data=[
            [15, shapely.Polygon([[175096, 450908], [175089, 450908], [175091, 450921], [175096, 450908]])],
        ],
        geometry="geometry",
        crs=Config.CRS,
        columns=["suitability_value", "geometry"],
    )
    if debug:
        criterion_a_1.to_file(Config.PATH_RESULTS / "criterion_a1.geojson")
        criterion_a_2.to_file(Config.PATH_RESULTS / "criterion_a2.geojson")
        criterion_b_1.to_file(Config.PATH_RESULTS / "criterion_b1.geojson")
        criterion_b_2.to_file(Config.PATH_RESULTS / "criterion_b2.geojson")

    rasters_to_merge = []
    for i in [
        ["a", criterion_a_1, "criterion_a1"],
        ["a", criterion_a_2, "criterion_a2"],
        ["b", criterion_b_1, "criterion_b1"],
        ["b", criterion_b_2, "criterion_b2"],
    ]:
        path_raster = rasterize_vector_data(
            "pytest_",
            i[2],
            gpd.read_file(Config.PATH_PROJECT_AREA_EDE_COMPONISTENBUURT).iloc[0].geometry,
            i[1],
            0.5,
        )
        rasters_to_merge.append({path_raster: i[0]})

    path_suitability_raster = sum_rasters(rasters_to_merge, "pytest_suitability_raster")

    with rasterio.open(path_suitability_raster, "r") as out:
        result = out.read(1)
        unique_values = np.unique(result)
        assert set(unique_values) == {final_min_value, 1, 5, 10, 14, 15, 50, 70, final_max_value}
        # Check that the overlapping part has the highest value
        values = list(
            rasterio.sample.sample_gen(
                out,
                [
                    [175090.35, 450911.67],
                    [175091.8234, 450911.7488],
                    [175088.2180, 450912.7950],
                    [0, 0],
                    [175013.3110, 450910.3013],
                    [174839.089, 451050.785],
                    [174813.2646, 451113.9146]
                    # TODO add one within the raster bounding box but outside the project area (should be no data)
                ],
            )
        )
        assert values[0][0] == 14  # overlap between b1 and b2
        assert values[1][0] == final_min_value  # overlap between a1, b1 and b2
        assert values[2][0] == final_min_value  # only b1
        assert values[3][0] == 0  # out of extent
        assert values[4][0] == final_max_value  # overlap between b1 and a1
        assert values[5][0] == 5  # just a1
        assert values[6][0] == 70  # overlap between b1 and a2


@pytest.mark.parametrize("invalid_input", [[{"key": "c"}], [{"key": "c"}, {"key": "b"}]])
def test_invalid_group_value_in_suitability_raster(invalid_input):
    with pytest.raises(InvalidGroupValue):
        sum_rasters(invalid_input, "pytest")


def test_invalid_suitability_raster_input():
    with pytest.raises(InvalidSuitabilityRasterInput):
        sum_rasters([], "pytest")
