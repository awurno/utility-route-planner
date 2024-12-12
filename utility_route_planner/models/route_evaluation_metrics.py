import rasterio.mask
import rasterio.features
import geopandas as gpd
import shapely
import structlog

from settings import Config
from utility_route_planner.util.write import write_results_to_geopackage

logger = structlog.get_logger(__name__)


class RouteEvaluationMetrics:
    def __init__(self, route: shapely.LineString, path_cost_surface: str, debug: bool = False):
        self.route = route
        self.path_cost_surface = path_cost_surface
        self.debug = debug

        self.route_length = 0
        self.route_relative_cost = 0

    def get_route_evaluation_metrics(self):
        """
        Get the evaluation metrics for the route. These consist out of:

        - Route length in meters.
        - Route relative cost. Note that the cell size used is important when comparing multiple routes.
        - route_computation_time: time it took to compute the route.

        Manually determined: ability to cope with design criteria constraints:
          - Minimum bending radius is respected (340mm)
          - Route alignment to existing infrastructure
          - Minimum working width is respected
          - Road crossings are straight and perpendicular
          - Metadata about route is available for annotation (what type of material is crossed and where)

        """
        self.route_length = self.route.length
        self.route_relative_cost, cell_size = self.get_route_cost_estimation(self.route, self.path_cost_surface)

        logger.info(f"Route length: {self.route_length:.2f} meters.")
        logger.info(
            f"Route relative cost: {self.route_relative_cost:2f} on a cost surface with cell size: {cell_size:.2f} meters."
        )

    def get_route_cost_estimation(self, route: shapely.LineString, path_cost_surface: str) -> tuple:
        with rasterio.Env():
            with rasterio.open(path_cost_surface) as src:
                image, transform = rasterio.mask.mask(
                    src,
                    [route],
                    all_touched=True,  # Include a pixel in the mask if it touches any of the shapes.
                    crop=True,  # Crop result to input project area.
                    filled=True,  # Values outside input project area will be set to nodata.
                    indexes=1,
                )
                no_data = src.nodata

                intersecting_cells = list(
                    rasterio.features.shapes(image.astype("uint8"), transform=transform, connectivity=8)
                )
                gdf_cells = gpd.GeoDataFrame(
                    [[i[1], shapely.Polygon(i[0]["coordinates"][0])] for i in intersecting_cells],
                    columns=["suitability_value", "geometry"],
                    crs=28992,
                )

                gdf_cells = gdf_cells[gdf_cells["suitability_value"] != no_data]

        gdf_route_segments = gpd.GeoDataFrame(geometry=gpd.GeoSeries(route), crs=28992).overlay(
            gdf_cells, how="intersection", keep_geom_type=False
        )
        gdf_route_segments["length"] = gdf_route_segments.length
        gdf_route_segments["cost"] = gdf_route_segments["length"] * gdf_route_segments["suitability_value"]
        total_relative_cost = gdf_route_segments["cost"].sum()

        if self.debug:
            write_results_to_geopackage(Config.PATH_GEOPACKAGE_LCPA_OUTPUT, route, "route", overwrite=True)
            write_results_to_geopackage(
                Config.PATH_GEOPACKAGE_LCPA_OUTPUT, gdf_cells, "intersecting_cells", overwrite=True
            )
            write_results_to_geopackage(
                Config.PATH_GEOPACKAGE_LCPA_OUTPUT, gdf_route_segments, "route_intersection", overwrite=True
            )

        return total_relative_cost, transform[0]
