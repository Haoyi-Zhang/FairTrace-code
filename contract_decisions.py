"""Complete fixed-parameter decision packets for regular fairness contracts.

An exact verdict embeds the locally checkable positive certificate.  An inexact
verdict carries either a finite source-valid/target-overflow prefix or a
source-overflow/target-safe lasso.  The checker simulates only the supplied
witness and delegates positive packets to ``contract_certificates``.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy

import contract_certificates as positive
import contract_oracle
from regular_contracts import invalid_safe_lasso, process_output, source_step
from transducers import Transducer

SCHEMA = 'fair-contract-decision-1'
MAX_WITNESS = 1_000_000


def _parameters(source_bound: int, target_bound: int,
                source_debt: int, target_debt: int) -> dict:
    values = (source_bound, target_bound, source_debt, target_debt)
    if any(type(x) is not int or x < 0 for x in values):
        raise ValueError('bounds and debts must be natural numbers')
    if source_debt > source_bound:
        raise ValueError('source debt exceeds source bound')
    return {'source_bound': source_bound, 'target_bound': target_bound,
            'source_debt': source_debt, 'target_debt': target_debt}


def _overflow_step(value: int, output: tuple[int, ...], bound: int) -> int:
    if value == bound + 1:
        return value
    for bit in output:
        value = 0 if bit == 0 else value + 1
        if value > bound:
            return bound + 1
    return value


def _forward_counterexample(machine: Transducer, params: dict) -> tuple[int, ...] | None:
    b = params['source_bound']; c = params['target_bound']
    target = params['target_debt'] if params['target_debt'] <= c else c + 1
    start = (params['source_debt'], machine.initial, target)
    states = [start]; index = {start: 0}; parent = [None]
    queue = deque([0])
    found = 0 if target > c else None
    while queue and found is None:
        vertex = queue.popleft()
        source, q, debt = states[vertex]
        for symbol in range(machine.alphabet):
            reset = machine.input_resets[symbol]
            next_source = source_step(source, reset, b)
            if next_source > b:
                continue
            edge = machine.step(q, symbol)
            nxt = (next_source, edge.next_state,
                   _overflow_step(debt, edge.output, c))
            if nxt not in index:
                if len(states) >= MAX_WITNESS:
                    raise ValueError('counterexample search exceeds witness budget')
                index[nxt] = len(states); states.append(nxt)
                parent.append((vertex, symbol)); queue.append(index[nxt])
            if nxt[2] > c:
                found = index[nxt]; break
    if found is None:
        return None
    symbols = []
    while parent[found] is not None:
        found, symbol = parent[found]
        symbols.append(symbol)
    symbols.reverse()
    return tuple(symbols)


def generate(machine: Transducer, source_bound: int, target_bound: int,
             source_debt: int = 0, target_debt: int = 0) -> dict:
    params = _parameters(source_bound, target_bound, source_debt, target_debt)
    answer = contract_oracle.equivalent(machine, source_bound, target_bound,
                                        source_debt, target_debt)
    packet = {'schema': SCHEMA, 'transducer': machine.to_json(),
              'parameters': params}
    if answer.equivalent:
        packet.update({'verdict': 'exact',
                       'certificate': positive.generate(machine, source_bound,
                                                        target_bound, source_debt,
                                                        target_debt)})
    elif answer.source_not_target:
        prefix = _forward_counterexample(machine, params)
        if prefix is None:
            raise AssertionError('oracle reports missing forward counterexample')
        packet.update({'verdict': 'inexact',
                       'direction': 'source-valid-target-invalid',
                       'prefix': list(prefix)})
    else:
        lasso = invalid_safe_lasso(machine, source_bound, source_debt,
                                   target_bound, target_debt)
        if lasso is None:
            raise AssertionError('oracle reports missing reverse counterexample')
        packet.update({'verdict': 'inexact',
                       'direction': 'source-invalid-target-valid',
                       'prefix': list(lasso.prefix), 'loop': list(lasso.loop)})
    if not check(packet):
        raise AssertionError('generated decision packet failed its checker')
    return packet


def _symbols(raw, machine: Transducer) -> tuple[int, ...] | None:
    if (not isinstance(raw, list) or len(raw) > MAX_WITNESS or
            any(type(symbol) is not int or not 0 <= symbol < machine.alphabet
                for symbol in raw)):
        return None
    return tuple(raw)


def _simulate(machine: Transducer, params: dict, symbols: tuple[int, ...],
              state: tuple[int, int, int] | None = None,
              require_target_safe: bool = False):
    b = params['source_bound']; c = params['target_bound']
    if state is None:
        target = params['target_debt']
        if require_target_safe and target > c:
            return None
        state = (params['source_debt'], machine.initial,
                 target if target <= c else c + 1)
    source, q, debt = state
    source_ever_overflow = source > b
    target_ever_overflow = debt > c
    for symbol in symbols:
        edge = machine.step(q, symbol)
        source = source_step(source, machine.input_resets[symbol], b)
        if require_target_safe:
            next_debt = process_output(debt, edge.output, c)
            if next_debt is None:
                return None
            debt = next_debt
        else:
            debt = _overflow_step(debt, edge.output, c)
        q = edge.next_state
        source_ever_overflow |= source > b
        target_ever_overflow |= debt > c
    return (source, q, debt), source_ever_overflow, target_ever_overflow


def check(packet: object) -> bool:
    try:
        if not isinstance(packet, dict) or packet.get('schema') != SCHEMA:
            return False
        if not isinstance(packet.get('parameters'), dict):
            return False
        params = packet['parameters']
        if set(params) != {'source_bound', 'target_bound', 'source_debt', 'target_debt'}:
            return False
        checked = _parameters(params['source_bound'], params['target_bound'],
                              params['source_debt'], params['target_debt'])
        if checked != params:
            return False
        machine = Transducer.from_json(packet.get('transducer'))
        verdict = packet.get('verdict')
        if verdict == 'exact':
            if set(packet) != {'schema', 'transducer', 'parameters', 'verdict', 'certificate'}:
                return False
            certificate = packet['certificate']
            return (positive.check(certificate) and
                    certificate['transducer'] == packet['transducer'] and
                    certificate['parameters'] == params)
        if verdict != 'inexact':
            return False
        direction = packet.get('direction')
        if direction == 'source-valid-target-invalid':
            if set(packet) != {'schema', 'transducer', 'parameters', 'verdict',
                               'direction', 'prefix'}:
                return False
            prefix = _symbols(packet['prefix'], machine)
            if prefix is None:
                return False
            result = _simulate(machine, params, prefix)
            if result is None:
                return False
            final, source_overflow, target_overflow = result
            # A reset-annotated symbol exists by construction; repeating it
            # extends any source-safe finite prefix to a source-valid omega word.
            return not source_overflow and target_overflow and final[0] <= params['source_bound']
        if direction == 'source-invalid-target-valid':
            if set(packet) != {'schema', 'transducer', 'parameters', 'verdict',
                               'direction', 'prefix', 'loop'}:
                return False
            prefix = _symbols(packet['prefix'], machine)
            loop = _symbols(packet['loop'], machine)
            if prefix is None or loop is None or not loop:
                return False
            first = _simulate(machine, params, prefix, require_target_safe=True)
            if first is None:
                return False
            state, overflow1, _ = first
            second = _simulate(machine, params, loop, state, require_target_safe=True)
            if second is None:
                return False
            end, overflow2, _ = second
            return end == state and (overflow1 or overflow2) and state[0] > params['source_bound']
        return False
    except (KeyError, TypeError, ValueError):
        return False


def mutated(packet: dict) -> list[dict]:
    """Small deterministic mutation family used by tests and reproduction."""
    result = []
    bad = deepcopy(packet); bad['schema'] = 'bad'; result.append(bad)
    bad = deepcopy(packet); bad['parameters']['source_debt'] = bad['parameters']['source_bound'] + 1; result.append(bad)
    bad = deepcopy(packet); bad['transducer']['transitions'][0][0]['output'] = []; result.append(bad)
    if packet['verdict'] == 'exact':
        bad = deepcopy(packet); bad['certificate']['parameters']['target_bound'] += 1; result.append(bad)
    elif packet['direction'] == 'source-valid-target-invalid':
        bad = deepcopy(packet); bad['prefix'] = bad['prefix'] + [999]; result.append(bad)
        bad = deepcopy(packet); bad['direction'] = 'source-invalid-target-valid'; result.append(bad)
    else:
        bad = deepcopy(packet); bad['loop'] = []; result.append(bad)
        bad = deepcopy(packet); bad['loop'] = [999]; result.append(bad)
    return result
