# SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#
# SPDX-License-Identifier: Apache-2.0
import pytest
import geopandas as gpd

from settings import Config
from utility_route_planner.models.mcda.mcda_engine import McdaCostSurfaceEngine
from utility_route_planner.models.multilayer_network.pipe_ramming import GetPotentialPipeRammingCrossings
from utility_route_planner.util.osm_graph_preprocessing import OSMGraphPreprocessor


class TestPipeRamming:
    @pytest.fixture
    def setup_pipe_ramming_example_polygon(self, load_osm_graph_pickle):
        project_area = (
            gpd.read_file(Config.PYTEST_PATH_GEOPACKAGE_MCDA, layer=Config.PYTEST_LAYER_NAME_PROJECT_AREA)
            .iloc[0]
            .geometry
        )

        osm_graph_preprocessor = OSMGraphPreprocessor(load_osm_graph_pickle)
        osm_graph_preprocessed = osm_graph_preprocessor.preprocess_graph()

        mcda_engine = McdaCostSurfaceEngine(
            Config.RASTER_PRESET_NAME_BENCHMARK, Config.PYTEST_PATH_GEOPACKAGE_MCDA, project_area
        )
        mcda_engine.preprocess_vectors()

        return osm_graph_preprocessed, mcda_engine

    def test_find_road_crossings(self, setup_pipe_ramming_example_polygon):
        osm_graph, mcda_engine = setup_pipe_ramming_example_polygon

        obstacles = mcda_engine.processed_vectors["pand"]  # can be expanded with water, trees.
        roads = mcda_engine.processed_vectors["wegdeel"]
        crossings = GetPotentialPipeRammingCrossings(osm_graph, roads, obstacles)
        crossings.get_crossings()
