import structlog
import datetime

from src.models.mcda.mcda_engine import McdaCostSurfaceEngine

logger = structlog.get_logger(__name__)


def get_mcda_cost_surface(preset_name: str):
    """
    Main method for running preprocessing on raster and vector data.
    """
    start = datetime.datetime.now()
    logger.info(f"Starting preprocessing for: {preset_name}.")

    # Load raster preset to process as pydantic model. Initialize mcda engine.
    mcda_engine = McdaCostSurfaceEngine(preset_name)

    # Run vector preprocessing per preset.
    mcda_engine.preprocess_vectors()

    # Run raster preprocessing per preset.
    mcda_engine.preprocess_rasters()

    end = datetime.datetime.now()
    logger.info(f"Finished preprocessing preset: {preset_name} in {end - start} time.")

    return mcda_engine
