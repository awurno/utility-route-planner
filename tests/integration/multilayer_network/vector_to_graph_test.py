import math

import networkx as nx
import osmnx as ox
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

        # Compute hexagon height and width for determining centerpoints. Here, we use the flat-top orientation hexagons
        # TODO: should we divide the hexagon width / 2 as each hexagon size is now 2 * cell size?
        hexagon_width = 2 * Config.RASTER_CELL_SIZE
        hexagon_height = math.sqrt(3) * Config.RASTER_CELL_SIZE

        # 0.75 is used to correctly set the offset of the x coordinate of the center, as each hexagon is partially covered
        # by the surrounding tiles
        x_coordinates = np.arange(x_min, x_max, hexagon_width * 0.75)
        y_coordinates = np.arange(y_min, y_max, hexagon_height)

        # For each coordinate, check if within the geometry. If this is the case, add node to the graph
        node_id = 0
        graph = nx.MultiGraph(crs=Config.CRS)
        for x in x_coordinates:
            for y in y_coordinates:
                # Every odd column must be offset by half of the hexagon height to properly determine the vertical
                # position of the hexagon. A column is odd when the distance between the x coordinate and the min_x
                # can be divided by hexagon_width * 0.75
                if ((x - x_min) / (hexagon_width * 0.75)) % 2:
                    y += hexagon_height / 2

                if first_vector.geometry.contains(shapely.Point(x, y)):
                    graph.add_node(node_id, suitability_value=first_vector["suitability_value"], x=x, y=y)
                    node_id += 1

        # Add temp edge for testing
        graph.add_edge(1, 2)

        nodes_gdf, edges_gdf = ox.convert.graph_to_gdfs(graph)

        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, first_vector.geometry, "processed_vector", overwrite=True
        )
        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, nodes_gdf, "vector_points", overwrite=True
        )
        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, edges_gdf, "vector_edges", overwrite=True
        )
