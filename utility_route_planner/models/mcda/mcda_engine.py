import math
import pathlib
from functools import cached_property

import affine
import numpy as np

from models.mcda.exceptions import RasterCellSizeTooSmall
from settings import Config
from utility_route_planner.models.mcda.load_mcda_preset import RasterPreset, load_preset
import structlog
import geopandas as gpd

from utility_route_planner.models.mcda.mcda_rasterizing import rasterize_vector_data, merge_criteria_rasters
from utility_route_planner.util.timer import time_function

logger = structlog.get_logger(__name__)


class McdaCostSurfaceEngine:
    raster_preset: RasterPreset
    path_geopackage_input: pathlib.Path

    def __init__(self, preset_to_load, path_geopackage_mcda_input, project_area_geometry):
        self.raster_preset = load_preset(preset_to_load, path_geopackage_mcda_input, project_area_geometry)
        self.processed_vectors = {}
        self.unprocessed_criteria_names = set()
        self.processed_criteria_names = set()

    @cached_property
    def number_of_criteria(self):
        return len(self.raster_preset.criteria)

    @cached_property
    def number_of_criteria_to_rasterize(self):
        return len(self.processed_vectors)

    @time_function
    def preprocess_vectors(self):
        logger.info(
            f"Processing {self.number_of_criteria} criteria using geopackage: {self.raster_preset.general.path_input_geopackage}"
        )
        for idx, criterion in enumerate(self.raster_preset.criteria):
            logger.info(f"Processing criteria number {idx+1} of {self.number_of_criteria}.")
            is_processed, processed_gdf = self.raster_preset.criteria[criterion].preprocessing_function.execute(
                self.raster_preset.general, self.raster_preset.criteria[criterion]
            )
            if is_processed:
                self.processed_vectors[criterion] = processed_gdf
            else:
                assert processed_gdf.empty
                self.unprocessed_criteria_names.add(criterion)

        self.processed_criteria_names = set(self.raster_preset.criteria.keys()).difference(
            set(self.unprocessed_criteria_names)
        )

    def run_raster_preprocessing(
        self, vector_to_convert: dict[str, gpd.GeoDataFrame], cell_size: float = Config.RASTER_CELL_SIZE
    ):
        logger.info(f"Starting rasterizing for {self.number_of_criteria_to_rasterize} criteria.")

        # with ProcessPoolExecutor() as executor:
        #     futures = [executor.submit(
        #         self.rasterize_vector,
        #         idx,
        #         criterion,
        #         gdf,
        #     ) for idx, (criterion, gdf) in enumerate(vector_to_convert.items())]
        #
        #     rasters_to_sum = [future.result() for future in as_completed(futures)]

        minx, miny, maxx, maxy = self.raster_preset.general.project_area_geometry.bounds

        # In order to fit the given cell size to the project area bounds, we slightly extend the maxx and maxy accordingly.
        if cell_size > maxx - minx or cell_size > maxy - miny:
            raise RasterCellSizeTooSmall("Given raster cell size is too large for the project area.")

        rasterize_settings = dict(
            width=math.ceil((maxx - minx) / cell_size),
            height=math.ceil((maxy - miny) / cell_size),
            nodata=Config.INTERMEDIATE_RASTER_NO_DATA,
            transform=affine.Affine(cell_size, 0.0, round(minx), 0.0, -cell_size, round(maxy)),
        )

        rasters_to_sum = [
            self.rasterize_vector(idx, criterion, gdf, rasterize_settings)
            for idx, (criterion, gdf) in enumerate(vector_to_convert.items())
        ]

        return rasters_to_sum, rasterize_settings

    def rasterize_vector(
        self, idx: int, criterion: str, gdf: gpd.GeoDataFrame, rasterize_settings: dict
    ) -> tuple[str, np.ndarray, str]:
        logger.info(f"Processing criteria number {idx + 1} of {self.number_of_criteria_to_rasterize}.")
        rasterized_vector = rasterize_vector_data(criterion, gdf, rasterize_settings)
        raster_criteria = self.raster_preset.criteria[criterion]
        return criterion, rasterized_vector, raster_criteria.group

    @time_function
    def preprocess_rasters(
        self, vector_to_convert: dict[str, gpd.GeoDataFrame], cell_size: float = Config.RASTER_CELL_SIZE
    ) -> str:
        logger.info(f"Starting rasterizing for {self.number_of_criteria_to_rasterize} criteria.")

        minx, miny, maxx, maxy = self.raster_preset.general.project_area_geometry.bounds

        # In order to fit the given cell size to the project area bounds, we slightly extend the maxx and maxy accordingly.
        if cell_size > maxx - minx or cell_size > maxy - miny:
            raise RasterCellSizeTooSmall("Given raster cell size is too large for the project area.")

        rasterize_settings = dict(
            width=math.ceil((maxx - minx) / cell_size),
            height=math.ceil((maxy - miny) / cell_size),
            nodata=Config.INTERMEDIATE_RASTER_NO_DATA,
            transform=affine.Affine(cell_size, 0.0, round(minx), 0.0, -cell_size, round(maxy)),
        )

        rasters_to_sum = [
            self.rasterize_vector(idx, criterion, gdf, rasterize_settings)
            for idx, (criterion, gdf) in enumerate(vector_to_convert.items())
        ]

        path_suitability_raster = merge_criteria_rasters(
            rasters_to_sum, rasterize_settings, self.raster_preset.general.final_raster_name
        )
        return path_suitability_raster
