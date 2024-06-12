import datetime

import shapely
import structlog

from settings import Config
from utility_route_planner.models.lcpa.lcpa_engine import LcpaUtilityRouteEngine
from utility_route_planner.util.timer import time_function
from utility_route_planner.util.write import write_results_to_geopackage

logger = structlog.get_logger(__name__)


@time_function
def get_lcpa_utility_route(path_raster, utility_route_sketch: shapely.LineString, project_area: shapely.Polygon = None):
    """
    Driver function which creates the least cost path through the suitability/cost raster.
    """
    start = datetime.datetime.now()
    logger.info("Start calculating cable route.")

    if not project_area:
        project_area = utility_route_sketch.buffer(200)

    lcpa_engine = LcpaUtilityRouteEngine()
    lcpa_engine.get_lcpa_route(path_raster, project_area, utility_route_sketch)

    if Config.DEBUG:
        write_results_to_geopackage(Config.PATH_GEOPACKAGE_LCPA_OUTPUT, lcpa_engine.lcpa_result, "utility_route_result")

    end = datetime.datetime.now()
    logger.info(f"Calculated cable route in {end - start} time.")

    return lcpa_engine
