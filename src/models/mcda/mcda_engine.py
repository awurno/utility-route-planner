from src.models.mcda.load_mcda_preset2 import RasterPreset, load_preset
import structlog

logger = structlog.get_logger(__name__)


class McdaCostSurfaceEngine:
    raster_preset: RasterPreset

    def __init__(self, preset_to_load):
        self.raster_preset = load_preset(preset_to_load)

    def preprocess_vectors(self):
        pass

    def preprocess_rasters(self):
        pass
