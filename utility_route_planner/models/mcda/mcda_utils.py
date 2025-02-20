import math

import geopandas as gpd
import numpy as np
from shapely.geometry.geo import box

from settings import Config


def create_project_area_grid(min_x: float, min_y: float, max_x: float, max_y: float):
    # The tile size is computed based on the preferred number of tiles on each axis. In case this would exceed the
    # max tile size, the max tile is used to constrain the amount of memory required.
    tile_width = min(math.ceil((max_x - min_x) / Config.RASTER_NR_OF_TILES_ON_AXIS), Config.MAX_TILE_SIZE)
    tile_height = min(math.ceil((max_y - min_y) / Config.RASTER_NR_OF_TILES_ON_AXIS), Config.MAX_TILE_SIZE)

    x_coords = np.arange(min_x, max_x, tile_width)
    y_coords = np.arange(min_y, max_y, tile_height)
    grid_cells = [box(x, y, x + tile_width, y + tile_height) for x in x_coords for y in y_coords]
    grid = gpd.GeoDataFrame(grid_cells, columns=["geometry"], crs=Config.CRS)
    return grid
