from pathlib import Path

import rasterio
import rasterio.mask
import shapely
import structlog

from settings import Config

logger = structlog.get_logger(__name__)


def load_suitability_raster_data(path_raster: Path | str, project_area: shapely.Polygon):
    """
    Read only the intersection of the project area with the large suitability raster from S3 (or local).
    """
    # load with mask, based on geom using rasterio.mask. This replaces the preprocessing.py
    logger.info(f"Loading a portion of {path_raster} based on input project area.")

    with rasterio.Env():
        with rasterio.open(path_raster) as src:
            image, transform = rasterio.mask.mask(
                src,
                [project_area],
                all_touched=True,  # Include a pixel in the mask if it touches any of the shapes.
                crop=True,  # Crop result to input project area.
                filled=True,  # Values outside input project area will be set to nodata.
                indexes=1,  # Read only values from band 1.
                nodata=Config.RASTER_NO_DATA,  # As our values are always =< 128, this can be used for filtering.
            )

    if len(image) < 1:
        critical_txt = "Unexpected values retrieved from suitability raster. Check project area."
        logger.critical(critical_txt)
        raise ValueError(critical_txt)

    return image, transform.to_gdal()
