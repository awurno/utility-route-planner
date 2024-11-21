from settings import Config
import geopandas as gpd

from utility_route_planner.models.mcda.vector_preprocessing.begroeidterreindeel import BegroeidTerreindeel
from utility_route_planner.models.mcda.vector_preprocessing.existing_substations import ExistingSubstations
from utility_route_planner.models.mcda.vector_preprocessing.wegdeel import Wegdeel
from utility_route_planner.models.mcda.vector_preprocessing.excluded_area import ExcludedArea
from utility_route_planner.models.mcda.vector_preprocessing.existing_utilities import ExistingUtilities
from utility_route_planner.models.mcda.vector_preprocessing.kunstwerkdeel import Kunstwerkdeel
from utility_route_planner.models.mcda.vector_preprocessing.onbegroeid_terreindeel import OnbegroeidTerreindeel
from utility_route_planner.models.mcda.vector_preprocessing.ondersteunend_waterdeel import OndersteunendWaterdeel
from utility_route_planner.models.mcda.vector_preprocessing.ondersteunend_wegdeel import OndersteunendWegdeel
from utility_route_planner.models.mcda.vector_preprocessing.overig_bouwwerk import OverigBouwwerk
from utility_route_planner.models.mcda.vector_preprocessing.pand import Pand
from utility_route_planner.models.mcda.vector_preprocessing.protected_area import ProtectedArea
from utility_route_planner.models.mcda.vector_preprocessing.small_above_ground_obstacles import (
    SmallAboveGroundObstacles,
)
from utility_route_planner.models.mcda.vector_preprocessing.vegetation_object import VegetationObject
from utility_route_planner.models.mcda.vector_preprocessing.waterdeel import Waterdeel

preset_collection = {
    "preset_benchmark_raw": {
        "general": {
            "description": "Preset used for benchmark results.",
            "prefix": "bm_",
            "final_raster_name": "benchmark_suitability_raster",
            "project_area_geometry": gpd.read_file(
                Config.PYTEST_PATH_GEOPACKAGE_MCDA, layer=Config.PYTEST_LAYER_NAME_PROJECT_AREA
            )
            .iloc[0]
            .geometry,
        },
        # BGT attribute explanation: https://docs.geostandaarden.nl/imgeo/catalogus/bgt/#attributen-en-associaties
        "criteria": {
            # https://geonovum.github.io/IMGeo-objectenhandboek/waterdeel
            "waterdeel": {
                "description": "Information on water.",
                "layer_names": ["bgt_waterdeel_V"],
                "preprocessing_function": Waterdeel(),
                "group": "a",
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
                "geometry_values": {"zee": 20},
            },
            "wegdeel": {
                # https://geonovum.github.io/IMGeo-objectenhandboek/wegdeel
                "description": "Information on roads.",
                "layer_names": ["bgt_wegdeel_V"],
                "preprocessing_function": Wegdeel(),
                "group": "a",
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
            },
            "ondersteunend_wegdeel": {
                # https://geonovum.github.io/IMGeo-objectenhandboek/ondersteunendwegdeel
                "description": "Complementary information on roads.",
                "layer_names": ["bgt_ondersteunendwegdeel_V"],
                "preprocessing_function": OndersteunendWegdeel(),
                "group": "a",
                "weight_values": {
                    # bgt_functie
                    "berm": -25,
                    "verkeerseiland": 126,
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
                "layer_names": ["bgt_onbegroeidterreindeel_V"],
                "preprocessing_function": OnbegroeidTerreindeel(),
                "group": "a",
                "weight_values": {
                    # bgt_fysiekvoorkomen
                    "erf": 76,  # is now used as an approximation if ground is public or privately owned.
                    "gesloten verharding": 10,
                    "half verhard": 5,
                    "onverhard": 2,
                    "open verharding": 1,
                    "zand": 1,
                },
            },
            "begroeid_terreindeel": {
                # https://geonovum.github.io/IMGeo-objectenhandboek/begroeidterreindeel
                "description": "placeholder",
                "layer_names": ["bgt_begroeidterreindeel_V"],
                "preprocessing_function": BegroeidTerreindeel(),
                "group": "a",
                "weight_values": {
                    # bgt_fysiekvoorkomen
                    "boomteelt": 76,
                    "bouwland": 76,
                    "duin": 63,
                    "fruitteelt": 73,
                    "gemengd bos": 25,
                    "grasland agrarisch": 76,
                    "grasland overig": 76,
                    "groenvoorziening": -13,
                    "heide": 63,
                    "houtwal": 13,
                    "kwelder": 76,
                    "loofbos": 25,
                    "moeras": 38,
                    "naaldbos": 25,
                    "rietland": 76,
                    "struiken": -13,
                    # plus_fysiekvoorkomen
                    "akkerbouw": 76,
                    "bodembedekkers": -13,
                    "bollenteelt": 76,
                    "bosplantsoen": 25,
                    "braakliggend": 76,
                    "gesloten duinvegetatie": 63,
                    "gras- en kruidachtigen": -13,
                    "griend en hakhout": 25,
                    "heesters": -13,
                    "hoogstam boomgaarden": 76,
                    "klein fruit": 76,
                    "laagstam boomgaarden": 76,
                    "open duinvegetatie": 63,
                    "planten": -13,
                    "struikrozen": -13,
                    "vollegrondsteelt": 76,
                    "wijngaarden": 76,
                },
            },
            "ondersteunend_waterdeel": {
                # https://geonovum.github.io/IMGeo-objectenhandboek/ondersteunendwaterdeel
                "description": "placeholder",
                "layer_names": ["bgt_ondersteunendwaterdeel_V"],
                "preprocessing_function": OndersteunendWaterdeel(),
                "group": "a",
                "weight_values": {
                    # bgt_type
                    "oever, slootkant": 76,
                    "slik": 76,
                },
            },
            "pand": {
                # https://geonovum.github.io/IMGeo-objectenhandboek/pand
                "description": "placeholder",
                "layer_names": ["bgt_pand_V"],
                "preprocessing_function": Pand(),
                "group": "a",
                "weight_values": {"pand": 125},
            },
            "overig_bouwwerk": {
                # https://geonovum.github.io/IMGeo-objectenhandboek/overigbouwwerk
                "description": "placeholder",
                "layer_names": ["bgt_overigbouwwerk_V"],
                "preprocessing_function": OverigBouwwerk(),
                "group": "b",
                "weight_values": {
                    # bgt_type
                    "functie": 26,
                    "bassin": 1,
                    "bezinkbak": 1,
                    "lage trafo": 1,  # Includes Alliander substations, but not always. Is overwritten by existing_substation.
                    "niet-bgt": 1,  # Delete these records if they exist.
                    "open loods": 1,
                    "opslagtank": 1,
                    "overkapping": 1,
                    "windturbine": 126,
                },
            },
            # TODO discuss: Could be used as a multilayer raster. It may be beneficial to place cables there? Can optionally be guessed from the "relative hoogteligging" in wegdeel.
            # "tunneldeel": {
            #     # https://geonovum.github.io/IMGeo-objectenhandboek/tunneldeel
            #     "description": "placeholder",
            #     "layer_names": ["bgt_tunneldeel_V"],
            #     "preprocessing_function": None,
            #     "constraint": False,
            #     "group": "a",
            #     "weight_values": {"tunnel": 0},
            # },
            "kunstwerkdeel": {
                # https://geonovum.github.io/IMGeo-objectenhandboek/kunstwerkdeel
                "description": "placeholder",
                "layer_names": ["bgt_kunstwerkdeel_V"],
                "preprocessing_function": Kunstwerkdeel(),
                "group": "a",
                "weight_values": {
                    # bgt_type
                    "gemaal": 126,
                    "hoogspanningsmast": 126,
                    "niet-bgt": 1,  # Delete these records if they exist.
                    "perron": 126,
                    "sluis": 126,
                    "steiger": 126,
                    "strekdam": 126,
                    "stuw": 126,
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
                # The order of layers matter here, first two must be bgt_scheiding.
                "layer_names": [
                    "bgt_scheiding_V",
                    "bgt_scheiding_L",
                    "bgt_bak_P",
                    "bgt_bord_P",
                    "bgt_kast_P",
                    "bgt_mast_P",
                    "bgt_paal_P",
                    "bgt_put_P",
                    "bgt_sensor_P",
                    "bgt_straatmeubilair_P",
                ],
                "preprocessing_function": SmallAboveGroundObstacles(),
                "group": "b",
                "weight_values": {
                    # scheiding: bgt_type
                    "damwand": 76,
                    "muur": 76,
                    "kademuur": 76,
                    "geluidsscherm": 76,
                    "hek": 13,
                    "niet-bgt": 1,  # Delete these records if they exist.
                    "walbescherming": 76,
                    # bak: plus_type
                    "afval apart plaats": 76,
                    "afvalbak": 1,
                    "bloembak": 1,
                    "container": 26,
                    "drinkbak": 1,
                    "zand- / zoutbak": 1,
                    # bord: plus_type
                    "dynamische snelheidsindicator": 1,
                    "informatiebord": 1,
                    "plaatsnaambord": 1,
                    "reclamebord": 1,
                    "scheepvaartbord": 1,
                    "straatnaambord": 1,
                    "verkeersbord": 1,
                    "verklikker transportleiding": 1,
                    "waarschuwingshek": 1,
                    "wegwijzer": 1,
                    # kast: plus_type
                    "CAI-kast": 1,
                    "elektrakast": 1,
                    "gaskast": 1,
                    "GMS kast": 1,
                    "openbare verlichtingkast": 1,
                    "rioolkast": 1,
                    "telecom kast": 1,
                    "telkast": 1,
                    "verkeersregelinstallatiekast": 1,
                    # mast: plus_type
                    "bovenleidingmast": 1,
                    "laagspanningsmast": 1,
                    "radarmast": 1,
                    "straalzender": 1,
                    "zendmast": 1,
                    # paal: plus_type
                    "afsluitpaal": 1,
                    "dijkpaal": 1,
                    "drukknoppaal": 1,
                    "grensmarkering": 1,
                    "haltepaal": 1,
                    "hectometerpaal": 1,
                    "lichtmast": 1,
                    "poller": 1,
                    "portaal": 1,
                    "praatpaal": 1,
                    "sirene": 1,
                    "telpaal": 1,
                    "verkeersbordpaal": 1,
                    "verkeersregelinstallatiepaal": 1,
                    "vlaggenmast": 1,
                    # put: plus_type
                    "benzine- / olieput": 1,
                    "brandkraan / -put": 1,
                    "drainageput": 1,
                    "gasput": 1,
                    "inspectie- / rioolput": 1,
                    "kolk": 1,
                    "waterleidingput": 1,
                    # sensor:
                    "detectielus": 1,
                    "camera": 1,
                    "debietmeter": 1,
                    "flitser": 1,
                    "GMS sensor": 1,
                    "hoogtedetectieapparaat": 1,
                    "lichtcel": 1,
                    "radar detector": 1,
                    "waterstandmeter": 1,
                    "weerstation": 1,
                    "windmeter": 1,
                    # straatmeubilair:
                    "abri": 1,
                    "bank": 1,
                    "betaalautomaat": 1,
                    "bolder": 1,
                    "brievenbus": 1,
                    "fietsenkluis": 1,
                    "fietsenrek": 1,
                    "fontein": 1,
                    "herdenkingsmonument": 1,
                    "kunstobject": 1,
                    "lichtpunt": 1,
                    "openbaar toilet": 1,
                    "parkeerbeugel": 1,
                    "picknicktafel": 1,
                    "reclamezuil": 1,
                    "slagboom": 1,
                    "speelvoorziening": 1,
                    "telefooncel": 1,
                    # Value occurs on all these tables, remove if present.
                    "waardeOnbekend": 1,
                },
            },
            "vegetation_object": {
                # https://geonovum.github.io/IMGeo-objectenhandboek/vegetatieobject
                "description": "placeholder",
                "layer_names": ["bgt_vegetatieobject_P", "bgt_vegetatieobject_V"],
                "preprocessing_function": VegetationObject(),
                "group": "b",
                "weight_values": {
                    # plus_type
                    "haag": 25,
                    "boom": 76,
                    "waardeOnbekend": 1,  # Delete these records if they exist.
                },
                "geometry_values": {"boom": 5},
            },
            "protected_area": {
                # https://geonovum.github.io/IMGeo-objectenhandboek/functioneelgebied
                "description": "Protected area such as dykes and nature which may have additional rules or policies.",
                "layer_names": ["bgt_functioneelgebied_V", "natura2000"],
                "preprocessing_function": ProtectedArea(),
                "group": "b",
                "weight_values": {
                    # bgt_type
                    "kering": 25,  # Dykes, all other features of bgt_functioneelgebied are removed.
                    "natura2000": 25,
                    # TODO add these datasources and expand test in mcda_vector_raster_test.py
                    # "Aardkundig_monument": 1,
                    # "Archeologisch_monument": 1,
                    # "niet_gesprongen_explosieven_wo2": 1,
                    # "brosse_leidingen": 1,
                    # "verontreinigde_grond": 1,
                    # "groene_en_rijksmonumenten": 1,
                },
            },
            "existing_utilities": {
                # TenneT, Alliander, Gasunie.
                "description": "Existing utility assets for gas, electricity.",
                "layer_names": [
                    "hoogspanningskabel_bovengronds",
                    "hoogspanningskabel_ondergronds",
                    "gasunie_leidingen",
                    "alliander_stationsterrein",
                ],
                "preprocessing_function": ExistingUtilities(),
                "group": "b",
                "weight_values": {
                    "hoogspanning_bovengronds": 10,  # TenneT & Alliander combined.
                    "hoogspanning_ondergronds": 30,  # TenneT & Alliander combined.
                    "gasunie_leidingen": 20,
                    "alliander_stationsterrein": 10,  # Only the larger (>30m2) areas are included.
                },
                "geometry_values": {
                    "hoogspanning_bovengronds_buffer": 5,
                    "hoogspanning_ondergronds_buffer": 5,
                    "gasunie_leidingen_buffer": 5,
                },
            },
            "existing_substations": {
                "description": "Existing substations.",
                "layer_names": ["alliander_middenspanningsstation"],
                "preprocessing_function": ExistingSubstations(),
                "group": "a",
                "weight_values": {
                    "alliander_middenspanningsstation": 76,  # Building footprint of a (sub)station.
                },
            },
            "excluded_area": {
                "description": "Area to exclude were no utility network can be placed, manually provided.",
                "layer_names": ["area_to_exclude"],
                "preprocessing_function": ExcludedArea(),
                "group": "c",
                "weight_values": {
                    # The weight value does not matter as group c determines that all features are excluded.
                    "constraint": 1,
                },
            },
        },
    },
}
