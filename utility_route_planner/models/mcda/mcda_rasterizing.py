import math
from dataclasses import asdict

import affine
import shapely
import structlog
import rasterio
import rasterio.features
import rasterio.merge
import rasterio.mask
import numpy as np
import geopandas as gpd
from rasterio.windows import Window

from models.mcda.mcda_datastructures import McdaRasterSettings, McdaRasterBlock
from settings import Config
from utility_route_planner.models.mcda.exceptions import (
    InvalidGroupValue,
    InvalidSuitabilityRasterInput,
    RasterCellSizeTooSmall,
)

logger = structlog.get_logger(__name__)


def get_raster_settings(
    project_area: shapely.MultiPolygon | shapely.Polygon, cell_size: float = Config.RASTER_CELL_SIZE
) -> McdaRasterSettings:
    minx, miny, maxx, maxy = project_area.bounds

    # In order to fit the given cell size to the project area bounds, we slightly extend the maxx and maxy accordingly.
    if cell_size > maxx - minx or cell_size > maxy - miny:
        raise RasterCellSizeTooSmall("Given raster cell size is too large for the project area.")

    raster_settings = McdaRasterSettings(
        width=math.ceil((maxx - minx) / cell_size),
        height=math.ceil((maxy - miny) / cell_size),
        nodata=Config.INTERMEDIATE_RASTER_NO_DATA,
        transform=affine.Affine(cell_size, 0.0, round(minx), 0.0, -cell_size, round(maxy)),
    )
    return raster_settings


def rasterize_vector_data(
    criterion: str,
    gdf_to_rasterize: gpd.GeoDataFrame,
    raster_settings: McdaRasterSettings,
) -> np.ndarray:
    """
    Burns the vector data to the project area in the desired raster cell size.
    If values overlap in the geodataframe, pick the highest value.
    """

    # TODO make raster cell size param dynamic
    logger.info(f"Rasterizing layer: {criterion} in cell size: {Config.RASTER_CELL_SIZE} meters")
    # Highest value is leading within a criteria, using sorting we create the reverse painters algorithm effect.
    gdf_to_rasterize.sort_values("suitability_value", ascending=True, inplace=True)
    # Bump values which would be no-data prior to rasterizing to avoid marking them as no-data unwanted.
    gdf_to_rasterize.suitability_value = gdf_to_rasterize.suitability_value.replace(
        raster_settings.nodata, raster_settings.nodata + 1
    )
    # Reset values exceeding the min/max.
    gdf_to_rasterize.loc[
        gdf_to_rasterize.suitability_value < Config.INTERMEDIATE_RASTER_VALUE_LIMIT_LOWER, "suitability_value"
    ] = Config.INTERMEDIATE_RASTER_VALUE_LIMIT_LOWER
    gdf_to_rasterize.loc[
        gdf_to_rasterize.suitability_value > Config.INTERMEDIATE_RASTER_VALUE_LIMIT_UPPER, "suitability_value"
    ] = Config.INTERMEDIATE_RASTER_VALUE_LIMIT_UPPER

    out_array = np.full(
        (raster_settings.height, raster_settings.width), Config.INTERMEDIATE_RASTER_NO_DATA, dtype="int16"
    )
    shapes = ((geom, value) for geom, value in zip(gdf_to_rasterize.geometry, gdf_to_rasterize.suitability_value))
    rasterized_vector = rasterio.features.rasterize(
        shapes=shapes, out=out_array, transform=raster_settings.transform, all_touched=False
    )

    return rasterized_vector


def merge_criteria_rasters(
    rasters_to_process: list[tuple[str, np.ndarray, str]],
) -> dict[tuple[int, int], McdaRasterBlock]:
    """
    List of rasters to combine and their respective group.

    Criteria in group a: highest value in group a is leading.
    Criteria in group b: values in group b are added or subtracted to group a if present.
    Criteria in group c: mark as no data if present, overruling group a and b.
    """
    logger.info(f"Starting summing {len(rasters_to_process)} rasters into the final cost surface.")

    # Split groups and process accordingly prior to summing all together.
    group_a, group_b, group_c = [], [], []
    for rasterized_vector in rasters_to_process:
        match rasterized_vector[2]:
            case "a":
                group_a.append(rasterized_vector)
            case "b":
                group_b.append(rasterized_vector)
            case "c":
                group_c.append(rasterized_vector)
            case _:
                raise InvalidGroupValue(
                    f"Invalid group value encountered during raster processing: {rasterized_vector[2]}"
                )

    merged_group_a = {}
    merged_group_b = {}
    merged_group_c = {}
    if len(group_a) > 0:
        merged_group_a = process_raster_groups(group_a, "max")
    if len(group_b) > 0:
        merged_group_b = process_raster_groups(group_b, "sum")
    if len(group_c) > 0:
        merged_group_c = process_raster_groups(group_c, "sum")

    summed_raster = {}
    if len(group_b) > 0 and len(group_a) > 0:
        for key in merged_group_a:
            summed_array = np.ma.sum([merged_group_a[key].array, merged_group_b[key].array], axis=0)
            summed_raster[key] = McdaRasterBlock(array=summed_array, window=merged_group_a[key].window)

    elif len(group_b) > 0 and len(group_a) == 0:
        summed_raster = merged_group_b
    elif len(group_a) > 0 and len(group_b) == 0:
        summed_raster = merged_group_a
    else:
        raise InvalidSuitabilityRasterInput("No rasters to sum, exiting.")

    # Force values to fit in the int8 datatype
    for (row, col), block in summed_raster.items():
        summed_raster[row, col].array = np.ma.clip(
            block.array, Config.FINAL_RASTER_VALUE_LIMIT_LOWER, Config.FINAL_RASTER_VALUE_LIMIT_UPPER
        )

    # Update the mask of the summed_raster so that every cell intersecting with group c is set to no data.
    if len(group_c) > 0:
        for window_index in summed_raster.keys():
            summed_raster[window_index].array.mask = np.ma.mask_or(
                summed_raster[window_index].array.mask, ~merged_group_c[window_index].array.mask
            )

    return summed_raster


def process_raster_groups(group: list, method: str) -> dict[tuple[int, int], McdaRasterBlock]:
    """Per group, process the criteria arrays."""
    # Use numpy masks to ignore the nodata values in the computations.
    blocked_raster_dict: dict[tuple[int, int], McdaRasterBlock] = {}

    block_height, block_width = Config.RASTER_BLOCK_SIZE, Config.RASTER_BLOCK_SIZE
    for idx, raster_dict in enumerate(group):
        matrix = raster_dict[1]
        for row, col, raster_block in iter_blocks(matrix, block_height, block_width):
            if idx == 0:
                blocked_raster_dict[(row, col)] = raster_block
                continue

            match method:
                case "sum":
                    result = np.ma.sum([blocked_raster_dict[(row, col)].array, raster_block.array], axis=0)
                case "max":
                    result = np.ma.max(
                        np.ma.stack((blocked_raster_dict[(row, col)].array, raster_block.array), axis=0), axis=0
                    )
                case _:
                    raise InvalidSuitabilityRasterInput(
                        f"Invalid method for processing raster group: {method}. Expected 'sum' or 'max'."
                    )
            blocked_raster_dict[(row, col)].array = result

    return blocked_raster_dict


def iter_blocks(matrix: np.ndarray, block_width: int, block_height: int):
    for row, row_offset in enumerate(range(0, matrix.shape[0], block_width)):
        for col, coll_offset in enumerate(range(0, matrix.shape[1], block_height)):
            chunk = matrix[row_offset : row_offset + block_width, coll_offset : coll_offset + block_height]
            masked_chunk = np.ma.masked_equal(chunk, Config.INTERMEDIATE_RASTER_NO_DATA)
            window = Window(coll_offset, row_offset, block_width, block_height)
            yield row, col, McdaRasterBlock(masked_chunk, window)


def construct_complete_raster(
    summed_raster: dict[tuple[int, int], McdaRasterBlock], raster_settings: McdaRasterSettings
) -> np.ma.array:
    complete_raster = np.ma.empty(shape=(raster_settings.height, raster_settings.width), dtype=raster_settings.dtype)
    for raster_block in summed_raster.values():
        window = raster_block.window
        complete_raster[
            window.row_off : window.row_off + window.height, window.col_off : window.col_off + window.width
        ] = raster_block.array

    return complete_raster


def write_raster(complete_raster: np.ma.array, raster_settings: McdaRasterSettings, final_raster_name) -> str:
    raster_settings.nodata = Config.FINAL_RASTER_NO_DATA
    final_raster_path = Config.PATH_RESULTS / (final_raster_name + ".tif")
    with rasterio.open(final_raster_path, "w", **asdict(raster_settings)) as dest:
        dest.write(np.ma.filled(complete_raster, Config.FINAL_RASTER_NO_DATA), 1)

    return final_raster_path.__str__()
