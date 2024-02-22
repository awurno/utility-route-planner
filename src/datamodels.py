from dataclasses import dataclass

import shapely


@dataclass
class RouteModel:
    input_linestring: shapely.LineString
    idx_start: tuple
    idx_end: tuple
    idx_stops: list[tuple]
