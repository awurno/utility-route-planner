import pathlib
from functools import cached_property

import numpy as np
import shapely
from shapely.geometry.geo import box

from models.mcda.mcda_datastructures import McdaRasterSettings, RasterizedCriterion
from settings import Config
from utility_route_planner.models.mcda.load_mcda_preset import RasterPreset, load_preset
import structlog
import geopandas as gpd

from utility_route_planner.models.mcda.mcda_rasterizing import (
    rasterize_vector_data,
    get_raster_settings,
    merge_criteria_rasters,
    write_raster,
)
from utility_route_planner.util.timer import time_function

logger = structlog.get_logger(__name__)


class McdaCostSurfaceEngine:
    raster_preset: RasterPreset
    path_geopackage_input: pathlib.Path

    def __init__(self, preset_to_load, path_geopackage_mcda_input, project_area_geometry: shapely.Polygon):
        self.raster_preset = load_preset(preset_to_load, path_geopackage_mcda_input, project_area_geometry)
        self.processed_vectors: dict = {}
        self.project_area_grid = self.create_project_area_grid(*project_area_geometry.bounds)
        self.unprocessed_criteria_names: set = set()
        self.processed_criteria_names: set = set()

    @staticmethod
    def create_project_area_grid(min_x: float, min_y: float, max_x: float, max_y: float):
        grid_size = Config.RASTER_BLOCK_SIZE
        x_coords = np.arange(min_x, max_x, grid_size)
        y_coords = np.arange(min_y, max_y, grid_size)
        grid_cells = [box(x, y, x + grid_size, y + grid_size) for x in x_coords for y in y_coords]
        grid = gpd.GeoDataFrame(grid_cells, columns=["geometry"], crs=Config.CRS)
        return grid

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

        self.assign_vector_group_to_grid()

    def assign_vector_group_to_grid(self):
        for processed_group_name, vector in self.processed_vectors.items():
            vector_with_grid = gpd.sjoin(vector, self.project_area_grid, how="left", predicate="intersects")
            vector_with_grid = vector_with_grid.rename(columns={"index_right": "tile_id"})
            vector_with_grid = vector_with_grid.set_index("tile_id", drop=True)
            self.processed_vectors[processed_group_name] = vector_with_grid

    @time_function
    def preprocess_rasters(
        self, vector_to_convert: dict[str, gpd.GeoDataFrame], cell_size: float = Config.RASTER_CELL_SIZE
    ) -> str:
        tile_ids = list(self.project_area_grid.index)

        logger.info(
            f"Starting rasterizing for {self.number_of_criteria_to_rasterize} criteria using {len(tile_ids)} tiles."
        )
        for tile_id in tile_ids:
            tile_geometry = self.project_area_grid.iloc[tile_id].values[0]
            raster_settings = get_raster_settings(tile_geometry, cell_size)
            rasters_to_sum = [
                self.rasterize_vector(idx, criterion, gdf, raster_settings)
                for idx, (criterion, gdf) in enumerate(vector_to_convert.items())
            ]

            complete_raster = merge_criteria_rasters(rasters_to_sum, raster_settings.height, raster_settings.width)
            # complete_raster = construct_complete_raster(
            #     merged_rasters, raster_settings.height, raster_settings.width, raster_settings.dtype
            # )
            write_raster(complete_raster, raster_settings, f"{self.raster_preset.general.final_raster_name}-{tile_id}")
        return "path_suitability_raster"

    def rasterize_vector(
        self, idx: int, criterion: str, gdf: gpd.GeoDataFrame, raster_settings: McdaRasterSettings
    ) -> RasterizedCriterion:
        logger.info(f"Processing criteria number {idx + 1} of {self.number_of_criteria_to_rasterize}.")
        rasterized_vector = rasterize_vector_data(criterion, gdf, raster_settings)
        raster_criteria = self.raster_preset.criteria[criterion]
        return RasterizedCriterion(criterion, rasterized_vector, raster_criteria.group)
