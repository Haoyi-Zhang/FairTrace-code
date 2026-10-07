"""Concrete-bit reference for owned finite safe-ceiling fixtures."""
from itertools import product
from math import inf
import unittest
from unittest.mock import patch

import contract_decisions as decisions
import contract_oracle as oracle
import regular_contracts as contracts
from transducers import Transition, Transducer, morphism, relabel_states


def concrete_ceiling(machine, bound, initial_source, initial_target):
    # Explore actual debts, without profiles, a DAG recurrence, or pruning.
    # Above this loose finite-control/block bound an all-miss cycle must exist.
    limit = initial_target + ((bound + 1) * machine.states + 2) * machine.maximum_block
    pending = [(initial_source, machine.initial, initial_target)]
    seen = set(pending)
    peak = initial_target
    for source, control, target in pending:
        for symbol, transition in enumerate(machine.transitions[control]):
            next_source = 0 if machine.input_resets[symbol] == 0 else source + 1
            if next_source > bound:
                continue
            debt = target
            for bit in transition.output:
                debt = 0 if bit == 0 else debt + 1
                peak = max(peak, debt)
                if peak > limit:
                    return inf
            state = (next_source, transition.next_state, debt)
            if state not in seen:
                seen.add(state)
                pending.append(state)
    return peak


def machines():
    words = ((0,), (1,), (0, 1), (1, 0), (1, 1), (0, 1, 1, 0))
    for zero, one in product(words, repeat=2):
        yield morphism(zero, one)
    for mask in range(16):
        yield Transducer(tuple(tuple(Transition(((1, 0), (0, 1))[q][symbol],
                                                ((mask >> (2 * q + symbol)) & 1,))
                                     for symbol in range(2)) for q in range(2)))
    yield Transducer(((Transition(1, (1, 1, 0)), Transition(1, (1, 1)), Transition(1, (0, 1, 1))),
                      (Transition(1, (0, 1)), Transition(0, (1, 1, 0)), Transition(0, (1, 1, 0)))),
                     input_resets=(0, 1, 1))
    yield Transducer(((Transition(0, (0,)), Transition(0, (1,))),
                      (Transition(1, (1,)), Transition(1, (1,)))))


class ProfileReuseTests(unittest.TestCase):
    def test_concrete_bit_ceiling_and_witness(self):
        for machine in machines():
            for bound in range(3):
                for source in range(bound + 1):
                    for target in range(3):
                        result = contracts.safe_ceiling(machine, bound, source, target)
                        self.assertEqual(result.value, concrete_ceiling(machine, bound, source, target))
                        debt, control, peak = source, machine.initial, target
                        target_debt = target
                        for symbol in result.witness_prefix:
                            debt = 0 if machine.input_resets[symbol] == 0 else debt + 1
                            self.assertLessEqual(debt, bound)
                            transition = machine.transitions[control][symbol]
                            for bit in transition.output:
                                target_debt = 0 if bit == 0 else target_debt + 1
                                peak = max(peak, target_debt)
                            control = transition.next_state
                        if result.value == inf:
                            self.assertTrue(result.zero_free_cycle)
                            state = (debt, control)
                            for symbol in result.zero_free_cycle:
                                debt = 0 if machine.input_resets[symbol] == 0 else debt + 1
                                self.assertLessEqual(debt, bound)
                                transition = machine.transitions[control][symbol]
                                self.assertNotIn(0, transition.output)
                                control = transition.next_state
                            self.assertEqual((debt, control), state)
                        else:
                            self.assertEqual(peak, result.value)

    def test_exact_intervals_and_independent_packet_consumers(self):
        for machine in tuple(machines())[::7]:
            for bound in (0, 1, 2):
                interval = contracts.exact_interval(machine, bound, bound, 1)
                for target in range(5):
                    expected = oracle.equivalent(machine, bound, target, bound, 1)
                    self.assertEqual(interval.contains(target), expected.equivalent)
                    packet = decisions.generate(machine, bound, target, bound, 1)
                    self.assertTrue(decisions.check(packet))
                    self.assertTrue(all(not decisions.check(bad) for bad in decisions.mutated(packet)))

    def test_one_profile_per_encountered_transition_only(self):
        machine = tuple(machines())[-1]
        with patch.object(contracts, "profile", wraps=contracts.profile) as observed:
            states, rows, parents = contracts._safe_controls(machine, 4, 0)
        keys = {(control, symbol) for (_, control), row in zip(states, rows) for symbol, _, _ in row}
        self.assertEqual(observed.call_count, len(keys))
        self.assertEqual(keys, {(0, 0), (0, 1)})
        self.assertGreater(sum(map(len, rows)), len(keys))
        instances = {}
        for (_, control), row in zip(states, rows):
            for symbol, _, block in row:
                key = (control, symbol)
                if key in instances:
                    self.assertIs(block, instances[key])
                instances[key] = block
        self.assertEqual(len(parents), len(states))

    def test_profiles_are_invocation_local(self):
        first = morphism((0,), (1,))
        second = morphism((1, 0), (1, 1))
        for machine in (first, second, first):
            with patch.object(contracts, "profile", wraps=contracts.profile) as observed:
                result = contracts.safe_ceiling(machine, 2, 1, 2)
            self.assertEqual(observed.call_count, 2)
            self.assertEqual(result.value, concrete_ceiling(machine, 2, 1, 2))

    def test_budget_boundary_and_relabeling(self):
        machine = tuple(machines())[36]
        states, _, _ = contracts._safe_controls(machine, 2, 0)
        with patch.object(contracts, "MAX_PRODUCT_STATES", len(states)):
            result = contracts.safe_ceiling(machine, 2, 0, 1)
        with patch.object(contracts, "MAX_PRODUCT_STATES", len(states) - 1):
            with self.assertRaisesRegex(ValueError, "source-safe product exceeds explicit state budget"):
                contracts.safe_ceiling(machine, 2, 0, 1)
        self.assertEqual(result.value, contracts.safe_ceiling(relabel_states(machine, (1, 0)), 2, 0, 1).value)

    def test_parameter_errors_precede_profile_evaluation(self):
        machine = morphism((0,), (1,))
        for args in ((True, 0, 0), (-1, 0, 0), (1, 2, 0), (1, 0, 1.0), (1, False, 0)):
            with patch.object(contracts, "profile", side_effect=AssertionError("must not profile")):
                with self.assertRaises(ValueError):
                    contracts.safe_ceiling(machine, *args)


if __name__ == "__main__":
    unittest.main()
