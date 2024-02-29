import numpy as np
import shapely
from skimage.graph import route_through_array

from settings import Config
from src.util.datastructures import RouteModel
from src.util.geo_utilities import logger
from src.util.write import write_to_file


def preprocess_input_linestring(geotransform: tuple, utility_route_sketch: shapely.LineString) -> RouteModel:
    """
    Convert input to a dictionary for further processing and check if we have optional stops. The current input is
    a tuple, this might be changed to a shapely / GeoJSON linestring geometry later on depending on the GUI.

    :param geotransform: metadata of the raster from gdal.
    :param utility_route_sketch: input linestring sketch for which to compute a utility route.
    :return route_model: input converted to a route_model.
    """

    route_model = RouteModel(utility_route_sketch, geotransform)

    if Config.DEBUG:
        write_to_file(route_model.input_linestring, "utility_sketch_route.geojson")
        write_to_file(route_model.route_points, "route_points.geojson")

    return route_model


def calculate_least_cost_path(suit_raster_array: "np.ndarray", utility_route_model: RouteModel) -> tuple:
    """
    Calculates the least cost path in the given suitability raster. Handle one or multiple stops if present.

    :param suit_raster_array: numpy array containing the values of the suitability raster.
    :param utility_route_model: dictionary containing the start, end and optional stops raster indices.
    :return: numpy array containing the least cost path.
    """

    # Check if we have to account for intermediate stops in the path calculations.
    if len(utility_route_model.idx_stops) == 0:
        logger.info("There are no intermediate stops to account for in determining the cable route.")
        indices, weight = route_through_array(
            suit_raster_array,
            utility_route_model.idx_start,
            utility_route_model.idx_end,
            geometric=True,
            fully_connected=True,
        )
    else:
        # Call the route finding function multiple times.
        logger.info(f"There are {len(utility_route_model.idx_stops)} intermediate stop(s) in the utility route.")
        indices = []
        weight = []
        for idx, item in enumerate(utility_route_model.idx_stops):
            # For the first call, we take the start point and the first stop.
            if idx == 0:
                tmp_indices, tmp_weight = route_through_array(
                    suit_raster_array, utility_route_model.idx_start, item, geometric=True, fully_connected=True
                )
            # Check if there are more stops to account for. Take the current stop and the previous one.
            else:
                tmp_indices, tmp_weight = route_through_array(
                    suit_raster_array,
                    utility_route_model.idx_stops[idx - 1],
                    item,
                    geometric=True,
                    fully_connected=True,
                )
            # Add route part to the complete cable route.
            indices += tmp_indices
            weight += tmp_weight

        # Finally, add the ending route segment. Use the last stop point in combination with the end point.
        tmp_indices, tmp_weight = route_through_array(
            suit_raster_array,
            utility_route_model.idx_stops[-1],
            utility_route_model.idx_end,
            geometric=True,
            fully_connected=True,
        )
        indices += tmp_indices
        weight += tmp_weight

    # Gather all indices and paths, merge them. Create a new array where 1 = cable route, 0 = not cable route.
    indices_np = np.array(indices).T
    path = np.zeros_like(suit_raster_array)
    path[indices_np[0], indices_np[1]] = 1

    return path, indices
