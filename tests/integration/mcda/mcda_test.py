from src.models.mcda.mcda_main import get_mcda_cost_surface
from settings import Config


def test_get_mcda_cost_surface_raster_preset():
    get_mcda_cost_surface(Config.RASTER_PRESET)
