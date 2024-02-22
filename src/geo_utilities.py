import geopandas
import numpy as np
from pathlib import Path
import shapely
import rasterio
import rasterio.mask
import structlog
from skimage.graph import route_through_array
import geopandas as gpd

from settings import Config
from src.datamodels import RouteModel

logger = structlog.get_logger(__name__)


def load_suitability_raster_data(path_raster: Path | str, project_area: shapely.Polygon):
    """
    Read only the intersection of the project area with the large suitability raster from S3 (or local).
    """
    # load with mask, based on geom using rasterio.mask. This replaces the preprocessing.py
    logger.info(f"Loading a portion of {path_raster} based on input project area.")

    with rasterio.Env():
        with rasterio.open(path_raster) as src:
            image, transform = rasterio.mask.mask(
                src,
                [project_area],
                all_touched=True,  # Include a pixel in the mask if it touches any of the shapes.
                crop=True,  # Crop result to input project area.
                filled=True,  # Values outside input project area will be set to nodata.
                indexes=1,  # Read only values from band 1.
                nodata=Config.RASTER_NO_DATA,  # As our values are always =< 128, this can be used for filtering.
            )

    if len(image) < 1:
        critical_txt = "Unexpected values retrieved from suitability raster. Check project area."
        logger.critical(critical_txt)
        raise ValueError(critical_txt)

    return image, transform.to_gdal()


def preprocess_input_linestring(geotransform: tuple, utility_route_sketch: shapely.LineString):
    """
    Convert input to a dictionary for further processing and check if we have optional stops. The current input is
    a tuple, this might be changed to a shapely / GeoJSON linestring geometry later on depending on the GUI.

    :param geotransform: metadata of the raster as tuple.
    GeoTransform[0] /* top left x */
    GeoTransform[1] /* w-e pixel resolution */
    GeoTransform[2] /* 0 */
    GeoTransform[3] /* top left y */
    GeoTransform[4] /* 0 */
    GeoTransform[5] /* n-s pixel resolution (negative value) */
    :param route_coords: list containing the start, optional stops and end point of the trace to be generated.
    :return route_dict: dictionary containing the formatted start, stop and optional stops with numpy array index.
    """

    # Set raster metadata values.
    upper_left_x = geotransform[0]
    upper_left_y = geotransform[3]
    x_size = geotransform[1]
    y_size = geotransform[5]

    route_coords = shapely.get_coordinates(utility_route_sketch)

    # Get raster array index value of the coordinates. Use indexing to select the start and end point.
    start_idx = _coord_to_rastercell_index(
        route_coords[0][0], route_coords[0][1], upper_left_x, upper_left_y, x_size, y_size
    )
    end_idx = _coord_to_rastercell_index(
        route_coords[-1][0], route_coords[-1][1], upper_left_x, upper_left_y, x_size, y_size
    )

    # Check if we have some intermediate stops.
    idx_stops = []
    if len(route_coords) > 2:
        stops = route_coords[1:-1]
        idx_stops = [_coord_to_rastercell_index(i[0], i[1], upper_left_x, upper_left_y, x_size, y_size) for i in stops]

    route_model = RouteModel(utility_route_sketch, start_idx, end_idx, idx_stops)

    if Config.DEBUG:
        write_to_file(route_model.input_linestring, "utility_sketch_route.geojson")

    return route_model


def _coord_to_rastercell_index(
    x: float, y: float, upper_left_x: float, upper_left_y: float, x_size: float, y_size: float
) -> tuple:
    """
    Calculates the index of the rastercell which intersects with the input coordinates.

    :param x: x coordinate in RD_new EPSG(28992).
    :param y: y coordinate in RD_new EPSG(28992).
    :param upper_left_x: upper left corner x coordinate (RD_New) of the suitability raster.
    :param upper_left_y: upper left corner y coordinate (RD_New) of the suitability raster.
    :param x_size: x cell size in meters as we are using the RD_new coordinate reference system.
    :param y_size: y cell size in meters as we are using the RD_new coordinate reference system.
    :return: tuple containing the rastercell index.
    """
    x_index = int((x - upper_left_x) / x_size)  # We round down because array indices start at 0.
    y_index = int((y - upper_left_y) / y_size)  # Instead of using math.floor, we truncate using int() as y is negative.

    return y_index, x_index  # Note that the order must be y, x because of indexing on the suitability raster.


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


def array_to_linestring(raster_metadata: tuple, array_indices: list) -> geopandas.geoseries.GeoSeries:
    """
    Create a linestring from the raster by stringing the centroids together for each cost path cell.

    :param raster_metadata: GeoTransform() gdal properties of the clipped raster.
    :param array_indices: list of the cost path.

    :return the cost path as linestring in a geoseries.
    """
    # Get the raster metadata
    upper_left_x, x_size, x_rotation, upper_left_y, y_rotation, y_size = raster_metadata

    # String the centroids of each raster cell together in the right sequence.
    cost_path_coords = []
    for idx in array_indices:
        # Calculate the coordinates of the rastercell centroids using map algebra
        x = upper_left_x + ((idx[1] * x_size) + (x_size / 2))
        y = upper_left_y - abs(((idx[0] * y_size) + (y_size / 2)))  # subtract from y as we start in upper_left corner.
        cost_path_coords.append((x, y))

    # Create the linestring.
    cost_path_rdnew = geopandas.GeoSeries(shapely.geometry.LineString(cost_path_coords))
    cost_path_rdnew.crs = "EPSG:28992"

    return cost_path_rdnew


def _array_index_to_coordinates(array_index_to_transform: np.array, geotransform: list) -> list:
    """
    # TODO can be removed.

    Change index values of a raster (combined with geotransform) to real coordinates.
    Example: (306, 886) should become (174768.627, 451001.5161999986) given (174615.377, 451444.7661999986)
    Follow these steps:
    1. Use upper left coordinates
    2. add difference in x, but consider tile-size (default 0.5x0.5),
    3. Take the centre of the tile

    Note that in different coordinate systems, y_size can be negative (even though one might not expect it),
    there an abs() is used
    """
    upper_left_x, x_size, x_rotation, upper_left_y, y_rotation, y_size = geotransform

    real_coordinates = []
    for y_index, x_index in array_index_to_transform:
        x = upper_left_x + ((x_index * x_size) + (x_size / 2))
        y = upper_left_y - abs(((y_index * y_size) + (y_size / 2)))
        real_coordinates.append((x, y))
    return real_coordinates


def _coordinates_to_array_index(coordinates: np.array, geotransform: list) -> np.array:
    """
    # TODO can be removed.

    Calculates the index of the rastercell which intersects with the input coordinates. In other words, transform
    real coordinates to index value for matrix indexing.
    Example: (174768.515, 451001.739) should become (306, 886) given band (174615.377, 451444.7661999986)
    Follow these steps:
    1. Use upper left coordinates
    2. Subtract difference in x, but consider tile-size (default 0.5x0.5),
    """
    upper_left_x, x_size, x_rotation, upper_left_y, y_rotation, y_size = geotransform

    xy_coordinates = []
    for _x, _y in coordinates:
        x_index = int((_x - upper_left_x) / x_size)  # We round down because array indices start at 0.
        y_index = int(
            (_y - upper_left_y) / y_size
        )  # Instead of using math.floor, we truncate using int() as y is negative.
        xy_coordinates.append(
            (y_index, x_index)
        )  # Note that the order must be y, x because of indexing on the suitability raster.

    return np.array(xy_coordinates)


def align_linestring(linestring: "geopandas.geoseries.GeoSeries", cell_size: float) -> "geopandas.geoseries.GeoSeries":
    """
    Write the cost path to a linestring. For now, this is a very primitive function which produces acceptable results.

    In future, possible improvements depending on the environment could be:
        - Align the linestring to existing trace by comparing the actual geometries to each other. This is more
        difficult than it may seem as the network can be quite dense at some places. When there are many cables in one
        'sleuf', it is hard to tell to which cable the linestring needs to be aligned. Ideally, a 'sleuf' dataset
        should be created which can be used to align tracé to. It could be created by an aggregation of the Alliander
        network.
        - Align the linestring to the centerlines of the pavement. If there is no existing cable tracé to follow, we
        would like to align it to existing infrastructure, for example the pavement. Computing centerlines of the BGT
        which includes this data is computationally expensive and geometrically complex.

    :param linestring: the resulting vectorized raster cost path as geoseries.
    :param cell_size: resolution/cell_size of the raster.

    :return the cost path as linestring in a geodataframe.
    """
    aligned_linestring = linestring.simplify(cell_size, preserve_topology=True)

    return aligned_linestring


def write_to_file(geometry: gpd.GeoSeries | gpd.GeoDataFrame | shapely.Geometry, name: str):
    if isinstance(geometry, shapely.Geometry):
        geometry = gpd.GeoSeries(geometry, crs=28992)

    if isinstance(geometry, gpd.GeoSeries | gpd.GeoDataFrame):
        pass

    geometry.to_file(Config.PATH_RESULTS / name)
