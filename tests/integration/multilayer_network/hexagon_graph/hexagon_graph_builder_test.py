# SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#
# SPDX-License-Identifier: Apache-2.0

import geopandas as gpd
import pytest
import shapely

from settings import Config
from utility_route_planner.models.mcda.load_mcda_preset import RasterPreset, load_preset
from utility_route_planner.models.multilayer_network.hexagon_graph.hexagon_graph_builder import HexagonGraphBuilder
from utility_route_planner.models.multilayer_network.hexagon_graph.hexagon_utils import convert_hexagon_graph_to_gdfs
from utility_route_planner.util.write import write_results_to_geopackage


@pytest.fixture()
def ede_project_area() -> shapely.MultiPolygon:
    return (
        gpd.read_file(Config.PYTEST_PATH_GEOPACKAGE_MCDA, layer=Config.PYTEST_LAYER_NAME_PROJECT_AREA).iloc[0].geometry
    )


@pytest.fixture()
def raster_preset(ede_project_area):
    return load_preset(Config.RASTER_PRESET_NAME_BENCHMARK, Config.PYTEST_PATH_GEOPACKAGE_MCDA, ede_project_area)


def test_build_graph_for_single_criterion(
    single_criterion_vectors: gpd.GeoDataFrame,
    raster_preset: RasterPreset,
    ede_project_area: shapely.MultiPolygon,
    debug: bool = False,
):
    vectors = {
        "wegdeel": single_criterion_vectors(
            Config.MAX_NODE_SUITABILITY_VALUE, Config.MIN_NODE_SUITABILITY_VALUE, Config.MAX_NODE_SUITABILITY_VALUE
        )
    }

    hexagon_graph_builder = HexagonGraphBuilder(
        ede_project_area,
        raster_preset,
        vectors,
        hexagon_size=0.5,
    )
    graph = hexagon_graph_builder.build_graph()
    nodes_gdf, edges_gdf = convert_hexagon_graph_to_gdfs(graph)

    max_value = Config.MAX_NODE_SUITABILITY_VALUE
    min_value = Config.MIN_NODE_SUITABILITY_VALUE
    no_data = Config.MAX_NODE_SUITABILITY_VALUE

    points_to_sample = gpd.GeoDataFrame(
        data=[
            [1, 10, shapely.Point(174871.877, 451084.402)],  #
            [2, 5, shapely.Point(174868.877, 451086.134)],  #
            [5, max_value, shapely.Point(175012.877, 450908.599)],
            [6, min_value, shapely.Point(175093.877, 450912.929)],
            [7, no_data, shapely.Point(174923.627, 450959.261)],
        ],
        geometry="geometry",
        crs=Config.CRS,
        columns=["sample_id", "expected_suitability_value", "geometry"],
    )

    # TODO: assert if suitability values are matching
    # result = points_to_sample.sjoin_nearest(nodes_gdf)

    if debug:
        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, single_criterion_vectors, "vectors", overwrite=True
        )
        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, nodes_gdf, "graph_nodes", overwrite=True
        )
        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, edges_gdf, "graph_edges", overwrite=True
        )
        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, points_to_sample, "points_to_sample", overwrite=True
        )
