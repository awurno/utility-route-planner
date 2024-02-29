import geopandas as gpd
import shapely

from settings import Config


def write_to_file(geometry: gpd.GeoSeries | gpd.GeoDataFrame | shapely.Geometry, name: str):
    if isinstance(geometry, shapely.Geometry):
        geometry = gpd.GeoSeries(geometry, crs=28992)

    if isinstance(geometry, gpd.GeoSeries | gpd.GeoDataFrame):
        pass

    geometry.to_file(Config.PATH_RESULTS / name)
