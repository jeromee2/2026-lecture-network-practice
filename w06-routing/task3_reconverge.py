#!/usr/bin/env python3
"""Week 6 · Task 3 — Reconverge without recomputing the world.

Textbook §5.2.1, §5.3.

A link flaps. Every router in the area has to decide what changed. `FullRecompute`
does the honest thing: throw the table away and run Dijkstra again, from scratch,
for every event. It is correct and it is what the first implementations did.

It is also why a single flapping link in a large area used to melt the CPU of
every router that could see it.

Beat it:

    python3 bench.py
    python3 bench.py --yours

Correctness first. `bench.py` compares your table against a full recompute after
**every single event**. A router that is fast and wrong black-holes traffic.
"""
import heapq

# The harness counts how many times you run a full SPF. This is the score:
# wall-clock time in Python says more about dictionary overhead than about
# routing, but "how many times did the CPU have to recompute the world" is
# exactly what melted real routers.
SPF_RUNS = 0


def dijkstra_table(graph, source, *, with_state=False):
    """Reference shortest-path-first. Returns {destination: first_hop}.

    Use THIS function whenever you need a full recompute. Rolling your own to
    dodge the counter is not an optimisation, it is cheating the meter.
    """
    global SPF_RUNS
    SPF_RUNS += 1
    best = {source: (0, None)}
    parent = {}
    pq, done = [(0, source, None)], set()
    while pq:
        cost, node, first_hop = heapq.heappop(pq)
        if node in done:
            continue
        done.add(node)
        best[node] = (cost, first_hop)
        for nbr, w in sorted(graph[node].items()):
            if nbr in done:
                continue
            hop = nbr if node == source else first_hop
            if cost + w < best.get(nbr, (float("inf"), None))[0]:
                best[nbr] = (cost + w, hop)
                parent[nbr] = node
                heapq.heappush(pq, (cost + w, nbr, hop))
    table = {d: h for d, (_, h) in best.items() if d != source and h}
    if with_state:
        return table, {d: cost for d, (cost, _) in best.items()}, parent
    return table


class FullRecompute:
    """On every event, forget everything and run SPF again."""

    def __init__(self, graph, source):
        self.graph = {n: dict(e) for n, e in graph.items()}
        self.source = source
        self.table = dijkstra_table(self.graph, source)

    def link_change(self, a, b, cost):
        """cost=None means the link went down."""
        if cost is None:
            self.graph[a].pop(b, None)
            self.graph[b].pop(a, None)
        else:
            self.graph[a][b] = cost
            self.graph[b][a] = cost
        self.table = dijkstra_table(self.graph, self.source)


class YourRouter:
    """Your router. Same two methods, same table, less work per event.

    What is actually true after one link changes:

      * most destinations are not affected at all
      * a link that is not on any of your shortest paths, going *up*, can only
        matter if it creates something shorter
      * a link going *down* only matters if you were using it

    Deciding which of those applies, cheaply, without getting it wrong, is the
    task. Getting it wrong is worse than being slow - the harness will catch it
    on the event where it happens.
    """

    def __init__(self, graph, source):
        self.graph = {n: dict(e) for n, e in graph.items()}
        self.source = source
        self.table, self.distances, self.parent = dijkstra_table(
            self.graph, source, with_state=True)

    def _recompute(self):
        self.table, self.distances, self.parent = dijkstra_table(
            self.graph, self.source, with_state=True)

    def _uses_tree_edge(self, a, b):
        return self.parent.get(a) == b or self.parent.get(b) == a

    def _repair_decrease(self, a, b, cost):
        queue = []

        def relax(node, neighbour, distance, hop):
            if neighbour == self.source:
                return
            candidate = distance + self.graph[node][neighbour]
            old = self.distances.get(neighbour, float("inf"))
            next_hop = neighbour if node == self.source else hop
            better_tie = False
            if candidate == old and neighbour in self.parent:
                old_parent = self.parent[neighbour]
                old_hop = None if old_parent == self.source else self.table[old_parent]
                better_tie = ((node == old_parent and next_hop != self.table[neighbour]) or
                              (distance, node, hop) <
                              (self.distances[old_parent], old_parent, old_hop))
            if candidate < old or better_tie:
                self.distances[neighbour] = candidate
                self.parent[neighbour] = node
                self.table[neighbour] = next_hop
                heapq.heappush(queue, (candidate, neighbour, next_hop))

        relax(a, b, self.distances.get(a, float("inf")),
              None if a == self.source else self.table.get(a))
        relax(b, a, self.distances.get(b, float("inf")),
              None if b == self.source else self.table.get(b))

        while queue:
            distance, node, hop = heapq.heappop(queue)
            if (distance, hop) != (self.distances[node], self.table[node]):
                continue
            for neighbour, weight in sorted(self.graph[node].items()):
                relax(node, neighbour, distance, hop)

    def link_change(self, a, b, cost):
        old_cost = self.graph[a].get(b)
        if cost is None:
            if old_cost is None:
                return
            affected = self._uses_tree_edge(a, b)
            self.graph[a].pop(b, None)
            self.graph[b].pop(a, None)
        else:
            if old_cost == cost:
                return
            if old_cost is None or cost < old_cost:
                self.graph[a][b] = cost
                self.graph[b][a] = cost
                self._repair_decrease(a, b, cost)
                return
            else:
                affected = self._uses_tree_edge(a, b)
            self.graph[a][b] = cost
            self.graph[b][a] = cost

        # ponytail: selected-tree loss/increase recomputes the world; local
        # subtree repair is the upgrade if these events dominate.
        if affected:
            self._recompute()
