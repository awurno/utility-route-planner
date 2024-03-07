from dataclasses import dataclass

import shapely
import geopandas as gpd

from settings import Config
from src.util.geo_utilities import coordinates_to_array_index


@dataclass
class Geotransform:
    def __init__(self, geotransform):
        """
        :param geotransform: metadata of the raster as tuple.
        GeoTransform[0] /* top left x */
        GeoTransform[1] /* w-e pixel resolution */
        GeoTransform[2] /* 0 */
        GeoTransform[3] /* top left y */
        GeoTransform[4] /* 0 */
        GeoTransform[5] /* n-s pixel resolution (negative value) */
        """
        self.upper_left_x, self.x_size, self.x_rotation, self.upper_left_y, self.y_rotation, self.y_size = geotransform


@dataclass
class LcpaModel:
    input_linestring: shapely.LineString
    idx_start = tuple
    idx_end = tuple
    idx_stops = list[tuple]
    route_points = gpd.GeoDataFrame

    def __init__(self, input_linestring, geotransform):
        self.input_linestring = input_linestring
        self.geotransform = Geotransform(geotransform)

        # Match the coordinates to the indices of the input raster.
        route_coordinates = shapely.get_coordinates(input_linestring)
        self.idx_start = coordinates_to_array_index(
            route_coordinates[0][0],
            route_coordinates[0][1],
            self.geotransform.upper_left_x,
            self.geotransform.upper_left_y,
            self.geotransform.x_size,
            self.geotransform.y_size,
        )
        self.idx_end = coordinates_to_array_index(
            route_coordinates[-1][0],
            route_coordinates[-1][1],
            self.geotransform.upper_left_x,
            self.geotransform.upper_left_y,
            self.geotransform.x_size,
            self.geotransform.y_size,
        )
        if len(route_coordinates) > 2:
            stops = route_coordinates[1:-1]
            idx_stops = [
                coordinates_to_array_index(
                    i[0],
                    i[1],
                    self.geotransform.upper_left_x,
                    self.geotransform.upper_left_y,
                    self.geotransform.x_size,
                    self.geotransform.y_size,
                )
                for i in stops
            ]
            self.idx_stops = idx_stops
            point_raster_indices = self.idx_start, *self.idx_stops, self.idx_end
        else:
            self.idx_stops = []
            point_raster_indices = self.idx_start, self.idx_end

        # Create GeoDataFrame with points and their respective raster indices for easier debugging.
        self.route_points = gpd.GeoDataFrame(
            data=zip(point_raster_indices, [shapely.Point(i) for i in input_linestring.coords]),
            columns=["raster_index", "geometry"],
            geometry="geometry",
            crs=Config.CRS,
        )
        self.route_points.reset_index(names="point_visiting_order_asc", inplace=True)
        self.route_points.raster_index = self.route_points.raster_index.astype(str)


# TODO maak dit NIET te generiek, het moet gewoon 1 preset zijn.
@dataclass
class McdaModelGeneral:
    description: str = "Preset voor stedelijk gebied."
    raster_resolution: tuple = (0.5, 0.5)
    final_raster_name: str = "suitability_raster"
    final_raster_value_limit_lower: int = 0
    final_raster_value_limit_upper: int = 126
    intermediate_raster_value_limit_lower: int = -126
    intermediate_raster_value_limit_upper: int = 126
    raster_no_data: int = -127


@dataclass
class McdaModelCriteria:
    group: str
    weight_values: dict
    geometry_values: dict

    def __init__(self, group, weight_values, geometry_values):
        self.group = group  # TODO check if it is a or b
        self.weight_values = weight_values  # TODO validate
        self.geometry_values = geometry_values  # TODO validate


@dataclass
class McdaModelPreset:
    # https://geoforum.nl/t/bgt-data-inlezen-in-python-met-geopandas/8047/5
    general = McdaModelGeneral
    criteria = McdaModelCriteria
