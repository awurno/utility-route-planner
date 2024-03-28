from settings import Config
import geopandas as gpd
from src.models.mcda.vector_preprocessing.waterdeel import Waterdeel

preset_collection = {
    "preset_benchmark_raw": {
        "general": {
            "description": "Preset used for benchmark results.",
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
            # https://geonovum.github.io/IMGeo-objectenhandboek/waterdeel
            "waterdeel": {
                "description": "Information on water.",
                "layer_names": ["bgt_waterdeel_V"],
                "preprocessing_function": Waterdeel(),
                "constraint": False,
                "group": "b",
                "weight_values": {
                    # Column "class"
                    "greppel, droge sloot": -13,
                    "waterloop": 126,
                    "watervlakte": 124,
                    "zee": 126,
                    # Column "plus-type"
                    "rivier": 126,
                    "sloot": 126,
                    "kanaal": 126,
                    "beek": 126,
                    "gracht": 126,
                    "bron": 126,
                    "haven": 126,
                    "meer, plas, ven, vijver": 125,
                },
                "geometry_values": {"zee": 20},  # buffer in meters
            }
        },
    }
}
