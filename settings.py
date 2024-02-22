import os
from pathlib import Path
import logging


class Config:
    BASEDIR = Path(__file__).parent
    LOG_LEVEL = int(os.environ.get("LOG_LEVEL", logging.INFO))
    RASTER_NO_DATA = -127
    DEBUG = True

    PATH_EXAMPLE_RASTER_1 = BASEDIR / "data/examples/p_pytest_suitability_raster_apeldoorn.tif"
    PATH_EXAMPLE_ROUTE_1 = BASEDIR / "data/examples/traceontwerp_apeldoorn.geojson"
    PATH_PROJECT_AREA = BASEDIR / "data/examples/project_area_sample_apeldoorn.geojson"
    PATH_PROJECT_AREA_ROAD_CROSSING = BASEDIR / "data/examples/road_crossing_example.geojson"
    PATH_RESULTS = BASEDIR / "data/processed"
