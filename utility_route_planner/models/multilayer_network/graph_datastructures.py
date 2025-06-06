#  SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#  #
#  SPDX-License-Identifier: Apache-2.0
from dataclasses import dataclass

import shapely


@dataclass
class NodeInfo:
    osm_id: int
    geometry: shapely.Point
    node_id: int | None = None  # index of the node in the rustworkx graph.


@dataclass
class EdgeInfo:
    osm_id: int
    length: float
    geometry: shapely.LineString
    edge_id: int | None = None  # index of the edge in the rustworkx graph.
