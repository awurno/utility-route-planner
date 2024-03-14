from settings import Config
import geopandas as gpd
from src.models.mcda.vector_preprocessing.waterdeel import Waterdeel

preset_collection = {
    "preset_benchmark_raw": {
        "general": {
            "description": "Preset used for benchmark results.",
            "prefix": "b_",
            "raster_resolution": (Config.RASTER_CELL_SIZE, Config.RASTER_CELL_SIZE),
            "intermediate_raster_value_limit_lower": -126,
            "intermediate_raster_value_limit_upper": 126,
            "final_raster_name": "benchmark_suitability_raster",
            "final_raster_value_limit_lower": 0,
            "final_raster_value_limit_upper": 126,
            "raster_no_data": Config.RASTER_NO_DATA,
            "project_area_geometry": gpd.read_file(Config.PATH_PROJECT_AREA_EDE_COMPONISTENBUURT).iloc[0].geometry,
        },
        "criteria": {
            "waterdeel": {
                "description": "Information on water.",
                "preprocessing_function": Waterdeel(),
                "constraint": False,
                "group": "a",
                "weight_values": {
                    "w_zee": 126,
                    "w_watervlakte": 126,
                    "w_waterloop": 126,
                    "w_rivier": 126,
                    "w_sloot": 126,
                    "w_kanaal": 126,
                    "w_beek": 126,
                    "w_gracht": 126,
                    "w_bron": 126,
                    "w_haven": 126,
                    "w_meer_plas_ven_vijver": 126,
                    "w_greppel_droge_sloot": -13,
                },
                "geometry_values": {"buffer_m_zee": 20},
            }
        },
    }
}
