import math

import shapely
import structlog
import rasterio
import rasterio.features
import rasterio.merge
import numpy as np
import geopandas as gpd
import affine

from settings import Config
from src.models.mcda.exceptions import RasterCellSizeTooSmall

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
    If values overlap in the geodataframe, pick the highest value
    """
    minx, miny, maxx, maxy = project_area.bounds

    # In order to fit the given cell size to the project area bounds, we slightly extend the maxx and maxy accordingly.
    if cell_size > maxx - minx or cell_size > maxy - miny:
        raise RasterCellSizeTooSmall("Given raster cell size is too large for the project area.")

    width = math.ceil((maxx - minx) / cell_size)
    height = math.ceil((maxy - miny) / cell_size)

    # noinspection PyUnresolvedReferences
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


def sum_rasters(rasters_to_sum: list[dict]):
    logger.info(f"Starting summing {len(rasters_to_sum)} rasters into the final cost surface.")
    # TODO use groups with summing

    src_files_to_mosaic = [rasterio.open(list(i.keys())[0]) for i in rasters_to_sum]
    # Merge the rasters
    # TODO check the merge docs
    mosaic, out_trans = rasterio.merge.merge(src_files_to_mosaic)
    # TODO set upper/lower limit of raster
    summed_raster = mosaic.sum(axis=0)

    # Update metadata
    # TODO set proper datatype
    out_meta = src_files_to_mosaic[0].meta.copy()
    out_meta.update(
        {"driver": "GTiff", "height": summed_raster.shape[0], "width": summed_raster.shape[1], "transform": out_trans}
    )

    with rasterio.open(Config.PATH_RESULTS / "zz_final_raster.tif", "w", **out_meta) as dest:
        dest.write(summed_raster, 1)
