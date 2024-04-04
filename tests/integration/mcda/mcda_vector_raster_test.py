import pandas as pd
import pytest

from settings import Config
from src.models.mcda.mcda_engine import McdaCostSurfaceEngine
from src.models.mcda.vector_preprocessing.waterdeel import Waterdeel
from src.models.mcda.mcda_presets import preset_collection
from src.util.write import reset_geopackage
import geopandas as gpd
import shapely


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

    def test_process_waterdeel(self):
        weight_values = {
            # Column "class"
            "greppel, droge sloot": -10,
            "waterloop": 1,
            "watervlakte": 2,
            "zee": 3,
            # Column "plus-type"
            "rivier": 40,
            "sloot": 50,
            "kanaal": 60,
            "beek": 70,
            "gracht": 80,
            "bron": 90,
            "haven": 100,
            "meer, plas, ven, vijver": 110,
        }
        input_gdf = gpd.GeoDataFrame(
            [
                ["greppel, droge sloot", "WaardeOnbekend", shapely.Polygon([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]])],
                ["waterloop", "WaardeOnbekend", shapely.Polygon([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]])],
                ["waterloop", "rivier", shapely.Polygon([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]])],
                ["waterloop", "sloot", shapely.Polygon([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]])],
                ["waterloop", "kanaal", shapely.Polygon([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]])],
                ["waterloop", "beek", shapely.Polygon([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]])],
                ["waterloop", "gracht", shapely.Polygon([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]])],
                ["waterloop", "bron", shapely.Polygon([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]])],
                ["watervlakte", "haven", shapely.Polygon([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]])],
                ["watervlakte", "meer, plas, ven, vijver", shapely.Polygon([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]])],
                ["zee", "WaardeOnbekend", shapely.Polygon([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]])],
            ],
            columns=["class", "plus-type", "geometry"],
            crs=Config.CRS,
            geometry="geometry",
        )

        reclassified_gdf = Waterdeel._set_suitability_values(input_gdf, weight_values)
        pd.testing.assert_series_equal(
            reclassified_gdf["sv_1"],
            pd.Series([-10, 1, 1, 1, 1, 1, 1, 1, 2, 2, 3]),
            check_names=False,
            check_exact=True,
            check_dtype=False,
        )
        pd.testing.assert_series_equal(
            reclassified_gdf["sv_2"],
            pd.Series(["WaardeOnbekend", "WaardeOnbekend", 40, 50, 60, 70, 80, 90, 100, 110, "WaardeOnbekend"]),
            check_names=False,
            check_exact=True,
        )
        pd.testing.assert_series_equal(
            reclassified_gdf["suitability_value"],
            pd.Series([-10, 1, 40, 50, 60, 70, 80, 90, 100, 110, 3]),
            check_names=False,
            check_exact=True,
            check_dtype=False,
        )

        buffered_gdf = Waterdeel._update_geometry_values(reclassified_gdf, {"zee": 20})
        assert buffered_gdf.iloc[:10].area.round(1).unique().tolist() == [1.0]
        assert buffered_gdf.iloc[[10]].area.round(1).tolist() == [1335.6]

    def test_process_all_vectors(self):
        mcda_engine = McdaCostSurfaceEngine("preset_benchmark_raw")
        mcda_engine.preprocess_vectors()


@pytest.mark.usefixtures("setup_clean_start")
class TestRasterPreprocessing:
    def test_preprocess_rasters(self):
        preset_to_load = {
            "general": preset_collection["preset_benchmark_raw"]["general"],
            "criteria": {
                "waterdeel": preset_collection["preset_benchmark_raw"]["criteria"]["waterdeel"],
                "wegdeel": preset_collection["preset_benchmark_raw"]["criteria"]["wegdeel"],
            },
        }
        mcda_engine = McdaCostSurfaceEngine(preset_to_load)
        mcda_engine.preprocess_vectors()
        mcda_engine.preprocess_rasters(mcda_engine.processed_vectors)
