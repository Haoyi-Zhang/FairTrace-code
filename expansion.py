"""Canonical regular microstep expansion of reset/observation-labelled systems."""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass

from transducers import Transducer

ERASE = -1
MAX_STATES = 100_000


@dataclass(frozen=True)
class Edge:
    source: int
    target: int
    reset: int
    low: int

    def __post_init__(self) -> None:
        if any(type(x) is not int for x in (self.source, self.target, self.reset, self.low)):
            raise ValueError('edge fields must be integers')
        if self.source < 0 or self.target < 0 or self.reset not in (0, 1) or self.low < ERASE:
            raise ValueError('invalid labelled edge')


@dataclass(frozen=True)
class TraceSystem:
    """Finite labelled multigraph with stable edge identities.

    Edge identity is its index in the immutable ``edges`` tuple.  Parallel
    edges may have identical labels and endpoints; path APIs therefore use
    edge indices rather than structural edge equality.
    """
    states: int
    initial: int
    edges: tuple[Edge, ...]

    def __post_init__(self) -> None:
        if type(self.states) is not int or self.states <= 0 or self.states > MAX_STATES:
            raise ValueError('invalid state count')
        if type(self.initial) is not int or not 0 <= self.initial < self.states:
            raise ValueError('invalid initial state')
        for edge in self.edges:
            if edge.source >= self.states or edge.target >= self.states:
                raise ValueError('edge outside state space')

    def outgoing(self, state: int) -> tuple[tuple[int, Edge], ...]:
        if type(state) is not int or not 0 <= state < self.states:
            raise ValueError('invalid state')
        return tuple((i, edge) for i, edge in enumerate(self.edges) if edge.source == state)


@dataclass(frozen=True)
class Expanded:
    system: TraceSystem
    boundary: dict[tuple[int, int], int]
    chains: dict[tuple[int, int], tuple[int, ...]]
    chain_edges: dict[tuple[int, int], tuple[int, ...]]
    edge_owners: tuple[tuple[int, int, int], ...]
    edge_symbols: tuple[int, ...]


def _edge_symbols(source: TraceSystem, machine: Transducer,
                  edge_symbols: tuple[int, ...] | None) -> tuple[int, ...]:
    if edge_symbols is None:
        if machine.alphabet != 2 or machine.input_resets != (0, 1):
            raise ValueError('noncanonical input alphabets require edge-symbol annotations')
        edge_symbols = tuple(edge.reset for edge in source.edges)
    if (not isinstance(edge_symbols, tuple) or len(edge_symbols) != len(source.edges) or
            any(type(symbol) is not int or not 0 <= symbol < machine.alphabet
                for symbol in edge_symbols)):
        raise ValueError('invalid edge-symbol annotations')
    if any(machine.input_resets[symbol] != edge.reset
           for symbol, edge in zip(edge_symbols, source.edges)):
        raise ValueError('edge symbol disagrees with source reset annotation')
    return edge_symbols


def canonical_expansion(source: TraceSystem, machine: Transducer,
                        edge_symbols: tuple[int, ...] | None = None) -> Expanded:
    """Expand each source edge into the block emitted by ``machine``.

    Boundary states are pairs of source and transducer states.  A source edge is
    chosen only at a boundary; all remaining microsteps of its block are
    deterministic.  The source low label appears on the final microstep and all
    preceding microsteps erase.
    """
    symbols = _edge_symbols(source, machine, edge_symbols)
    boundary: dict[tuple[int, int], int] = {}
    state_count = 0
    for s in range(source.states):
        for q in range(machine.states):
            boundary[s, q] = state_count; state_count += 1
    target_edges: list[Edge] = []
    edge_owners: list[tuple[int, int, int]] = []
    chains: dict[tuple[int, int], tuple[int, ...]] = {}
    chain_edges: dict[tuple[int, int], tuple[int, ...]] = {}
    for q in range(machine.states):
        for edge_id, source_edge in enumerate(source.edges):
            transition = machine.step(q, symbols[edge_id])
            block = transition.output
            start = boundary[source_edge.source, q]
            end = boundary[source_edge.target, transition.next_state]
            vertices = [start]
            for _ in range(len(block) - 1):
                if state_count >= MAX_STATES:
                    raise ValueError('expanded system exceeds state budget')
                vertices.append(state_count); state_count += 1
            vertices.append(end)
            target_ids = []
            for position, bit in enumerate(block):
                low = source_edge.low if position == len(block) - 1 else ERASE
                target_ids.append(len(target_edges))
                target_edges.append(Edge(vertices[position], vertices[position + 1], bit, low))
                edge_owners.append((q, edge_id, position))
            chains[q, edge_id] = tuple(vertices)
            chain_edges[q, edge_id] = tuple(target_ids)
    target = TraceSystem(state_count, boundary[source.initial, machine.initial], tuple(target_edges))
    return Expanded(target, boundary, chains, chain_edges, tuple(edge_owners), symbols)


def expand_target_edge_path(expanded: Expanded, source: TraceSystem,
                            machine: Transducer, edge_ids: tuple[int, ...],
                            edge_symbols: tuple[int, ...] | None = None
                            ) -> tuple[int, ...]:
    """Expand a boundary-complete source edge path to target edge identities."""
    symbols = _edge_symbols(
        source, machine, expanded.edge_symbols if edge_symbols is None else edge_symbols)
    if symbols != expanded.edge_symbols:
        raise ValueError('edge-symbol annotations disagree with the expansion')
    if not isinstance(edge_ids, tuple):
        raise ValueError('source edge path must be a tuple of stable edge ids')
    state = source.initial
    q = machine.initial
    current = expanded.system.initial
    result: list[int] = []
    for edge_id in edge_ids:
        if type(edge_id) is not int or not 0 <= edge_id < len(source.edges):
            raise ValueError('invalid source edge id')
        source_edge = source.edges[edge_id]
        if source_edge.source != state:
            raise ValueError('edge sequence is not a source path')
        chain = expanded.chain_edges[q, edge_id]
        for target_edge_id in chain:
            target_edge = expanded.system.edges[target_edge_id]
            if target_edge.source != current:
                raise AssertionError('stored target chain is not contiguous')
            current = target_edge.target
            result.append(target_edge_id)
        transition = machine.step(q, symbols[edge_id])
        state = source_edge.target
        q = transition.next_state
        if current != expanded.boundary[state, q]:
            raise AssertionError('stored target chain has the wrong boundary endpoint')
    return tuple(result)


def decompose_target_edge_path(expanded: Expanded,
                               target_edge_ids: tuple[int, ...]) -> tuple[int, ...]:
    """Recover source edge identities from a complete expanded edge path.

    The parser requires the complete target edge sequence.  Boundary states
    alone are insufficient when parallel length-one chains share endpoints.
    """
    if not isinstance(target_edge_ids, tuple):
        raise ValueError('target edge path must be a tuple of stable edge ids')
    if any(type(edge_id) is not int or
           not 0 <= edge_id < len(expanded.system.edges)
           for edge_id in target_edge_ids):
        raise ValueError('invalid target edge id')
    current = expanded.system.initial
    cursor = 0
    source_path: list[int] = []
    while cursor < len(target_edge_ids):
        target_edge_id = target_edge_ids[cursor]
        if (type(target_edge_id) is not int or
                not 0 <= target_edge_id < len(expanded.system.edges)):
            raise ValueError('invalid target edge id')
        first = expanded.system.edges[target_edge_id]
        if first.source != current:
            raise ValueError('target edge sequence is not a path from the initial state')
        q, source_edge_id, position = expanded.edge_owners[target_edge_id]
        if position != 0:
            raise ValueError('target path starts inside an expansion chain')
        chain = expanded.chain_edges[q, source_edge_id]
        stop = cursor + len(chain)
        if tuple(target_edge_ids[cursor:stop]) != chain:
            raise ValueError('target path does not follow one complete identified chain')
        for edge_id in chain:
            edge = expanded.system.edges[edge_id]
            if edge.source != current:
                raise ValueError('target edge sequence is not contiguous')
            current = edge.target
        source_path.append(source_edge_id)
        cursor = stop
    if current not in expanded.boundary.values():
        raise ValueError('target path ends inside an expansion chain')
    return tuple(source_path)


def erase(labels: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(label for label in labels if label != ERASE)


def expand_finite_path(source: TraceSystem, machine: Transducer,
                       edge_ids: tuple[int, ...],
                       edge_symbols: tuple[int, ...] | None = None
                       ) -> tuple[tuple[int, ...], tuple[int, ...], int]:
    """Return target reset bits, low labels and final transducer state."""
    symbols = _edge_symbols(source, machine, edge_symbols)
    state = source.initial
    q = machine.initial
    resets: list[int] = []
    lows: list[int] = []
    for edge_id in edge_ids:
        if type(edge_id) is not int or not 0 <= edge_id < len(source.edges):
            raise ValueError('invalid source edge id')
        edge = source.edges[edge_id]
        if edge.source != state:
            raise ValueError('edge sequence is not a source path')
        transition = machine.step(q, symbols[edge_id])
        resets.extend(transition.output)
        lows.extend([ERASE] * (len(transition.output) - 1) + [edge.low])
        state = edge.target; q = transition.next_state
    return tuple(resets), tuple(lows), q


def monitored_graph(system: TraceSystem, bound: int, debt: int = 0):
    if any(type(x) is not int or x < 0 for x in (bound, debt)) or debt > bound:
        raise ValueError('invalid monitor parameters')
    start = (system.initial, debt)
    states = [start]; index = {start: 0}; graph = []
    cursor = 0
    while cursor < len(states):
        base, value = states[cursor]
        row = []
        for _, edge in system.outgoing(base):
            next_value = 0 if edge.reset == 0 else value + 1
            if next_value > bound:
                continue
            nxt = (edge.target, next_value)
            if nxt not in index:
                if len(states) >= MAX_STATES:
                    raise ValueError('monitored graph exceeds state budget')
                index[nxt] = len(states); states.append(nxt)
            row.append(index[nxt])
        graph.append(tuple(sorted(set(row)))); cursor += 1
    return tuple(graph), tuple(states)


def live(graph: tuple[tuple[int, ...], ...]) -> frozenset[int]:
    current = set(range(len(graph)))
    while True:
        following = {v for v in current if any(w in current for w in graph[v])}
        if following == current:
            return frozenset(current)
        current = following
