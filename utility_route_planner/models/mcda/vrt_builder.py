# Based on the script generously provided by 12rambau on https://github.com/12rambau/rio-vrt
from os.path import relpath
from pathlib import Path
from statistics import mean
import xml.etree.cElementTree as ET
from xml.dom import minidom

import rasterio
from rasterio.enums import ColorInterp


types = {
    "byte": "Byte",
    "uint8": "Byte",
    "uint16": "UInt16",
    "int8": "Int8",
    "int16": "Int16",
    "uint32": "UInt32",
    "int32": "Int32",
    "uint64": "UInt64",
    "int64": "Int64",
    "float32": "Float32",
    "float63": "Float64",
    "cint16": "CInt16",
    "cint32": "CInt32",
    "cfloat32": "CFloat32",
    "cfloat64": "CFloat64",
}


def _add_source_content(Source: ET.Element, src: rasterio.DatasetReader, type: str, xoff: str, yoff: str) -> None:
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

    ET.SubElement(Source, "SourceProperties", attr)

    attr = {"xOff": "0", "yOff": "0", "xSize": width, "ySize": height}
    ET.SubElement(Source, "SrcRect", attr)

    attr = {"xOff": xoff, "yOff": yoff, "xSize": width, "ySize": height}
    ET.SubElement(Source, "DstRect", attr)


def build_vrt_file(
    files: list[str],
    vrt_path: Path,
):
    with rasterio.open(files[0]) as f:
        crs = f.crs
        dtypes = f.dtypes  # --> is altijd int8
        colorinterps = f.colorinterp
        indexes = f.indexes
        nodatavals = f.nodatavals

    # read all files to extract information on the spatial extend of the vrt --> kunnen we misschien ook al uit de project geometry halen?
    left_, bottom_, right_, top_, xres_, yres_ = [], [], [], [], [], []
    for file in files:
        with rasterio.open(file) as f:
            xres_.append(f.res[0])
            yres_.append(f.res[0])
            left_.append(f.bounds.left)
            right_.append(f.bounds.right)
            top_.append(f.bounds.top)
            bottom_.append(f.bounds.bottom)

    # get the spatial extend of the dataset
    left = min(*left_)
    bottom = min(*bottom_)
    right = max(*right_)
    top = max(*top_)

    # get the resolution (res = average for now) --> deze weten we al, die is altijd 0.5 en kan uit de setting gelezen worden
    xres, yres = mean(xres_), mean(yres_)

    # rebuild the affine transformation from gathered information along with total bounds
    # negative y_res as we start from the top-left corner
    transform = rasterio.Affine.from_gdal(left, xres, 0, top, 0, -yres)
    total_width = round((right - left) / xres)
    total_height = round((top - bottom) / yres)

    # start the tree
    attr = {"rasterXSize": str(total_width), "rasterYSize": str(total_height)}
    VRTDataset = ET.Element("VRTDataset", attr)

    # don't know how to extract dataAxisToSRSAxisMapping
    # https://gis.stackexchange.com/questions/458781/how-to-get-dataaxistosrsaxismapping-from-an-image
    # revert to OAMS_TRADITIONAL_GIS_ORDER  until then
    ET.SubElement(VRTDataset, "SRS").text = crs.wkt

    text = ", ".join([str(i) for i in transform.to_gdal()])
    ET.SubElement(VRTDataset, "GeoTransform").text = text

    ET.SubElement(VRTDataset, "OverviewList", {"resampling": "nearest"}).text = "2 4 8"

    VRTRasterBands_dict = {}
    for i in indexes:
        attr = {"dataType": types[dtypes[i - 1]], "band": str(i)}  # --> is altijd int8
        VRTRasterBands_dict[i] = ET.SubElement(VRTDataset, "VRTRasterBand", attr)

        ET.SubElement(VRTRasterBands_dict[i], "Offset").text = "0.0"

        ET.SubElement(VRTRasterBands_dict[i], "Scale").text = "1.0"

        if colorinterps[i - 1] != ColorInterp.undefined:
            color = colorinterps[i - 1].name.capitalize()
            ET.SubElement(VRTRasterBands_dict[i], "ColorInterp").text = color  # --> is altijd Gray

        if nodatavals[i - 1] is not None:
            text = str(nodatavals[i - 1])  # --> Is altijd 0.0
            ET.SubElement(VRTRasterBands_dict[i], "NoDataValue").text = text

    # add the files
    for f in files:
        relativeToVRT = "1"
        with rasterio.open(f) as src:
            for i in indexes:
                is_alpha = colorinterps[i - 1] == ColorInterp.alpha  # --> is altijd False (altijd grijs namelijk)
                has_nodata = nodatavals[i - 1] is not None
                source_type = "ComplexSource" if is_alpha or has_nodata else "SimpleSource"
                Source = ET.SubElement(VRTRasterBands_dict[i], source_type)

                attr = {"relativeToVRT": relativeToVRT}
                text = relpath(f, vrt_path.parent)
                ET.SubElement(Source, "SourceFilename", attr).text = text

                ET.SubElement(Source, "SourceBand").text = str(i)

                _add_source_content(
                    Source=Source,
                    src=src,
                    type=types[dtypes[i - 1]],
                    xoff=str(abs(round((src.bounds.left - left) / xres))),
                    yoff=str(abs(round((src.bounds.top - top) / yres))),
                )

                if nodatavals[i - 1] is not None:
                    text = str(nodatavals[i - 1])
                    ET.SubElement(Source, "NODATA").text = text

    vrt_path.resolve().write_text(
        minidom.parseString(ET.tostring(VRTDataset).decode("utf-8")).toprettyxml(indent="  ").replace("&quot;", '"')
    )


if __name__ == "__main__":
    raster_ids = list(range(0, 30))
    raster_files = [f"data/processed/benchmark_suitability_raster-{i}.tif" for i in list(range(0, 30))]
    build_vrt_file(raster_files, Path("data", "processed", "example.vrt"))

    pass
