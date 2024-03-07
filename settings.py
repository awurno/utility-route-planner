import os
from pathlib import Path
import logging


class Config:
    # General
    BASEDIR = Path(__file__).parent
    LOG_LEVEL = int(os.environ.get("LOG_LEVEL", logging.INFO))
    DEBUG = False
    CRS = 28992  # https://epsg.io/28992

    # MCDA
    RASTER_PRESET = "preset_default"
    RASTER_CELL_SIZE = 0.5
    PATH_RASTER_PRESET_FILE = BASEDIR / "src/models/mcda_presets.yaml"

    # LCPA
    RASTER_NO_DATA = -127
    PATH_LCPA_GEOPACKAGE = BASEDIR / "data/processed/lcpa_results.gpkg"

    # Testing & debug paths
    PATH_EXAMPLE_RASTER_1 = BASEDIR / "data/examples/p_pytest_suitability_raster_apeldoorn.tif"
    PATH_EXAMPLE_ROUTE_1 = BASEDIR / "data/examples/traceontwerp_apeldoorn.geojson"
    PATH_PROJECT_AREA = BASEDIR / "data/examples/project_area_sample_apeldoorn.geojson"
    PATH_PROJECT_AREA_ROAD_CROSSING = BASEDIR / "data/examples/road_crossing_example.geojson"
    PATH_RESULTS = BASEDIR / "data/processed"
