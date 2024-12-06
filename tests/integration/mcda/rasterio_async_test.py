import asyncio
import time

import rasterio

from settings import Config


class TestReadRasterAsync:
    @staticmethod
    async def read_raster():
        with rasterio.open(Config.PATH_EXAMPLE_RASTER_EDE, "r") as src:
            file = src.read(1)
        await asyncio.sleep(1)
        print(file.shape)

    async def main(self):
        await asyncio.gather(*(self.read_raster() for _ in range(5)))

    def test_read_raster_async(self):
        asyncio.run(self.main())


class TestReadRasterSynchronously:
    @staticmethod
    def read_raster():
        with rasterio.open(Config.PATH_EXAMPLE_RASTER_EDE, "r") as src:
            file = src.read(1)
        time.sleep(1)
        print(file.shape)

    def test_read_raster_synchronously(self):
        [self.read_raster() for _ in range(5)]
