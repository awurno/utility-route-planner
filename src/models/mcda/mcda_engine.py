from functools import cached_property

from src.models.mcda.load_mcda_preset import RasterPreset, load_preset
import structlog

logger = structlog.get_logger(__name__)


class McdaCostSurfaceEngine:
    raster_preset: RasterPreset

    def __init__(self, preset_to_load):
        self.raster_preset = load_preset(preset_to_load)

    @cached_property
    def number_of_criteria(self):
        return len(self.raster_preset.criteria)

    def preprocess_vectors(self):
        logger.info(f"Processing {self.number_of_criteria} criteria.")
        for idx, criterion in enumerate(self.raster_preset.criteria):
            logger.info(f"Processing criteria number {idx+1} of {self.number_of_criteria}.")
            is_processed = self.raster_preset.criteria[criterion].preprocessing_function.execute(
                self.raster_preset.general, self.raster_preset.criteria[criterion]
            )
            print(self.raster_preset.criteria[criterion].description, is_processed)

    def preprocess_rasters(self):
        pass
