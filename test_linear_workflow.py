"""Owned graph/workflow regressions; no external programs or targets."""
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import regular_contracts as rc
import reference
from transducers import morphism

ROOT = Path(__file__).resolve().parent


class CountedRow(list):
    visits = 0
    def __iter__(self):
        for value in super().__iter__():
            type(self).visits += 1
            yield value


class LinearEndpointTests(unittest.TestCase):
    def test_live_matches_all_531_small_graphs_and_parallel_edges(self):
        checked = 0
        for n in range(4):
            edges = tuple(itertools.product(range(n), repeat=2))
            for mask in range(1 << len(edges)):
                graph = tuple(tuple(t for i, (s, t) in enumerate(edges)
                                    if s == v and mask & (1 << i)) for v in range(n))
                labelled = [[(i, t) for i, t in enumerate(row)] for row in graph]
                self.assertEqual(rc._live_vertices(labelled),
                                 set(reference.infinite_vertices(graph)))
                checked += 1
        self.assertEqual(checked, 531)
        self.assertEqual(rc._live_vertices([[(0, 1), (1, 1)], [(0, 1)], []]), {0, 1})
        self.assertEqual(rc._live_vertices([[(0, 1), (1, 1)], []]), set())

    def test_dead_chain_has_linear_edge_visits(self):
        n = 128
        rows = [CountedRow([(0, i + 1)]) if i + 1 < n else CountedRow() for i in range(n)]
        CountedRow.visits = 0
        self.assertEqual(rc._live_vertices(rows), set())
        self.assertLessEqual(CountedRow.visits, 2 * (n - 1))

    def test_finite_ceiling_reconstructs_only_selected_witness(self):
        machine = morphism((0,), (1,))
        with patch.object(rc, "_input_path", wraps=rc._input_path) as paths:
            answer = rc.safe_ceiling(machine, 128)
        self.assertEqual(answer.value, 128)
        self.assertEqual(answer.witness_prefix, (1,) * 128)
        self.assertLessEqual(paths.call_count, 1)

    def test_reset_seed_internal_and_initial_peaks(self):
        cases = (((1, 0, 1), (1,), 3, 1, 2),
                 ((0, 1, 1, 0), (1,), 0, 0, 0),
                 ((0,), (1,), 0, 0, 5))
        from test_profile_reuse import concrete_ceiling
        for zero, one, b, a, t in cases:
            machine = morphism(zero, one)
            answer = rc.safe_ceiling(machine, b, a, t)
            self.assertEqual(answer.value, concrete_ceiling(machine, b, a, t))
            debt, peak = t, t
            _, output = machine.run(answer.witness_prefix)
            for bit in output:
                debt = 0 if bit == 0 else debt + 1
                peak = max(peak, debt)
            self.assertEqual(peak, answer.value)


class PortableWorkflowTests(unittest.TestCase):
    def run_driver(self, out, *flags, optimized=False):
        command = [sys.executable, "-B"]
        if optimized:
            command += ["-O"]
        command += [str(ROOT / "reproduce.py"), "--output", str(out), *flags]
        return subprocess.run(command, cwd=ROOT, text=True, encoding="utf-8",
                              capture_output=True, timeout=30)

    def test_portable_stage_records_missing_limit_honestly(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "new"
            result = self.run_driver(out, "--portable", "--stage", "saturation")
            self.assertEqual(result.returncode, 0, result.stderr)
            resource = json.loads((out / "saturation-resources.json").read_text())
            self.assertEqual(resource["resource_backend"], "portable-no-posix-limit")
            self.assertIsNone(resource["address_space_limit_bytes"])
            self.assertIsNone(resource["peak_rss_kib"])
            self.assertEqual(json.loads((out / "summary.json").read_text())["saturation"]["cases"], 256)

    def test_optimized_campaign_still_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "new"
            result = self.run_driver(out, "--portable", "--stage", "saturation", optimized=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Validation requires assertions", result.stderr)
            self.assertFalse(out.exists())

    def test_full_run_refuses_existing_directory_without_touching_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "existing"
            out.mkdir()
            sentinel = out / "sentinel.txt"
            sentinel.write_bytes(b"owned-original")
            result = self.run_driver(out, "--portable")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("fresh output directory", result.stderr)
            self.assertEqual(sentinel.read_bytes(), b"owned-original")

    def test_stage_resume_refuses_completed_stage(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "existing"
            out.mkdir()
            summary = out / "summary.json"
            summary.write_bytes(b'{"saturation": {"owned_sentinel": true}}')
            original = summary.read_bytes()
            result = self.run_driver(out, "--portable", "--stage", "saturation")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("already recorded", result.stderr)
            self.assertEqual(summary.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()

