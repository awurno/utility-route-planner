from __future__ import annotations

from src.models.mcda.vector_preprocessing.base import VectorPreprocessorBase
import structlog
import geopandas as gpd
import typing

if typing.TYPE_CHECKING:
    from src.models.mcda.load_mcda_preset import RasterPresetCriteria

logger = structlog.get_logger(__name__)


class Waterdeel(VectorPreprocessorBase):
    criterion = "waterdeel"  # TODO set this after loading the preset?

    def specific_preprocess(self, input_gdf: list, criterion: RasterPresetCriteria) -> gpd.GeoDataFrame:
        input_gdf = self._set_suitability_values(input_gdf[0], criterion.weight_values)
        input_gdf = self._update_geometry_values(input_gdf)
        return input_gdf

    @staticmethod
    def _set_suitability_values(input_gdf: gpd.GeoDataFrame, weight_values: dict) -> gpd.GeoDataFrame:
        logger.info("Setting suitability values.")
        input_gdf["suitability_value"] = input_gdf.apply(
            lambda row: weight_values.get(row["class"], row["suitability_value"]), axis=1
        )
        input_gdf["suitability_value"] = input_gdf.apply(
            lambda row: weight_values.get(row["plus-type"], row["suitability_value"]), axis=1
        )
        return input_gdf

    def _update_geometry_values(self, input_gdf):
        logger.info("Updating geometry values.")
        # TODO: buffer values
        return input_gdf
