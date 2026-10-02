"""Deterministic non-erasing finite-input/binary-output transducers.

Each input symbol carries a binary source-reset annotation.  A transition
consumes one symbol and emits a nonempty finite binary target-reset word.  The
binary two-symbol case embeds ordinary non-erasing word morphisms, while larger
alphabets let expansion blocks depend on source-edge classes rather than only
on the source reset bit.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from typing import Iterable

MAX_STATES = 64
MAX_ALPHABET = 64
MAX_BLOCK = 256
MAX_COMPOSED_STATES = 4096


def bit_word(value: Iterable[int]) -> tuple[int, ...]:
    result = tuple(value)
    if not result or len(result) > MAX_BLOCK:
        raise ValueError(f'output blocks must contain 1..{MAX_BLOCK} bits')
    if any(type(x) is not int or x not in (0, 1) for x in result):
        raise ValueError('output blocks contain integer bits only')
    return result


@dataclass(frozen=True)
class Transition:
    next_state: int
    output: tuple[int, ...]

    def __post_init__(self) -> None:
        if type(self.next_state) is not int or self.next_state < 0:
            raise ValueError('next state must be a nonnegative integer')
        object.__setattr__(self, 'output', bit_word(self.output))


@dataclass(frozen=True)
class Transducer:
    """A total deterministic transducer with a reset annotation per input symbol."""

    transitions: tuple[tuple[Transition, ...], ...]
    initial: int = 0
    input_resets: tuple[int, ...] = (0, 1)

    def __post_init__(self) -> None:
        rows = tuple(tuple(row) for row in self.transitions)
        resets = tuple(self.input_resets)
        if not rows or len(rows) > MAX_STATES:
            raise ValueError(f'transducer must contain 1..{MAX_STATES} states')
        if not resets or len(resets) > MAX_ALPHABET:
            raise ValueError(f'input alphabet must contain 1..{MAX_ALPHABET} symbols')
        if any(type(bit) is not int or bit not in (0, 1) for bit in resets):
            raise ValueError('input reset annotations must be integer bits')
        if 0 not in resets:
            raise ValueError('input alphabet must contain a reset-annotated symbol')
        if type(self.initial) is not int or not 0 <= self.initial < len(rows):
            raise ValueError('invalid initial transducer state')
        for row in rows:
            if len(row) != len(resets) or any(not isinstance(x, Transition) for x in row):
                raise ValueError('each state needs one transition per input symbol')
            if any(x.next_state >= len(rows) for x in row):
                raise ValueError('transition target outside transducer')
        object.__setattr__(self, 'transitions', rows)
        object.__setattr__(self, 'input_resets', resets)

    @property
    def states(self) -> int:
        return len(self.transitions)

    @property
    def alphabet(self) -> int:
        return len(self.input_resets)

    @property
    def maximum_block(self) -> int:
        return max(len(edge.output) for row in self.transitions for edge in row)

    def step(self, state: int, symbol: int) -> Transition:
        if type(state) is not int or not 0 <= state < self.states:
            raise ValueError('invalid transducer state')
        if type(symbol) is not int or not 0 <= symbol < self.alphabet:
            raise ValueError('input symbol outside alphabet')
        return self.transitions[state][symbol]

    def run(self, value: Iterable[int], state: int | None = None) -> tuple[int, tuple[int, ...]]:
        q = self.initial if state is None else state
        if type(q) is not int or not 0 <= q < self.states:
            raise ValueError('invalid transducer state')
        output: list[int] = []
        for symbol in value:
            edge = self.step(q, symbol)
            output.extend(edge.output)
            q = edge.next_state
        return q, tuple(output)

    def source_projection(self, value: Iterable[int]) -> tuple[int, ...]:
        result = []
        for symbol in value:
            if type(symbol) is not int or not 0 <= symbol < self.alphabet:
                raise ValueError('input symbol outside alphabet')
            result.append(self.input_resets[symbol])
        return tuple(result)

    def reachable(self) -> tuple[int, ...]:
        seen = {self.initial}
        queue = deque([self.initial])
        while queue:
            q = queue.popleft()
            for edge in self.transitions[q]:
                if edge.next_state not in seen:
                    seen.add(edge.next_state)
                    queue.append(edge.next_state)
        return tuple(sorted(seen))

    def to_json(self) -> dict:
        return {
            'initial': self.initial,
            'input_resets': list(self.input_resets),
            'transitions': [
                [
                    {'next': edge.next_state, 'output': list(edge.output)}
                    for edge in row
                ]
                for row in self.transitions
            ],
        }

    @staticmethod
    def from_json(value: object) -> 'Transducer':
        if not isinstance(value, dict) or set(value) != {
                'initial', 'input_resets', 'transitions'}:
            raise ValueError('invalid transducer object')
        raw_rows = value['transitions']
        raw_resets = value['input_resets']
        if not isinstance(raw_rows, list) or not isinstance(raw_resets, list):
            raise ValueError('transitions and input resets must be lists')
        rows = []
        for raw_row in raw_rows:
            if not isinstance(raw_row, list) or len(raw_row) != len(raw_resets):
                raise ValueError('transition row has wrong alphabet size')
            row = []
            for raw_edge in raw_row:
                if not isinstance(raw_edge, dict) or set(raw_edge) != {'next', 'output'}:
                    raise ValueError('invalid transition entry')
                row.append(Transition(raw_edge['next'], tuple(raw_edge['output'])))
            rows.append(tuple(row))
        return Transducer(tuple(rows), value['initial'], tuple(raw_resets))


def morphism(zero: Iterable[int], one: Iterable[int]) -> Transducer:
    """Embed a non-erasing binary word morphism as a one-state transducer."""
    return Transducer(((Transition(0, bit_word(zero)), Transition(0, bit_word(one))),))


def compose(first: Transducer, second: Transducer) -> Transducer:
    """Compose source->binary ``first`` with binary->binary ``second``.

    Only reachable state pairs are retained.  The first machine may have any
    finite input alphabet.  The second machine must use the canonical binary
    alphabet whose reset annotations are (0,1), because it consumes the actual
    bits emitted by the first machine.
    """
    if second.alphabet != 2 or second.input_resets != (0, 1):
        raise ValueError('second transducer in a composition must read binary bits')
    start = (first.initial, second.initial)
    pairs = [start]
    index = {start: 0}
    rows: list[tuple[Transition, ...]] = []
    cursor = 0
    while cursor < len(pairs):
        q1, q2 = pairs[cursor]
        out_row = []
        for symbol in range(first.alphabet):
            e1 = first.step(q1, symbol)
            q = q2
            output: list[int] = []
            for middle in e1.output:
                e2 = second.step(q, middle)
                output.extend(e2.output)
                q = e2.next_state
            pair = (e1.next_state, q)
            if pair not in index:
                if len(pairs) >= MAX_COMPOSED_STATES:
                    raise ValueError('composed transducer exceeds state budget')
                index[pair] = len(pairs)
                pairs.append(pair)
            out_row.append(Transition(index[pair], tuple(output)))
        rows.append(tuple(out_row))
        cursor += 1
    return Transducer(tuple(rows), 0, first.input_resets)


def relabel_states(machine: Transducer, order: tuple[int, ...]) -> Transducer:
    """Return an isomorphic machine in a supplied permutation (test helper)."""
    if tuple(sorted(order)) != tuple(range(machine.states)):
        raise ValueError('order must be a state permutation')
    new = {old: i for i, old in enumerate(order)}
    rows = []
    for old in order:
        rows.append(tuple(Transition(new[e.next_state], e.output)
                          for e in machine.transitions[old]))
    return Transducer(tuple(rows), new[machine.initial], machine.input_resets)
