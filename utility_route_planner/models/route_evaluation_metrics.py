import rasterio.mask
import rasterio.features
import geopandas as gpd
import shapely
import structlog

from settings import Config
from utility_route_planner.util.write import write_results_to_geopackage

logger = structlog.get_logger(__name__)


class RouteEvaluationMetrics:
    def __init__(
        self,
        route_sota: shapely.LineString,
        path_cost_surface: str,
        route_human: shapely.LineString = shapely.LineString(),
        project_area: shapely.Polygon = shapely.Polygon(),
        similarity_threshold_m: int = 2,
        debug: bool = False,
    ):
        self.route_sota = route_sota
        self.path_cost_surface = path_cost_surface
        self.route_human = route_human
        self.project_area = project_area
        self.similarity_threshold_m = similarity_threshold_m
        self.debug = debug

        self.route_relative_cost_sota: int = 0
        self.route_relative_cost_human: int = 0
        self.route_similarity_sota: float = 0
        self.route_similarity_human: float = 0

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
        self.route_relative_cost_sota, cell_size, raster_shape = self.get_route_cost_estimation(
            self.route_sota, self.path_cost_surface
        )

        if self.project_area.area > 0:
            logger.info(f"Project area size is: {round(self.project_area.area/10000)} hectare.")
        logger.info(f"Cost-surface used has a shape {raster_shape} and a cell size of {cell_size:.2f} meters.")
        logger.info(f"Route SOTA length: {round(self.route_sota.length)} meters.")
        logger.info(f"Route SOTA relative cost SOTA: {round(self.route_relative_cost_sota)}.")
        if self.route_human.length > 0:
            logger.info(f"Route human length: {round(self.route_human.length)} meters.")
            self.route_relative_cost_human, cell_size, _ = self.get_route_cost_estimation(
                self.route_human, self.path_cost_surface
            )
            logger.info(f"Route human relative cost: {round(self.route_relative_cost_human)}.")

            self.route_similarity_sota, self.route_similarity_human = self.get_route_similarity(
                self.route_sota, self.route_human, self.similarity_threshold_m
            )
            logger.info(f"SOTA route overlaps: {self.route_similarity_sota}% with the human route.")
            logger.info(f"Human route overlaps: {self.route_similarity_human}% with the SOTA route.")

    def get_route_cost_estimation(self, route: shapely.LineString, path_cost_surface: str) -> tuple:
        with rasterio.Env():
            with rasterio.open(path_cost_surface) as src:
                raster_shape = src.shape
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
            write_results_to_geopackage(Config.PATH_GEOPACKAGE_LCPA_OUTPUT, route, "pytest_route", overwrite=True)
            write_results_to_geopackage(
                Config.PATH_GEOPACKAGE_LCPA_OUTPUT, gdf_cells, "pytest_intersecting_cells", overwrite=True
            )
            write_results_to_geopackage(
                Config.PATH_GEOPACKAGE_LCPA_OUTPUT, gdf_route_segments, "pytest_route_intersection", overwrite=True
            )

        return total_relative_cost, transform[0], raster_shape

    def get_route_similarity(
        self, route_sota: shapely.LineString, route_human: shapely.LineString, threshold_m
    ) -> tuple[float, float]:
        """Calculates simple overlap between two routes."""
        overlap_human = route_sota.buffer(threshold_m).intersection(route_human)
        overlap_percentage_human = 100 * overlap_human.length / route_human.length
        overlap_sota = route_human.buffer(threshold_m).intersection(route_sota)
        overlap_percentage_sota = 100 * overlap_sota.length / route_sota.length
        if self.debug:
            write_results_to_geopackage(
                Config.PATH_GEOPACKAGE_LCPA_OUTPUT, route_sota, "pytest_route_sota", overwrite=True
            )
            write_results_to_geopackage(
                Config.PATH_GEOPACKAGE_LCPA_OUTPUT, route_human, "pytest_route_human", overwrite=True
            )
            write_results_to_geopackage(
                Config.PATH_GEOPACKAGE_LCPA_OUTPUT,
                overlap_human,
                "pytest_overlap_human",
                overwrite=True,
            )
            write_results_to_geopackage(
                Config.PATH_GEOPACKAGE_LCPA_OUTPUT,
                overlap_sota,
                "pytest_overlap_sota",
                overwrite=True,
            )

        return round(overlap_percentage_sota, 2), round(overlap_percentage_human, 2)
