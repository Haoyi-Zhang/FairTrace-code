# Same-input endpoint implementation cost

`measurement.json` retains all authored input graphs/machine parameters,
six alternating-order timing samples per path, separate input-edge visits,
path-reconstruction counts, allocation peaks, answers/witnesses, environment
and source bindings. All ten before/after comparisons agree exactly.

`source-before.py` is the exact reviewed pre-change endpoint implementation,
not an audit log. The measurement tool refuses any baseline with a different
SHA-256 before loading it. Replay with fresh output:

```sh
python -B measure_endpoint_cost.py --baseline results/endpoint-cost/source-before.py --out NEW_DIRECTORY
```

Dead chains and identity-expander debt chains isolate repeated peeling/path
copying; all-live self-loops are retained as a non-peeling control. These are
owned cost fixtures, not sampled production workloads or empirical novelty.
Input-edge visits exclude predecessor-array/set operations. Tracemalloc peaks
are Python allocations, not process RSS. Complete raw samples are retained;
no whole-synthesizer, different-host or production speedup is inferred.
