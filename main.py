# TODO: orchestration function for calling MCDA + LCPA (with or without calculating the raster)
import shapely

from settings import Config
from src.models.lcpa.lcpa_engine import LcpaUtilityRouteEngine
from src.models.mcda.mcda_engine import McdaCostSurfaceEngine
from src.util.write import write_results_to_geopackage, reset_geopackage
import geopandas as gpd


def run_mcda_lcpa(preset, path_geopackage_mcda_input, project_area_geometry):
    reset_geopackage(Config.PATH_GEOPACKAGE_MCDA_OUTPUT, truncate=False)
    reset_geopackage(Config.PATH_GEOPACKAGE_LCPA_OUTPUT)

    mcda_engine = McdaCostSurfaceEngine(preset, path_geopackage_mcda_input, project_area_geometry)
    mcda_engine.preprocess_vectors()
    path_suitability_raster = mcda_engine.preprocess_rasters(mcda_engine.processed_vectors)

    lcpa_engine = LcpaUtilityRouteEngine()
    lcpa_engine.get_lcpa_route(
        path_suitability_raster,
        mcda_engine.raster_preset.general.project_area_geometry,
        shapely.LineString([(233214.2, 442964.2), (236773.04, 440541.40)]),
    )

    # TODO just move to the lcpa engine?
    write_results_to_geopackage(Config.PATH_GEOPACKAGE_LCPA_OUTPUT, lcpa_engine.lcpa_result, "utility_route_result")


if __name__ == "__main__":
    # TODO determine how to cope with areas which do not contain all criteria:
    #  - 1) skip the criteria
    #  - 2) raise an error
    #  - 3) filter mcda_preset prior to feeding it to the mcda engine (delete keys)
    #  - I think 3) is most robust but might be very restrictive and not intuitive. Think about how the flow works. How enforcing should the preset be? Should the raster contain everything in the preset?
    #  - 4) save used criteria to the mcda engine so we can assert on this in tests. Possible add to the raster metadata later
    run_mcda_lcpa(
        "preset_benchmark_raw",
        Config.PATH_GEOPACKAGE_CASE_01,
        gpd.read_file(Config.PATH_GEOPACKAGE_CASE_01, layer=Config.PATH_PROJECT_AREA_CASE_01_LAYER_NAME)
        .iloc[0]
        .geometry,
    )
