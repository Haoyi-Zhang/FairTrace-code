# Regular fairness contracts: standalone mathematical note

This note restates the mathematical content implemented by the repository. It is independent of the manuscript directory. The proofs are conventional mathematical arguments reviewed inside the same AI-assisted workflow as the code; they are not proof-assistant checked.

## 1. Debt languages and annotated inputs

Let `N` include zero. A debt monitor with bound `B` has states `0,...,B` and absorbing overflow `bot`. On reset bit `0` it moves to zero. On miss bit `1` it increments, entering `bot` when the previous debt was `B`. For legal initial debt `a <= B`, define `L(B,a)` as the infinite binary words whose run never reaches `bot`.

For target initial debt `t` and an infinite binary word `y`, let `Gap_t(y)` be the supremum of the debts reached by the unbounded reset/increment recurrence. It is infinity when `y` has an all-one suffix or finite one-runs of unbounded length. Then

```text
y in L(C,t)  iff  t <= C and Gap_t(y) <= C.
```

Every accepted word has infinitely many zeros and a unique decomposition

```text
1^k0 0 1^k1 0 1^k2 0 ... .
```

It belongs to `L(B,a)` exactly when `k0 <= B-a` and every later `kj <= B`. The monitor is residual: if a finite prefix is safe and leaves debt `a'`, then every continuation is accepted from the original boundary exactly when it is accepted from debt `a'`.

Let `Sigma` be a finite nonempty alphabet and `chi : Sigma -> {0,1}` a reset annotation with at least one reset symbol. Define

```text
F^chi(B,a) = { x in Sigma^omega | chi(x) in L(B,a) }.
```

The existence of a reset symbol ensures that every finite source-safe prefix extends to an infinite source-fair word by repeating that symbol.

## 2. Deterministic non-erasing expanders

A deterministic finite-state non-erasing expander is

```text
T = (Q, q0, delta, lambda)
```

where `Q` is finite and nonempty, `delta(q,sigma)` is total and deterministic, and every output block `lambda(q,sigma)` is a nonempty binary word. Processing an input word concatenates the emitted blocks. Non-erasure ensures that every infinite input has an infinite output.

For fixed `(B,a,t,T)`, define two extrema:

```text
U_T(B,a,t) = sup { Gap_t(T(x)) | x in F^chi(B,a) }
R_T(B,a,t) = inf { Gap_t(T(x)) | x notin F^chi(B,a) }.
```

The supremum and infimum range over `N union {infinity}`; the infimum of an empty set is infinity.

### The exact-contract interval

For any target bound `C`,

```text
T^{-1}(L(C,t)) = F^chi(B,a)
```

if and only if

```text
U_T(B,a,t) <= C < R_T(B,a,t).
```

**Proof.** The left inclusion `F^chi(B,a) subseteq T^{-1}(L(C,t))` holds exactly when every source-fair input has target gap at most `C`, which is exactly `U <= C`. The reverse inclusion holds exactly when no source-unfair input has target gap at most `C`, which is exactly `C < R`. Combining the two gives the equivalence. Thus all exact integer bounds form one interval, possibly empty or unbounded above. This theorem is order-theoretic; the remaining work is to compute both endpoints and finite evidence.

## 3. Block profiles

For a nonempty binary block `u`, record:

- `z(u)`: whether `u` contains a zero;
- `p(u)`: number of leading ones before the first zero;
- `s(u)`: number of trailing ones after the last zero;
- `m(u)`: greatest run of ones strictly between two zeros;
- `|u|`: length.

For a zero-free block, only length is relevant. If incoming debt is `d`, then:

```text
peak(d,u) = d + |u|,       outgoing(d,u) = d + |u|    when z(u)=0;
peak(d,u) = max(d+p(u), m(u), s(u)),
outgoing(d,u) = s(u)                                      when z(u)=1.
```

This follows by splitting a resetful block at its zeros. The profile is closed under concatenation, so it is sufficient for endpoint synthesis.

## 4. Safe ceiling

Build the reachable source-safe control graph. Its vertices are pairs `(d,q)` with source debt `0 <= d <= B` and transducer state `q`. From `(d,q)` on symbol `sigma`, update the source debt using `chi(sigma)`; retain the edge only when it remains at most `B`, and update control with `delta`. Every reachable path spells a safe source prefix, and every such prefix extends to an infinite fair input.

Let `G1` contain exactly the edges whose output blocks are zero-free.

### Infinite case

`U_T(B,a,t) = infinity` if and only if `G1` has a reachable directed cycle.

**Proof.** Repeating a zero-free cycle emits at least one target miss per traversal because blocks are nonempty, so target debt grows without bound while the source remains safe. Conversely, if no such cycle exists, every zero-free suffix of a source-safe path is a path in a finite DAG and therefore has bounded total length; resetful blocks have finite profiles, so all target peaks are bounded.

A stem to the cycle plus the cycle itself is an ultimately periodic witness for the infinite ceiling.

### Finite case

Assume `G1` is acyclic. For each safe vertex `v`, let `D(v)` be the greatest target debt possible immediately before the next source symbol at `v`. Its possible origins are:

1. the initial debt `t`, propagated along zero-free edges from the initial vertex; or
2. the suffix `s(u)` of the last resetful block, propagated along subsequent zero-free edges.

Thus, in a topological order of `G1`, `D(v)` is the maximum of the initial seed, all resetful-predecessor suffix seeds, and all zero-free predecessor values plus block lengths. The safe ceiling is the maximum of `t` and every possible peak inside one outgoing block, using the profile equations above.

Every recurrence term is attainable by a source-safe prefix. Predecessor pointers yield a finite witness, and repetition of any reset-annotated symbol extends it to a fair infinite word without removing the already attained peak. Therefore the computed maximum equals the semantic supremum.

The graph has at most `(B+1)|Q|` vertices and `(B+1)|Q||Sigma|` edges. With explicit output blocks, cycle detection, topological sorting, and the recurrence are linear in this graph and the stored blocks. The dependence on a binary-encoded `B` is pseudo-polynomial.

## 5. Invalid floor

The floor asks when an unfair source input can nevertheless remain target-safe. For fixed target bound `C`, build a target-safe product with components:

```text
(absorbing source debt in {0,...,B,B+1}, transducer control, target debt in {0,...,C}).
```

Source overflow is represented by `B+1` and remains absorbing even after reset symbols; this records that the source word is already outside the prefix-closed fair language. A product edge exists only when processing the complete emitted target block remains at most `C`.

Finite product paths correspond exactly to finite input words whose outputs remain target-safe. Infinite product paths correspond exactly to infinite inputs in `T^{-1}(L(C,t))`.

A finite directed vertex is **live** when an infinite path begins there. Equivalently, live vertices are the greatest set in which every vertex has a successor in the set, or the vertices that can reach a directed cycle. Hence:

```text
there exists x notin F^chi(B,a) with T(x) in L(C,t)
```

if and only if the reachable target-safe product contains a live vertex whose source component is `B+1`.

### Completeness horizon

Let `L` be the maximum emitted block length and

```text
N = (B+2)|Q|,
H = t + (N+2)L.
```

If any source-unfair input has finite target gap, then there is an ultimately periodic source-unfair input `alpha beta^omega` with nonempty `beta`, whose target gap is at most `H`, and whose loop begins with a resetful output block.

**Proof architecture.** Choose a shortest path in the augmented source-control graph to a selected overflow control; it has at most `N-1` transitions. A finite target gap implies infinitely many target resets after overflow, so some resetful transition occurs infinitely often. Select that transition and a shortest return path to make a simple-control cycle of at most `|Q|` transitions. Repeating the cycle preserves absorbing source overflow. The prefix, first reset in the cycle, complete loop, and cross-boundary suffix/prefix each contribute at most the explicit block-length budget in `H`. The construction need not preserve the original counterexample or minimize its gap; it only normalizes existence below a finite bound.

Therefore:

- if the fixed-bound product at `H` has no live overflow vertex, `R_T(B,a,t)=infinity`;
- otherwise `R_T(B,a,t)` is the least `C` in `[t,H]` with a live overflow vertex.

The predicate is monotone in `C`, so binary search finds the least true bound. Combining this with the safe-ceiling algorithm and the interval theorem is a complete decision procedure.

## 6. Certificates and counterexamples

Discovery and checking are separated.

### Positive exact-contract packet

For fixed `(B,a,C,t,T)`, an exact packet contains:

1. **Source-safe closure.** Every reachable state with source debt at most `B` and target debt at most `C`, parent/distance data proving reachability, and closure under every source-safe symbol. Any omitted target-safe successor or target overflow rejects the packet.
2. **Target-safe closure.** Every reachable state in the target-safe product, again with local parent evidence and complete reconstructed successors.
3. **Live/dead partition.** Each live vertex names a successor inside the live set; every dead vertex has a natural-number rank strictly decreasing along every dead-to-dead edge, and no dead vertex may point to a live vertex. This proves exactly which vertices have infinite continuation.
4. **No live overflow.** Every source-overflow vertex is dead.

These finite checks establish preservation and reflection for the fixed parameters without trusting the synthesizer's reported endpoints.

### Complete negative decisions

If a fixed candidate is inexact, one of two directional witnesses exists:

- **source-valid / target-invalid:** a finite source-safe prefix whose emitted target block overflows `C`; repeating a reset source symbol extends it to a source-fair infinite counterexample;
- **source-invalid / target-valid:** a finite stem reaching absorbing source overflow plus a nonempty target-safe product loop, yielding a source-unfair, target-fair lasso.

Thus every fixed candidate admits a complete precedence-ordered decision: exact candidates have a positive certificate; an inexact candidate has a forward prefix whenever preservation fails and a reverse lasso whenever reflection fails. The two negative witnesses can coexist, so the generator uses the canonical priority `exact`, then `forward`, then `reverse`. The checker reconstructs all semantic steps from the transducer and parameters rather than trusting serialized successor claims.

## 7. Composition

For deterministic non-erasing expanders `T1 : Sigma -> Gamma^+` and `T2 : Gamma -> {0,1}^+`, their ordinary finite-state composition carries both controls and feeds every symbol emitted by `T1` through `T2`. Non-erasure is preserved.

If `T1` exactly maps source fairness `(B,a)` to an intermediate contract `(C,t)`, and `T2` exactly maps that intermediate language to `(D,u)`, then the composite exactly maps `(B,a)` to `(D,u)`:

```text
(T2 o T1)^{-1}(L(D,u))
= T1^{-1}(T2^{-1}(L(D,u)))
= T1^{-1}(L(C,t))
= F^chi(B,a).
```

This is equality of complete languages, not a heuristic addition of scalar dilation factors. The implementation checks extensional block composition and reruns the independent oracle on composite contracts.

## 8. One-state binary special case

A binary block morphism maps source reset `0` to nonempty block `u` and source miss `1` to nonempty block `v`. The general endpoint algorithms specialize to closed forms.

For source bound `B >= 2`, exactness forces `v = 1^d` for some positive `d`; a reset inside `v` makes allowed and forbidden adjacent miss patterns indistinguishable to a finite target gap threshold. Let `p,s,m` be the leading-one, trailing-one, and maximum internal-one profile of resetful `u`. Then the exact bounds are those satisfying

```text
max(m, dB+p+s, d(B-a)+p+t) <= C
C <= min(d(B+1)+p+s-1, d(B-a+1)+p+t-1).
```

The semantic invalid floor must retain baseline demands even when this interval is empty.  It is

```text
R_init = max(m, p+s, t + d*(B-a+1) + p)
R_int  = max(m, t+p, s + d*(B+1) + p)
R      = min(R_init, R_int).
```

The first branch is attained by an initial violating gap, and the second by a violating gap after a reset.  Only under the nonempty-interval premises do the baseline terms become dominated and `R` simplify to one plus the smaller syntactic upper endpoint.  The identity map at `B=a=0,t=2` and `u=0110,v=1,B=a=t=0` both have true `R=2`, although that invalid simplification gives `1`; both exact intervals are empty.

Bounds zero and one have additional resetful-miss cases and are handled separately in the classifier. Canonical carried debt is `t = da+s`; a canonical target bound has the form `C = dB+p+s+slack` with `0 <= slack < d`, subject to the internal-gap gate. These formulas are a strict special case: a stateful or larger-alphabet expander may distinguish symbols with the same reset annotation and emit different blocks while finite control is carried across source boundaries.

## 9. Canonical reactive microstep expansion

A finite source reactive system has states, an initial state, and edges carrying:

- an operation class `sigma` used by the expander;
- a source low label `ell`, possibly erasure `epsilon`;
- source and target states.

A tracked action induces the source reset annotation: reset when the action is disabled or served; miss when it is enabled and another action is selected.

The canonical expansion creates boundary states `[v,q]` consisting of a source state and transducer control. Selecting a source edge at a boundary computes the block emitted by `T(q,sigma)` and creates a deterministic chain of that many target microsteps. Parallel source edges are retained by stable edge identity, and every generated target edge records its source-edge identity and chain position. The first `k-1` microsteps carry low erasure; the last carries the source low label and ends at `[v',q']`.

### Run bijection

Every source edge identity determines exactly one nonempty target chain. Every intermediate state has exactly one successor and belongs to exactly one identified chain. Consequently:

- expanding identified source edges gives one infinite target edge run;
- every infinite target run visits boundary states infinitely often (chains are finite and nonempty);
- parsing the complete target edge sequence by chain identity recovers a unique source edge run.

These two operations are inverse. Boundary-state pairs alone are not a unique code: in a one-state identity expansion, distinct reset-zero and reset-one self-loops yield the same constant boundary-state sequence but different edge runs. For every finite prefix, the target reset word is exactly the transducer output on the source operation-class word, and erasing target `epsilon` labels yields exactly the source low sequence.

If `(B,a,C,t,T)` is an exact word contract, the run bijection restricts to a bijection between source-fair and target-fair runs. Paired runs have identical low observations. Therefore their fair observation sets are equal.

### Extensional consequences

Equality of fair observation sets preserves:

- viability (nonemptiness);
- existential / may predicates;
- universal predicates;
- nonvacuous must predicates;
- visible-event eventuality and recurrence defined on the complete low sequence;
- equality of secret-indexed low observation sets (possibilistic low-trace noninterference).

The theorem does **not** preserve predicates about exact target microstep positions, physical time, or instruction cost. It does not synthesize a scheduler strategy: a strategy theorem would require a game model and an account of the histories visible to each player.

For several obligations, one expanded run may carry a vector of reset bits. Coordinatewise exact contracts are a sufficient condition because all coordinates refer to the same chain and boundary factorization. The converse fails: equality of an intersection does not imply equality of each factor. With two source coordinates both equal to `L(1,0)`, vector output `(0,x)`, and target bounds `(0,1)` at zero debt, the vector contract is exact while its first scalar contract is not. Expanding coordinates independently with different chains would not prove simultaneous fairness.

## 10. Worked stateful contract

Let `Sigma={r,m,n}` with annotations `chi(r)=0` and `chi(m)=chi(n)=1`. Let transducer states be `A,B`, initially `A`:

| state | `r` | `m` | `n` |
|---|---|---|---|
| `A` | `(B,110)` | `(B,11)` | `(B,011)` |
| `B` | `(B,01)` | `(A,110)` | `(A,110)` |

Take source bound `B=2`, source debt `a=1`, and target debt `t=1`. Endpoint synthesis gives

```text
U = 3,  R = 4,
```

so `C=3` is the unique exact target bound.

The one-symbol fair prefix `r` emits `110`, reaching target debt three before resetting, so `U>=3`; the zero-free subgraph is acyclic and the profile recurrence bounds all safe peaks by three. For the floor, the lasso with stem `nmrr` and loop `r` overflows the source on the second miss but emits

```text
011 110 110 01 (01)^omega,
```

whose maximum target debt from one is four. The target-safe product at `C=3` has no live overflow vertex, so `R=4`. This example cannot be represented by a morphism of the reset bit alone because `m` and `n` share annotation one but emit different blocks. In either control state they have the same next state (`A` to `B`, and `B` to `A`), so substituting one class for the other leaves the control trajectory unchanged; only the block emitted at `A` changes.

## 11. Evidence and limitations

The implementation compares both endpoints with an independent fixed-bound omega-language product oracle on complete declared finite families. It also checks positive certificates, all three decision forms, deliberate packet mutations, transducer composition, and finite paths through canonical reactive expansions. Those checks are designed to expose off-by-one, reachability, state-indexing, closure, and parser errors. They do not prove the general theorems or establish practical workload diversity.

The work excludes erasing outputs, nondeterministic transducers, probabilistic schedulers, unrestricted fairness, wall-clock timing, production compiler passes, real programs, and human evidence. Applying the result in a compiler proof requires a separate two-sided source/target run relation, correct operation-class annotations, complete low-label preservation, and a viability argument when a nonvacuous universal property is claimed.
