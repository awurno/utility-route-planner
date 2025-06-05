# SPDX-FileCopyrightText: Contributors to the utility-route-project and Alliander N.V.
#
# SPDX-License-Identifier: Apache-2.0
import shapely

from utility_route_planner.models.multilayer_network.osm_graph_preprocessing import NodeInfo, EdgeInfo


def create_edge_info(osm_id: int, start_node: NodeInfo, end_node: NodeInfo) -> EdgeInfo:
    geometry = shapely.LineString([start_node.geometry, end_node.geometry])
    length = geometry.length
    return EdgeInfo(osm_id=osm_id, length=length, geometry=geometry)
