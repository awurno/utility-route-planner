import geopandas as gpd
import pytest
import shapely

from models.lcpa.lcpa_engine import LcpaUtilityRouteEngine
from models.mcda.mcda_engine import McdaCostSurfaceEngine
from settings import Config


class TestVRTRouting:
    @pytest.fixture(scope="session")
    def project_area(self) -> shapely.Polygon:
        return gpd.read_file(
            Config.PYTEST_PATH_GEOPACKAGE_MCDA, layer=Config.PYTEST_LAYER_NAME_PROJECT_AREA
        ).geometry.iloc[0]

    @pytest.fixture(scope="session")
    def preprocessed_vectors(self, project_area: shapely.Polygon) -> McdaCostSurfaceEngine:
        mcda_engine = McdaCostSurfaceEngine(
            Config.RASTER_PRESET_NAME_BENCHMARK, Config.PYTEST_PATH_GEOPACKAGE_MCDA, project_area
        )
        mcda_engine.preprocess_vectors()

        return mcda_engine

    @pytest.fixture(scope="session")
    def start_end_point_route(self) -> tuple[shapely.Point, shapely.Point]:
        start_point = shapely.Point(174823.0, 450979.7)
        end_point = shapely.Point(175841.0, 450424.2)

        return start_point, end_point

    @pytest.fixture(scope="session")
    def route_for_tiff_file(self, start_end_point_route, project_area) -> shapely.LineString:
        lcpa_engine = LcpaUtilityRouteEngine()
        lcpa_route = lcpa_engine.get_lcpa_route(
            Config.PATH_EXAMPLE_RASTER,
            shapely.LineString(start_end_point_route),
            project_area,
        )
        return lcpa_route

    @pytest.mark.parametrize("max_block_size", [512, 1024, 2048])
    @pytest.mark.usefixtures("setup_mcda_lcpa_testing")
    def test_vrt_results_in_same_route_as_single_tiff(
        self,
        preprocessed_vectors: McdaCostSurfaceEngine,
        start_end_point_route: tuple[shapely.Point, shapely.Point],
        route_for_tiff_file: shapely.LineString,
        max_block_size: int,
        monkeypatch,
    ):
        monkeypatch.setattr(Config, "MAX_BLOCK_SIZE", max_block_size)

        # Given the set of preprocessed vectors, preprocess the rasters given the max block size
        mcda_engine = preprocessed_vectors
        raster_path = mcda_engine.preprocess_rasters(mcda_engine.processed_vectors)

        lcpa_engine = LcpaUtilityRouteEngine()
        route_using_vrt = lcpa_engine.get_lcpa_route(
            raster_path,
            shapely.LineString(start_end_point_route),
            mcda_engine.raster_preset.general.project_area_geometry,
        )

        # Verify that the route that was computed using the vrt raster is equal to the route that was computed using
        # the standard tiff file.
        assert route_for_tiff_file.equals(route_using_vrt)
