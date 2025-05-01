#  SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#  #
#  SPDX-License-Identifier: Apache-2.0

import math


def get_hexagon_width_and_height(self) -> tuple[float, float]:
    hexagon_width = 2 * self.hexagon_size
    hexagon_height = math.sqrt(3) * self.hexagon_size

    return hexagon_width, hexagon_height
