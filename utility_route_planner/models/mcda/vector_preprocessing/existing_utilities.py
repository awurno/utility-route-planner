from __future__ import annotations

import pandas as pd

from utility_route_planner.models.mcda.vector_preprocessing.base import VectorPreprocessorBase
import structlog
import geopandas as gpd
import typing

from utility_route_planner.util.geo_utilities import get_empty_geodataframe

if typing.TYPE_CHECKING:
    from utility_route_planner.models.mcda.load_mcda_preset import RasterPresetCriteria

logger = structlog.get_logger(__name__)


class ExistingUtilities(VectorPreprocessorBase):
    criterion = "existing_utilities"

    def specific_preprocess(
        self, input_gdf: list[gpd.GeoDataFrame], criterion: RasterPresetCriteria
    ) -> gpd.GeoDataFrame:
        input_gdf = self._set_suitability_values(input_gdf, criterion.weight_values, criterion.geometry_values)  # type: ignore
        return input_gdf

    @staticmethod
    def _set_suitability_values(
        input_gdf: list[gpd.GeoDataFrame], weight_values: dict, buffer_values: dict
    ) -> gpd.GeoDataFrame:
        logger.info("Setting suitability values.")
        # High voltage assets
        gdf_high_voltage_underground, gdf_high_voltage_overhead, gdf_gasunie_leiding = (
            get_empty_geodataframe(),
            get_empty_geodataframe(),
            get_empty_geodataframe(),
        )
        for gdf in input_gdf:
            if "type" in gdf.columns:
                gdf = gdf[gdf["SPANNINGSNIVEAU"] != 0]
                if gdf.iloc[0].type == "high_voltage_cable_overhead":
                    gdf_high_voltage_overhead = gdf.copy()
                    gdf_high_voltage_overhead["suitability_value"] = weight_values["hoogspanning_bovengronds"]
                    gdf_high_voltage_overhead["geometry"] = gdf_high_voltage_overhead["geometry"].buffer(
                        buffer_values["hoogspanning_bovengronds_buffer"]
                    )
                elif gdf.iloc[0].type == "high_voltage_cable_underground":
                    gdf_high_voltage_underground = gdf.copy()
                    gdf_high_voltage_underground["suitability_value"] = weight_values["hoogspanning_ondergronds"]
                    gdf_high_voltage_underground["geometry"] = gdf_high_voltage_underground["geometry"].buffer(
                        buffer_values["hoogspanning_ondergronds_buffer"]
                    )
            elif "Leiding" in gdf.columns:
                gdf_gasunie_leiding = gdf.copy()
                gdf_gasunie_leiding = gdf_gasunie_leiding[gdf_gasunie_leiding["StatusOperationeel"] == "In Bedrijf"]
                gdf_gasunie_leiding["suitability_value"] = weight_values["gasunie_leidingen"]
                gdf_gasunie_leiding["geometry"] = gdf_gasunie_leiding["geometry"].buffer(
                    buffer_values["gasunie_leidingen_buffer"]
                )
            else:
                logger.warning(f"Unknown layer found in existing utilities: {gdf.columns}.")

        gdf_merged = pd.concat([gdf_high_voltage_underground, gdf_high_voltage_overhead, gdf_gasunie_leiding])
        return gdf_merged
