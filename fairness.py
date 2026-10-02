"""Finite reset monitors and reactive-graph queries.

No function in this module synthesizes a scheduler against demonic choices.
`live` means existence of an infinite path, not a winning strategy.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product
from typing import Iterable

Graph = tuple[tuple[int, ...], ...]
MAX_PRODUCT_STATES = 100_000
MAX_OBLIGATIONS = 16


def natural(x: int, name: str) -> None:
    if type(x) is not int or x < 0:
        raise ValueError(f'{name} must be a nonnegative integer')


def longest_miss(word: Iterable[int]) -> int:
    current = maximum = 0
    for bit in word:
        if type(bit) is not int or bit not in (0, 1):
            raise ValueError('reset words contain integer bits only')
        current = current + 1 if bit else 0
        maximum = max(maximum, current)
    return maximum


def transported_bound(bound: int, expansion: int, aligned: bool = False) -> int:
    natural(bound, 'bound'); natural(expansion, 'expansion')
    if expansion == 0:
        raise ValueError('expansion blocks must be nonempty')
    return expansion * (bound + (1 if aligned else 2)) - (1 if aligned else 2)


def update(debt: tuple[int, ...], ready: frozenset[int], chosen: int,
           bound: int) -> tuple[int, ...] | None:
    """Reset on *source-state* disablement or service; reject only above bound."""
    natural(bound, 'bound')
    if any(type(x) is not int or not 0 <= x <= bound for x in debt):
        raise ValueError('invalid input debt')
    if type(chosen) is not int or not 0 <= chosen < len(debt):
        raise ValueError('invalid chosen action')
    if any(type(i) is not int or not 0 <= i < len(debt) for i in ready):
        raise ValueError('invalid ready set')
    if chosen not in ready:
        raise ValueError('chosen action must be enabled')
    result = tuple(0 if i not in ready or i == chosen else c + 1
                   for i, c in enumerate(debt))
    return None if any(c > bound for c in result) else result


@dataclass(frozen=True)
class System:
    """State-labelled, action-labelled LTS; each action is a fairness obligation."""
    observations: tuple[int, ...]
    actions: int
    edges: tuple[tuple[int, int, int], ...]

    def __post_init__(self) -> None:
        if not self.observations or any(type(x) is not int for x in self.observations):
            raise ValueError('nonempty integer observations required')
        natural(self.actions, 'actions')
        if not 1 <= self.actions <= MAX_OBLIGATIONS:
            raise ValueError('between 1 and 16 action obligations required')
        n = len(self.observations)
        for edge in self.edges:
            if len(edge) != 3 or any(type(x) is not int for x in edge):
                raise ValueError('invalid edge')
            s, a, t = edge
            if not (0 <= s < n and 0 <= t < n and 0 <= a < self.actions):
                raise ValueError('edge outside model bounds')
        if len(set(self.edges)) != len(self.edges):
            raise ValueError('duplicate edges are not a multiset semantics')

    def outgoing(self, state: int) -> tuple[tuple[int, int], ...]:
        return tuple((a, t) for s, a, t in self.edges if s == state)

    def ready(self, state: int) -> frozenset[int]:
        return frozenset(a for a, _ in self.outgoing(state))

    def is_total(self) -> bool:
        return all(self.outgoing(s) for s in range(len(self.observations)))


@dataclass(frozen=True)
class Product:
    graph: Graph
    states: tuple[tuple[int, tuple[int, ...]], ...]
    observations: tuple[int, ...]
    labelled_edges: tuple[tuple[int, int, int], ...]
    initials: tuple[int, ...]


def monitored(system: System, bound: int) -> Product:
    natural(bound, 'bound')
    n = len(system.observations)
    # Avoid constructing a large power or Cartesian product for untrusted dimensions.
    size = n
    for _ in range(system.actions):
        if size > MAX_PRODUCT_STATES // (bound + 1):
            raise ValueError('product exceeds explicit finite-state budget')
        size *= bound + 1
    if size > MAX_PRODUCT_STATES:
        raise ValueError('product exceeds explicit finite-state budget')
    debts = tuple(product(range(bound + 1), repeat=system.actions))
    states = tuple((s, d) for s in range(n) for d in debts)
    index = {v: i for i, v in enumerate(states)}
    adjacency: list[set[int]] = [set() for _ in states]
    edges = []
    for j, (s, d) in enumerate(states):
        ready = system.ready(s)
        for a, t in system.outgoing(s):
            out = update(d, ready, a, bound)
            if out is not None:
                k = index[t, out]
                adjacency[j].add(k); edges.append((j, a, k))
    return Product(tuple(tuple(sorted(x)) for x in adjacency), states,
                   tuple(system.observations[s] for s, _ in states), tuple(edges),
                   tuple(index[s, (0,) * system.actions] for s in range(n)))


def validate_graph(graph: Graph) -> None:
    n = len(graph)
    for row in graph:
        if any(type(t) is not int or not 0 <= t < n for t in row):
            raise ValueError('graph successor outside vertex set')
        if len(set(row)) != len(row):
            raise ValueError('graph rows must not have duplicates')


def live(graph: Graph, allowed: frozenset[int] | None = None) -> frozenset[int]:
    """Greatest fixed point of existential predecessor on an induced subgraph."""
    validate_graph(graph)
    current = set(range(len(graph))) if allowed is None else set(allowed)
    if any(type(v) is not int or not 0 <= v < len(graph) for v in current):
        raise ValueError('invalid allowed vertices')
    while True:
        following = {s for s in current if any(t in current for t in graph[s])}
        if following == current:
            return frozenset(current)
        current = following


def backward_reach(graph: Graph, targets: frozenset[int]) -> frozenset[int]:
    current = set(targets)
    while True:
        following = current | {s for s, row in enumerate(graph)
                               if any(t in current for t in row)}
        if following == current:
            return frozenset(current)
        current = following


def modes(graph: Graph, goal: frozenset[int]) -> dict[str, frozenset[int]]:
    viable = live(graph)
    avoiding = live(graph, frozenset(range(len(graph))) - goal)
    return {
        'viable': viable,
        'may_eventually': backward_reach(graph, viable & goal),
        'must_eventually': viable - avoiding,
        'must_recur': viable - backward_reach(graph, avoiding),
    }


def bisimulation(left: System, right: System,
                 relation: frozenset[tuple[int, int]]) -> bool:
    if left.actions != right.actions:
        return False
    for s, t in relation:
        if not (0 <= s < len(left.observations) and 0 <= t < len(right.observations)):
            return False
        if left.observations[s] != right.observations[t]:
            return False
        # This explicit check is redundant with full bidirectional action matching,
        # but documents the fairness interface and gives a useful diagnostic boundary.
        if left.ready(s) != right.ready(t):
            return False
        ls, rs = left.outgoing(s), right.outgoing(t)
        if any(not any(a == b and (u, v) in relation for b, v in rs)
               for a, u in ls):
            return False
        if any(not any(a == b and (u, v) in relation for a, u in ls)
               for b, v in rs):
            return False
    return True


def lifted_relation(left: Product, right: Product,
                    relation: frozenset[tuple[int, int]]) -> frozenset[tuple[int, int]]:
    return frozenset((i, j) for i, (s, d) in enumerate(left.states)
                     for j, (t, e) in enumerate(right.states)
                     if d == e and (s, t) in relation)


def tagged_interleaving(left: System, right: System) -> System:
    nr = len(right.observations)
    states = tuple(product(range(len(left.observations)), range(nr)))
    if min(left.observations + right.observations) < 0:
        raise ValueError('interleaving encoding requires nonnegative observations')
    # Cantor pairing is independent of each model's observation alphabet.
    # An encoding whose radix depends on one model's maximum would not be
    # preserved when bisimilar models contain different unreachable states.
    def pair(x: int, y: int) -> int:
        return (x + y) * (x + y + 1) // 2 + y
    observations = tuple(pair(left.observations[s], right.observations[t])
                         for s, t in states)
    edges = []
    for s, t in states:
        for a, u in left.outgoing(s):
            edges.append((s * nr + t, a, u * nr + t))
        for a, v in right.outgoing(t):
            edges.append((s * nr + t, left.actions + a, s * nr + v))
    return System(observations, left.actions + right.actions, tuple(edges))
