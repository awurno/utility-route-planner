# TODO: orchestration function for calling MCDA + LCPA (with or without calculating the raster)
import pathlib

import shapely

from settings import Config
from utility_route_planner.models.lcpa.lcpa_engine import LcpaUtilityRouteEngine
from utility_route_planner.models.mcda.mcda_engine import McdaCostSurfaceEngine
from utility_route_planner.util.write import write_results_to_geopackage, reset_geopackage
import geopandas as gpd


def run_mcda_lcpa(
    preset: dict | str,
    path_geopackage_mcda_input: pathlib.Path,
    project_area_geometry: shapely.Polygon,
    start_mid_end_points: tuple,
):
    reset_geopackage(Config.PATH_GEOPACKAGE_MCDA_OUTPUT, truncate=False)
    reset_geopackage(Config.PATH_GEOPACKAGE_LCPA_OUTPUT)

    mcda_engine = McdaCostSurfaceEngine(preset, path_geopackage_mcda_input, project_area_geometry)
    mcda_engine.preprocess_vectors()
    path_suitability_raster = mcda_engine.preprocess_rasters(mcda_engine.processed_vectors)

    lcpa_engine = LcpaUtilityRouteEngine()
    lcpa_engine.get_lcpa_route(
        path_suitability_raster,
        mcda_engine.raster_preset.general.project_area_geometry,
        shapely.LineString(start_mid_end_points),
    )

    write_results_to_geopackage(Config.PATH_GEOPACKAGE_LCPA_OUTPUT, lcpa_engine.lcpa_result, "utility_route_result")


if __name__ == "__main__":
    run_mcda_lcpa(
        "preset_benchmark_raw",
        Config.PATH_GEOPACKAGE_CASE_01,
        gpd.read_file(Config.PATH_GEOPACKAGE_CASE_01, layer=Config.LAYER_NAME_PROJECT_AREA_CASE_01).iloc[0].geometry,
        ((233214.2, 442964.2), (236773.04, 440541.40)),
    )
