# Regular fairness contracts for reactive trace refinement

This standalone repository accompanies the paper **Regular Fairness Contracts for Reactive Trace Refinement**. It implements and checks a bounded-fairness interface for deterministic finite-state, non-erasing step expanders. Source symbols carry reset annotations; each transducer transition emits a nonempty binary target-reset block. For fixed source bound and initial debt, target initial debt, and transducer, the accepted target bounds form an integer interval whose endpoints are synthesized by finite graph algorithms.

The repository also contains a canonical microstep expansion of finite reactive transition systems. Intermediate target steps are deterministic, transducer control is retained at source boundaries, and only the final microstep of a chain exposes the source low label. The executable checks are finite validation of the implementation. The general theorems are paper proofs, not proof-assistant-checked metatheory.

## Reproduce the retained campaign

Requirements: Linux, Python 3.10 or later, and the Python standard library. No package installation, solver, proof assistant, network request, GPU, private data, model API, or external service is used. Run from this directory without `-O` or `PYTHONOPTIMIZE`:

```sh
python3 -m unittest -v test_artifact
python3 reproduce.py --output reproduced
python3 check_reproduction.py results reproduced
python3 certificates.py results/certificates/m017-b0.json
```

The first command runs 45 tests, including regressions for overlapping negative directions, semantic invalid-floor thresholds, vector-coordinate masking, and parallel expansion chains with identical structural edges. The second executes 22 deterministic stages in one process and writes a fresh directory. The third compares every deterministic CSV, JSON summary, exact input, and retained certificate packet; machine-dependent CPU, wall-time, and peak-RSS records are intentionally excluded. The final command exercises the independent command-line parser and local live-set checker on one retained graph certificate.

The campaign can be resumed one stage at a time:

```sh
python3 reproduce.py --stage regular-decisions --output reproduced
```

The stage names are:

```text
expansion, monitor, graphs, bisimulation, saturation, boundaries,
classify0, classify1, classify2, classify3, classify4,
public-budget, composition,
regular-one-bit, regular-blocks, regular-annotated,
regular-certificates, regular-decisions,
regular-composition, annotated-composition,
canonical-expansions, annotated-expansions
```

A stage-only directory is not a complete comparison target. Do not overwrite `results/` during ordinary reproduction.

The retained clean-copy replay is recorded in `results/clean-reproduction/`. All 45 tests and all 22 stages were rerun from a clean copy using the documented stage interface; the final summary contains every stage exactly once, and the comparator matched 60 deterministic scientific files with zero mismatches. The paper was separately rebuilt from source-only input to 50 pages with all fonts embedded and an empty critical-warning scan.

## Main retained results

| Check | Complete retained domain | Outcome |
|---|---:|---:|
| Stateful endpoint algorithms vs. independent fixed-bound omega-language oracle | 576 machines; 23,040 parameter tuples; 407,040 target bounds | 0 disagreements; 459 exact bounds; 400 feasible intervals; 7,200 infinite safe ceilings |
| Positive exact-contract certificates | 3,456 candidates | 150 generated and accepted; 374 mutated packets rejected |
| Complete fixed-bound decision packets | 29,680 packets | 130 exact; 6,061 forward packets; 23,489 reverse-by-precedence packets; 29,807 mutations rejected; 0 disagreements |
| Stateful transducer composition | 512 ordered pairs across binary and three-symbol families | 584 exact composites; 47,104 emitted-word checks; 0 disagreements |
| Canonical reactive microstep expansion | 7,200 expanded systems | 262,176 finite paths; 814,592 source labels; 16,650 exact-contract viability checks; 0 disagreements |
| Stateless closed-form classification and semantic floor | 449,820 fixed configurations; 1,980 direct floor instances | 2,232 exact equalities; 3,960 `R-1`/`R` reflection checks and 1,980 lasso witnesses; 0 disagreements |
| Public-budget families | 360 configurations | 167 feasible; 193 infeasible |
| Auxiliary monitor and graph semantics | 21,844 event-word checks; 900 monitored products; 216,000 Boolean property answers | 0 disagreements |
| Unit tests | 45 tests, including all 531 directed graphs on at most three vertices plus endpoint, vector-mask, and parallel-edge regressions | all pass |

The stateful total combines three separately reported families:

- all 256 two-state deterministic controls with one-bit outputs;
- all 256 assignments of blocks in `{0,1,01,10}` on a fixed nontrivial two-state graph;
- all 64 one-bit assignments on a fixed three-symbol graph with annotations `(0,1,1)`.

The three-symbol family is important: two source symbols can have the same fairness annotation while selecting different input classes and emitting different blocks. In the worked two-state machine they have the same next state at each control state, so category replacement does not change the control trajectory; the family still cannot be reduced to a morphism on the reset bit alone.


The direct floor evidence is retained in `results/stateless-floor-0.csv` through `results/stateless-floor-4.csv`. Each row records the formula value, the independent fixed-bound reflection answers at `R-1` and `R`, and a reverse lasso accepted by the packet checker.

`results/campaign-resources.json` records the retained 22-stage campaign: 73.176 CPU seconds, 73.186 wall seconds, one worker, a 3 GiB address-space ceiling, and maximum retained peak RSS of 104,876 KiB in the execution environment. These numbers are resource accounting, not performance claims.

## Repository map

| File | Role |
|---|---|
| `transducers.py` | Validated deterministic finite-state non-erasing transducers, composition, state relabeling, and block traversal. |
| `regular_contracts.py` | Safe-ceiling and invalid-floor synthesis, exact intervals, witnesses, and the completeness horizon. |
| `contract_oracle.py` | Independent fixed-bound product oracle over infinite words; it does not call endpoint synthesis. |
| `contract_certificates.py` | Positive fixed-parameter closure/liveness packet generation and local checking. |
| `contract_decisions.py` | Precedence-ordered exact / forward-prefix / reverse-lasso decision packets and mutation-resistant checking; negative directions may overlap. |
| `expansion.py` | Canonical reactive microstep graph expansion, finite path expansion, reset projection, and low-label erasure. |
| `regular_checks.py` | Deterministic complete finite families for the stateful algorithms, certificates, composition, and expansion. |
| `morphisms.py`, `omega_oracle.py` | Closed-form one-state binary special case and an algorithmically distinct whole-omega-language oracle. |
| `fairness.py`, `reference.py`, `certificates.py` | Debt monitors, finite reactive systems, graph queries, bisimulation, saturation, and generic live-set certificates. |
| `reproduce.py` | One-worker 22-stage campaign driver with a 3 GiB address-space limit. |
| `check_reproduction.py` | Semantic result comparator; resource files are excluded. |
| `test_artifact.py` | Forty-five unit, boundary, parser, relabeling, oracle, composition, certificate, endpoint, vector-mask, and expansion tests. |
| `theory.md` | Standalone definitions, theorem statements, proof architecture, worked example, and scope. |
| `literature.md`, `references.bib` | Closest-work comparison and bibliographic metadata used by the project. |
| `claim_evidence_ledger.csv` | Material-claim to theorem/code/result mapping and maturity. |
| `external_resources.csv` | Source, license/access, acquisition, integration, and claim provenance. |
| `results/` | Exact retained inputs, CSVs, summaries, certificates, mutations, and resource records. |

## Mathematical interface

Let `Sigma` be a finite nonempty alphabet with reset annotation `chi : Sigma -> {0,1}` and at least one reset symbol. A source word is fair at bound `B` and initial debt `a` when its annotated reset word never exceeds `B`. A transducer `T` has finite control, is deterministic and total on `Sigma`, and emits a nonempty binary block on every transition.

For target initial debt `t`, define:

```text
U_T(B,a,t) = sup { target_gap_t(T(x)) | x is source-fair }
R_T(B,a,t) = inf { target_gap_t(T(x)) | x is source-unfair }
```

with the infimum of the empty set equal to infinity. The exact target bounds are precisely

```text
U_T(B,a,t) <= C < R_T(B,a,t).
```

The safe ceiling is infinite exactly when the reachable source-safe control graph contains a cycle whose output blocks contain no target reset. Otherwise a block-profile longest-path recurrence computes it. The invalid floor is decided by a target-safe product with absorbing source overflow. If `Q` is the transducer state set and `L` the maximum block length, every finite-gap invalid behavior has an ultimately periodic witness below

```text
H = t + (((B + 2) * |Q|) + 2) * L.
```

This makes the floor a finite monotone search and yields finite lasso evidence.

## Interpretation and trust boundary

- The results quantify over infinite paths, not adversarial scheduler strategies. Strategy transfer would require a game model and observable-history relation.
- Bounded semantic steps are not processor time. The work makes no timing-channel or deployment-performance claim.
- The low-observation result is possibilistic trace equality. It is not probabilistic noninterference or cryptographic constant time.
- Coordinatewise fairness is sound only when every coordinate shares the same underlying expanded run. Independent per-coordinate expansions do not establish simultaneous schedulability.
- Finite enumeration validates the distributed implementation on declared domains. It is not a proof of the general theorems and not practical workload evidence.
- The certificate checkers are handwritten Python, not extracted from Rocq, Lean, Isabelle, or another proof assistant.
- No production compiler correspondence is implemented. Applying the theorem requires a separate two-sided run relation and justification of source annotations, target blocks, low labels, and viability.

No experiment or obligation named `F3` is defined in this repository, and no unrun `F3` result is claimed.

Substantive generative-AI assistance was used in research design, literature analysis, arguments, implementation, testing, finite experiments, interpretation, writing, and typesetting. The work has not received independent peer review or proof-assistant verification. Human authors must review the complete packet, accept accountability, and satisfy current publisher disclosure and authorship policies before external use. No public repository URL is asserted.
