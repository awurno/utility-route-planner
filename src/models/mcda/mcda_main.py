import structlog
import datetime

from src.util.load_raster_preset import load_preset

logger = structlog.get_logger(__name__)


def main(preset_name: str = "preset_benchmark"):
    """
    Main method for running preprocessing on raster and vector data.
    """
    start = datetime.datetime.now()
    logger.info("Starting preprocessing for: .")

    # Load raster preset to process as pydantic model.
    preset_model = load_preset(preset_name)

    # Run vector preprocessing per preset.

    # Run raster preprocessing per preset.

    end = datetime.datetime.now()
    logger.info(f"Finished preprocessing preset: {preset_name} in {end - start} time.")


if __name__ == "__main__":
    main()
