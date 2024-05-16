from unittest.mock import Mock

import geopandas as gpd
import numpy as np

import pytest

from settings import Config
from src.models.mcda.exceptions import InvalidSuitabilityValue, UnassignedValueFoundDuringReclassify

from src.models.mcda.load_mcda_preset import RasterPresetCriteria
from src.models.mcda.vector_preprocessing.base import VectorPreprocessorBase
from src.models.mcda.vector_preprocessing.validation import validate_values_to_reclassify


@pytest.fixture
def setup_base_class():
    class MyVectorPreprocessor(VectorPreprocessorBase):
        criterion = "test_criterion"

        def specific_preprocess(self, **kwargs):
            pass

    return MyVectorPreprocessor()


@pytest.fixture
def setup_mock_criterion():
    description = "Test"
    layer_names = ["bgt_begroeidterreindeel_V", "bgt_kast_P", "bgt_spoor_L"]
    constraint = False
    group = "a"
    weight_values = {"value1": 10, "value2": 20}

    test_criterion = RasterPresetCriteria(
        description=description,
        layer_names=layer_names,
        constraint=constraint,
        preprocessing_function=Mock(spec=VectorPreprocessorBase),
        group=group,
        weight_values=weight_values,
    )

    return test_criterion


class TestBaseVectorPreprocessing:
    def test_base_prepare_input_happy(self, setup_base_class, setup_mock_criterion):
        base_instance = setup_base_class
        criterion = setup_mock_criterion
        project_area = gpd.read_file(Config.PATH_PROJECT_AREA_EDE_COMPONISTENBUURT).iloc[0].geometry

        result = base_instance.prepare_input_data(project_area, criterion)
        assert len(result) == len(criterion.layer_names) - 1  # bgt_spoor is not inside the project area
        for gdf in result:
            assert gdf.columns.__contains__("suitability_value")
        raw = gpd.read_file(Config.PATH_INPUT_MCDA_GEOPACKAGE, layer="bgt_begroeidterreindeel_V")
        assert len(raw) > len(result[0])  # Check that the filtering worked for historic features.

    def test_base_prepare_input_data_not_in_project_area(self, setup_base_class, setup_mock_criterion):
        base_instance = setup_base_class
        criterion = setup_mock_criterion
        project_area = gpd.read_file(Config.PATH_PROJECT_AREA_EDE_COMPONISTENBUURT).iloc[0].geometry

        criterion.layer_names = ["bgt_spoor_L"]  # Outside the project area.
        result = base_instance.prepare_input_data(project_area, criterion)
        assert len(result) == 1
        assert result[0].empty

    @pytest.mark.parametrize(
        "invalid_input", [[1, 2, 3, "invalid"], [1, 2, 3, np.NaN], [1, 2, 3, [1, 2]], [1, 2, 3, None]]
    )
    def test_base_validate_result_unhappy(self, setup_base_class, invalid_input):
        base_instance = setup_base_class
        with pytest.raises(InvalidSuitabilityValue):
            base_instance.validate_result(gpd.GeoDataFrame({"suitability_value": invalid_input}))

    @pytest.mark.parametrize("valid_input", [[1, 211, 33], [20, 2, 300.123]])
    def test_base_validate_result_happy(self, setup_base_class, valid_input):
        base_instance = setup_base_class
        base_instance.validate_result(gpd.GeoDataFrame({"suitability_value": valid_input}))


def test_all_values_present():
    values_to_reclassify = [1, 2, 3]
    assigned_values = {1: "A", 2: "B", 3: "C"}
    validate_values_to_reclassify(values_to_reclassify, assigned_values)


@pytest.mark.parametrize("input_which_should_raise", [{1: "A", 2: "B", 3: "C"}, {1: "A", 4: 0}])
def test_missing_values(input_which_should_raise):
    values_to_reclassify = [1, 2, 4]
    wrong_input = input_which_should_raise
    with pytest.raises(UnassignedValueFoundDuringReclassify):
        validate_values_to_reclassify(values_to_reclassify, wrong_input)
