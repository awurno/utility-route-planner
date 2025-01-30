from dataclasses import dataclass

import numpy as np
from affine import Affine
from pyproj import CRS
from rasterio.windows import Window

from settings import Config


# TODO maak dit NIET te generiek, het moet gewoon 1 preset zijn.
@dataclass
class McdaModelGeneral:
    description: str = "Preset voor stedelijk gebied."
    prefix: str = "b_"
    raster_resolution: tuple = (0.5, 0.5)
    final_raster_name: str = "benchmark_suitability_raster"
    final_raster_value_limit_lower: int = 0
    final_raster_value_limit_upper: int = 126
    intermediate_raster_value_limit_lower: int = -126
    intermediate_raster_value_limit_upper: int = 126
    raster_no_data: int = -127


@dataclass
class McdaModelCriteria:
    name: str
    group: str
    constraint: bool
    weight_values: dict
    geometry_values: dict

    def __init__(self, name, constraint, group, weight_values, geometry_values):
        self.name = name
        self.constraint = constraint
        self.group = group  # TODO check if it is a or b
        self.weight_values = weight_values  # TODO validate
        self.geometry_values = geometry_values  # TODO validate


@dataclass
class McdaModelPreset:
    # https://geoforum.nl/t/bgt-data-inlezen-in-python-met-geopandas/8047/5
    general = McdaModelGeneral
    criteria = McdaModelCriteria


@dataclass
class McdaRasterSettings:
    width: int
    height: int
    nodata: int
    transform: Affine
    driver: str = "GTiff"
    compress: str = "lzw"
    tiled: bool = True
    dtype: str = "int8"
    count: int = 1
    crs: CRS = CRS.from_epsg(code=Config.CRS)


@dataclass
class McdaRasterBlock:
    array: np.ma.MaskedArray
    window: Window
