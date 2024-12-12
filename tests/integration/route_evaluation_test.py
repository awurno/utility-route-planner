import shapely

from settings import Config
from utility_route_planner.models.route_evaluation_metrics import RouteEvaluationMetrics


class TestRouteEvaluationMetrics:
    def test_route_costs_simple(self):
        path_raster = Config.PATH_EXAMPLE_RASTER
        route = shapely.LineString([[174877.07, 451050.52], [174978.55, 451105.11]])

        route_evaluation_metrics = RouteEvaluationMetrics(route, path_raster)
        route_evaluation_metrics.get_route_evaluation_metrics()

        assert round(route_evaluation_metrics.route_relative_cost) == 9969
        assert route_evaluation_metrics.route.length == route.length

    def test_route_costs_of_linestring_in_single_cell(self):
        path_raster = Config.PATH_EXAMPLE_RASTER
        route = shapely.LineString(
            [
                [174962.5653, 451096.9245],
                [174962.8651, 451096.8886],
                [174962.9070, 451096.6188],
                [174962.5594, 451096.5829],
            ]
        )

        route_evaluation_metrics = RouteEvaluationMetrics(route, path_raster)
        route_evaluation_metrics.get_route_evaluation_metrics()

        cost_of_single_cell = 126  # As viewed in QGIS.

        assert round(route_evaluation_metrics.route_relative_cost) == round(cost_of_single_cell * route.length)
