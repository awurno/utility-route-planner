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
    RASTER_BLOCK_SIZE = 512
    # No data is ignored during creation of the raster.
    INTERMEDIATE_RASTER_NO_DATA = -32768
    # To prevent unwanted rounding/capping at the intermediate steps, allow larger values as int16 datatype.
    INTERMEDIATE_RASTER_VALUE_LIMIT_LOWER = -32767
    INTERMEDIATE_RASTER_VALUE_LIMIT_UPPER = 32767
    # No data is set for areas: outside the project area, manually set, invalid data which are ignored during LCPA.
    FINAL_RASTER_NO_DATA = 0
    # Cap final data to the int8 datatype.
    FINAL_RASTER_VALUE_LIMIT_LOWER = 1
    FINAL_RASTER_VALUE_LIMIT_UPPER = 126
    PATH_GEOPACKAGE_MCDA_INPUT = BASEDIR / "data/examples/ede.gpkg"
    PATH_GEOPACKAGE_MCDA_OUTPUT = BASEDIR / "data/processed/mcda_output.gpkg"

    # LCPA
    PATH_GEOPACKAGE_LCPA_OUTPUT = BASEDIR / "data/processed/lcpa_results.gpkg"

    # Testing & input/output paths
    PATH_RESULTS = BASEDIR / "data/processed"
    PATH_EXAMPLE_RASTER_EDE = BASEDIR / "data/examples/pytest_example_suitability_raster_ede.tif"
    PATH_PROJECT_AREA_EDE_COMPONISTENBUURT = BASEDIR / "data/examples/project_area_ede_componistenbuurt.geojson"

    # Research question 1 routes
    PATH_GEOPACKAGE_CASE_01 = BASEDIR / "data/examples/case_01.gpkg"
    PATH_PROJECT_AREA_CASE_01 = BASEDIR / "data/examples/case_01_project_area.geojson"
    PATH_CASE_01_ROUTE = BASEDIR / "data/examples/case_01_human_designed_route.geojson"
