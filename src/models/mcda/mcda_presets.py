from settings import Config
import geopandas as gpd
from src.models.mcda.vector_preprocessing.waterdeel import Waterdeel
from src.models.mcda.vector_preprocessing.wegdeel import Wegdeel

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
        # BGT attribute explanation: https://docs.geostandaarden.nl/imgeo/catalogus/bgt/#attributen-en-associaties
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
            },
            "wegdeel": {
                # https://geonovum.github.io/IMGeo-objectenhandboek/wegdeel
                "description": "Information on roads.",
                "layer_names": ["bgt_wegdeel_V"],
                "preprocessing_function": Wegdeel(),
                "constraint": False,
                "group": "b",
                "weight_values": {
                    # Column "bgt_functie"
                    "baan voor vliegverkeer": 126,
                    "fietspad": 63,
                    "inrit": 63,
                    "OV-baan": 126,
                    "overweg": 126,
                    "parkeervlak": -13,
                    "rijbaan autosnelweg": 126,
                    "rijbaan autoweg": 126,
                    "rijbaan lokale weg": 63,
                    "rijbaan regionale weg": 126,
                    "ruiterpad": 25,
                    "spoorbaan": 126,
                    "voetgangersgebied": 1,
                    "voetpad": 25,
                    "voetpad op trap": 38,
                    "woonerf": 25,
                    # Column bgt_fysiekvoorkomen
                    "gesloten verharding": 10,
                    "half verhard": 5,
                    "onverhard": 1,
                    "open verharding": 2,
                    "transitie": 1,
                },
                "ondersteunend_wegdeel": {
                    # https://geonovum.github.io/IMGeo-objectenhandboek/ondersteunendwegdeel
                    "description": "Complementary information on roads.",
                    "layer_names": [""],
                    "preprocessing_function": None,
                    "constraint": False,
                    "group": None,
                    "weight_values": {
                        # bgt_functie
                        "berm": 0,
                        "verkeerseiland": 0,
                        # bgt_fysiekvoorkomen
                        "gesloten verharding": 10,
                        "groenvoorziening": 1,
                        "half verhard": 5,
                        "onverhard": 2,
                        "open verharding": 1,
                    },
                },
                "onbegroeid_terreindeel": {
                    # https://geonovum.github.io/IMGeo-objectenhandboek/onbegroeidterreindeel
                    "description": "placeholder",
                    "layer_names": [],
                    "preprocessing_function": None,
                    "constraint": False,
                    "group": None,
                    "weight_values": {
                        # bgt_fysiekvoorkomen
                        "erf": 0,
                        "gesloten verharding": 0,
                        "half verhard": 0,
                        "onverhard": 0,
                        "open verharding": 0,
                        "zand": 0,
                    },
                },
                "begroeidterreindeel": {
                    # https://geonovum.github.io/IMGeo-objectenhandboek/begroeidterreindeel
                    "description": "placeholder",
                    "layer_names": [],
                    "preprocessing_function": None,
                    "constraint": False,
                    "group": None,
                    "weight_values": {
                        # bgt_fysiekvoorkomen
                        "boomteelt": 0,
                        "bouwland": 0,
                        "duin": 0,
                        "fruitteelt": 0,
                        "gemengd bos": 0,
                        "grasland agrarisch": 0,
                        "grasland overig": 0,
                        "groenvoorziening": 0,
                        "heide": 0,
                        "houtwal": 0,
                        "kwelder": 0,
                        "loofbos": 0,
                        "moeras": 0,
                        "naaldbos": 0,
                        "rietland": 0,
                        "struiken": 0,
                        # plus_fysiekvoorkomen
                        "akkerbouw": 0,
                        "bodembedekkers": 0,
                        "bollenteelt": 0,
                        "bosplantsoen": 0,
                        "braakliggend": 0,
                        "gesloten duinvegetatie": 0,
                        "gras- en kruidachtigen": 0,
                        "griend en hakhout": 0,
                        "heesters": 0,
                        "hoogstam boomgaarden": 0,
                        "klein fruit": 0,
                        "laagstam boomgaarden": 0,
                        "open duinvegetatie": 0,
                        "planten": 0,
                        "struikrozen": 0,
                        "vollegrondsteelt": 0,
                        "waardeOnbekend": 0,
                        "wijngaarden": 0,
                    },
                },
                "ondersteunend_waterdeel": {
                    # https://geonovum.github.io/IMGeo-objectenhandboek/ondersteunendwaterdeel
                    "description": "placeholder",
                    "layer_names": [],
                    "preprocessing_function": None,
                    "constraint": False,
                    "group": None,
                    "weight_values": {},
                },
                "pand": {
                    # https://geonovum.github.io/IMGeo-objectenhandboek/pand
                    "description": "placeholder",
                    "layer_names": [],
                    "preprocessing_function": None,
                    "constraint": False,
                    "group": None,
                    "weight_values": {
                        # bgt_type
                        "oever, slootkant": 0,
                        "slik": 0,
                    },
                },
                "overig_bouwwerk": {
                    # https://geonovum.github.io/IMGeo-objectenhandboek/overigbouwwerk
                    "description": "placeholder",
                    "layer_names": [],
                    "preprocessing_function": None,
                    "constraint": False,
                    "group": None,
                    "weight_values": {
                        # bgt_type
                        "functie": 0,
                        "bassin": 0,
                        "bezinkbak": 0,
                        "lage trafo": 0,
                        "niet-bgt": 0,  # Delete these records if they exist.
                        "open loods": 0,
                        "opslagtank": 0,
                        "overkapping": 0,
                        "windturbine": 0,
                    },
                },
                # TODO determine if we want to include this. It may be beneficial to place cables there?
                "tunneldeel": {
                    # https://geonovum.github.io/IMGeo-objectenhandboek/tunneldeel
                    "description": "placeholder",
                    "layer_names": [],
                    "preprocessing_function": None,
                    "constraint": False,
                    "group": None,
                    "weight_values": {"tunnel": 0},
                },
                "kunstwerkdeel": {
                    # https://geonovum.github.io/IMGeo-objectenhandboek/kunstwerkdeel
                    "description": "placeholder",
                    "layer_names": [],
                    "preprocessing_function": None,
                    "constraint": False,
                    "group": None,
                    "weight_values": {
                        # bgt_type
                        "gemaal": 0,
                        "hoogspanningsmast": 0,
                        "niet-bgt": 0,  # Delete these records if they exist.
                        "perron": 0,
                        "sluis": 0,
                        "steiger": 0,
                        "strekdam": 0,
                        "stuw": 0,
                    },
                },
                "small_above_ground_obstacles": {
                    # https://geonovum.github.io/IMGeo-objectenhandboek/scheiding
                    # https://geonovum.github.io/IMGeo-objectenhandboek/bak
                    # https://geonovum.github.io/IMGeo-objectenhandboek/bord
                    # https://geonovum.github.io/IMGeo-objectenhandboek/kast
                    # https://geonovum.github.io/IMGeo-objectenhandboek/mast
                    # https://geonovum.github.io/IMGeo-objectenhandboek/paal
                    # https://geonovum.github.io/IMGeo-objectenhandboek/put
                    # https://geonovum.github.io/IMGeo-objectenhandboek/sensor
                    # https://geonovum.github.io/IMGeo-objectenhandboek/straatmeubilair
                    "description": "placeholder",
                    "layer_names": [],
                    "preprocessing_function": None,
                    "constraint": False,
                    "group": None,
                    "weight_values": {
                        # scheiding: bgt_type
                        "damwand": 0,
                        "muur": 0,
                        "kademuur": 0,
                        "geluidsscherm": 0,
                        "hek": 0,
                        "niet-bgt": 0,  # Delete these records if they exist.
                        "walbescherming": 0,
                        # bak: plus_type
                        "afval apart plaats": 0,
                        "afvalbak": 0,
                        "bloembak": 0,
                        "container": 0,
                        "drinkbak": 0,
                        "zand- / zoutbak": 0,
                        # bord: plus_type
                        "dynamische snelheidsindicator": 0,
                        "informatiebord": 0,
                        "plaatsnaambord": 0,
                        "reclamebord": 0,
                        "scheepvaartbord": 0,
                        "straatnaambord": 0,
                        "verkeersbord": 0,
                        "verklikker transportleiding": 0,
                        "waarschuwingshek": 0,
                        "wegwijzer": 0,
                        # kast: plus_type
                        "CAI-kast": 0,
                        "elektrakast": 0,
                        "gaskast": 0,
                        "GMS kast": 0,
                        "openbare verlichtingkast": 0,
                        "rioolkast": 0,
                        "telecom kast": 0,
                        "telkast": 0,
                        "verkeersregelinstallatiekast": 0,
                        # mast: plus_type
                        "bovenleidingmast": 0,
                        "laagspanningsmast": 0,
                        "radarmast": 0,
                        "straalzender": 0,
                        "zendmast": 0,
                        # paal: plus_type
                        "afsluitpaal": 0,
                        "dijkpaal": 0,
                        "drukknoppaal": 0,
                        "grensmarkering": 0,
                        "haltepaal": 0,
                        "hectometerpaal": 0,
                        "lichtmast": 0,
                        "poller": 0,
                        "portaal": 0,
                        "praatpaal": 0,
                        "sirene": 0,
                        "telpaal": 0,
                        "verkeersbordpaal": 0,
                        "verkeersregelinstallatiepaal": 0,
                        "vlaggenmast": 0,
                        # put: plus_type
                        "benzine- / olieput": 0,
                        "brandkraan / -put": 0,
                        "drainageput": 0,
                        "gasput": 0,
                        "inspectie- / rioolput": 0,
                        "kolk": 0,
                        "waterleidingput": 0,
                        # sensor:
                        "detectielus": 0,
                        "camera": 0,
                        "debietmeter": 0,
                        "flitser": 0,
                        "GMS sensor": 0,
                        "hoogtedetectieapparaat": 0,
                        "lichtcel": 0,
                        "radar detector": 0,
                        "waterstandmeter": 0,
                        "weerstation": 0,
                        "windmeter": 0,
                        # straatmeubilair:
                        "abri": 0,
                        "bank": 0,
                        "betaalautomaat": 0,
                        "bolder": 0,
                        "brievenbus": 0,
                        "fietsenkluis": 0,
                        "fietsenrek": 0,
                        "fontein": 0,
                        "herdenkingsmonument": 0,
                        "kunstobject": 0,
                        "lichtpunt": 0,
                        "openbaar toilet": 0,
                        "parkeerbeugel": 0,
                        "picknicktafel": 0,
                        "reclamezuil": 0,
                        "slagboom": 0,
                        "speelvoorziening": 0,
                        "telefooncel": 0,
                        # Value occurs on all these tables, ignore.
                        "waardeOnbekend": 0,
                    },
                },
                "special_trees": {
                    # https://geonovum.github.io/IMGeo-objectenhandboek/vegetatieobject
                    "description": "placeholder",
                    "layer_names": [],
                    "preprocessing_function": None,
                    "constraint": False,
                    "group": None,
                    "weight_values": {
                        # plus_type
                        "haag": 0,
                        "boom": 0,
                        "waardeOnbekend": 0,
                    },
                },
                "protected_area": {
                    # https://geonovum.github.io/IMGeo-objectenhandboek/functioneelgebied
                    # Natura2000
                    "description": "placeholder",
                    "layer_names": [],
                    "preprocessing_function": None,
                    "constraint": False,
                    "group": None,
                    "weight_values": {
                        # bgt_type
                        "kering": 0,  # Dykes
                        "niet-bgt": 0,  # Delete these records if they exist.
                    },
                },
            },
        },
    }
}
