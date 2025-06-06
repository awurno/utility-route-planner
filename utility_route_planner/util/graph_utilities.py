# SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#
# SPDX-License-Identifier: Apache-2.0
import shapely

from models.multilayer_network.graph_datastructures import OSMNodeInfo, EdgeInfo


def create_edge_info(osm_id: int, start_node: OSMNodeInfo, end_node: OSMNodeInfo) -> EdgeInfo:
    geometry = shapely.LineString([start_node.geometry, end_node.geometry])
    length = geometry.length
    return EdgeInfo(osm_id=osm_id, length=length, geometry=geometry)
