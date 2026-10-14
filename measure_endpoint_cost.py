"""Same-input endpoint cost checks on owned graphs and identity expanders."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import statistics
import sys
import time
import tracemalloc
from unittest.mock import patch

import regular_contracts as current
import transducers

APPROVED_BASELINE_SHA256 = "ef771198a1291998d07ad8053cd6ed957d0907403ba3f5ac8dd7d7be2e4eb3c3"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def baseline(path):
    if digest(path) != APPROVED_BASELINE_SHA256:
        raise ValueError("baseline is not the exact reviewed source snapshot")
    spec = importlib.util.spec_from_file_location("fairtrace_reviewed_baseline", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CountedRow(list):
    visits = 0
    def __iter__(self):
        for value in super().__iter__():
            type(self).visits += 1
            yield value


def timings(old, new):
    samples = {"before": [], "after": []}
    for index in range(6):
        order = (("before", old), ("after", new)) if index % 2 == 0 else (("after", new), ("before", old))
        for name, function in order:
            started = time.perf_counter_ns()
            function()
            samples[name].append(time.perf_counter_ns() - started)
    return {"samples_ns": samples,
            "median_ns": {name: statistics.median(values) for name, values in samples.items()},
            "protocol": "six uninstrumented calls per path, alternating paired order; memory/visit samples separate"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    old = baseline(args.baseline)
    args.out.mkdir(parents=True, exist_ok=False)
    rows = []
    inputs = []
    for shape in ("dead-chain", "self-loops"):
        for n in (128, 512, 2048):
            graph = [[(0, i + 1)] if i + 1 < n else [] for i in range(n)] if shape == "dead-chain" else [[(0, i)] for i in range(n)]
            before = old._live_vertices(graph)
            after = current._live_vertices(graph)
            if before != after:
                raise AssertionError("live-set disagreement")
            visits = {}
            for name, implementation in (("before", old), ("after", current)):
                counted = [CountedRow(row) for row in graph]
                CountedRow.visits = 0
                implementation._live_vertices(counted)
                visits[name] = CountedRow.visits
            inputs.append({"kind": "graph", "shape": shape, "vertices": n, "adjacency": graph})
            rows.append({"kind": "live", "shape": shape, "vertices": n,
                         "edge_occurrences": sum(map(len, graph)),
                         "live_count": len(after), "same_information_equal": True,
                         "input_edge_visits": visits,
                         **timings(lambda: old._live_vertices(graph), lambda: current._live_vertices(graph))})
    machine = transducers.morphism((0,), (1,))
    for b in (32, 128, 512, 1024):
        params = (b, 0, 0)
        before = old.safe_ceiling(machine, *params)
        after = current.safe_ceiling(machine, *params)
        signature = lambda value: (value.value, value.witness_prefix, value.witness_kind, value.zero_free_cycle)
        if signature(before) != signature(after):
            raise AssertionError("ceiling or witness disagreement")
        allocations, calls = {}, {}
        for name, implementation in (("before", old), ("after", current)):
            with patch.object(implementation, "_input_path", wraps=implementation._input_path) as count:
                implementation.safe_ceiling(machine, *params)
                calls[name] = count.call_count
            tracemalloc.start()
            implementation.safe_ceiling(machine, *params)
            _, allocations[name] = tracemalloc.get_traced_memory()
            tracemalloc.stop()
        inputs.append({"kind": "ceiling", "machine": machine.to_json(),
                       "source_bound": b, "source_debt": 0, "target_debt": 0})
        rows.append({"kind": "ceiling", "source_bound": b, "safe_controls": b + 1,
                     "safe_ceiling": after.value, "witness_prefix": list(after.witness_prefix),
                     "witness_kind": after.witness_kind, "same_information_equal": True,
                     "bfs_path_reconstruction_calls": calls, "python_allocation_peak_bytes": allocations,
                     **timings(lambda: old.safe_ceiling(machine, *params), lambda: current.safe_ceiling(machine, *params))})
    root = Path(__file__).resolve().parent
    report = {"scope": "Owned authored graph/expander cost fixtures, not production compiler workloads or new semantic novelty",
              "inputs": inputs, "measurements": rows, "all_answers_and_witnesses_equal": True,
              "environment": {"python": sys.version, "executable": sys.executable,
                              "platform": platform.platform(), "argv": sys.argv},
              "source_bindings": {
                  "before_regular_contracts_sha256": digest(args.baseline),
                  "after_regular_contracts_sha256": digest(root / "regular_contracts.py"),
                  "transducers_sha256": digest(root / "transducers.py"),
                  "measurement_script_sha256": digest(Path(__file__))},
              "limitations": ["Input edge visits do not count Python set/list operations or predecessor-array accesses.",
                              "tracemalloc peaks are Python allocations, not RSS/process memory.",
                              "A dead-chain case favors queue peeling; self-loops retain a potential queue overhead negative.",
                              "No whole-synthesizer or independent-host speedup claim."]}
    (args.out / "measurement.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(rows), "agreement": True,
                      "summary": [{k: r[k] for k in ("kind", "median_ns")} for r in rows]}))


if __name__ == "__main__":
    main()

