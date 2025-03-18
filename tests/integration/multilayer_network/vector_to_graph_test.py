import numpy as np
import pytest
import shapely
import geopandas as gpd

from models.mcda.mcda_engine import McdaCostSurfaceEngine
from models.mcda.mcda_presets import preset_collection
from settings import Config
from util.write import write_results_to_geopackage


class TestVectorToGraph:
    @pytest.fixture()
    def project_area(self) -> shapely.Polygon:
        return shapely.Polygon(
            [
                shapely.Point(174992.960, 451097.964),
                shapely.Point(174993.753, 451088.943),
                shapely.Point(175004.559, 451089.438),
                shapely.Point(175005.154, 451097.468),
                shapely.Point(174992.960, 451097.964),
            ]
        )

    @pytest.fixture()
    def vector_for_project_area(self, project_area: shapely.Polygon) -> gpd.GeoDataFrame:
        criterium_name = "wegdeel"
        preset_to_load = {
            "general": preset_collection["preset_benchmark_raw"]["general"],
            "criteria": {criterium_name: preset_collection["preset_benchmark_raw"]["criteria"][criterium_name]},
        }
        mcda_engine = McdaCostSurfaceEngine(
            preset_to_load,
            Config.PYTEST_PATH_GEOPACKAGE_MCDA,
            project_area,
        )
        mcda_engine.preprocess_vectors()
        return mcda_engine.processed_vectors[criterium_name]

    def test_vector_to_graph(self, vector_for_project_area: gpd.GeoDataFrame):
        first_vector = vector_for_project_area.iloc[0]

        # Create a grid of all points within the geometry boundaries
        x_min, y_min, x_max, y_max = first_vector.geometry.bounds
        x_coordinates = np.arange(x_min, x_max, Config.RASTER_CELL_SIZE)
        y_coordinates = np.arange(y_min, y_max, Config.RASTER_CELL_SIZE)

        # For each coordinate, check if within the geometry. If this is the case, create a node later on
        points = []
        for x in x_coordinates:
            for y in y_coordinates:
                point = shapely.Point(x, y)
                if first_vector.geometry.contains(point):
                    points.append((first_vector["suitability_value"], point))
        points_gdf = gpd.GeoDataFrame(points, columns=["suitability_value", "geometry"])
        points_gdf = points_gdf.set_geometry("geometry", crs=Config.CRS)

        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, first_vector.geometry, "processed_vector", overwrite=True
        )
        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, points_gdf, "vector_points", overwrite=True
        )
