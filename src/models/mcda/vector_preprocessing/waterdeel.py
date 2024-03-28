from __future__ import annotations

from src.models.mcda.vector_preprocessing.base import VectorPreprocessorBase
import structlog
import geopandas as gpd
import numpy as np
import typing

if typing.TYPE_CHECKING:
    from src.models.mcda.load_mcda_preset import RasterPresetCriteria

logger = structlog.get_logger(__name__)


class Waterdeel(VectorPreprocessorBase):
    criterion = "waterdeel"

    def specific_preprocess(self, input_gdf: list, criterion: RasterPresetCriteria) -> gpd.GeoDataFrame:
        input_gdf = self._set_suitability_values(input_gdf[0], criterion.weight_values)
        input_gdf = self._update_geometry_values(input_gdf, criterion.geometry_values)  # type: ignore
        return input_gdf

    @staticmethod
    def _set_suitability_values(input_gdf: gpd.GeoDataFrame, weight_values: dict) -> gpd.GeoDataFrame:
        logger.info("Setting suitability values.")

        # Class is always filled in.
        input_gdf["sv_1"] = input_gdf["class"]
        input_gdf["sv_1"] = input_gdf["sv_1"].case_when(
            [(input_gdf["sv_1"].eq(i), weight_values[i]) for i in weight_values]
        )
        # plus-type is optionally filled in, complementary to class.
        input_gdf["sv_2"] = input_gdf["plus-type"]
        input_gdf["sv_2"] = input_gdf["sv_2"].case_when(
            [(input_gdf["sv_2"].eq(i), weight_values[i]) for i in weight_values]
        )
        input_gdf["suitability_value"] = input_gdf["sv_1"]
        # Overwrite suitability_value if sv_2 is filled in with a valid integer
        mask = input_gdf["sv_2"].astype(str).str.isnumeric()
        input_gdf.loc[mask, "suitability_value"] = input_gdf.loc[mask, "sv_2"]

        return input_gdf

    @staticmethod
    def _update_geometry_values(input_gdf: gpd.GeoDataFrame, buffer_values: dict):
        logger.info("Updating geometry values.")

        # TODO check which version to use
        # Version 1: seems bloated
        # input_gdf["buffer_values"] = input_gdf['class']
        # input_gdf["buffer_values"] = input_gdf['class'].case_when(
        #     [(input_gdf['class'].eq(i), buffer_values[i]) for i in buffer_values]
        # )
        # mask = input_gdf['buffer_values'].astype(str).str.isnumeric()
        # input_gdf.loc[mask, 'geom'] = input_gdf.loc[mask, 'geom']
        # input_gdf.loc[mask, 'geom'] = input_gdf.loc[mask, 'geom'].buffer(input_gdf.loc[mask, 'buffer_values'].astype(int))

        # # Version 2: alternative, looks simpeler
        for key, value in buffer_values.items():
            input_gdf["geometry"] = np.where(
                input_gdf["class"].eq(key), input_gdf["geometry"].buffer(value), input_gdf["geometry"]
            )

        return input_gdf
