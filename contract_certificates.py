"""Locally checkable exact-contract certificates.

A positive packet contains two reachability proofs and one infinite-path
certificate.  The checker rebuilds only local semantic successors; it does not
run the interval synthesizer or a greatest-fixed-point solver.
"""
from __future__ import annotations
import argparse
import json
from collections import deque
from pathlib import Path

import certificates
from regular_contracts import process_output, source_step
from transducers import Transducer

SCHEMA = 'fair-contract-certificate-1'
MAX_PACKET = 16 * 1024 * 1024
MAX_STATES = 250_000


def _key(state: tuple[int, int, int]) -> str:
    return ','.join(map(str, state))


def _state(value: object) -> tuple[int, int, int]:
    if (not isinstance(value, list) or len(value) != 3 or
            any(type(x) is not int or x < 0 for x in value)):
        raise ValueError('invalid product state')
    return tuple(value)  # type: ignore[return-value]


def _successor(machine: Transducer, params: dict, state: tuple[int, int, int], symbol: int,
               source_must_remain_safe: bool) -> tuple[int, int, int] | None:
    b = params['source_bound']; c = params['target_bound']
    source, q, debt = state
    edge = machine.step(q, symbol)
    next_source = source_step(source, machine.input_resets[symbol], b)
    if source_must_remain_safe and next_source > b:
        return None
    next_debt = process_output(debt, edge.output, c)
    if next_debt is None:
        if source_must_remain_safe:
            raise ValueError('source-safe transition overflows target')
        return None
    return next_source, edge.next_state, next_debt


def _build(machine: Transducer, params: dict, source_only: bool):
    start = (params['source_debt'], machine.initial, params['target_debt'])
    if params['target_debt'] > params['target_bound']:
        return [], [], []
    states = [start]; index = {start: 0}; parent = [None]; graph = []
    cursor = 0
    while cursor < len(states):
        row = []
        for symbol in range(machine.alphabet):
            try:
                nxt = _successor(machine, params, states[cursor], symbol, source_only)
            except ValueError:
                raise
            if nxt is None:
                continue
            if nxt not in index:
                if len(states) >= MAX_STATES:
                    raise ValueError('certificate graph exceeds state budget')
                index[nxt] = len(states); states.append(nxt); parent.append((cursor, symbol))
            row.append(index[nxt])
        graph.append(tuple(sorted(set(row)))); cursor += 1
    return states, graph, parent


def _reach_certificate(states, parent):
    distances = [0] * len(states)
    parents = {}
    for i in range(1, len(states)):
        p, symbol = parent[i]
        distances[i] = distances[p] + 1
        parents[_key(states[i])] = {'parent': list(states[p]), 'symbol': symbol,
                                    'distance': distances[i]}
    return {'states': [list(x) for x in states], 'parents': parents}


def generate(machine: Transducer, source_bound: int, target_bound: int,
             source_debt: int = 0, target_debt: int = 0) -> dict:
    params = {'source_bound': source_bound, 'target_bound': target_bound,
              'source_debt': source_debt, 'target_debt': target_debt}
    forward_states, _, forward_parent = _build(machine, params, True)
    target_states, target_graph, target_parent = _build(machine, params, False)
    live = certificates.generate(tuple(target_graph))
    packet = {
        'schema': SCHEMA,
        'transducer': machine.to_json(),
        'parameters': params,
        'forward': _reach_certificate(forward_states, forward_parent),
        'target_safe': _reach_certificate(target_states, target_parent),
        'live': live,
    }
    if not check(packet):
        raise ValueError('parameters do not form an exact contract')
    return packet


def _check_reach(machine: Transducer, params: dict, raw: object, source_only: bool):
    if not isinstance(raw, dict) or set(raw) != {'states', 'parents'}:
        return None
    raw_states = raw['states']; raw_parents = raw['parents']
    if not isinstance(raw_states, list) or not isinstance(raw_parents, dict):
        return None
    states = [_state(x) for x in raw_states]
    if len(states) != len(set(states)) or len(states) > MAX_STATES:
        return None
    if params['target_debt'] > params['target_bound']:
        return None
    start = (params['source_debt'], machine.initial, params['target_debt'])
    if not states or states[0] != start:
        return None
    index = {state: i for i, state in enumerate(states)}
    if set(raw_parents) != {_key(state) for state in states[1:]}:
        return None
    distances = {start: 0}
    unresolved = set(states[1:])
    while unresolved:
        changed = False
        for state in list(unresolved):
            item = raw_parents[_key(state)]
            if (not isinstance(item, dict) or set(item) != {'parent', 'symbol', 'distance'}):
                return None
            try:
                parent = _state(item['parent'])
            except ValueError:
                return None
            symbol = item['symbol']; distance = item['distance']
            if (type(symbol) is not int or not 0 <= symbol < machine.alphabet or
                    type(distance) is not int):
                return None
            if parent in distances:
                try:
                    successor = _successor(machine, params, parent, symbol, source_only)
                except ValueError:
                    return None
                if successor != state or distance != distances[parent] + 1:
                    return None
                distances[state] = distance; unresolved.remove(state); changed = True
        if not changed:
            return None
    graph = []
    for state in states:
        row = []
        for symbol in range(machine.alphabet):
            try:
                successor = _successor(machine, params, state, symbol, source_only)
            except ValueError:
                return None
            if successor is not None:
                if successor not in index:
                    return None
                row.append(index[successor])
        graph.append(tuple(sorted(set(row))))
    return states, tuple(graph)


def check(packet: object) -> bool:
    try:
        if not isinstance(packet, dict) or set(packet) != {
            'schema', 'transducer', 'parameters', 'forward', 'target_safe', 'live'
        } or packet['schema'] != SCHEMA:
            return False
        machine = Transducer.from_json(packet['transducer'])
        params = packet['parameters']
        if not isinstance(params, dict) or set(params) != {
            'source_bound', 'target_bound', 'source_debt', 'target_debt'
        }:
            return False
        b = params['source_bound']; c = params['target_bound']
        a = params['source_debt']; t = params['target_debt']
        if any(type(x) is not int or x < 0 for x in (b, c, a, t)) or a > b or t > c:
            return False
        forward = _check_reach(machine, params, packet['forward'], True)
        target = _check_reach(machine, params, packet['target_safe'], False)
        if forward is None or target is None:
            return False
        target_states, target_graph = target
        if not certificates.check(target_graph, packet['live']):
            return False
        live = set(packet['live']['live'])
        return all(not (target_states[i][0] == b + 1) for i in live)
    except (KeyError, TypeError, ValueError):
        return False


def load_json(path: Path) -> object:
    if path.stat().st_size > MAX_PACKET:
        raise ValueError('packet exceeds size budget')
    def no_duplicates(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON field')
            result[key] = value
        return result
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=no_duplicates)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packet', type=Path)
    args = parser.parse_args()
    try:
        valid = check(load_json(args.packet))
    except (OSError, ValueError, TypeError) as exc:
        print(f'INVALID: {exc}')
        return 2
    print('VALID exact-contract certificate' if valid else 'INVALID certificate')
    return 0 if valid else 2


if __name__ == '__main__':
    raise SystemExit(main())
