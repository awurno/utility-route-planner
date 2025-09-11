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
from utility_route_planner.util.write import reset_geopackage, write_results_to_geopackage


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
        reset_geopackage(Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT)
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

    graph = hexagon_graph_builder.build_graph()
    nodes_gdf, edges_gdf = convert_hexagon_graph_to_gdfs(graph)

    points_to_sample = gpd.GeoDataFrame(
        data=[
            [1, 14.0, shapely.Point(175090.35, 450911.67)],  # overlap between b1 and b2
            [2, min_value, shapely.Point(175091.8234, 450911.7488)],  # overlap between a1, b1 and b2
            [3, -1.0, shapely.Point(175088.2180, 450912.7950)],  # only b1
            [5, max_value, shapely.Point(175013.3110, 450910.3013)],  # overlap between b1 and a1
            [6, 5.0, shapely.Point(174839.089, 451050.785)],  # just a1
            [7, 70.0, shapely.Point(174813.2646, 451113.9146)],  # overlap between b1 and a1
            [9, 0.0, shapely.Point(174833.90, 451067.57)],  # b1 and a1 sum is 0 here
            [10, max_value, shapely.Point(174878.65, 451132.89)],  # c1 overlaps a1
            [11, max_value, shapely.Point(174799.54, 451170.54)],  # c1
            [12, max_value, shapely.Point(174921.44, 451123.59)],  # c1 overlapping c1
            [13, max_value, shapely.Point(174745.32, 451159.41)],  # c1 outside the project area
            [14, max_value, shapely.Point(175092.267, 450908.932)],  # c2 overlapping b2
            [15, max_value, shapely.Point(175097.673, 450912.390)],  # c2 overlapping b2, a1
            [16, max_value, shapely.Point(174847.32, 451177.96)],  # c2 overlapping c1
        ],
        geometry="geometry",
        crs=Config.CRS,
        columns=["sample_id", "expected_suitability_value", "geometry"],
    )

    # Verify that the nodes near the sample points are equal to the expected value on the sample points.
    joined_sample_points = points_to_sample.sjoin_nearest(nodes_gdf)
    assert joined_sample_points["expected_suitability_value"].equals(joined_sample_points["suitability_value"])

    if debug:
        reset_geopackage(Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT)
        write_results_to_geopackage(
            Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT, ede_project_area, "pytest_project_area", overwrite=True
        )
        for criterion in multiple_criteria_vectors:
            criterion_name, _, criterion_gdf = criterion

            write_results_to_geopackage(
                Config.PATH_GEOPACKAGE_VECTOR_GRAPH_OUTPUT,
                criterion_gdf,
                f"pytest_sum_{criterion_name}",
                overwrite=True,
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
