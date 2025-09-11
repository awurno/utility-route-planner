# SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#
# SPDX-License-Identifier: Apache-2.0

from typing import Callable
import geopandas as gpd
import pytest
import shapely

from settings import Config
from utility_route_planner.models.multilayer_network.hexagon_graph.hexagon_graph_builder import HexagonGraphBuilder
from utility_route_planner.models.multilayer_network.hexagon_graph.hexagon_utils import convert_hexagon_graph_to_gdfs
from utility_route_planner.util.write import write_results_to_geopackage


@pytest.fixture()
def ede_project_area() -> shapely.MultiPolygon:
    return (
        gpd.read_file(Config.PYTEST_PATH_GEOPACKAGE_MCDA, layer=Config.PYTEST_LAYER_NAME_PROJECT_AREA).iloc[0].geometry
    )


def test_build_graph_for_single_criterion(
    single_criterion_vectors: Callable,
    ede_project_area: shapely.MultiPolygon,
    debug: bool = False,
):
    max_value = Config.MAX_NODE_SUITABILITY_VALUE
    min_value = Config.MIN_NODE_SUITABILITY_VALUE
    single_criterion_vectors = single_criterion_vectors(max_value, min_value, max_value)

    # Create a simple vector dict for the single criterion.
    vectors = {"test": single_criterion_vectors}
    raster_criteria_groups = {"test": "a"}

    hexagon_graph_builder = HexagonGraphBuilder(
        ede_project_area,
        raster_criteria_groups,
        vectors,
        hexagon_size=0.5,
    )
    graph = hexagon_graph_builder.build_graph()
    nodes_gdf, edges_gdf = convert_hexagon_graph_to_gdfs(graph)

    points_to_sample = gpd.GeoDataFrame(
        data=[
            # Multiple overlapping values, take the max value
            [1, 10, shapely.Point(174871.877, 451084.402)],
            # Single vector, must be equal to vector suitability value
            [2, 5, shapely.Point(174868.877, 451086.134)],
            # Vector value exceeds max node value, must be reset to max value
            [3, max_value, shapely.Point(175012.877, 450908.599)],
            # Vector value lower than node min value, must be reset to min value
            [4, min_value, shapely.Point(175093.877, 450912.929)],
            # Vector value equal to max value, must remain the same
            [5, max_value, shapely.Point(174923.627, 450959.261)],
        ],
        geometry="geometry",
        crs=Config.CRS,
        columns=["sample_id", "expected_suitability_value", "geometry"],
    )

    # Verify that the nodes near the sample points are equal to the expected value on the sample points.
    joined_sample_points = points_to_sample.sjoin_nearest(nodes_gdf)
    assert joined_sample_points["expected_suitability_value"].equals(joined_sample_points["suitability_value"])

    if debug:
        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, ede_project_area, "pytest_project_area", overwrite=True
        )
        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, single_criterion_vectors, "pytest_vectors", overwrite=True
        )
        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, nodes_gdf, "pytest_graph_nodes", overwrite=True
        )
        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, edges_gdf, "pytest_graph_edges", overwrite=True
        )
        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, points_to_sample, "pytest_points_to_sample", overwrite=True
        )


def test_build_graph_for_multiple_criteria(
    multi_criteria_vectors: gpd.GeoDataFrame, ede_project_area: shapely.MultiPolygon, debug: bool = False
):
    max_value = Config.MAX_NODE_SUITABILITY_VALUE
    min_value = Config.MIN_NODE_SUITABILITY_VALUE
    multiple_criteria_vectors = multi_criteria_vectors(max_value, min_value)

    raster_criteria_groups = {criterion_name: group for criterion_name, group, _ in multiple_criteria_vectors}
    preprocessed_vectors = {
        criterion_name: criterion_gdf for criterion_name, _, criterion_gdf in multiple_criteria_vectors
    }

    hexagon_graph_builder = HexagonGraphBuilder(
        ede_project_area,
        raster_criteria_groups,
        preprocessed_vectors,
        hexagon_size=0.5,
    )
    hexagon_graph_builder.build_graph()
