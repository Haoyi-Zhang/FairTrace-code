"""Independent fixed-parameter omega-language oracle for regular expansions.

The oracle constructs the reachable product of the source counter, transducer
control and target counter.  It decides both language inclusions by induced-
graph cycle reachability.  It deliberately does not import the interval
synthesis implementation.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass

from transducers import Transducer

MAX_REACHABLE = 250_000


def _natural(value: int, name: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f'{name} must be a nonnegative integer')


def _source(value: int, bit: int, bound: int) -> int:
    if value == bound + 1:
        return value
    return 0 if bit == 0 else min(bound + 1, value + 1)


def _target(value: int, block: tuple[int, ...], bound: int) -> int:
    if value == bound + 1:
        return value
    for bit in block:
        value = 0 if bit == 0 else value + 1
        if value > bound:
            return bound + 1
    return value


def _live(graph: tuple[tuple[int, ...], ...], allowed: set[int]) -> set[int]:
    current = set(allowed)
    while True:
        following = {v for v in current if any(w in current for w in graph[v])}
        if following == current:
            return current
        current = following


@dataclass(frozen=True)
class OracleResult:
    equivalent: bool
    source_not_target: bool
    target_not_source: bool
    reachable: int


def equivalent(machine: Transducer, source_bound: int, target_bound: int,
               source_debt: int = 0, target_debt: int = 0) -> OracleResult:
    for value, name in ((source_bound, 'source bound'), (target_bound, 'target bound'),
                        (source_debt, 'source debt'), (target_debt, 'target debt')):
        _natural(value, name)
    if source_debt > source_bound:
        raise ValueError('source debt exceeds source bound')
    target_start = target_debt if target_debt <= target_bound else target_bound + 1
    start = (source_debt, machine.initial, target_start)
    states = [start]
    index = {start: 0}
    graph = []
    cursor = 0
    while cursor < len(states):
        source, q, target = states[cursor]
        row = []
        for symbol in range(machine.alphabet):
            edge = machine.step(q, symbol)
            reset = machine.input_resets[symbol]
            nxt = (_source(source, reset, source_bound), edge.next_state,
                   _target(target, edge.output, target_bound))
            if nxt not in index:
                if len(states) >= MAX_REACHABLE:
                    raise ValueError('oracle product exceeds explicit state budget')
                index[nxt] = len(states); states.append(nxt)
            row.append(index[nxt])
        graph.append(tuple(sorted(set(row))))
        cursor += 1
    graph_tuple = tuple(graph)

    source_safe = {i for i, state in enumerate(states) if state[0] <= source_bound}
    target_safe = {i for i, state in enumerate(states) if state[2] <= target_bound}
    source_live = _live(graph_tuple, source_safe)
    target_live = _live(graph_tuple, target_safe)
    source_not_target = any(i in source_live and states[i][2] > target_bound
                            for i in source_safe)
    target_not_source = any(i in target_live and states[i][0] > source_bound
                            for i in target_safe)
    return OracleResult(not source_not_target and not target_not_source,
                        source_not_target, target_not_source, len(states))
