import pathlib
from functools import cached_property

from utility_route_planner.models.mcda.load_mcda_preset import RasterPreset, load_preset
import structlog
import geopandas as gpd

from utility_route_planner.models.mcda.mcda_rasterizing import rasterize_vector_data, merge_criteria_rasters

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

    def preprocess_rasters(self, vector_to_convert: dict[str, gpd.GeoDataFrame]) -> str:
        logger.info(f"Starting rasterizing for {self.number_of_criteria_to_rasterize} criteria.")
        rasters_to_sum = []
        for idx, (criterion, gdf) in enumerate(vector_to_convert.items()):
            logger.info(f"Processing criteria number {idx + 1} of {self.number_of_criteria_to_rasterize}.")
            path_raster = rasterize_vector_data(
                self.raster_preset.general.prefix, criterion, self.raster_preset.general.project_area_geometry, gdf
            )
            rasters_to_sum.append({path_raster: self.raster_preset.criteria[criterion].group})

        path_suitability_raster = merge_criteria_rasters(rasters_to_sum, self.raster_preset.general.final_raster_name)
        return path_suitability_raster
