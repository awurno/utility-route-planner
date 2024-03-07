from src.models.mcda.mcda_main import get_mcda_cost_surface
from src.models.mcda.mcda_presets import preset_benchmark


def test_get_mcda_cost_surface_raster_preset():
    get_mcda_cost_surface(preset_benchmark)
