#  SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#  #
#  SPDX-License-Identifier: Apache-2.0
from dataclasses import dataclass

import shapely


@dataclass
class NodeInfo:
    node_id: int | None
    geometry: shapely.Point


@dataclass
class OSMNodeInfo(NodeInfo):
    osm_id: int


@dataclass
class HexagonNodeInfo(NodeInfo):
    suitability_value: float
    axial_q: float
    axial_r: float


@dataclass
class EdgeInfo:
    length: float
    geometry: shapely.LineString


@dataclass
class OSMEdgeInfo(EdgeInfo):
    osm_id: int


@dataclass
class HexagonEdgeInfo(EdgeInfo):
    weight: float
