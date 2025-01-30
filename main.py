import pathlib

import shapely
import structlog

from models.lcpa.lcpa_engine import LcpaUtilityRouteEngine
from settings import Config
from utility_route_planner.models.mcda.mcda_engine import McdaCostSurfaceEngine
from utility_route_planner.util.geo_utilities import get_first_last_point_from_linestring
from utility_route_planner.util.write import reset_geopackage
import geopandas as gpd

logger = structlog.get_logger(__name__)


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
        shapely.LineString(start_mid_end_points),
        mcda_engine.raster_preset.general.project_area_geometry,
    )


if __name__ == "__main__":
    cases = [
        (
            Config.PATH_GEOPACKAGE_CASE_01,
            Config.LAYER_NAME_PROJECT_AREA_CASE_01,
            Config.LAYER_NAME_HUMAN_DESIGNED_ROUTE_CASE_01,
        ),
        (
            Config.PATH_GEOPACKAGE_CASE_02,
            Config.LAYER_NAME_PROJECT_AREA_CASE_02,
            Config.LAYER_NAME_HUMAN_DESIGNED_ROUTE_CASE_02,
        ),
        (
            Config.PATH_GEOPACKAGE_CASE_03,
            Config.LAYER_NAME_PROJECT_AREA_CASE_03,
            Config.LAYER_NAME_HUMAN_DESIGNED_ROUTE_CASE_03,
        ),
        (
            Config.PATH_GEOPACKAGE_CASE_04,
            Config.LAYER_NAME_PROJECT_AREA_CASE_04,
            Config.LAYER_NAME_HUMAN_DESIGNED_ROUTE_CASE_04,
        ),
        (
            Config.PATH_GEOPACKAGE_CASE_05,
            Config.LAYER_NAME_PROJECT_AREA_CASE_05,
            Config.LAYER_NAME_HUMAN_DESIGNED_ROUTE_CASE_05,
        ),
    ]

    case_to_run = 1  # 0/1/2/3/4
    geopackage, layer_project_area, human_designed_route = cases[case_to_run]

    run_mcda_lcpa(
        "preset_benchmark_raw",
        geopackage,
        gpd.read_file(geopackage, layer=layer_project_area).iloc[0].geometry,
        get_first_last_point_from_linestring(gpd.read_file(geopackage, layer=human_designed_route).iloc[0].geometry),
    )
