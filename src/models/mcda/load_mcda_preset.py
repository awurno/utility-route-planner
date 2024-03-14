import typing

import pydantic
import shapely
import structlog
from pydantic import field_validator, ConfigDict
from src.models.mcda.mcda_presets import preset_collection

from src.models.mcda.vector_preprocessing.base import VectorPreprocessorBase

logger = structlog.get_logger(__name__)


class RasterPresetCriteria(pydantic.BaseModel):
    """
    Class for defining the datamodel for a criteria in the raster preset. Is part of the RasterPreset datamodel.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    description: str = pydantic.Field(description="Description of the criteria.")
    constraint: bool = pydantic.Field(description="Determines how the criteria is handled")
    preprocessing_function: VectorPreprocessorBase
    group: str = pydantic.Field(description="Determines how the criteria is handled.")

    @field_validator("group")
    def validate_group(cls, v: str) -> str:
        if v not in ["a", "b"]:
            raise ValueError("Group must be 'a' or 'b'.")
        return v.title()

    weight_values: dict = pydantic.Field(..., description="Contains values for defining how important the layer is.")
    geometry_values: typing.Optional[dict] = pydantic.Field(
        default=None,
        description="Contains values for optional computational geometry steps, e.g., buffer.",
    )


class RasterPresetGeneral(pydantic.BaseModel):
    """
    Check if we have the necessary general settings for the cost-surface generation using MCDA.
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    description: typing.Optional[str] = pydantic.Field(..., description="Description of the preset.")
    prefix: str = pydantic.Field(
        ...,
        description="Prefix to apply for all files relevant for a given preset.",
    )
    raster_resolution: tuple = pydantic.Field(
        default=(1, 1),
        description="Resolution to be used for the (intermediate) raster.",
    )
    intermediate_raster_value_limit_lower: int = pydantic.Field(
        ...,
        description="Contains the min value for the intermediate rasters to sum in the final suit raster.",
    )
    intermediate_raster_value_limit_upper: int = pydantic.Field(
        ...,
        description="Contains the max value for the intermediate rasters to sum in the final suit raster.",
    )
    final_raster_name: str = pydantic.Field(default="zz_test_raster", description="Name of the final raster.")
    final_raster_value_limit_lower: int = pydantic.Field(
        ...,
        description="Contains the min value for the final raster.",
    )
    final_raster_value_limit_upper: int = pydantic.Field(
        ...,
        description="Contains the max value for the final raster.",
    )
    raster_no_data: int = pydantic.Field(
        ...,
        description="Contains the nodata value to set for areas outside the project area for which the raster is made.",
    )
    project_area_geometry: shapely.MultiPolygon | shapely.Polygon = pydantic.Field(
        ...,
        description="Shapely geometry to use defining the project area for the utility route.",
    )

    @field_validator("project_area_geometry")
    def validate_group(cls, v: shapely.MultiPolygon | shapely.Polygon) -> shapely.MultiPolygon:
        if v.geom_type == "Polygon":
            v = shapely.MultiPolygon([v])
        if shapely.get_num_geometries(v) < 1:
            raise ValueError("Input project MultiPolygon is not valid as it does not contain 1 or more geometries.")
        return v


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


def load_preset(preset_name: str) -> RasterPreset:
    """
    Convert the raw configuration file to a pydantic datamodel.

    :param preset_name: preset dictionary to load from the mcda_presets.py.
    :return: datamodel containing configuration for the raster to create.
    """

    try:
        preset_to_load_raw = preset_collection.get(preset_name)
        if preset_to_load_raw is None:
            logger.error(f"Preset: {preset_to_load_raw} is not implemented. Options are: {preset_collection.keys()}")
            raise ValueError
        preset_model = RasterPreset(
            general=preset_to_load_raw["general"],
            criteria=preset_to_load_raw["criteria"],
        )

        logger.info("Successfully loaded the raster preset datamodel.")
        return preset_model

    except pydantic.ValidationError as e:
        logger.error(f"Exception as str: {e}")
        logger.error(e)
        raise
