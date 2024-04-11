import math

import shapely
import structlog
import rasterio
import rasterio.features
import rasterio.merge
import rasterio.mask
import numpy as np
import geopandas as gpd
import affine

from settings import Config
from src.models.mcda.exceptions import RasterCellSizeTooSmall, InvalidGroupValue, InvalidSuitabilityRasterInput

logger = structlog.get_logger(__name__)


def rasterize_vector_data(
    raster_prefix: str,
    criterion: str,
    project_area: shapely.MultiPolygon | shapely.Polygon,
    gdf_to_rasterize: gpd.GeoDataFrame,
    cell_size: int | float,
) -> str:
    """
    Burns the vector data to the project area in the desired raster cell size.
    If values overlap in the geodataframe, pick the highest value.
    """
    minx, miny, maxx, maxy = project_area.bounds

    # In order to fit the given cell size to the project area bounds, we slightly extend the maxx and maxy accordingly.
    if cell_size > maxx - minx or cell_size > maxy - miny:
        raise RasterCellSizeTooSmall("Given raster cell size is too large for the project area.")

    width = math.ceil((maxx - minx) / cell_size)
    height = math.ceil((maxy - miny) / cell_size)

    # 0 is never allowed as a suitability_value and is therefore a safe nodata value.
    nodata = 0
    profile = {
        "driver": "GTiff",
        "dtype": "int16",
        "nodata": nodata,
        "compress": "lzw",
        "tiled": True,
        "width": width,
        "height": height,
        "blockxsize": Config.RASTER_BLOCK_SIZE,
        "blockysize": Config.RASTER_BLOCK_SIZE,
        "count": 1,
        "crs": rasterio.CRS.from_epsg(Config.CRS),  # rasterio.crs.CRS({"init": "epsg:28992"})
        "transform": affine.Affine(cell_size, 0.0, round(minx), 0.0, -cell_size, round(maxy)),
    }

    logger.info(f"Rasterizing layer: {criterion} in cell size: {cell_size} meters")
    # TODO check if we can use /vsimem/
    # Highest value is leading within a criteria, using sorting we create the reverse painters algorithm effect.
    gdf_to_rasterize.sort_values("suitability_value", ascending=True, inplace=True)
    path_raster = Config.PATH_RESULTS / f"{raster_prefix+criterion}.tif"
    with rasterio.open(path_raster, "w+", **profile) as out:
        out_arr = out.read(1)
        shapes = ((geom, value) for geom, value in zip(gdf_to_rasterize.geometry, gdf_to_rasterize.suitability_value))
        burned = rasterio.features.rasterize(
            shapes=shapes, fill=nodata, out=out_arr, transform=out.transform, all_touched=False
        )
        burned = np.clip(
            burned, Config.INTERMEDIATE_RASTER_VALUE_LIMIT_LOWER, Config.INTERMEDIATE_RASTER_VALUE_LIMIT_UPPER
        )
        out.write_band(1, burned)

    return path_raster.__str__()


def sum_rasters(rasters_to_sum: list[dict], final_raster_name: str) -> str:
    """
    List of rasters to sum and their respective group.

    Highest value (most expensive) is leading in the group a
    Values are added group b

    """
    logger.info(f"Starting summing {len(rasters_to_sum)} rasters into the final cost surface.")

    group_a, group_b = [], []
    for raster_dict in rasters_to_sum:
        for key in raster_dict:
            if raster_dict[key] == "a":
                group_a.append(raster_dict)
            elif raster_dict[key] == "b":
                group_b.append(raster_dict)
            else:
                raise InvalidGroupValue(f"Invalid group value encountered during raster processing: {raster_dict[key]}")

    merged_group_a, merged_group_b = [], []
    if len(group_a) > 0:
        # TODO replace with just our own method and mask afterwards? Saves overhead of rasterio
        src_files_to_mosaic = [rasterio.open(list(i.keys())[0]) for i in group_a]
        merged_group_a, out_transform = rasterio.merge.merge(src_files_to_mosaic, method="max")

    # TODO check how we can avoid creating nodata values by accident during summing. Ignore nodata values in the array during summing?
    if len(group_b) > 0:
        src_files_to_mosaic = [rasterio.open(list(i.keys())[0]) for i in group_b]
        merged_group_b, out_transform = rasterio.merge.merge(src_files_to_mosaic, method="sum")
        # for idx, raster_dict in enumerate(group_b):
        #     with rasterio.open(list(raster_dict.keys())[0], "r") as src:
        #         if idx == 0:
        #             merged_group_b = src.read(1)
        #         else:
        #             merged_group_b += src.read(1)

    if len(group_b) > 0 and len(group_a) > 0:
        summed_raster = merged_group_a[0] + merged_group_b[0]
    elif len(group_b) > 0 and len(group_a) == 0:
        summed_raster = merged_group_b[0]
    elif len(group_a) > 0 and len(group_b) == 0:
        summed_raster = merged_group_a[0]
    else:
        raise InvalidSuitabilityRasterInput("No rasters to sum, exiting.")

    summed_raster = np.clip(summed_raster, Config.FINAL_RASTER_VALUE_LIMIT_LOWER, Config.FINAL_RASTER_VALUE_LIMIT_UPPER)
    # mask with project area to set all values outside the mask to nodata again.
    mask, _, _ = rasterio.mask.raster_geometry_mask(
        src_files_to_mosaic[0],  # TODO replace
        [gpd.read_file(Config.PATH_PROJECT_AREA_EDE_COMPONISTENBUURT).iloc[0].geometry],
    )
    summed_raster[mask] = 0

    # TODO experiment with replacing the nodata to np.inf during the lcpa part. During loading the raster in load.py. I think it ignores negative values?
    # TODO add nodata for final raster as config variable, reuse this for LCPA
    out_meta = src_files_to_mosaic[0].meta.copy()
    out_meta.update(
        {
            "dtype": "uint8",
            "compress": "lzw",
            "tiled": True,
            "blockxsize": Config.RASTER_BLOCK_SIZE,
            "blockysize": Config.RASTER_BLOCK_SIZE,
            "nodata": 0,
        }
    )
    final_raster_path = Config.PATH_RESULTS / (final_raster_name + ".tif")
    with rasterio.open(final_raster_path, "w", **out_meta) as dest:
        dest.write(summed_raster, 1)

    return final_raster_path.__str__()
