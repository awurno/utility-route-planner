from unittest import mock
from unittest.mock import MagicMock

import pydantic
import pytest
import geopandas as gpd

from settings import Config
from src.models.mcda.load_mcda_preset import load_preset
from src.models.mcda.vector_preprocessing.base import VectorPreprocessorBase


def test_load_benchmark_with_default_settings():
    # Pydantic validates the values in the model.
    load_preset(Config.RASTER_PRESET_NAME)


def test_invalid_preset_name():
    with pytest.raises(ValueError):
        load_preset("this_preset_does_not_exist_and_should_raise_an_error")


@pytest.mark.parametrize("invalid_input", [1, False, None, [1, 2, 3]])
def test_invalid_input(invalid_input):
    with pytest.raises(ValueError):
        load_preset(invalid_input)


@pytest.fixture
def setup_raster_preset_dummy():
    dummy_preset = {
        "general": {
            "description": "Dummy preset.",
            "prefix": "b_",
            "raster_resolution": (Config.RASTER_CELL_SIZE, Config.RASTER_CELL_SIZE),
            "intermediate_raster_value_limit_lower": Config.INTERMEDIATE_RASTER_VALUE_LIMIT_LOWER,
            "intermediate_raster_value_limit_upper": Config.INTERMEDIATE_RASTER_VALUE_LIMIT_UPPER,
            "final_raster_name": "benchmark_suitability_raster",
            "final_raster_value_limit_lower": Config.FINAL_RASTER_VALUE_LIMIT_LOWER,
            "final_raster_value_limit_upper": Config.FINAL_RASTER_VALUE_LIMIT_UPPER,
            "raster_no_data": Config.RASTER_NO_DATA,
            "project_area_geometry": gpd.read_file(Config.PATH_PROJECT_AREA_EDE_COMPONISTENBUURT).iloc[0].geometry,
        },
        "criteria": {
            "test_criteria": {
                "description": "Information on something.",
                "layer_names": ["my_layer_name"],
                "preprocessing_function": MagicMock(spec=VectorPreprocessorBase),
                "constraint": False,
                "group": "b",
                "weight_values": {
                    "w_dummy": 50,
                    "w_dummy2": 1,
                },
                "geometry_values": {"buffer_m_dummy": 20},
            }
        },
    }
    yield dummy_preset


class TestCriteriaInput:
    def test_invalid_group(self, setup_raster_preset_dummy):
        preset_input_dict = setup_raster_preset_dummy
        preset_input_dict["criteria"]["test_criteria"]["group"] = "c"
        with pytest.raises(pydantic.ValidationError):
            load_preset(preset_input_dict)

    def test_correct_group(self, setup_raster_preset_dummy):
        preset_input_dict = setup_raster_preset_dummy
        preset_input_dict["criteria"]["test_criteria"]["group"] = "a"
        load_preset(preset_input_dict)

        preset_input_dict["criteria"]["test_criteria"]["group"] = "b"
        load_preset(preset_input_dict)

    def test_invalid_constraint(self, setup_raster_preset_dummy):
        preset_input_dict = setup_raster_preset_dummy

        preset_input_dict["criteria"]["test_criteria"]["constraint"] = "wrong-value"
        with pytest.raises(pydantic.ValidationError):
            load_preset(preset_input_dict)

    def test_correct_constraint(self, setup_raster_preset_dummy):
        preset_input_dict = setup_raster_preset_dummy

        preset_input_dict["criteria"]["test_criteria"]["constraint"] = False
        load_preset(preset_input_dict)

        preset_input_dict["criteria"]["test_criteria"]["constraint"] = "false"
        load_preset(preset_input_dict)

        preset_input_dict["criteria"]["test_criteria"]["constraint"] = True
        load_preset(preset_input_dict)

        preset_input_dict["criteria"]["test_criteria"]["constraint"] = "true"
        load_preset(preset_input_dict)

    @pytest.mark.parametrize(
        "valid_input",
        [
            Config.INTERMEDIATE_RASTER_VALUE_LIMIT_LOWER,
            Config.INTERMEDIATE_RASTER_VALUE_LIMIT_UPPER,
            Config.INTERMEDIATE_RASTER_VALUE_LIMIT_UPPER - 1,
        ],
    )
    def test_correct_weight_values(self, setup_raster_preset_dummy, valid_input):
        preset_input_dict = setup_raster_preset_dummy
        preset_input_dict["criteria"]["test_criteria"]["weight_values"]["w_dummy"] = valid_input
        load_preset(preset_input_dict)

    @pytest.mark.parametrize(
        "invalid_input",
        [Config.INTERMEDIATE_RASTER_VALUE_LIMIT_LOWER - 1, Config.INTERMEDIATE_RASTER_VALUE_LIMIT_UPPER + 1],
    )
    def test_invalid_weight_values(self, setup_raster_preset_dummy, invalid_input):
        preset_input_dict = setup_raster_preset_dummy
        preset_input_dict["criteria"]["test_criteria"]["weight_values"]["w_dummy"] = invalid_input
        with pytest.raises(pydantic.ValidationError):
            load_preset(preset_input_dict)

    @pytest.mark.parametrize(
        "invalid_input",
        [[1, 2], 1, False, "layer_name_invalid_too", ["layer_name_invalid", False]],
    )
    def test_invalid_layer_name_values(self, setup_raster_preset_dummy, invalid_input):
        preset_input_dict = setup_raster_preset_dummy
        preset_input_dict["criteria"]["test_criteria"]["layer_names"] = invalid_input
        with pytest.raises(pydantic.ValidationError):
            load_preset(preset_input_dict)

    # TODO ask Jasper how to fix this.
    @mock.patch("src.models.mcda.load_mcda_preset.RasterPresetCriteria.get_existing_layers_geopackage")
    @pytest.mark.parametrize(
        "valid_input",
        [["single_layer"], ["layer1", "layer2"]],
    )
    def test_valid_layer_name_values(
        self, setup_raster_preset_dummy, valid_input, patched_get_existing_layers_geopackage
    ):
        preset_input_dict = setup_raster_preset_dummy
        patched_get_existing_layers_geopackage.return_value = ["single_layer", "layer1", "layer2"]
        preset_input_dict["criteria"]["test_criteria"]["layer_names"] = valid_input
        load_preset(preset_input_dict)
