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
from rasterio import DatasetReader

from settings import Config
from utility_route_planner.models.mcda.exceptions import (
    RasterCellSizeTooSmall,
    InvalidGroupValue,
    InvalidSuitabilityRasterInput,
)

logger = structlog.get_logger(__name__)


def rasterize_vector_data(
    raster_prefix: str,
    criterion: str,
    project_area: shapely.MultiPolygon | shapely.Polygon,
    gdf_to_rasterize: gpd.GeoDataFrame,
    cell_size: int | float = Config.RASTER_CELL_SIZE,
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

    no_data = Config.INTERMEDIATE_RASTER_NO_DATA
    profile = {
        "driver": "GTiff",
        "dtype": "int16",
        "nodata": no_data,
        "compress": "lzw",
        "tiled": True,
        "width": width,
        "height": height,
        "blockxsize": Config.RASTER_BLOCK_SIZE,
        "blockysize": Config.RASTER_BLOCK_SIZE,
        "count": 1,
        "crs": rasterio.CRS.from_epsg(code=Config.CRS),
        "transform": affine.Affine(cell_size, 0.0, round(minx), 0.0, -cell_size, round(maxy)),
    }

    logger.info(f"Rasterizing layer: {criterion} in cell size: {cell_size} meters")
    # Highest value is leading within a criteria, using sorting we create the reverse painters algorithm effect.
    gdf_to_rasterize.sort_values("suitability_value", ascending=True, inplace=True)
    # Bump values which would be no-data prior to rasterizing to avoid marking them as no-data unwanted.
    gdf_to_rasterize.suitability_value = gdf_to_rasterize.suitability_value.replace(no_data, no_data + 1)
    # Reset values exceeding the min/max.
    gdf_to_rasterize.loc[
        gdf_to_rasterize.suitability_value < Config.INTERMEDIATE_RASTER_VALUE_LIMIT_LOWER, "suitability_value"
    ] = Config.INTERMEDIATE_RASTER_VALUE_LIMIT_LOWER
    gdf_to_rasterize.loc[
        gdf_to_rasterize.suitability_value > Config.INTERMEDIATE_RASTER_VALUE_LIMIT_UPPER, "suitability_value"
    ] = Config.INTERMEDIATE_RASTER_VALUE_LIMIT_UPPER
    # TODO check if we can use /vsimem/
    path_raster = Config.PATH_RESULTS / f"{raster_prefix+criterion}.tif"
    with rasterio.open(path_raster, "w+", **profile) as out:
        out_arr = out.read(1)
        shapes = ((geom, value) for geom, value in zip(gdf_to_rasterize.geometry, gdf_to_rasterize.suitability_value))
        burned = rasterio.features.rasterize(shapes=shapes, out=out_arr, transform=out.transform, all_touched=False)
        out.write_band(1, burned)

    return path_raster.__str__()


def merge_criteria_rasters(rasters_to_process: list[dict], final_raster_name: str) -> str:
    """
    List of rasters to combine and their respective group.

    Criteria in group a: highest value in group a is leading.
    Criteria in group b: values in group b are added or subtracted to group a if present.
    Criteria in group c: mark as no data if present, overruling group a and b.
    """
    logger.info(f"Starting summing {len(rasters_to_process)} rasters into the final cost surface.")

    # Split groups and process accordingly prior to summing all together.
    group_a, group_b, group_c = [], [], []
    for raster_dict in rasters_to_process:
        for key in raster_dict:
            if raster_dict[key] == "a":
                group_a.append(raster_dict)
            elif raster_dict[key] == "b":
                group_b.append(raster_dict)
            elif raster_dict[key] == "c":
                group_c.append(raster_dict)
            else:
                raise InvalidGroupValue(f"Invalid group value encountered during raster processing: {raster_dict[key]}")

    if len(group_a) > 0:
        merged_group_a, out_meta = process_raster_groups(group_a, "max")
    if len(group_b) > 0:
        merged_group_b, out_meta = process_raster_groups(group_b, "sum")
    if len(group_c) > 0:
        merged_group_c, _ = process_raster_groups(group_c, "sum")

    if len(group_b) > 0 and len(group_a) > 0:
        summed_raster = np.ma.sum([merged_group_a, merged_group_b], axis=0)
    elif len(group_b) > 0 and len(group_a) == 0:
        summed_raster = merged_group_b
    elif len(group_a) > 0 and len(group_b) == 0:
        summed_raster = merged_group_a
    else:
        raise InvalidSuitabilityRasterInput("No rasters to sum, exiting.")

    # Force values to fit in the int8 datatype.
    summed_raster = np.ma.clip(
        summed_raster, Config.FINAL_RASTER_VALUE_LIMIT_LOWER, Config.FINAL_RASTER_VALUE_LIMIT_UPPER
    )

    # Update the mask of the summed_raster so that every cell intersecting with group c is set to no data.
    if len(group_c) > 0:
        summed_raster.mask = np.ma.mask_or(summed_raster.mask, ~merged_group_c.mask)  # type: ignore

    out_meta.update(
        {
            "dtype": "int8",
            "compress": "lzw",
            "tiled": True,
            "blockxsize": Config.RASTER_BLOCK_SIZE,
            "blockysize": Config.RASTER_BLOCK_SIZE,
            "nodata": Config.FINAL_RASTER_NO_DATA,
        }
    )
    final_raster_path = Config.PATH_RESULTS / (final_raster_name + ".tif")
    with rasterio.open(final_raster_path, "w", **out_meta) as dest:
        dest.write(np.ma.filled(summed_raster, Config.FINAL_RASTER_NO_DATA), 1)

    return final_raster_path.__str__()


def process_raster_groups(group: list, method: str) -> tuple:
    """Per group, process the criteria arrays."""
    # Use numpy masks to ignore the nodata values in the computations.
    blocked_raster_dict = {}
    raster_meta_data = {}

    # TODO check fill value after stacking, summing. Is this value important? --> part of metadata as well.
    for idx, raster_dict in enumerate(group):
        with rasterio.open(list(raster_dict.keys())[0], "r") as src:
            raster_meta_data = src.meta.copy()
            for (row, col), window in src.block_windows(1):
                raster_block = src.read(1, window=window, masked=True)

                if idx == 0:
                    blocked_raster_dict[(row, col)] = raster_block

                match method:
                    case "sum":
                        result = np.ma.sum([blocked_raster_dict[(row, col)], raster_block], axis=0)
                    case "max":
                        result = np.ma.max(np.ma.stack((blocked_raster_dict[(row, col)], raster_block), axis=0), axis=0)
                    case _:
                        raise InvalidSuitabilityRasterInput(
                            f"Invalid method for processing raster group: {method}. Expected 'sum' or 'max'."
                        )
                blocked_raster_dict[(row, col)] = result

    return blocked_raster_dict, raster_meta_data


def read_raster_in_windows(src: DatasetReader):
    pass
