import abc
import datetime

import shapely
import geopandas as gpd
import structlog

from settings import Config
from src.models.mcda.exceptions import SuitabilityValueNotSet
from src.util.write import write_results_to_geopackage

logger = structlog.get_logger(__name__)


class VectorPreprocessorBase(abc.ABC):
    # TODO how to init the raster preset here so we dont have to pass things around?

    @property
    @abc.abstractmethod
    def criterion(self) -> str:
        """Name of the criteria"""

    def execute(self, project_area: shapely.MultiPolygon, criterion) -> str:
        start = datetime.datetime.now()
        logger.info(f"Start preprocessing: {self.criterion}.")

        prepared_gdfs = self.prepare_input_data(project_area, criterion)
        processed_gdf = self.specific_preprocess(prepared_gdfs, criterion)
        self.validate_result(processed_gdf)
        self.write_to_file(processed_gdf)

        end = datetime.datetime.now()
        logger.info(f"Finished {self.criterion} in: {end - start} time.")
        return self.criterion

    def prepare_input_data(self, project_area: shapely.MultiPolygon, criterion) -> list[gpd.GeoDataFrame]:
        """Check existing layers in geopackage / clip data / add check if gdf is empty"""
        # load and clip data
        prepared_input = []
        for layer_name in criterion.layer_names:
            gdf = gpd.read_file(
                Config.PATH_INPUT_MCDA_GEOPACKAGE, layer=layer_name, engine="pyogrio", bbox=project_area.bounds
            ).clip(project_area)
            gdf["suitability_value"] = None  # Placeholder value
            prepared_input.append(gdf)

        # TODO handle: if all are empty, skip this vector.
        if all([i.empty for i in prepared_input]):
            logger.info(f"No data available in project area for criterion {self.criterion}")

        return prepared_input

    @abc.abstractmethod
    def specific_preprocess(self, prepared_data, criterion) -> gpd.GeoDataFrame:
        """Subclasses must implement this abstract method which contains logic for handling the criteria."""

    def validate_result(self, processed_gdf: gpd.GeoDataFrame) -> None:
        """Validate the result if all values are set and within expected tolerances."""
        # Check if the placeholder value got overwritten. # TODO make tests for this, this does not work yet
        if None in processed_gdf["suitability_value"].unique():
            logger.error(
                f"Suitability value missing for these rows: {processed_gdf[processed_gdf['suitability_value'] is None]}. Check mcda_presets.yaml for criteria: {self.criterion}."
            )
            raise SuitabilityValueNotSet

    def write_to_file(self, validated_gdf: gpd.GeoDataFrame) -> None:
        """Write to the geopackage."""
        # TODO add prefix from preset model
        write_results_to_geopackage(Config.PATH_OUTPUT_MCDA_GEOPACKAGE, validated_gdf, self.criterion)
