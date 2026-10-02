"""Unit and adversarial toy-input tests. All data are constructed locally."""
import itertools
import json
from pathlib import Path
import tempfile
import unittest

import certificates as c
import fairness as f
import morphisms as m
import omega_oracle as o
import reference as r
import transducers as tr
import regular_contracts as rc
import contract_oracle as co
import contract_certificates as cc
import contract_decisions as cd
import expansion as ex

class MonitorTests(unittest.TestCase):
    def test_overflow_is_not_equality(self):
        self.assertEqual(f.update((0,0),frozenset({0,1}),0,1),(0,1))
        self.assertIsNone(f.update((0,1),frozenset({0,1}),0,1))
    def test_source_disablement(self):
        self.assertEqual(f.update((0,1),frozenset({0}),0,1),(0,0))
    def test_bad_arguments(self):
        for bound in (-1,True,1.0):
            with self.assertRaises(ValueError): f.transported_bound(bound,1)
        with self.assertRaises(ValueError): f.transported_bound(1,0)
        with self.assertRaises(ValueError): f.update((0,),frozenset(),0,1)
        with self.assertRaises(ValueError): f.System((0,),17,())
        with self.assertRaises(ValueError): f.monitored(f.System((0,),1,((0,0,0),)),100000)
    def test_global_viability(self):
        s=f.System((0,),1,((0,0,0),)); both=f.tagged_interleaving(s,s)
        self.assertTrue(f.live(f.monitored(s,0).graph))
        self.assertFalse(f.live(f.monitored(both,0).graph))
        self.assertTrue(f.live(f.monitored(both,1).graph))
    def test_interleaving_encoding_unreachable_observations(self):
        # A per-model maximum-based radix would break this compositional test.
        l=f.System((1,),1,((0,0,0),))
        lp=f.System((1,999),1,((0,0,0),(1,0,1)))
        rgt=f.System((2,),1,((0,0,0),))
        self.assertTrue(f.bisimulation(l,lp,frozenset({(0,0)})))
        a=f.tagged_interleaving(rgt,l); b=f.tagged_interleaving(rgt,lp)
        self.assertTrue(f.bisimulation(a,b,frozenset({(0,0)})))
    def test_empty_fair_set(self):
        modes=f.modes(((),),frozenset({0}))
        self.assertTrue(all(not v for v in modes.values()))
    def test_goal_at_initial_state(self):
        self.assertEqual(f.modes(((0,),),frozenset({0}))['must_eventually'],frozenset({0}))
    def test_some_path_is_not_all_paths(self):
        modes=f.modes(((1,2),(1,),(2,)),frozenset({1}))
        self.assertIn(0,modes['may_eventually']); self.assertNotIn(0,modes['must_eventually'])
    def test_all_small_unlabelled_graphs(self):
        for n in range(4):
            edges=list(itertools.product(range(n),repeat=2))
            for mask in range(1<<len(edges)):
                g=tuple(tuple(t for i,(s,t) in enumerate(edges) if s==v and mask&(1<<i)) for v in range(n))
                self.assertEqual(f.live(g),r.infinite_vertices(g))
                self.assertTrue(c.check(g,c.generate(g)))

class CertificateTests(unittest.TestCase):
    def test_empty_graph(self): self.assertTrue(c.check((),c.generate(())))
    def test_natural_ranks_and_full_domain(self):
        g=((1,),()); p=c.generate(g)
        self.assertTrue(c.check(g,p)); self.assertEqual(p['rank'],{'1':0,'0':1})
        for val in (True,-1,2,'1',None):
            q=json.loads(json.dumps(p)); q['rank']['0']=val
            self.assertFalse(c.check(g,q))
    def test_dead_to_live_edge_must_not_be_omitted(self):
        g=((1,),(1,)); p={'live':[1],'successor':{'1':1},'rank':{'0':1}}
        self.assertFalse(c.check(g,p))
    def test_invalid_graph(self):
        self.assertFalse(c.check(((1,),),{'live':[],'successor':{},'rank':{'0':0}}))
        self.assertFalse(c.check(((0,0),),c.generate(((0,),))))
    def test_duplicate_json_fields(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json'; p.write_text('{"graph":[],"graph":[]}')
            with self.assertRaises(ValueError): c.load_json(p)
    def test_missing_extra_and_duplicate_certificate_fields(self):
        good=c.generate(((0,),))
        for key in good:
            bad=dict(good); del bad[key]; self.assertFalse(c.check(((0,),),bad))
        bad=dict(good); bad['extra']=1; self.assertFalse(c.check(((0,),),bad))
        bad=dict(good); bad['live']=[0,0]; self.assertFalse(c.check(((0,),),bad))

class MorphismTests(unittest.TestCase):
    def check(self,u,v,b,C,a=0,t=0,expected=True):
        self.assertEqual(m.classifies(u,v,b,C,a,t),expected)
        self.assertEqual(o.equivalent(u,v,b,C,a,t)[0],expected)
    def test_identity_all_debts(self):
        for b in range(8):
            for a in range(b+1): self.check((0,),(1,),b,b,a,a)
    def test_suffix_requires_carried_debt(self):
        for b in range(6):
            self.check((0,1),(1,),b,b+1,0,1)
            for C in range(12): self.check((0,1),(1,),b,C,expected=False)
    def test_two_reset_small_bound_exception(self):
        # u=0, v=101 admits isolated source misses but not consecutive misses.
        self.check((0,),(1,0,1),1,1)
        self.check((0,),(1,0,1),2,1,expected=False)
        self.check((0,),(1,0,1),1,1,1,1)
    def test_zero_bound_resetful_exception(self):
        self.check((0,),(1,0),0,0)
    def test_nonreset_zero_block_impossible(self):
        for C in range(4): self.check((1,),(0,),0,C,expected=False)
    def test_internal_gap_gate(self):
        with self.assertRaises(ValueError): m.canonical_parameters((0,1,0),(1,),0)
        self.check((0,1,0),(1,),0,0,expected=False)
    def test_public_quantifier_counterexample(self):
        identity=((0,),(1,)); double=((0,),(1,1))
        for b in range(1,5):
            self.assertIsNotNone(m.uniform_public_budget((identity,),b))
            self.assertIsNotNone(m.uniform_public_budget((double,),b))
            self.assertIsNone(m.uniform_public_budget((identity,double),b))
    def test_one_zero_profile_has_no_internal_pair(self):
        self.assertEqual(m.profile((1,0,1)).internal,0)
        self.assertEqual(m.profile(m.substitute((0,),(1,0,1),(1,1))).internal,0)
    def test_wrong_initial_debt_changes_language(self):
        self.check((0,),(1,),2,2,1,0,expected=False)
    def test_input_validation(self):
        for w in ((),(True,),(2,),(-1,),('0',)):
            with self.assertRaises(ValueError): m.profile(w)
        with self.assertRaises(ValueError): m.classifies((0,),(1,),1,1,2)
        with self.assertRaises(ValueError): m.uniform_public_budget((),1)
        for vals in (((0,),(True,),1,1),((0,),(1,),True,1),((0,),(1,),1,129)):
            with self.assertRaises(ValueError): o.equivalent(*vals)
    def test_true_invalid_floor_includes_baseline_demands(self):
        cases = (
            ((0,), (1,), 0, 0, 2, 2),
            ((0, 1, 1, 0), (1,), 0, 0, 0, 2),
        )
        for u, v, bound, debt, target_debt, expected_floor in cases:
            machine = tr.morphism(u, v)
            self.assertEqual(
                m.invalid_floor_all_miss(u, v, bound, debt, target_debt),
                expected_floor,
            )
            floor = rc.invalid_floor(machine, bound, debt, target_debt)
            self.assertEqual(floor.value, expected_floor)
            before = co.equivalent(
                machine, bound, expected_floor - 1, debt, target_debt)
            at = co.equivalent(
                machine, bound, expected_floor, debt, target_debt)
            self.assertFalse(before.target_not_source)
            self.assertTrue(at.target_not_source)
            self.assertIsNone(rc.invalid_safe_lasso(
                machine, bound, debt, expected_floor - 1, target_debt))
            witness = rc.invalid_safe_lasso(
                machine, bound, debt, expected_floor, target_debt)
            self.assertIsNotNone(witness)
            assert witness is not None
            packet = {
                'schema': cd.SCHEMA,
                'transducer': machine.to_json(),
                'parameters': {
                    'source_bound': bound,
                    'target_bound': expected_floor,
                    'source_debt': debt,
                    'target_debt': target_debt,
                },
                'verdict': 'inexact',
                'direction': 'source-invalid-target-valid',
                'prefix': list(witness.prefix),
                'loop': list(witness.loop),
            }
            self.assertTrue(cd.check(packet))

    def test_vector_exactness_need_not_be_coordinatewise_necessary(self):
        # Both source coordinates are L(1,0).  The first target coordinate
        # emits 0 on either source symbol and is therefore universal at C=0;
        # the second is the identity at C=1.  Their conjunction is exactly
        # L(1,0), even though the first scalar contract is not exact.
        self.assertFalse(m.classifies((0,), (0,), 1, 0))
        self.assertTrue(m.classifies((0,), (1,), 1, 1))
        self.assertFalse(o.equivalent((0,), (0,), 1, 0)[0])
        self.assertTrue(o.equivalent((0,), (1,), 1, 1)[0])
        for source_debt in range(3):
            for bit in (0, 1):
                next_source = 2 if source_debt == 2 else (0 if bit == 0 else min(2, source_debt + 1))
                first_target = 0  # output coordinate is always reset
                second_target = next_source
                self.assertEqual(
                    (next_source <= 1 and next_source <= 1),
                    (first_target <= 0 and second_target <= 1),
                )

    def test_overflow_is_absorbing_in_oracle(self):
        self.assertEqual(o.transition(2,(0,),1),2)
        self.assertEqual(o.transition(0,(1,1,0),1),2)


class RegularContractTests(unittest.TestCase):
    @staticmethod
    def stateful_machine():
        return tr.Transducer((
            (tr.Transition(1, (0, 1)), tr.Transition(0, (1,))),
            (tr.Transition(0, (0,)), tr.Transition(1, (1, 0, 1))),
        ))

    def test_transducer_composition_is_extensional(self):
        first = self.stateful_machine()
        second = tr.Transducer((
            (tr.Transition(0, (0,)), tr.Transition(1, (1, 1))),
            (tr.Transition(0, (1, 0)), tr.Transition(1, (1,))),
        ))
        composite = tr.compose(first, second)
        for length in range(7):
            for word in itertools.product((0, 1), repeat=length):
                middle_state, middle = first.run(word)
                target_state, target = second.run(middle)
                composed_state, direct = composite.run(word)
                self.assertEqual(direct, target)
                # State numbers are an internal reachable-pair encoding; output
                # equality is the extensional composition obligation.
                self.assertGreaterEqual(composed_state, 0)
                self.assertGreaterEqual(middle_state, 0)
                self.assertGreaterEqual(target_state, 0)

    def test_regular_interval_matches_both_stateless_deciders(self):
        words = [(0,), (1,), (0, 1), (1, 0), (1, 1)]
        for u in words:
            for v in words:
                machine = tr.morphism(u, v)
                for b in range(3):
                    for a in range(b + 1):
                        for t in range(3):
                            interval = rc.exact_interval(machine, b, a, t)
                            for target in range(interval.horizon + 2):
                                expected = m.classifies(u, v, b, target, a, t)
                                self.assertEqual(interval.contains(target), expected)
                                self.assertEqual(co.equivalent(machine, b, target, a, t).equivalent,
                                                 expected)

    def test_stateful_interval_matches_product_oracle(self):
        # All 16 output assignments for a fixed nontrivial two-state control
        # graph, enough to exercise resetful and zero-free cycles in unit tests.
        next_states = ((1, 0), (0, 1))
        for mask in range(16):
            rows = []
            for q in range(2):
                row = []
                for bit in range(2):
                    k = 2 * q + bit
                    row.append(tr.Transition(next_states[q][bit], ((mask >> k) & 1,)))
                rows.append(tuple(row))
            machine = tr.Transducer(tuple(rows))
            for b in range(3):
                for a in range(b + 1):
                    for t in range(2):
                        interval = rc.exact_interval(machine, b, a, t)
                        for target in range(interval.horizon + 2):
                            self.assertEqual(interval.contains(target),
                                             co.equivalent(machine, b, target, a, t).equivalent)

    def test_zero_free_safe_cycle_has_infinite_ceiling(self):
        machine = tr.morphism((1,), (0,))
        ceiling = rc.safe_ceiling(machine, 0)
        self.assertEqual(ceiling.value, float('inf'))
        self.assertEqual(ceiling.witness_kind, 'zero-free-cycle')
        self.assertFalse(rc.exact_interval(machine, 0).feasible)

    def test_exact_interval_and_lasso_witness(self):
        machine = tr.morphism((0, 1), (1,))
        interval = rc.exact_interval(machine, 2, 0, 1)
        self.assertEqual((interval.lower, interval.upper), (3, 3))
        self.assertTrue(co.equivalent(machine, 2, 3, 0, 1).equivalent)
        floor = rc.invalid_floor(machine, 2, 0, 1)
        self.assertEqual(floor.value, 4)
        self.assertIsNotNone(floor.witness)
        witness = floor.witness
        assert witness is not None
        self.assertTrue(witness.loop)

    def test_contract_certificate_and_mutations(self):
        machine = tr.morphism((0, 1), (1,))
        packet = cc.generate(machine, 2, 3, 0, 1)
        self.assertTrue(cc.check(packet))
        mutations = []
        bad = json.loads(json.dumps(packet)); bad['parameters']['target_bound'] = 4; mutations.append(bad)
        bad = json.loads(json.dumps(packet)); bad['forward']['states'].pop(); mutations.append(bad)
        bad = json.loads(json.dumps(packet)); bad['live']['live'] = list(reversed(bad['live']['live'])) + bad['live']['live'][:1]; mutations.append(bad)
        bad = json.loads(json.dumps(packet)); bad['schema'] = 'other'; mutations.append(bad)
        bad = json.loads(json.dumps(packet)); bad['transducer']['transitions'][0][0]['output'] = []; mutations.append(bad)
        self.assertTrue(all(not cc.check(value) for value in mutations))
        with self.assertRaises(ValueError):
            cc.generate(machine, 2, 4, 0, 1)

    def test_complete_decision_packets(self):
        machine = tr.morphism((0, 1), (1,))
        expected = {
            2: ('inexact', 'source-valid-target-invalid'),
            3: ('exact', None),
            4: ('inexact', 'source-invalid-target-valid'),
        }
        for target_bound, verdict in expected.items():
            packet = cd.generate(machine, 2, target_bound, 0, 1)
            self.assertTrue(cd.check(packet))
            self.assertEqual((packet['verdict'], packet.get('direction')), verdict)
            self.assertTrue(all(not cd.check(bad) for bad in cd.mutated(packet)))

    def test_decision_witness_directions_can_overlap(self):
        # Identity expansion with a carried target debt can lose preservation
        # before the first reset while the wider target bound loses reflection
        # after a reset.  The generator deliberately gives forward precedence;
        # the mathematical witness directions are not a disjoint trichotomy.
        machine = tr.morphism((0,), (1,))
        answer = co.equivalent(machine, 1, 2, 0, 2)
        self.assertTrue(answer.source_not_target)
        self.assertTrue(answer.target_not_source)
        packet = cd.generate(machine, 1, 2, 0, 2)
        self.assertEqual(
            (packet['verdict'], packet.get('direction')),
            ('inexact', 'source-valid-target-invalid'),
        )
        self.assertTrue(cd.check(packet))
        reverse = rc.invalid_safe_lasso(machine, 1, 0, 2, 2)
        self.assertIsNotNone(reverse)
        assert reverse is not None
        reverse_packet = {
            'schema': cd.SCHEMA,
            'transducer': machine.to_json(),
            'parameters': {
                'source_bound': 1,
                'target_bound': 2,
                'source_debt': 0,
                'target_debt': 2,
            },
            'verdict': 'inexact',
            'direction': 'source-invalid-target-valid',
            'prefix': list(reverse.prefix),
            'loop': list(reverse.loop),
        }
        self.assertTrue(cd.check(reverse_packet))

    def test_three_symbol_annotations_roundtrip_and_oracle(self):
        machine = tr.Transducer((
            (tr.Transition(1, (0,)), tr.Transition(0, (1,)), tr.Transition(1, (1, 1))),
            (tr.Transition(0, (0, 1)), tr.Transition(1, (1, 0)), tr.Transition(0, (1,))),
        ), input_resets=(0, 1, 1))
        self.assertEqual(tr.Transducer.from_json(machine.to_json()), machine)
        self.assertEqual(machine.source_projection((0, 1, 2, 0)), (0, 1, 1, 0))
        self.assertNotEqual(machine.run((0, 1))[1], machine.run((0, 2))[1])
        for bound in range(3):
            for debt in range(bound + 1):
                for target_debt in range(3):
                    interval = rc.exact_interval(machine, bound, debt, target_debt)
                    for target_bound in range(interval.horizon + 2):
                        self.assertEqual(
                            interval.contains(target_bound),
                            co.equivalent(machine, bound, target_bound,
                                          debt, target_debt).equivalent)

    def test_input_validation_and_relabeling(self):
        machine = self.stateful_machine()
        relabelled = tr.relabel_states(machine, (1, 0))
        for word in itertools.product((0, 1), repeat=5):
            self.assertEqual(machine.run(word)[1], relabelled.run(word)[1])
        with self.assertRaises(ValueError): tr.morphism((), (1,))
        with self.assertRaises(ValueError): tr.Transducer(((tr.Transition(2, (0,)), tr.Transition(0, (1,))),))
        with self.assertRaises(ValueError):
            tr.Transducer(((tr.Transition(0, (1,)), tr.Transition(0, (1,))),),
                          input_resets=(1, 1))
        with self.assertRaises(ValueError): rc.exact_interval(machine, -1)
        with self.assertRaises(ValueError): co.equivalent(machine, 1, -1)


class CanonicalExpansionTests(unittest.TestCase):
    @staticmethod
    def system():
        return ex.TraceSystem(2, 0, (
            ex.Edge(0, 0, 0, 7),
            ex.Edge(0, 1, 1, 8),
            ex.Edge(1, 0, 0, 9),
            ex.Edge(1, 1, 1, 10),
        ))

    def test_finite_path_reset_and_low_projection(self):
        source = self.system()
        machine = RegularContractTests.stateful_machine()
        path = (1, 3, 2, 0)
        resets, lows, final_q = ex.expand_finite_path(source, machine, path)
        state = machine.initial
        expected = []
        source_lows = []
        for edge_id in path:
            edge = source.edges[edge_id]
            step = machine.step(state, edge.reset)
            expected.extend(step.output)
            source_lows.append(edge.low)
            state = step.next_state
        self.assertEqual(resets, tuple(expected))
        self.assertEqual(ex.erase(lows), tuple(source_lows))
        self.assertEqual(final_q, state)

    def test_expansion_chains_and_deterministic_interiors(self):
        source = self.system()
        machine = RegularContractTests.stateful_machine()
        expanded = ex.canonical_expansion(source, machine)
        boundary_vertices = set(expanded.boundary.values())
        for (q, edge_id), chain in expanded.chains.items():
            edge = source.edges[edge_id]
            block = machine.step(q, edge.reset).output
            self.assertEqual(len(chain), len(block) + 1)
            self.assertEqual(chain[0], expanded.boundary[edge.source, q])
            for vertex in chain[1:-1]:
                self.assertNotIn(vertex, boundary_vertices)
                outgoing = expanded.system.outgoing(vertex)
                self.assertEqual(len(outgoing), 1)
                self.assertEqual(outgoing[0][1].low,
                                 edge.low if vertex == chain[-2] else ex.ERASE)
        for (state, q), vertex in expanded.boundary.items():
            self.assertEqual(len(expanded.system.outgoing(vertex)),
                             len(source.outgoing(state)))

    def test_edge_class_specific_three_symbol_expansion(self):
        source = self.system()
        machine = tr.Transducer((
            (tr.Transition(1, (0,)), tr.Transition(0, (1,)), tr.Transition(1, (1, 1))),
            (tr.Transition(0, (0, 1)), tr.Transition(1, (1,)), tr.Transition(0, (1, 1))),
        ), input_resets=(0, 1, 1))
        symbols = (0, 1, 0, 2)
        path = (1, 3, 2, 0)
        expanded = ex.canonical_expansion(source, machine, symbols)
        resets, lows, final_q = ex.expand_finite_path(source, machine, path, symbols)
        self.assertEqual(expanded.edge_symbols, symbols)
        q = machine.initial; expected = []
        for edge_id in path:
            transition = machine.step(q, symbols[edge_id])
            expected.extend(transition.output); q = transition.next_state
        self.assertEqual(resets, tuple(expected))
        self.assertEqual(ex.erase(lows), tuple(source.edges[i].low for i in path))
        self.assertEqual(final_q, q)
        with self.assertRaises(ValueError): ex.canonical_expansion(source, machine)
        with self.assertRaises(ValueError): ex.canonical_expansion(source, machine, (0, 0, 0, 2))

    def test_parallel_length_one_chains_keep_edge_identity(self):
        source = ex.TraceSystem(1, 0, (
            ex.Edge(0, 0, 0, 7),
            ex.Edge(0, 0, 1, 7),
        ))
        machine = tr.morphism((0,), (0,))
        expanded = ex.canonical_expansion(source, machine)
        first = ex.expand_target_edge_path(expanded, source, machine, (0,))
        second = ex.expand_target_edge_path(expanded, source, machine, (1,))
        self.assertNotEqual(first, second)
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)
        self.assertEqual(expanded.system.edges[first[0]], expanded.system.edges[second[0]])
        self.assertEqual(ex.decompose_target_edge_path(expanded, first), (0,))
        self.assertEqual(ex.decompose_target_edge_path(expanded, second), (1,))
        self.assertEqual(len(expanded.system.outgoing(expanded.system.initial)), 2)

    def test_parallel_shared_labels_long_short_roundtrip(self):
        source = ex.TraceSystem(1, 0, (
            ex.Edge(0, 0, 1, 7),
            ex.Edge(0, 0, 1, 7),
        ))
        machine = tr.Transducer(((
            tr.Transition(0, (0,)),
            tr.Transition(0, (1,)),
            tr.Transition(0, (1, 1, 1)),
        ),), input_resets=(0, 1, 1))
        symbols = (1, 2)
        expanded = ex.canonical_expansion(source, machine, symbols)
        path = (0, 1, 0)
        target_ids = ex.expand_target_edge_path(
            expanded, source, machine, path, symbols)
        self.assertEqual(ex.decompose_target_edge_path(expanded, target_ids), path)
        resets = tuple(expanded.system.edges[i].reset for i in target_ids)
        lows = tuple(expanded.system.edges[i].low for i in target_ids)
        self.assertEqual(resets, (1, 1, 1, 1, 1))
        self.assertEqual(ex.erase(lows), (7, 7, 7))
        long_chain = expanded.chain_edges[machine.initial, 1]
        with self.assertRaises(ValueError):
            ex.decompose_target_edge_path(expanded, long_chain[:-1])

    def test_monitor_viability_agrees_under_exact_contract(self):
        source = self.system()
        machine = tr.morphism((0, 1), (1,))
        expanded = ex.canonical_expansion(source, machine).system
        source_graph, _ = ex.monitored_graph(source, 2, 0)
        target_graph, _ = ex.monitored_graph(expanded, 3, 1)
        self.assertEqual(0 in ex.live(source_graph), 0 in ex.live(target_graph))

    def test_bad_path_and_bad_system(self):
        source = self.system()
        machine = tr.morphism((0,), (1,))
        with self.assertRaises(ValueError): ex.expand_finite_path(source, machine, (2,))
        with self.assertRaises(ValueError): ex.TraceSystem(1, 0, (ex.Edge(0, 1, 0, 0),))
        with self.assertRaises(ValueError): ex.monitored_graph(source, 1, 2)

if __name__=='__main__': unittest.main(verbosity=2)
