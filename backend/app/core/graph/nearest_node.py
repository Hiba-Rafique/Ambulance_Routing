"""Utilities for mapping real-world coordinates to graph nodes.

This module answers the question:

    "Given a latitude/longitude inside a city, which graph node should we
    use as the starting point for routing?"

In other words, it performs a **nearest-neighbor search** over the set of
nodes in a city. For now we use a simple linear scan, which is perfectly
fine for moderate graph sizes and very easy to understand and explain:

- Time complexity: O(N) per query, where N is the number of nodes
  in the city.
- Space complexity: O(1) additional space.

Later, if we want to highlight more advanced DSA, we can replace the
linear scan with a spatial data structure (e.g. k-d tree or R-tree).
The rest of the system will not need to change, because it only calls
`find_nearest_node_for_location`.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from ...db.models import Node


def _squared_euclidean_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute squared Euclidean distance between two (lat, lon) points.

    We intentionally do **not** take the square root because:
    - For comparison purposes (finding the minimum), the square root is
      monotonic, so the ranking of distances is the same.
    - Avoiding `sqrt` keeps the computation slightly cheaper and keeps
      the formula clean when explaining.

    This is an approximation because the Earth is curved, but for
    distances within a city it is good enough and keeps the math simple.
    """

    dlat = lat1 - lat2
    dlon = lon1 - lon2
    return dlat * dlat + dlon * dlon


def find_nearest_node_for_location(
    db: Session,
    city_id: int,
    latitude: float,
    longitude: float,
) -> Optional[int]:
    """Find the node in a given city that is closest to (latitude, longitude).

    Parameters
    ----------
    db:
        SQLAlchemy session used to query the `nodes` table.
    city_id:
        ID of the city in which we should search.
    latitude, longitude:
        Location of the patient/caller in decimal degrees.

    Returns
    -------
    Optional[int]
        ID of the nearest node, or None if the city has no nodes.

    Algorithm (how to explain it):
    1. Retrieve all nodes that belong to the specified city.
    2. For each node, compute an approximate squared distance from the
       given (lat, lon) to the node's (lat, lon).
    3. Keep track of the node with the smallest distance seen so far.
    4. Return the ID of that node.
    """

    nodes = db.query(Node).filter(Node.city_id == city_id).all()
    if not nodes:
        return None

    best_node_id: Optional[int] = None
    best_distance_sq: Optional[float] = None

    for node in nodes:
        dist_sq = _squared_euclidean_distance(latitude, longitude, node.lat, node.lon)

        if best_distance_sq is None or dist_sq < best_distance_sq:
            best_distance_sq = dist_sq
            best_node_id = node.id

    return best_node_id
