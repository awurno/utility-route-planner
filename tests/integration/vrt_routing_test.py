import geopandas as gpd
import pytest
import rasterio
import rasterio.merge
import shapely

from models.lcpa.lcpa_engine import LcpaUtilityRouteEngine
from models.mcda.mcda_engine import McdaCostSurfaceEngine
from settings import Config
from util.write import write_to_file


class TestVRTRouting:
    @pytest.fixture(scope="session")
    def preprocessed_vectors(self) -> McdaCostSurfaceEngine:
        mcda_engine = McdaCostSurfaceEngine(
            Config.RASTER_PRESET_NAME_BENCHMARK,
            Config.PYTEST_PATH_GEOPACKAGE_MCDA,
            gpd.read_file(
                Config.PYTEST_PATH_GEOPACKAGE_MCDA, layer=Config.PYTEST_LAYER_NAME_PROJECT_AREA
            ).geometry.iloc[0],
        )
        mcda_engine.preprocess_vectors()

        return mcda_engine

    @pytest.fixture(scope="session")
    def start_end_point_route(self) -> tuple[shapely.Point, shapely.Point]:
        start_point = shapely.Point(174823.0, 450979.7)
        end_point = shapely.Point(175841.0, 450424.2)

        return start_point, end_point

    # TODO: replace with fixture for calculating single tif using same preset in test_vrt_results_in_same_route_as_single_tiff
    # @pytest.fixture(scope="session")
    # def route_for_tiff_file(self, start_end_point_route, project_area) -> shapely.LineString:
    #     lcpa_engine = LcpaUtilityRouteEngine()
    #     lcpa_route = lcpa_engine.get_lcpa_route(
    #         Config.PATH_EXAMPLE_RASTER,
    #         shapely.LineString(start_end_point_route),
    #         project_area,
    #     )
    #     return lcpa_route

    @pytest.mark.parametrize("max_block_size", [512, 1024, 2048])
    @pytest.mark.usefixtures("setup_mcda_lcpa_testing")
    def test_vrt_results_in_same_route_as_single_tiff(
        self,
        preprocessed_vectors: McdaCostSurfaceEngine,
        start_end_point_route: tuple[shapely.Point, shapely.Point],
        # route_for_tiff_file: shapely.LineString,
        max_block_size: int,
        monkeypatch,
        debug: bool = False,
    ):
        monkeypatch.setattr(Config, "MAX_BLOCK_SIZE", max_block_size)

        # Given the set of preprocessed vectors, preprocess the rasters given the max block size
        mcda_engine = preprocessed_vectors
        raster_path_vrt = mcda_engine.preprocess_rasters(mcda_engine.processed_vectors)

        # # TODO calculate again, force to single tif

        # TODO replace this with option in mcda_engine to force into a VRT with only 1 tiff file.
        raster_path_tif = Config.PATH_RESULTS / "pytest_merged.tif"
        with rasterio.open(raster_path_vrt) as src:
            # Read the data from the VRT
            data, transform = rasterio.merge.merge([src])

            # Update the metadata
            out_meta = src.meta.copy()
            out_meta.update(
                {"driver": "GTiff", "height": data.shape[1], "width": data.shape[2], "transform": transform}
            )

            # Write the data to a new TIFF file
            with rasterio.open(raster_path_tif, "w", **out_meta) as dest:
                dest.write(data)

        lcpa_engine = LcpaUtilityRouteEngine()
        route_using_vrt = lcpa_engine.get_lcpa_route(
            raster_path_vrt,  # blokjes
            shapely.LineString(start_end_point_route),
            mcda_engine.raster_preset.general.project_area_geometry,
        )
        route_using_tif = lcpa_engine.get_lcpa_route(
            raster_path_tif,  # single tif
            shapely.LineString(start_end_point_route),
            mcda_engine.raster_preset.general.project_area_geometry,
        )

        # Verify that the route that was computed using the vrt raster is equal to the route that was computed using
        # the standard tiff file.
        assert route_using_vrt.equals(route_using_tif)

        if debug:
            write_to_file(route_using_vrt, "route_using_vrt.fgb")
            write_to_file(route_using_tif, "route_using_tif.fgb")
