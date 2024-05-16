import pytest
import shapely

from settings import Config
from src.models.lcpa.lcpa_engine import LcpaUtilityRouteEngine
from src.models.mcda.mcda_engine import McdaCostSurfaceEngine
from src.util.write import reset_geopackage, write_results_to_geopackage


@pytest.fixture
def setup_mcda_lcpa_testing(monkeypatch):
    reset_geopackage(Config.PATH_LCPA_GEOPACKAGE)
    reset_geopackage(Config.PATH_OUTPUT_MCDA_GEOPACKAGE, truncate=False)
    monkeypatch.setattr(Config, "DEBUG", True)


@pytest.mark.usefixtures("setup_mcda_lcpa_testing")
class TestMcdaLcpaChain:
    @pytest.mark.parametrize(
        "utility_route_sketch",
        (
            [(174896.9, 451130.5), (175279.7, 450519.6)],
            [(174896.9, 451130.5), (174968.1, 450985.7), (174975.1, 450731.1), (175279.7, 450519.6)],
        ),
    )
    def test_mcda_lcpa_chain_default(self, utility_route_sketch):
        mcda_engine = McdaCostSurfaceEngine("preset_benchmark_raw")
        mcda_engine.preprocess_vectors()
        path_suitability_raster = mcda_engine.preprocess_rasters(mcda_engine.processed_vectors)

        lcpa_engine = LcpaUtilityRouteEngine()
        lcpa_engine.get_lcpa_route(
            path_suitability_raster,
            mcda_engine.raster_preset.general.project_area_geometry,
            shapely.LineString(utility_route_sketch),
        )
        write_results_to_geopackage(Config.PATH_LCPA_GEOPACKAGE, lcpa_engine.lcpa_result, "utility_route_result")
