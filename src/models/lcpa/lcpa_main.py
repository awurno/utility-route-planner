import datetime

import shapely
import structlog
import geopandas
from settings import Config

from src.util.geo_utilities import (
    array_indices_to_linestring,
    align_linestring,
)
from src.util.load import load_suitability_raster_data
from src.models.lcpa.lcpa import preprocess_input_linestring, calculate_least_cost_path

logger = structlog.get_logger(__name__)


# TODO convert to a class with: raster preset to use, utility_route_sketch
def get_lcpa_utility_route(utility_route_sketch: shapely.LineString):
    """
    Driver function which creates the least cost path through the suitability/cost raster.
    """
    start = datetime.datetime.now()
    logger.info("Start calculating cable route.")

    # Creates a numpy array from cost surface raster and saves the metadata for further usage.
    suit_raster_array, suit_raster_geotransform = load_suitability_raster_data(
        Config.PATH_EXAMPLE_RASTER_1, geopandas.read_file(Config.PATH_PROJECT_AREA).iloc[0].geometry
    )

    # Preprocess input linestring geometry, calculate raster array index per input coordinate.
    route_model = preprocess_input_linestring(suit_raster_geotransform, utility_route_sketch)

    # Creates path array and the respective sequence as numpy array indices.
    cost_path, cost_path_indices = calculate_least_cost_path(suit_raster_array, route_model)

    # Converts path array to raster and linestring, writes them to file.
    linestring = array_indices_to_linestring(suit_raster_geotransform, cost_path_indices)  # array to linestring
    # The linestring is the result of a vectorized raster, which results in a jagged shape. Smoothen this.
    linestring_aligned = align_linestring(linestring, 0.5)

    end = datetime.datetime.now()
    logger.info(f"Calculated cable route in {end - start} time.")

    return linestring_aligned
