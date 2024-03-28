from __future__ import annotations

import abc
import datetime
import typing

import pandas
import shapely
import geopandas as gpd
import structlog

from settings import Config
from src.models.mcda.exceptions import InvalidSuitabilityValue
from src.util.geo_utilities import get_empty_geodataframe
from src.util.write import write_results_to_geopackage

if typing.TYPE_CHECKING:
    from src.models.mcda.load_mcda_preset import RasterPresetCriteria, RasterPresetGeneral


logger = structlog.get_logger(__name__)


class VectorPreprocessorBase(abc.ABC):
    @property
    @abc.abstractmethod
    def criterion(self) -> str:
        """Name of the criterion"""

    def execute(self, general: RasterPresetGeneral, criterion: RasterPresetCriteria) -> bool:
        start = datetime.datetime.now()
        logger.info(f"Start preprocessing: {self.criterion}.")

        prepared_gdfs = self.prepare_input_data(general.project_area_geometry, criterion)
        if len(prepared_gdfs) == 1 and prepared_gdfs[0].empty:
            return False  # Nothing to process when there is no data available, return.
        processed_gdf = self.specific_preprocess(prepared_gdfs, criterion)
        self.validate_result(processed_gdf)
        self.write_to_file(general.prefix, processed_gdf)

        end = datetime.datetime.now()
        logger.info(f"Finished {self.criterion} in: {end - start} time.")
        return True

    @staticmethod
    def prepare_input_data(
        project_area: shapely.MultiPolygon, criterion: RasterPresetCriteria
    ) -> list[gpd.GeoDataFrame]:
        """Check existing layers in geopackage / clip data / check if gdf is empty"""
        # load and clip data
        prepared_input = []
        for layer_name in criterion.layer_names:
            gdf = gpd.read_file(
                Config.PATH_INPUT_MCDA_GEOPACKAGE, layer=layer_name, engine="pyogrio", bbox=project_area.bounds
            ).clip(project_area)
            gdf["suitability_value"] = pandas.NA  # Placeholder value
            if not gdf.empty:
                prepared_input.append(gdf)

        if all([i.empty for i in prepared_input]):
            logger.info("No data available in project area for criterion.")
            prepared_input = [get_empty_geodataframe()]

        return prepared_input

    @abc.abstractmethod
    def specific_preprocess(self, prepared_data, criterion) -> gpd.GeoDataFrame:
        """Subclasses must implement this abstract method which contains logic for handling the criteria."""

    def validate_result(self, processed_gdf: gpd.GeoDataFrame) -> None:
        """Validate the result if all values are set and within expected tolerances."""
        # Check if the placeholder value got overwritten.
        try:
            processed_gdf.astype({"suitability_value": int}, errors="raise")
        except ValueError:
            logger.error(
                f"Suitability value is invalid rows: {processed_gdf.loc[~processed_gdf['suitability_value'].astype(str).str.isnumeric()]}. Check mcda_presets.yaml for criteria: {self.criterion}."
            )
            raise InvalidSuitabilityValue

    def write_to_file(self, prefix, validated_gdf: gpd.GeoDataFrame) -> None:
        """Write to the geopackage."""
        write_results_to_geopackage(Config.PATH_OUTPUT_MCDA_GEOPACKAGE, validated_gdf, prefix + self.criterion)
