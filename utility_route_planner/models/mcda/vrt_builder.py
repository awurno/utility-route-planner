# Based on the script generously provided by 12rambau on https://github.com/12rambau/rio-vrt
from os.path import relpath
from pathlib import Path
import xml.etree.cElementTree as et
from xml.dom import minidom

import rasterio
from pyproj import CRS
from rasterio.enums import ColorInterp


def _add_source_content(source: et.Element, src: rasterio.DatasetReader, type: str, xoff: str, yoff: str) -> None:
    """Add the content of a sourcefile in xml."""
    width, height = str(src.width), str(src.height)
    blockx = str(src.profile.get("blockxsize", ""))
    blocky = str(src.profile.get("blockysize", ""))

    attr = {
        "RasterXSize": width,
        "RasterYSize": height,
        "DataType": type,
    }

    # optional attributes
    if blockx and blocky:
        attr["BlockXSize"], attr["BlockYSize"] = blockx, blocky

    et.SubElement(source, "SourceProperties", attr)

    attr = {"xOff": "0", "yOff": "0", "xSize": width, "ySize": height}
    et.SubElement(source, "SrcRect", attr)

    attr = {"xOff": xoff, "yOff": yoff, "xSize": width, "ySize": height}
    et.SubElement(source, "DstRect", attr)


def build_vrt_file(
    files: list[str],
    vrt_path: Path,
    crs: CRS,
    raster_resolution: float,
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
):
    # rebuild the affine transformation from gathered information along with total bounds
    # negative y_res as we start from the top-left corner
    transform = rasterio.Affine.from_gdal(min_x, raster_resolution, 0, max_y, 0, -raster_resolution)
    total_width = round((max_x - min_x) / raster_resolution)
    total_height = round((max_y - min_y) / raster_resolution)

    # start the tree
    vrt_dataset = et.Element("VRTDataset", {"rasterXSize": str(total_width), "rasterYSize": str(total_height)})
    et.SubElement(vrt_dataset, "SRS").text = crs.to_wkt()

    transform_as_string = ", ".join([str(i) for i in transform.to_gdal()])
    et.SubElement(vrt_dataset, "GeoTransform").text = transform_as_string

    et.SubElement(vrt_dataset, "OverviewList", {"resampling": "nearest"}).text = "2 4 8"

    vrt_band = et.SubElement(vrt_dataset, "VRTRasterBand", {"dataType": "Int8", "band": "1"})

    et.SubElement(vrt_band, "Offset").text = "0.0"
    et.SubElement(vrt_band, "Scale").text = "1.0"
    et.SubElement(vrt_band, "ColorInterp").text = ColorInterp.gray.name.capitalize()
    et.SubElement(vrt_band, "NoDataValue").text = "0.0"

    # add the files
    relative_to_vrt = "1"
    for f in files:
        with rasterio.open(f) as src:
            source = et.SubElement(vrt_band, "ComplexSource")
            transform_as_string = relpath(f, vrt_path.parent)
            et.SubElement(source, "SourceFilename", {"relativeToVRT": relative_to_vrt}).text = transform_as_string
            et.SubElement(source, "SourceBand").text = "1"

            _add_source_content(
                source=source,
                src=src,
                type="Int8",
                xoff=str(abs(round((src.bounds.left - min_x) / raster_resolution))),
                yoff=str(abs(round((src.bounds.top - max_y) / raster_resolution))),
            )

            et.SubElement(source, "NODATA").text = "0.0"

    vrt_path.resolve().write_text(
        minidom.parseString(et.tostring(vrt_dataset).decode("utf-8")).toprettyxml(indent="  ").replace("&quot;", '"')
    )
