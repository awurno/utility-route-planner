import pathlib
from functools import cached_property

import numpy as np
from shapely.geometry.geo import box

from models.mcda.mcda_datastructures import McdaRasterSettings, RasterizedCriterion
from settings import Config
from utility_route_planner.models.mcda.load_mcda_preset import RasterPreset, load_preset
import structlog
import geopandas as gpd

from utility_route_planner.models.mcda.mcda_rasterizing import (
    rasterize_vector_data,
)
from utility_route_planner.util.timer import time_function

logger = structlog.get_logger(__name__)


class McdaCostSurfaceEngine:
    raster_preset: RasterPreset
    path_geopackage_input: pathlib.Path

    def __init__(self, preset_to_load, path_geopackage_mcda_input, project_area_geometry):
        self.raster_preset = load_preset(preset_to_load, path_geopackage_mcda_input, project_area_geometry)
        self.project_area_geometry = project_area_geometry
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
            logger.info(f"Processing criteria number {idx + 1} of {self.number_of_criteria}.")
            is_processed, processed_gdf = self.raster_preset.criteria[criterion].preprocessing_function.execute(
                self.raster_preset.general, self.raster_preset.criteria[criterion]
            )
            if is_processed:
                self.processed_vectors[criterion] = processed_gdf
            else:
                assert processed_gdf.empty
                self.unprocessed_criteria_names.add(criterion)

        project_area_grid = self.create_project_area_grid()
        self.assign_vector_group_to_grid(project_area_grid)

    def create_project_area_grid(self):
        min_x, min_y, max_x, max_y = self.project_area_geometry
        grid_size = (max_y - min_y) * 0.1
        x_coords = np.arange(min_x, max_x, grid_size)
        y_coords = np.arange(min_y, max_y, grid_size)
        grid_cells = [box(x, y, x + grid_size, y + grid_size) for x in x_coords for y in y_coords]
        grid = gpd.GeoDataFrame(grid_cells, columns=["geometry"], crs=Config.CRS)
        return grid

    def assign_vector_group_to_grid(self, grid: gpd.GeoDataFrame):
        for processed_group_name, vector in self.processed_vectors.items():
            vector_with_grid = gpd.sjoin(vector, grid, how="left", predicate="intersects")
            vector_with_grid = vector_with_grid.rename(columns={"index_right": "tile_id"})
            vector_with_grid = vector_with_grid.set_index("tile_id", drop=True)
            self.processed_vectors[processed_group_name] = vector_with_grid

    @time_function
    def preprocess_rasters(
        self, vector_to_convert: dict[str, gpd.GeoDataFrame], cell_size: float = Config.RASTER_CELL_SIZE
    ) -> str:
        logger.info(f"Starting rasterizing for {self.number_of_criteria_to_rasterize} criteria.")

        # raster_settings = get_raster_settings(self.raster_preset.general.project_area_geometry, cell_size)
        # rasters_to_sum = [
        #     self.rasterize_vector(idx, criterion, gdf, raster_settings)
        #     for idx, (criterion, gdf) in enumerate(vector_to_convert.items())
        # ]

        # complete_raster = merge_criteria_rasters(rasters_to_sum, raster_settings.height, raster_settings.width)
        # # complete_raster = construct_complete_raster(
        # #     merged_rasters, raster_settings.height, raster_settings.width, raster_settings.dtype
        # # )
        # path_suitability_raster = write_raster(
        #     complete_raster, raster_settings, self.raster_preset.general.final_raster_name
        # )
        return "path_suitability_raster"

    def rasterize_vector(
        self, idx: int, criterion: str, gdf: gpd.GeoDataFrame, raster_settings: McdaRasterSettings
    ) -> RasterizedCriterion:
        logger.info(f"Processing criteria number {idx + 1} of {self.number_of_criteria_to_rasterize}.")
        rasterized_vector = rasterize_vector_data(criterion, gdf, raster_settings)
        raster_criteria = self.raster_preset.criteria[criterion]
        return RasterizedCriterion(criterion, rasterized_vector, raster_criteria.group)
