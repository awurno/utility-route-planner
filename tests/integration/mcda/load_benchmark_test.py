from src.models.mcda.load_mcda_preset2 import load_preset
from src.models.mcda.mcda_presets import preset_benchmark


def test_load_benchmark_with_default_settings():
    load_preset(preset_benchmark)
