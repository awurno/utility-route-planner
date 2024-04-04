from functools import cached_property

from src.models.mcda.load_mcda_preset import RasterPreset, load_preset
import structlog
import geopandas as gpd

from src.models.mcda.mcda_rasterizing import rasterize_vector_data, sum_rasters

logger = structlog.get_logger(__name__)


class McdaCostSurfaceEngine:
    raster_preset: RasterPreset

    def __init__(self, preset_to_load):
        self.raster_preset = load_preset(preset_to_load)
        self.processed_vectors = {}
        self.unprocessed_vectors = []

    @cached_property
    def number_of_criteria(self):
        return len(self.raster_preset.criteria)

    @cached_property
    def number_of_criteria_to_rasterize(self):
        return len(self.processed_vectors)

    def preprocess_vectors(self):
        logger.info(f"Processing {self.number_of_criteria} criteria.")
        for idx, criterion in enumerate(self.raster_preset.criteria):
            logger.info(f"Processing criteria number {idx+1} of {self.number_of_criteria}.")
            is_processed, processed_gdf = self.raster_preset.criteria[criterion].preprocessing_function.execute(
                self.raster_preset.general, self.raster_preset.criteria[criterion]
            )
            if is_processed:
                self.processed_vectors[criterion] = processed_gdf
            else:
                assert processed_gdf.empty
                self.unprocessed_vectors.append(criterion)

    def preprocess_rasters(self, vector_to_convert: dict[str, gpd.GeoDataFrame]):
        logger.info(f"Starting rasterizing for {self.number_of_criteria_to_rasterize} criteria.")
        rasters_to_sum = []
        for idx, (criterion, gdf) in enumerate(vector_to_convert.items()):
            logger.info(f"Processing criteria number {idx + 1} of {self.number_of_criteria_to_rasterize}.")
            path_raster = rasterize_vector_data(
                self.raster_preset.general.prefix,
                criterion,
                self.raster_preset.general.project_area_geometry,
                gdf,
                self.raster_preset.general.raster_resolution[0],
            )
            rasters_to_sum.append({path_raster: self.raster_preset.criteria[criterion].group})

        sum_rasters(rasters_to_sum)
