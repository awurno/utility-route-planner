#  SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#  #
#  SPDX-License-Identifier: Apache-2.0

import math


def get_hexagon_width_and_height(hexagon_size: float) -> tuple[float, float]:
    hexagon_width = 2 * hexagon_size
    hexagon_height = math.sqrt(3) * hexagon_size

    return hexagon_width, hexagon_height
