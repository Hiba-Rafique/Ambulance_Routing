import random
import time
from statistics import mean

from app.core.graph.graph_manager import GraphManager
from app.core.graph.shortest_path import shortest_path_and_distance


def build_random_graph(num_nodes: int, avg_degree: int = 4) -> GraphManager:
    """Build a synthetic directed graph with approximately avg_degree outgoing
    edges per node. We only use the in-memory adjacency list, so no DB access.
    """

    adjacency: dict[int, list[tuple[int, float, int]]] = {}
    edge_id = 0

    for u in range(num_nodes):
        neighbors = []
        # sample distinct neighbors (avoid self-loops for simplicity)
        possible_vs = [v for v in range(num_nodes) if v != u]
        # limit degree if graph is very small
        degree = min(avg_degree, len(possible_vs))
        for v in random.sample(possible_vs, degree):
            weight = random.uniform(1.0, 10.0)
            neighbors.append((v, weight, edge_id))
            edge_id += 1
        adjacency[u] = neighbors

    # We do not need real Edge objects for benchmarking Dijkstra – only weights.
    return GraphManager(adjacency=adjacency, edges={})


def time_shortest_path(num_nodes: int, runs: int = 3) -> float:
    """Build a graph with num_nodes and measure average runtime of
    shortest_path_and_distance over the given number of runs.
    Returns average runtime in seconds.
    """

    graph = build_random_graph(num_nodes)
    source = 0
    target = num_nodes - 1

    timings: list[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        _dist, _path = shortest_path_and_distance(graph, source, target)
        end = time.perf_counter()
        timings.append(end - start)

    return mean(timings)


def main() -> None:
    # Evaluate on three input sizes. Adjust upward/downward if too slow/fast.
    sizes = [10**3, 10**4, 10**5]
    runs_per_size = 3

    print("Benchmarking shortest_path_and_distance (Dijkstra)\n")
    print(f"Each size is averaged over {runs_per_size} runs.\n")

    for n in sizes:
        avg_seconds = time_shortest_path(n, runs=runs_per_size)
        print(f"N = {n:>7}: avg time = {avg_seconds:.6f} seconds")

    print("\nExpected theoretical complexity for Dijkstra with a binary heap:")
    print("O((V + E) log V) ≈ O(E log V) for sparse graphs like these.")


if __name__ == "__main__":
    main()
