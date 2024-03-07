import shapely
import structlog


logger = structlog.get_logger(__name__)


def coordinates_to_array_index(
    x: float, y: float, upper_left_x: float, upper_left_y: float, x_size: float, y_size: float
) -> tuple:
    """
    Calculates the index of the rastercel which intersects with the input coordinates.

    :param x: x coordinate in RD_new EPSG(28992).
    :param y: y coordinate in RD_new EPSG(28992).
    :param upper_left_x: upper left corner x coordinate (RD_New) of the suitability raster.
    :param upper_left_y: upper left corner y coordinate (RD_New) of the suitability raster.
    :param x_size: x cell size in meters as we are using the RD_new coordinate reference system.
    :param y_size: y cell size in meters as we are using the RD_new coordinate reference system.
    :return: tuple containing the rastercel index.
    """
    x_index = int((x - upper_left_x) / x_size)  # We round down because array indices start at 0.
    y_index = int((y - upper_left_y) / y_size)  # Instead of using math.floor, we truncate using int() as y is negative.

    return y_index, x_index  # Note that the order must be y, x because of indexing on the suitability raster.


def array_indices_to_linestring(raster_metadata: tuple, array_indices: list) -> shapely.LineString:
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
    cost_path = shapely.geometry.LineString(cost_path_coords)

    return cost_path


def align_linestring(linestring: shapely.LineString, cell_size: float) -> shapely.LineString:
    """
    Write the cost path to a linestring. For now, this is a very primitive function.

    :param linestring: the resulting vectorized raster cost path.
    :param cell_size: resolution/cell_size of the raster.

    :return the cost path as simplified linestring.
    """
    aligned_linestring = linestring.simplify(cell_size, preserve_topology=True)

    return aligned_linestring
