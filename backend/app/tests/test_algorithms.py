import os
import sys
from datetime import datetime, timedelta

import pytest
import sqlalchemy
from sqlalchemy import create_engine as _real_create_engine

# Ensure the backend app package is on the path when tests run from repo root.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Force SQLAlchemy to use an in-memory SQLite engine during tests so imports
# of the app's database module do not require a MySQL driver or running server.
sqlalchemy.create_engine = lambda *_args, **_kwargs: _real_create_engine("sqlite:///:memory:")

from app.core.graph.graph_manager import GraphManager
from app.core.graph.nearest_node import find_nearest_node_for_location
from app.core.graph.shortest_path import shortest_path_and_distance
from app.core.routing import traffic_manager
from app.core.routing.traffic_manager import apply_dynamic_traffic
from app.db import models


def test_shortest_path_finds_optimal_route():
    graph = GraphManager(
        adjacency={
            1: [(2, 1.0, 1), (3, 5.0, 2)],
            2: [(3, 1.5, 3)],
            3: [],
        },
        edges={},
    )

    distance, path = shortest_path_and_distance(graph, 1, 3)

    assert distance == pytest.approx(2.5)
    assert path == [1, 2, 3]


def test_shortest_path_reports_unreachable_target():
    graph = GraphManager(
        adjacency={
            1: [(2, 1.0, 1)],
            2: [],
            3: [],
        },
        edges={},
    )

    distance, path = shortest_path_and_distance(graph, 1, 3)

    assert distance is None
    assert path == []


def test_apply_dynamic_traffic_blocks_and_updates_edges(monkeypatch):
    fixed_now = datetime(2024, 1, 1, 8, 0, 0)  # peak hour so traffic updates apply

    class _FixedDatetime(datetime):
        @classmethod
        def utcnow(cls):
            return fixed_now

    # Freeze time inside the traffic_manager module
    monkeypatch.setattr(traffic_manager, "datetime", _FixedDatetime)

    # Build edges/nodes used by the traffic rules
    blocked_edge = models.Edge(
        id=1, from_node=1, to_node=2, weight=5.0, adjusted_weight=None, distance=None, is_active=True
    )
    blocked_edge.from_node_rel = models.Node(id=1, lat=0.0, lon=0.0, type="intersection", city_id=1)
    blocked_edge.to_node_rel = models.Node(id=2, lat=0.0, lon=1.0, type="intersection", city_id=1)

    updated_edge = models.Edge(
        id=2, from_node=2, to_node=3, weight=2.0, adjusted_weight=None, distance=None, is_active=True
    )
    updated_edge.from_node_rel = models.Node(id=2, lat=0.0, lon=1.0, type="intersection", city_id=1)
    updated_edge.to_node_rel = models.Node(id=3, lat=0.0, lon=2.0, type="intersection", city_id=1)

    roadblock = models.Roadblock(
        edge=blocked_edge,
        start_time=fixed_now - timedelta(hours=1),
        end_time=None,
        reason="construction",
    )
    traffic_update = models.TrafficUpdate(edge=updated_edge, new_weight=10.0, timestamp=fixed_now)

    class _FakeQuery:
        def __init__(self, items):
            self._items = items

        def join(self, *args, **kwargs):
            return self

        def filter(self, *args, **kwargs):
            return self

        def all(self):
            return list(self._items)

    class _FakeSession:
        def __init__(self, roadblocks, updates):
            self.roadblocks = roadblocks
            self.updates = updates

        def query(self, model):
            if model is models.Roadblock:
                return _FakeQuery(self.roadblocks)
            if model is models.TrafficUpdate:
                return _FakeQuery(self.updates)
            return _FakeQuery([])

    graph = GraphManager(
        adjacency={
            1: [(2, 5.0, blocked_edge.id), (3, 1.0, 99)],
            2: [(3, 2.0, updated_edge.id)],
            3: [],
        },
        edges={},
    )

    apply_dynamic_traffic(graph, _FakeSession([roadblock], [traffic_update]), city_id=1)

    assert graph.adjacency[1] == [(3, 1.0, 99)]  # roadblock removed (1 -> 2)
    assert graph.adjacency[2] == [(3, 10.0, updated_edge.id)]  # weight updated during peak hour


def test_find_nearest_node_selects_closest_by_distance():
    class _FakeQuery:
        def __init__(self, items):
            self._items = items

        def filter(self, *args, **kwargs):
            return self

        def all(self):
            return list(self._items)

    class _FakeSession:
        def __init__(self, nodes):
            self._nodes = nodes

        def query(self, model):
            assert model is models.Node
            return _FakeQuery(self._nodes)

    nodes = [
        models.Node(id=1, lat=0.0, lon=0.0, city_id=1),
        models.Node(id=2, lat=1.0, lon=1.0, city_id=1),
        models.Node(id=3, lat=-1.0, lon=-1.0, city_id=1),
    ]
    session = _FakeSession(nodes)

    nearest = find_nearest_node_for_location(session, city_id=1, latitude=0.2, longitude=0.1)

    assert nearest == 1

