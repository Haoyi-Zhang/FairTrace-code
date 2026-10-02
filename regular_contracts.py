"""Exact bounded-reset contract synthesis for regular step expansions.

For fixed source parameters ``(B,a)``, target initial debt ``t`` and a total
non-erasing deterministic transducer T, the accepted target bounds form one
integer interval ``[safe_ceiling, invalid_floor)``.  This module computes both
endpoints.  It is executable finite-state mathematics, not a proof-assistant
formalization; the paper supplies the general argument and a separate fixed-
parameter oracle is used for differential checking.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from math import inf
from typing import Iterable

from transducers import Transducer

MAX_PRODUCT_STATES = 250_000
MAX_SYNTHESIS_HORIZON = 200_000


def natural(value: int, name: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f'{name} must be a nonnegative integer')


def source_step(debt: int, bit: int, bound: int) -> int:
    """Absorbing-overflow source counter; ``bound+1`` denotes overflow."""
    if debt == bound + 1:
        return debt
    return 0 if bit == 0 else min(bound + 1, debt + 1)


def process_output(debt: int, output: Iterable[int], bound: int) -> int | None:
    """Run a target block, returning the final debt or ``None`` on overflow."""
    value = debt
    if not 0 <= value <= bound:
        return None
    for bit in output:
        value = 0 if bit == 0 else value + 1
        if value > bound:
            return None
    return value


@dataclass(frozen=True)
class BlockProfile:
    length: int
    resetful: bool
    prefix: int
    suffix: int
    internal: int


def profile(output: Iterable[int]) -> BlockProfile:
    value = tuple(output)
    zeros = [i for i, bit in enumerate(value) if bit == 0]
    if not zeros:
        return BlockProfile(len(value), False, len(value), len(value), 0)
    return BlockProfile(
        len(value), True, zeros[0], len(value) - 1 - zeros[-1],
        max((right - left - 1 for left, right in zip(zeros, zeros[1:])), default=0),
    )


@dataclass(frozen=True)
class CeilingResult:
    value: int | float
    witness_prefix: tuple[int, ...]
    witness_kind: str
    zero_free_cycle: tuple[int, ...] = ()


@dataclass(frozen=True)
class Lasso:
    prefix: tuple[int, ...]
    loop: tuple[int, ...]


@dataclass(frozen=True)
class FloorResult:
    value: int | float
    horizon: int
    witness: Lasso | None


@dataclass(frozen=True)
class ContractInterval:
    safe_ceiling: int | float
    invalid_floor: int | float
    lower: int | None
    upper: int | None
    horizon: int

    @property
    def feasible(self) -> bool:
        return self.lower is not None and (self.upper is None or self.lower <= self.upper)

    def contains(self, target_bound: int) -> bool:
        natural(target_bound, 'target bound')
        return self.feasible and target_bound >= self.lower and (
            self.upper is None or target_bound <= self.upper)


def _safe_controls(machine: Transducer, bound: int, debt: int):
    start = (debt, machine.initial)
    states = [start]
    index = {start: 0}
    parent: list[tuple[int, int] | None] = [None]
    rows: list[list[tuple[int, int, BlockProfile]]] = []
    cursor = 0
    while cursor < len(states):
        source, q = states[cursor]
        row = []
        for symbol in range(machine.alphabet):
            reset = machine.input_resets[symbol]
            next_source = source_step(source, reset, bound)
            if next_source > bound:
                continue
            edge = machine.step(q, symbol)
            nxt = (next_source, edge.next_state)
            if nxt not in index:
                if len(states) >= MAX_PRODUCT_STATES:
                    raise ValueError('source-safe product exceeds explicit state budget')
                index[nxt] = len(states)
                states.append(nxt)
                parent.append((cursor, symbol))
            row.append((symbol, index[nxt], profile(edge.output)))
        rows.append(row)
        cursor += 1
    return states, rows, parent


def _input_path(parent: list[tuple[int, int] | None], vertex: int) -> tuple[int, ...]:
    value = []
    while parent[vertex] is not None:
        vertex, bit = parent[vertex]
        value.append(bit)
    value.reverse()
    return tuple(value)


def _live_vertices(adjacency: list[list[tuple[int, int]]]) -> set[int]:
    """Vertices from which some infinite path exists, by dead-end removal."""
    active = set(range(len(adjacency)))
    while True:
        following = {v for v in active if any(w in active for _, w in adjacency[v])}
        if following == active:
            return active
        active = following


def _find_directed_cycle(adjacency: list[list[tuple[int, int]]]) -> tuple[int, tuple[int, ...]] | None:
    """Return one cycle vertex and its edge-label word, without recursion."""
    live = _live_vertices(adjacency)
    if not live:
        return None
    vertex = min(live)
    position: dict[int, int] = {}
    bits: list[int] = []
    while vertex not in position:
        position[vertex] = len(bits)
        bit, following = min((bit, target) for bit, target in adjacency[vertex]
                             if target in live)
        bits.append(bit)
        vertex = following
    return vertex, tuple(bits[position[vertex]:])

def safe_ceiling(machine: Transducer, source_bound: int, source_debt: int = 0,
                 target_debt: int = 0) -> CeilingResult:
    """Supremum of target one-run debt over all source-valid infinite inputs."""
    for value, name in ((source_bound, 'source bound'), (source_debt, 'source debt'),
                        (target_debt, 'target debt')):
        natural(value, name)
    if source_debt > source_bound:
        raise ValueError('source debt exceeds source bound')
    states, rows, parent = _safe_controls(machine, source_bound, source_debt)

    zero_graph: list[list[tuple[int, int]]] = [[] for _ in states]
    for source, row in enumerate(rows):
        for bit, target, block in row:
            if not block.resetful:
                zero_graph[source].append((bit, target))
    cycle = _find_directed_cycle(zero_graph)
    if cycle is not None:
        vertex, loop = cycle
        return CeilingResult(inf, _input_path(parent, vertex), 'zero-free-cycle', loop)

    # Topological order of the zero-free subgraph.
    indegree = [0] * len(states)
    for row in zero_graph:
        for _, target in row:
            indegree[target] += 1
    queue = deque(i for i, degree in enumerate(indegree) if degree == 0)
    order = []
    while queue:
        v = queue.popleft()
        order.append(v)
        for _, w in zero_graph[v]:
            indegree[w] -= 1
            if indegree[w] == 0:
                queue.append(w)
    if len(order) != len(states):
        raise AssertionError('cycle detector/topological order disagreement')

    debt = [-1] * len(states)
    debt_path: list[tuple[int, ...] | None] = [None] * len(states)
    debt[0] = target_debt
    debt_path[0] = ()

    # A resetful edge supplies a fixed suffix seed, independent of incoming debt.
    for source, row in enumerate(rows):
        base = _input_path(parent, source)
        for bit, target, block in row:
            if block.resetful and block.suffix > debt[target]:
                debt[target] = block.suffix
                debt_path[target] = base + (bit,)

    maximum = target_debt
    witness: tuple[int, ...] = ()
    kind = 'initial-debt'
    # All dependence-preserving edges form a DAG; reset edges only contribute
    # fixed seeds and local maxima, so one topological pass is exact.
    for source in order:
        if debt[source] < 0 or debt_path[source] is None:
            continue
        for bit, target, block in rows[source]:
            if block.resetful:
                candidate = max(debt[source] + block.prefix, block.internal, block.suffix)
                if candidate > maximum:
                    maximum = candidate
                    witness = debt_path[source] + (bit,)
                    kind = 'reset-block-prefix-or-internal'
            else:
                candidate = debt[source] + block.length
                path = debt_path[source] + (bit,)
                if candidate > maximum:
                    maximum = candidate
                    witness = path
                    kind = 'zero-free-path'
                if candidate > debt[target]:
                    debt[target] = candidate
                    debt_path[target] = path
    if any(value < 0 for value in debt):
        raise AssertionError('reachable safe control without a debt witness')
    return CeilingResult(maximum, witness, kind)


def synthesis_horizon(machine: Transducer, source_bound: int, target_debt: int) -> int:
    """Finite completeness bound for the invalid-floor threshold search.

    Any target-safe source-invalid word has a cycle-deleted witness whose
    target zero-free segments cross at most ``(B+2)|Q|`` control states, plus
    at most two partial resetful blocks.  The intentionally loose expression
    below is easy to check and keeps the implementation independent of a
    minimality claim.
    """
    for value, name in ((source_bound, 'source bound'), (target_debt, 'target debt')):
        natural(value, name)
    controls = (source_bound + 2) * machine.states
    horizon = target_debt + (controls + 2) * machine.maximum_block
    if horizon > MAX_SYNTHESIS_HORIZON:
        raise ValueError('contract synthesis horizon exceeds explicit budget')
    return horizon


def _lasso_from_live(graph: list[list[tuple[int, int]]], start: int,
                     live: set[int]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Choose a finite bridge and nonempty loop within a live subgraph."""
    if start not in live:
        raise ValueError('lasso start is not live')
    vertex = start
    position: dict[int, int] = {}
    bits: list[int] = []
    while vertex not in position:
        position[vertex] = len(bits)
        candidates = [(bit, target) for bit, target in graph[vertex] if target in live]
        if not candidates:
            raise AssertionError('live vertex lacks a live successor')
        bit, vertex = min(candidates)
        bits.append(bit)
    split = position[vertex]
    loop = tuple(bits[split:])
    if not loop:
        raise AssertionError('extracted lasso has an empty loop')
    return tuple(bits[:split]), loop

def invalid_safe_lasso(machine: Transducer, source_bound: int, source_debt: int,
                       target_bound: int, target_debt: int) -> Lasso | None:
    """Find a source-invalid, target-safe ultimately periodic input, if one exists."""
    for value, name in ((source_bound, 'source bound'), (source_debt, 'source debt'),
                        (target_bound, 'target bound'), (target_debt, 'target debt')):
        natural(value, name)
    if source_debt > source_bound:
        raise ValueError('source debt exceeds source bound')
    if target_debt > target_bound:
        return None
    start = (source_debt, machine.initial, target_debt)
    states = [start]
    index = {start: 0}
    parent: list[tuple[int, int] | None] = [None]
    graph: list[list[tuple[int, int]]] = []
    cursor = 0
    while cursor < len(states):
        source, q, target_debt_now = states[cursor]
        row = []
        for symbol in range(machine.alphabet):
            edge = machine.step(q, symbol)
            next_target = process_output(target_debt_now, edge.output, target_bound)
            if next_target is None:
                continue
            reset = machine.input_resets[symbol]
            nxt = (source_step(source, reset, source_bound), edge.next_state, next_target)
            if nxt not in index:
                if len(states) >= MAX_PRODUCT_STATES:
                    raise ValueError('target-safe product exceeds explicit state budget')
                index[nxt] = len(states)
                states.append(nxt)
                parent.append((cursor, symbol))
            row.append((symbol, index[nxt]))
        graph.append(row)
        cursor += 1

    live = _live_vertices(graph)
    candidate = next((i for i, state in enumerate(states)
                      if state[0] == source_bound + 1 and i in live), None)
    if candidate is None:
        return None
    bridge, loop = _lasso_from_live(graph, candidate, live)
    prefix = _input_path(parent, candidate) + bridge
    return Lasso(prefix, loop)


def invalid_floor(machine: Transducer, source_bound: int, source_debt: int = 0,
                  target_debt: int = 0) -> FloorResult:
    """Minimum target bound admitting a source-invalid infinite input, or infinity."""
    for value, name in ((source_bound, 'source bound'), (source_debt, 'source debt'),
                        (target_debt, 'target debt')):
        natural(value, name)
    if source_debt > source_bound:
        raise ValueError('source debt exceeds source bound')
    horizon = synthesis_horizon(machine, source_bound, target_debt)
    witness = invalid_safe_lasso(machine, source_bound, source_debt, horizon, target_debt)
    if witness is None:
        return FloorResult(inf, horizon, None)
    low, high = target_debt, horizon
    while low < high:
        middle = (low + high) // 2
        if invalid_safe_lasso(machine, source_bound, source_debt, middle, target_debt) is None:
            low = middle + 1
        else:
            high = middle
    witness = invalid_safe_lasso(machine, source_bound, source_debt, low, target_debt)
    if witness is None:
        raise AssertionError('monotone threshold search lost its witness')
    return FloorResult(low, horizon, witness)


def exact_interval(machine: Transducer, source_bound: int, source_debt: int = 0,
                   target_debt: int = 0) -> ContractInterval:
    ceiling = safe_ceiling(machine, source_bound, source_debt, target_debt)
    floor = invalid_floor(machine, source_bound, source_debt, target_debt)
    if ceiling.value == inf:
        return ContractInterval(inf, floor.value, None, None, floor.horizon)
    lower = int(ceiling.value)
    upper = None if floor.value == inf else int(floor.value) - 1
    if upper is not None and lower > upper:
        return ContractInterval(ceiling.value, floor.value, None, None, floor.horizon)
    return ContractInterval(ceiling.value, floor.value, lower, upper, floor.horizon)
