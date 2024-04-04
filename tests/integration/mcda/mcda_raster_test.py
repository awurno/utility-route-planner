import pytest
import geopandas as gpd

from settings import Config
from src.models.mcda.exceptions import RasterCellSizeTooSmall
from src.models.mcda.mcda_rasterizing import rasterize_vector_data


def test_rasterize_vector_data_cell_size_error():
    with pytest.raises(RasterCellSizeTooSmall):
        project_area = gpd.read_file(Config.PATH_PROJECT_AREA_EDE_COMPONISTENBUURT).iloc[0].geometry
        rasterize_vector_data("temp", project_area, gpd.GeoDataFrame(), 500000)
