import pytest

from settings import Config
from src.models.mcda.mcda_engine import McdaCostSurfaceEngine
from src.models.mcda.mcda_presets import preset_collection
from src.util.write import reset_geopackage


@pytest.fixture
def setup_clean_start(monkeypatch):
    reset_geopackage(Config.PATH_OUTPUT_MCDA_GEOPACKAGE, truncate=False)


@pytest.mark.usefixtures("setup_clean_start")
class TestVectorPreprocessing:
    def test_process_vector_criteria_waterdeel(self):
        # Filter the preset to only 1 criterion.
        preset_to_load = {
            "general": preset_collection["preset_benchmark_raw"]["general"],
            "criteria": {"waterdeel": preset_collection["preset_benchmark_raw"]["criteria"]["waterdeel"]},
        }
        mcda_engine = McdaCostSurfaceEngine(preset_to_load)
        mcda_engine.preprocess_vectors()


class TestRasterPreprocessing:
    # TODO
    pass
