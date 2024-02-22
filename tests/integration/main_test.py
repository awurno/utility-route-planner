import shapely

from main import get_utility_route
from settings import Config


def test_get_utility_route_small_area():
    route = get_utility_route(shapely.LineString([(193077.740, 466510.697), (193031.551, 466474.721)]))
    route.to_file(Config.BASEDIR / "data/processed/pytest_small_utility_route.geojson")

    assert len(route) > 0


def test_get_utility_route_with_intermediate_stops_small_area():
    route = get_utility_route(
        shapely.LineString(
            [(193077.740, 466510.697), (193043.338, 466490.707), (193055.374, 466489.049), (193031.551, 466474.721)]
        )
    )
    route.to_file(Config.BASEDIR / "data/processed/pytest_small_utility_route_with_stops.geojson")

    assert len(route) > 0
