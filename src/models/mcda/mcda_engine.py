from src.models.mcda.load_mcda_preset import RasterPreset, load_preset


class McdaCostSurfaceEngine:
    raster_preset: RasterPreset

    def __init__(self, preset_name):
        self.raster_preset = load_preset(preset_name)

    def preprocess_vectors(self):
        pass

    def preprocess_rasters(self):
        pass
