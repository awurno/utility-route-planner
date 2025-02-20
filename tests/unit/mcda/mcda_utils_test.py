import numpy as np
import shapely

from models.mcda.mcda_utils import create_project_area_grid
from settings import Config


class TestProjectAreaGridCreation:
    def test_grid_tile_size_smaller_than_max_tile_size(self):
        project_area_geometry = shapely.Point(187542.57, 428280.47).buffer(1000)
        project_area_grid = create_project_area_grid(*project_area_geometry.bounds)

        # The number of tiles must be equal to RASTER_NR_OF_TILES_ON_AXIS^2 as each tile is smaller than the max
        # tile size
        assert len(project_area_grid) == Config.RASTER_NR_OF_TILES_ON_AXIS**2

        # The bounds of the project area must be equal to the bounding box of the grid
        assert np.array_equal(project_area_grid.total_bounds, np.array(project_area_geometry.bounds))

    def test_create_project_area_grid_tile_size_exceeds_max_tile_size(self):
        project_area_geometry = shapely.Point(187542.57, 428280.47).buffer(5000)
        project_area_grid = create_project_area_grid(*project_area_geometry.bounds)

        # As the tile size would exceed the max tile size when working with the configured number of tiles, the number
        # of tiles should exceed Config.RASTER_NR_OF_TILES_ON_AXIS ** 2
        assert len(project_area_grid) > Config.RASTER_NR_OF_TILES_ON_AXIS**2

        # Verify that the size of each tile is equal to the max tile size
        for tile_geom in project_area_grid.geometry:
            x_min, y_min, x_max, y_max = tile_geom.bounds
            assert x_max - x_min == Config.MAX_TILE_SIZE
            assert y_max - y_min == Config.MAX_TILE_SIZE

        # Verify that the project area is completely covered by the project area grid
        assert project_area_geometry.within(project_area_grid.unary_union)
