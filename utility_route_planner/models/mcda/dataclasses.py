from dataclasses import dataclass

import numpy as np
from rasterio.windows import Window


@dataclass
class RasterBlock:
    array: np.ma.MaskedArray
    window: Window
