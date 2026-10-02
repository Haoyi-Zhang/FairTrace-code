"""Deterministic finite checks for stateful regular step-expansion contracts.

The routines in this module deliberately use small complete universes and an
algorithmically separate fixed-bound omega-language oracle.  They validate the
implementation and expose boundary cases; they are not proofs of the general
mathematical theorems stated in the paper.
"""
from __future__ import annotations

from copy import deepcopy
import itertools as it
import json
from math import inf
from pathlib import Path

import contract_certificates as cc
import contract_decisions as decisions
import contract_oracle as oracle
import expansion as ex
import regular_contracts as rc
import transducers as tr


ONE_BIT_CHOICES = tuple((next_state, (output,))
                        for next_state in range(2) for output in range(2))
BLOCK_WORDS = ((0,), (1,), (0, 1), (1, 0))
FIXED_NEXT = ((1, 0), (0, 1))
ANNOTATED_NEXT = ((1, 0, 1), (0, 1, 0))
REPRESENTATIVE_CODES = (0, 1, 5, 17, 34, 85, 170, 255)


def finite(value):
    return 'infinity' if value == inf else int(value)


def one_bit_machines():
    """All 4^4 two-state machines with one output bit per transition."""
    for code, choices in enumerate(it.product(range(4), repeat=4)):
        rows = []
        for q in range(2):
            row = []
            for bit in range(2):
                next_state, output = ONE_BIT_CHOICES[choices[2 * q + bit]]
                row.append(tr.Transition(next_state, output))
            rows.append(tuple(row))
        yield f'o{code:03d}', tr.Transducer(tuple(rows))


def block_machines():
    """All 4^4 block assignments on one fixed, genuinely stateful control graph."""
    for code, choices in enumerate(it.product(range(4), repeat=4)):
        rows = []
        for q in range(2):
            rows.append(tuple(tr.Transition(FIXED_NEXT[q][bit], BLOCK_WORDS[choices[2*q+bit]])
                              for bit in range(2)))
        yield f'b{code:03d}', tr.Transducer(tuple(rows))





def annotated_machines():
    """All one-bit outputs on a fixed two-state, three-symbol control graph.

    Symbols 1 and 2 carry the same source-miss annotation but may trigger
    different control and output behavior.  This is the smallest complete
    family that cannot be reduced to a reset-bit morphism.
    """
    for mask in range(64):
        rows = []
        for q in range(2):
            row = []
            for symbol in range(3):
                k = 3 * q + symbol
                row.append(tr.Transition(ANNOTATED_NEXT[q][symbol],
                                         ((mask >> k) & 1,)))
            rows.append(tuple(row))
        yield f'a{mask:02d}', tr.Transducer(tuple(rows), input_resets=(0, 1, 1))


def annotated_faithful_machines():
    """Sixteen reset-faithful three-symbol machines for reactive expansion.

    The four mask bits independently dilate the two miss-symbol classes in
    the two control states.  Reset-symbol blocks are fixed resetful blocks;
    both miss classes stay zero-free while remaining behaviorally distinct.
    """
    for mask in range(16):
        rows = []
        for q in range(2):
            zero = (0, 1) if q else (0,)
            one = (1, 1) if mask & (1 << (2*q)) else (1,)
            two = (1, 1) if mask & (1 << (2*q+1)) else (1,)
            rows.append((tr.Transition(ANNOTATED_NEXT[q][0], zero),
                         tr.Transition(ANNOTATED_NEXT[q][1], one),
                         tr.Transition(ANNOTATED_NEXT[q][2], two)))
        yield f'af{mask:02d}', tr.Transducer(tuple(rows), input_resets=(0, 1, 1))


def faithful_machines():
    """Sixteen reset-faithful stateful machines with variable dilation.

    Every 0-transition emits a resetful block (0 or 01), every 1-transition
    emits a zero-free block (1 or 11), and the fixed control graph crosses and
    retains state.  The complete 2^4 output-assignment family is used rather
    than a favorable subset.
    """
    for mask in range(16):
        rows = []
        for q in range(2):
            zero = (0, 1) if mask & (1 << (2*q)) else (0,)
            one = (1, 1) if mask & (1 << (2*q+1)) else (1,)
            rows.append((tr.Transition(FIXED_NEXT[q][0], zero),
                         tr.Transition(FIXED_NEXT[q][1], one)))
        yield f'f{mask:02d}', tr.Transducer(tuple(rows))

def _interval_signature(interval: rc.ContractInterval):
    return (interval.safe_ceiling, interval.invalid_floor,
            interval.lower, interval.upper, interval.horizon)


def _differential_family(family, out: Path, write_csv, filename: str, scope: str):
    rows = []
    configurations = comparisons = exact_bounds = peak = feasible = 0
    infinite_ceilings = 0
    for machine_id, machine in family:
        relabelled = tr.relabel_states(machine, (1, 0))
        for bound in range(4):
            for debt in range(bound + 1):
                for target_debt in range(4):
                    interval = rc.exact_interval(machine, bound, debt, target_debt)
                    invariant = rc.exact_interval(relabelled, bound, debt, target_debt)
                    assert _interval_signature(interval) == _interval_signature(invariant)
                    configurations += 1
                    feasible += interval.feasible
                    infinite_ceilings += interval.safe_ceiling == inf
                    local_exact = local_peak = 0
                    # The completeness horizon plus one rejected/accepted point
                    # exercises the synthesized threshold on both sides.
                    for target_bound in range(interval.horizon + 2):
                        answer = oracle.equivalent(machine, bound, target_bound,
                                                   debt, target_debt)
                        predicted = interval.contains(target_bound)
                        assert answer.equivalent == predicted, (
                            machine_id, bound, debt, target_debt, target_bound,
                            interval, answer)
                        comparisons += 1
                        local_exact += predicted
                        local_peak = max(local_peak, answer.reachable)
                    exact_bounds += local_exact
                    peak = max(peak, local_peak)
                    rows.append({
                        'machine': machine_id,
                        'source_bound': bound,
                        'source_debt': debt,
                        'target_debt': target_debt,
                        'safe_ceiling': finite(interval.safe_ceiling),
                        'invalid_floor': finite(interval.invalid_floor),
                        'lower': '' if interval.lower is None else interval.lower,
                        'upper': ('infinity' if interval.feasible and interval.upper is None
                                  else '' if interval.upper is None else interval.upper),
                        'horizon': interval.horizon,
                        'bounds_checked': interval.horizon + 2,
                        'exact_bounds': local_exact,
                        'maximum_oracle_vertices': local_peak,
                        'relabel_invariant': 1,
                    })
    write_csv(out / filename, rows)
    return {
        'machines': len({row['machine'] for row in rows}),
        'parameter_configurations': configurations,
        'target_bounds_compared': comparisons,
        'exact_target_bounds': exact_bounds,
        'feasible_intervals': feasible,
        'infinite_safe_ceilings': infinite_ceilings,
        'maximum_oracle_vertices': peak,
        'mismatches': 0,
        'state_relabeling_checks': configurations,
        'scope': scope,
    }


def regular_one_bit(out: Path, write_csv):
    return _differential_family(
        one_bit_machines(), out, write_csv, 'regular-one-bit.csv',
        'all two-state deterministic controls and one-bit output assignments; '
        'B=0..3, all source debts, target debt 0..3, every bound through horizon+1')


def regular_blocks(out: Path, write_csv):
    return _differential_family(
        block_machines(), out, write_csv, 'regular-blocks.csv',
        'fixed nontrivial two-state control graph, all blocks in {0,1,01,10}; '
        'B=0..3, all source debts, target debt 0..3, every bound through horizon+1')


def regular_annotated(out: Path, write_csv):
    return _differential_family(
        annotated_machines(), out, write_csv, 'regular-annotated.csv',
        'fixed two-state, three-symbol control graph with reset annotations (0,1,1); '
        'all 64 one-bit output assignments; B=0..3, all source debts, target debt '
        '0..3, every bound through horizon+1')


def _mutations(packet):
    values = []
    bad = deepcopy(packet); bad['schema'] = 'wrong-schema'; values.append(('schema', bad))
    bad = deepcopy(packet); bad['parameters']['target_bound'] += 1; values.append(('bound', bad))
    bad = deepcopy(packet); bad['forward']['states'].append(bad['forward']['states'][0]); values.append(('duplicate-state', bad))
    bad = deepcopy(packet)
    if bad['forward']['parents']:
        key = next(iter(bad['forward']['parents']))
        bad['forward']['parents'][key]['distance'] += 1
    else:
        bad['forward']['parents']['0,0,0'] = {'parent': [0,0,0], 'symbol': 0, 'distance': 1}
    values.append(('parent-distance', bad))
    bad = deepcopy(packet); bad['live']['live'] = bad['live']['live'] + bad['live']['live'][:1]
    if not bad['live']['live']:
        bad['live']['live'] = [0, 0]
    values.append(('duplicate-live', bad))
    bad = deepcopy(packet)
    if bad['live']['rank']:
        key = next(iter(bad['live']['rank'])); bad['live']['rank'][key] = True
    else:
        bad['live']['rank']['0'] = True
    values.append(('boolean-rank', bad))
    bad = deepcopy(packet); bad['transducer']['transitions'][0][0]['output'] = []
    values.append(('erasing-block', bad))
    bad = deepcopy(packet); bad['extra'] = 0; values.append(('extra-field', bad))
    return values


def regular_certificates(out: Path, write_csv, write_json):
    rows = []
    generated = rejected = feasible = 0
    retained = []
    selected = (list(one_bit_machines()) + list(block_machines()) +
                list(annotated_machines()))
    for family_index, (machine_id, machine) in enumerate(selected):
        family = ('one-bit' if family_index < 256 else
                  'blocks' if family_index < 512 else 'annotated')
        for bound in range(3):
            for target_debt in range(2):
                interval = rc.exact_interval(machine, bound, 0, target_debt)
                if not interval.feasible:
                    continue
                feasible += 1
                target_bound = interval.lower
                assert target_bound is not None
                packet = cc.generate(machine, bound, target_bound, 0, target_debt)
                assert cc.check(packet)
                generated += 1
                local_rejected = 0
                # Apply all mutations to the first 32 packets and one rotating
                # mutation thereafter, so both breadth and campaign cost are fixed.
                mutations = _mutations(packet)
                chosen = mutations if generated <= 32 else [mutations[generated % len(mutations)]]
                for _, bad in chosen:
                    assert not cc.check(bad)
                    local_rejected += 1; rejected += 1
                if len(retained) < 8:
                    name = f'{family}-{machine_id}-b{bound}-t{target_debt}.json'
                    write_json(out / 'contract-certificates' / name, packet)
                    retained.append(name)
                rows.append({
                    'family': family, 'machine': machine_id,
                    'source_bound': bound, 'source_debt': 0,
                    'target_bound': target_bound, 'target_debt': target_debt,
                    'forward_states': len(packet['forward']['states']),
                    'target_safe_states': len(packet['target_safe']['states']),
                    'live_vertices': len(packet['live']['live']),
                    'mutations_rejected': local_rejected,
                })
    write_csv(out / 'regular-certificates.csv', rows)
    return {
        'candidate_parameter_configurations': 576 * 3 * 2,
        'feasible_contracts': feasible,
        'certificates_generated_and_checked': generated,
        'mutated_packets_rejected': rejected,
        'retained_packets': retained,
        'checker_scope': 'positive fixed-parameter exact-language certificates',
    }



def regular_decisions(out: Path, write_csv, write_json):
    """Check complete positive/negative decision packets around every threshold."""
    rows = []
    totals = {'exact': 0, 'source-valid-target-invalid': 0,
              'source-invalid-target-valid': 0}
    mutations = 0
    retained = {key: [] for key in totals}
    configurations = 0
    decision_machines = list(faithful_machines()) + list(annotated_faithful_machines())
    for machine_id, machine in decision_machines:
        for bound in range(4):
            for debt in range(bound + 1):
                for target_debt in range(4):
                    interval = rc.exact_interval(machine, bound, debt, target_debt)
                    for target_bound in range(interval.horizon + 2):
                        packet = decisions.generate(machine, bound, target_bound,
                                                    debt, target_debt)
                        assert decisions.check(packet)
                        configurations += 1
                        kind = ('exact' if packet['verdict'] == 'exact'
                                else packet['direction'])
                        totals[kind] += 1
                        candidates = decisions.mutated(packet)
                        chosen = candidates if configurations <= 32 else [
                            candidates[configurations % len(candidates)]]
                        for bad in chosen:
                            assert not decisions.check(bad)
                            mutations += 1
                        if len(retained[kind]) < 4:
                            name = f'{kind}-{machine_id}-b{bound}-a{debt}-c{target_bound}-t{target_debt}.json'
                            write_json(out / 'decision-certificates' / name, packet)
                            retained[kind].append(name)
                        rows.append({
                            'machine': machine_id, 'source_bound': bound,
                            'source_debt': debt, 'target_bound': target_bound,
                            'target_debt': target_debt, 'verdict': packet['verdict'],
                            'direction': '' if packet['verdict'] == 'exact' else packet['direction'],
                            'prefix_length': len(packet.get('prefix', [])),
                            'loop_length': len(packet.get('loop', [])),
                        })
    write_csv(out / 'regular-decisions.csv', rows)
    return {
        'decision_packets_generated_and_checked': configurations,
        'exact_packets': totals['exact'],
        'forward_counterexamples': totals['source-valid-target-invalid'],
        'reverse_lasso_counterexamples': totals['source-invalid-target-valid'],
        'mutated_packets_rejected': mutations,
        'retained_packets': retained,
        'mismatches': 0,
    }

def _machine_by_code(code: int):
    return dict(block_machines())[f'b{code:03d}']


def regular_composition(out: Path, write_csv):
    machines = list(faithful_machines())
    rows = []
    candidates = first_exact = second_exact = composed_exact = word_checks = peak = 0
    for first_id, first in machines:
        for second_id, second in machines:
            composed = tr.compose(first, second)
            for length in range(6):
                for word in it.product((0, 1), repeat=length):
                    _, middle = first.run(word)
                    _, expected = second.run(middle)
                    _, actual = composed.run(word)
                    # The public composition API exposes a fresh reachable-pair
                    # numbering but not the pair represented by each state id.
                    # This campaign therefore checks output extensionality only.
                    assert actual == expected
                    word_checks += 1
            local_candidates = local_composed = 0
            for bound in range(3):
                for debt in range(bound + 1):
                    for middle_debt in range(3):
                        candidates += 1; local_candidates += 1
                        one = rc.exact_interval(first, bound, debt, middle_debt)
                        if not one.feasible:
                            continue
                        first_exact += 1
                        middle_bound = one.lower
                        assert middle_bound is not None
                        for final_debt in range(3):
                            two = rc.exact_interval(second, middle_bound,
                                                    middle_debt, final_debt)
                            if not two.feasible:
                                continue
                            second_exact += 1
                            final_bound = two.lower
                            assert final_bound is not None
                            direct = rc.exact_interval(composed, bound, debt, final_debt)
                            assert direct.contains(final_bound)
                            result = oracle.equivalent(composed, bound, final_bound,
                                                       debt, final_debt)
                            assert result.equivalent
                            peak = max(peak, result.reachable)
                            composed_exact += 1; local_composed += 1
            rows.append({
                'first': first_id, 'second': second_id,
                'composed_states': composed.states,
                'first_contract_candidates': local_candidates,
                'composed_contracts_checked': local_composed,
            })
    write_csv(out / 'regular-composition.csv', rows)
    return {
        'transducers': len(machines),
        'ordered_pairs': len(rows),
        'first_contract_candidates': candidates,
        'feasible_first_contracts': first_exact,
        'feasible_second_contracts': second_exact,
        'exact_composite_contracts': composed_exact,
        'finite_word_extensional_checks': word_checks,
        'comparison_scope': 'emitted output words only; final control-state ids are not compared',
        'maximum_oracle_vertices': peak,
        'mismatches': 0,
    }


def annotated_composition(out: Path, write_csv):
    """Compose three-symbol first passes with binary second passes."""
    firsts = list(annotated_faithful_machines())
    seconds = list(faithful_machines())
    rows = []
    candidates = first_exact = second_exact = composed_exact = word_checks = peak = 0
    for first_id, first in firsts:
        for second_id, second in seconds:
            composed = tr.compose(first, second)
            assert composed.input_resets == first.input_resets
            for length in range(5):
                for word in it.product(range(first.alphabet), repeat=length):
                    _, middle = first.run(word)
                    _, expected = second.run(middle)
                    _, actual = composed.run(word)
                    # Output equality is asserted; returned control-state ids
                    # are intentionally outside this experimental claim.
                    assert actual == expected
                    word_checks += 1
            local_candidates = local_composed = 0
            for bound in range(3):
                for debt in range(bound + 1):
                    for middle_debt in range(3):
                        candidates += 1; local_candidates += 1
                        one = rc.exact_interval(first, bound, debt, middle_debt)
                        if not one.feasible:
                            continue
                        first_exact += 1
                        middle_bound = one.lower
                        assert middle_bound is not None
                        for final_debt in range(3):
                            two = rc.exact_interval(second, middle_bound,
                                                    middle_debt, final_debt)
                            if not two.feasible:
                                continue
                            second_exact += 1
                            final_bound = two.lower
                            assert final_bound is not None
                            direct = rc.exact_interval(composed, bound, debt, final_debt)
                            assert direct.contains(final_bound)
                            result = oracle.equivalent(composed, bound, final_bound,
                                                       debt, final_debt)
                            assert result.equivalent
                            peak = max(peak, result.reachable)
                            composed_exact += 1; local_composed += 1
            rows.append({
                'first': first_id, 'second': second_id,
                'composed_states': composed.states,
                'first_contract_candidates': local_candidates,
                'composed_contracts_checked': local_composed,
            })
    write_csv(out / 'annotated-composition.csv', rows)
    return {
        'three_symbol_first_transducers': len(firsts),
        'binary_second_transducers': len(seconds),
        'ordered_pairs': len(rows),
        'first_contract_candidates': candidates,
        'feasible_first_contracts': first_exact,
        'feasible_second_contracts': second_exact,
        'exact_composite_contracts': composed_exact,
        'finite_word_extensional_checks': word_checks,
        'comparison_scope': 'emitted output words only; final control-state ids are not compared',
        'maximum_oracle_vertices': peak,
        'mismatches': 0,
    }


def _trace_systems():
    universe = tuple((source, reset, target)
                     for source in range(2) for reset in range(2) for target in range(2))
    for mask in range(1, 1 << len(universe)):
        raw = [entry for i, entry in enumerate(universe) if mask & (1 << i)]
        if not all(any(source == state for source, _, _ in raw) for state in range(2)):
            continue
        edges = tuple(ex.Edge(source, target, reset, 2 * source + reset)
                      for source, reset, target in raw)
        yield f's{mask:03d}', ex.TraceSystem(2, 0, edges)


def _paths(system: ex.TraceSystem, maximum: int):
    yield ()
    frontier = [(system.initial, ())]
    for _ in range(maximum):
        following = []
        for state, path in frontier:
            for edge_id, edge in system.outgoing(state):
                value = path + (edge_id,)
                yield value
                following.append((edge.target, value))
        frontier = following


def canonical_expansions(out: Path, write_csv):
    machines = list(faithful_machines())
    rows = []
    interval_cache = {}
    systems = paths_checked = labels_checked = contracts = viability = 0
    for system_id, source in _trace_systems():
        systems += 1
        for machine_id, machine in machines:
            expanded = ex.canonical_expansion(source, machine)
            local_paths = 0
            for path in _paths(source, 4):
                resets, lows, final_q = ex.expand_finite_path(source, machine, path)
                # Independently concatenate the selected chains and inspect the
                # target edges, rather than reusing expand_finite_path's output.
                q = machine.initial; target_resets = []; target_lows = []; target_ids = []
                for edge_id in path:
                    source_edge = source.edges[edge_id]
                    transition = machine.step(q, source_edge.reset)
                    chain_ids = expanded.chain_edges[q, edge_id]
                    for position, target_edge_id in enumerate(chain_ids):
                        target_edge = expanded.system.edges[target_edge_id]
                        assert expanded.edge_owners[target_edge_id] == (q, edge_id, position)
                        target_ids.append(target_edge_id)
                        target_resets.append(target_edge.reset)
                        target_lows.append(target_edge.low)
                    q = transition.next_state
                assert tuple(target_resets) == resets
                assert ex.erase(tuple(target_lows)) == ex.erase(lows)
                assert ex.erase(lows) == tuple(source.edges[i].low for i in path)
                assert ex.decompose_target_edge_path(expanded, tuple(target_ids)) == path
                assert q == final_q
                local_paths += 1; paths_checked += 1
                labels_checked += len(path)
            local_contracts = local_viability = 0
            for bound in range(3):
                for debt in range(bound + 1):
                    for target_debt in range(3):
                        key = (machine_id, bound, debt, target_debt)
                        if key not in interval_cache:
                            interval_cache[key] = rc.exact_interval(machine, bound, debt, target_debt)
                        interval = interval_cache[key]
                        if not interval.feasible:
                            continue
                        target_bound = interval.lower
                        assert target_bound is not None
                        source_graph, _ = ex.monitored_graph(source, bound, debt)
                        target_graph, _ = ex.monitored_graph(expanded.system,
                                                             target_bound, target_debt)
                        assert (0 in ex.live(source_graph)) == (0 in ex.live(target_graph))
                        contracts += 1; viability += 1
                        local_contracts += 1; local_viability += 1
            rows.append({
                'system': system_id, 'machine': machine_id,
                'source_edges': len(source.edges),
                'expanded_states': expanded.system.states,
                'expanded_edges': len(expanded.system.edges),
                'finite_paths_checked': local_paths,
                'exact_contracts_checked': local_contracts,
                'viability_agreements': local_viability,
            })
    write_csv(out / 'canonical-expansions.csv', rows)
    return {
        'source_systems': systems,
        'transducers': len(machines),
        'expanded_systems': len(rows),
        'finite_paths_checked': paths_checked,
        'source_low_labels_checked': labels_checked,
        'exact_contracts_checked': contracts,
        'viability_agreements': viability,
        'mismatches': 0,
        'scope': 'all two-state nonblocking labelled edge subsets; all sixteen reset-faithful stateful transducers',
    }

def annotated_expansions(out: Path, write_csv):
    """Exercise edge-class-specific expansion over a three-symbol alphabet."""
    machines = list(annotated_faithful_machines())
    rows = []
    interval_cache = {}
    systems = paths_checked = labels_checked = contracts = viability = 0
    for system_id, source in _trace_systems():
        systems += 1
        # Reset edges use symbol 0.  Miss edges alternate between the two
        # same-annotation classes by stable edge id, so both are exercised.
        symbols = tuple(0 if edge.reset == 0 else 1 + (edge_id % 2)
                        for edge_id, edge in enumerate(source.edges))
        for machine_id, machine in machines:
            expanded = ex.canonical_expansion(source, machine, symbols)
            local_paths = 0
            for path in _paths(source, 3):
                resets, lows, final_q = ex.expand_finite_path(source, machine, path, symbols)
                q = machine.initial; target_resets = []; target_lows = []; target_ids = []
                for edge_id in path:
                    transition = machine.step(q, symbols[edge_id])
                    chain_ids = expanded.chain_edges[q, edge_id]
                    assert len(chain_ids) == len(transition.output)
                    for position, (target_edge_id, bit) in enumerate(
                            zip(chain_ids, transition.output)):
                        expected_low = (source.edges[edge_id].low
                                        if position == len(transition.output) - 1
                                        else ex.ERASE)
                        target_edge = expanded.system.edges[target_edge_id]
                        assert expanded.edge_owners[target_edge_id] == (q, edge_id, position)
                        assert target_edge.reset == bit and target_edge.low == expected_low
                        target_ids.append(target_edge_id)
                        target_resets.append(target_edge.reset)
                        target_lows.append(target_edge.low)
                    q = transition.next_state
                assert tuple(target_resets) == resets
                assert ex.erase(tuple(target_lows)) == ex.erase(lows)
                assert ex.erase(lows) == tuple(source.edges[i].low for i in path)
                assert ex.decompose_target_edge_path(expanded, tuple(target_ids)) == path
                assert q == final_q
                local_paths += 1; paths_checked += 1; labels_checked += len(path)
            local_contracts = local_viability = 0
            for bound in range(3):
                for debt in range(bound + 1):
                    for target_debt in range(3):
                        key = (machine_id, bound, debt, target_debt)
                        if key not in interval_cache:
                            interval_cache[key] = rc.exact_interval(machine, bound, debt, target_debt)
                        interval = interval_cache[key]
                        if not interval.feasible:
                            continue
                        target_bound = interval.lower
                        assert target_bound is not None
                        source_graph, _ = ex.monitored_graph(source, bound, debt)
                        target_graph, _ = ex.monitored_graph(expanded.system,
                                                             target_bound, target_debt)
                        assert (0 in ex.live(source_graph)) == (0 in ex.live(target_graph))
                        contracts += 1; viability += 1
                        local_contracts += 1; local_viability += 1
            rows.append({
                'system': system_id, 'machine': machine_id,
                'source_edges': len(source.edges),
                'expanded_states': expanded.system.states,
                'expanded_edges': len(expanded.system.edges),
                'finite_paths_checked': local_paths,
                'exact_contracts_checked': local_contracts,
                'viability_agreements': local_viability,
            })
    write_csv(out / 'annotated-expansions.csv', rows)
    return {
        'source_systems': systems,
        'transducers': len(machines),
        'expanded_systems': len(rows),
        'finite_paths_checked': paths_checked,
        'source_low_labels_checked': labels_checked,
        'exact_contracts_checked': contracts,
        'viability_agreements': viability,
        'mismatches': 0,
        'scope': 'all two-state nonblocking labelled edge subsets; sixteen reset-faithful three-symbol transducers; stable edge-class annotations',
    }

