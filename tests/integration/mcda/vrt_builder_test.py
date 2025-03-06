import geopandas as gpd
import pytest
import shapely

from main import run_mcda_lcpa
from models.lcpa.lcpa_engine import LcpaUtilityRouteEngine
from settings import Config


class TestVRTBuilder:
    @pytest.fixture()
    def project_area(self) -> shapely.Polygon:
        return gpd.read_file(
            Config.PYTEST_PATH_GEOPACKAGE_MCDA, layer=Config.PYTEST_LAYER_NAME_PROJECT_AREA
        ).geometry.iloc[0]

    @pytest.fixture()
    def start_end_point_route(self) -> tuple[shapely.Point, shapely.Point]:
        start_point = shapely.Point(174823.0, 450979.7)
        end_point = shapely.Point(175841.0, 450424.2)

        return start_point, end_point

    @pytest.fixture()
    def route_for_tiff_file(self, start_end_point_route, project_area):
        lcpa_engine = LcpaUtilityRouteEngine()
        lcpa_route = lcpa_engine.get_lcpa_route(
            Config.PATH_EXAMPLE_RASTER,
            shapely.LineString(start_end_point_route),
            project_area,
        )
        return lcpa_route

    @pytest.mark.parametrize("max_block_size", [512, 1024, 2048])
    def test_vrt_results_in_same_route_as_single_tiff(
        self, start_end_point_route, route_for_tiff_file, max_block_size: int, monkeypatch
    ):
        monkeypatch.setattr(Config, "MAX_BLOCK_SIZE", max_block_size)
        path_geopackage = Config.PYTEST_PATH_GEOPACKAGE_MCDA
        layer_name_project_area = Config.PYTEST_LAYER_NAME_PROJECT_AREA

        route_using_vrt_tiff = run_mcda_lcpa(
            Config.RASTER_PRESET_NAME_BENCHMARK,
            path_geopackage,
            gpd.read_file(path_geopackage, layer=layer_name_project_area).geometry.iloc[0],
            start_end_point_route,
        )

        assert route_for_tiff_file.equals(route_using_vrt_tiff)
