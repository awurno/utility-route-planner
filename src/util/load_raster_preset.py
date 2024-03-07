import typing

import pydantic
import shapely
import structlog
import yaml

from settings import Config

logger = structlog.get_logger(__name__)


class RasterPresetCriteria(pydantic.BaseModel):
    """
    Class for defining the datamodel for a criteria in the raster preset. Is part of the RasterPreset datamodel.
    """

    weight_values: dict = pydantic.Field(..., description="Contains values for defining how important the " "layer is.")
    geometry_values: typing.Optional[dict] = pydantic.Field(
        default=None,
        description="Contains values for optional " "computational geometry steps " "(e.g., buffer).",
    )
    rasterize_overlap_order: typing.Optional[dict] = pydantic.Field(
        default=None,
        description="Contains optional SQL statement used during rasterize steps in case of overlap.",
    )


class RasterPresetGeneral(pydantic.BaseModel):
    """
    Class for defining the datamodel containing general settings on how to handle the (intermediate) raster files. Is
    part of the RasterPreset datamodel.
    """

    # Throw an error when we encounter extra fields in general not covered below.
    class Config:
        extra = pydantic.Extra.forbid
        arbitrary_types_allowed = True

    description: typing.Optional[str] = pydantic.Field("Undefined", description="Description of the preset.")
    table_prefix: str = pydantic.Field(
        ...,
        description="Prefix to apply for all tables relevant " "for a given preset.",
    )
    schema_name: str = pydantic.Field(
        default="playground",
        description="Target schema to write the tables to during preprocessing.",
    )
    raster_resolution: tuple = pydantic.Field(
        default=(1, 1),
        description="Resolution to be used for the (" "intermediate) raster.",
    )
    final_raster_name: str = pydantic.Field(default="zz_test_raster", description="Name of the final raster.")
    final_raster_value_limits: tuple = pydantic.Field(
        ...,
        description="Contains the cut-off point of values for "
        "creating the final raster which will be "
        "rounded up or down to.",
    )
    intermediate_raster_value_limits: tuple = pydantic.Field(
        ...,
        description="Contains the max/min value for the " "intermediate rasters to sum in the " "final suit raster.",
    )
    raster_no_data: int = pydantic.Field(
        ...,
        description="Contains the nodata value to set for areas outside the project area for which the raster is made.",
    )
    raster_recolored_no_data: int = pydantic.Field(
        ...,
        description="Contains the nodata value to set for areas outside the project area for which the raster is made. "
        "Only applies to the recolored raster in RGB.",
    )
    raster_recolored_used_styling_name: str = pydantic.Field(
        ...,
        description="Contains the filename of the applied color styling used in the recolored raster in front-end. "
        "The front-end uses this to dynamically visualize the explanation field.",
    )
    project_area_schema_name: str = pydantic.Field(
        ...,
        description="Table name which contains the project area to compute the final raster for.",
    )
    project_area_table_name: str = pydantic.Field(
        ...,
        description="Schema name which contains the project area table to compute the final raster for.",
    )
    project_area_geometry: shapely.MultiPolygon = pydantic.Field(
        default=shapely.MultiPolygon([]),
        description="Shapely geometry later set in preprocessing.",
    )


class RasterPreset(pydantic.BaseModel):
    """
    Class for defining the datamodel of a raster preset. A raster preset contains:
    - General settings such as, but not limited to: names, directories, raster settings.
    - List of criteria to include in the raster.
    """

    # General settings.
    general: RasterPresetGeneral
    # List of criteria to include.
    criteria: typing.Dict[str, RasterPresetCriteria]


def load_preset(preset_to_load: str) -> RasterPreset:
    """
    Convert the raw configuration file to a pydantic datamodel.

    :param preset_to_load: preset to load from the mcda_presets.yaml.
    :return: datamodel containing configuration for the raster to create.
    """
    with open(Config.PATH_RASTER_PRESET_FILE, "r") as f:
        all_raster_presets_raw = yaml.load(f, Loader=yaml.FullLoader)

    try:
        preset_model = RasterPreset(
            general=all_raster_presets_raw[preset_to_load]["general"],
            criteria=all_raster_presets_raw[preset_to_load]["criteria"],
        )

        logger.info("Successfully loaded the raster preset datamodel.")
        return preset_model

    except pydantic.ValidationError as e:
        logger.error(f"Exception as str: {e}")
        logger.error(e)
        raise
