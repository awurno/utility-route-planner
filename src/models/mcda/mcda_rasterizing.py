import math

import shapely
import structlog
import rasterio
import rasterio.features
import geopandas as gpd
import affine

from settings import Config
from src.models.mcda.exceptions import RasterCellSizeTooSmall

logger = structlog.get_logger(__name__)


def rasterize_vector_data(
    criterion: str,
    project_area: shapely.MultiPolygon | shapely.Polygon,
    gdf_to_rasterize: gpd.GeoDataFrame,
    cell_size: int,
) -> None:
    """Burns the vector data to the project area in the desired raster cell size."""
    minx, miny, maxx, maxy = project_area.bounds

    # In order to fit the given cell size to the project area bounds, we slightly extend the maxx and maxy accordingly.
    if cell_size > maxx - minx or cell_size > maxy - miny:
        raise RasterCellSizeTooSmall("Given raster cell size is too large for the project area.")

    width = math.ceil((maxx - minx) / cell_size)
    height = math.ceil((maxy - miny) / cell_size)

    # the profile is used for creating the GeoTiff. It can be copied from an existing raster or manually defined.
    # noinspection PyUnresolvedReferences
    profile = {
        "driver": "GTiff",
        "dtype": "int16",
        "nodata": 0,  # TODO replace
        "width": width,
        "height": height,
        "count": 1,
        "crs": rasterio.crs.CRS({"init": "epsg:28992"}),
        "transform": affine.Affine(cell_size, 0.0, round(minx), 0.0, -cell_size, round(maxy)),
    }

    logger.info(f"Rasterizing layer: {criterion} in cell size: {cell_size} meters")
    # TODO check if we can use /vsimem/
    with rasterio.open(Config.PATH_RESULTS / f"zz_{criterion}.tif", "w+", **profile) as out:
        out_arr = out.read(1)
        # TODO check if sorting the order here impacts the raster creation, order by suitability_value
        shapes = ((geom, value) for geom, value in zip(gdf_to_rasterize.geometry, gdf_to_rasterize.suitability_value))
        burned = rasterio.features.rasterize(shapes=shapes, fill=0, out=out_arr, transform=out.transform)
        out.write_band(1, burned)
