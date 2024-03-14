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
    RASTER_PRESET_NAME = "preset_benchmark_raw"
    RASTER_CELL_SIZE = 0.5

    # LCPA
    RASTER_NO_DATA = -127
    PATH_LCPA_GEOPACKAGE = BASEDIR / "data/processed/lcpa_results.gpkg"

    # Testing & input/output paths
    PATH_RESULTS = BASEDIR / "data/processed"
    PATH_EXAMPLE_RASTER_APELDOORN = BASEDIR / "data/examples/p_pytest_suitability_raster_apeldoorn.tif"
    PATH_EXAMPLE_ROUTE_APELDOORN = BASEDIR / "data/examples/traceontwerp_apeldoorn.geojson"
    PATH_PROJECT_AREA_APELDOORN_SMALL = BASEDIR / "data/examples/project_area_sample_apeldoorn.geojson"
    PATH_PROJECT_AREA_APELDOORN_ROAD_CROSSING = BASEDIR / "data/examples/road_crossing_example.geojson"
    PATH_PROJECT_AREA_EDE_COMPONISTENBUURT = BASEDIR / "data/examples/project_area_ede_componistenbuurt.geojson"
