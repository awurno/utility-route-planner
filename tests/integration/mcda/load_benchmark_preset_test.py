import pytest

from settings import Config
from src.models.mcda.load_mcda_preset import load_preset


def test_load_benchmark_with_default_settings():
    # Pydantic validates the values in the model
    load_preset(Config.RASTER_PRESET_NAME)


def test_invalid_preset_name():
    with pytest.raises(ValueError):
        load_preset("this_preset_does_not_exist_and_should_raise_an_error")
