# Literature comparison and writing calibration

## Scope and method

This record supports the manuscript's positioning; it is not a priority claim or an independent novelty review.  Forty scholarly works are cited in the paper.  The set was selected by relevance to bounded/finitary fairness, promptness, regular transductions, reactive refinement, trace-set security, liveness reasoning, and independently checkable evidence.  Metadata were checked against DOI/publisher records or author/institutional copies, and the comparison below was made from substantive article text rather than titles alone.

For the twelve TOPLAS calibration papers, `bibliography scale` is a deliberately coarse full-text band rather than a fabricated exact count: **compact** means fewer than about 30 entries, **moderate** about 30--59, and **extensive** about 60 or more.  The band is used only to calibrate exposition.  Article lengths come from the published citation or publisher metadata.  Figure/table comments describe their argumentative role, not a visual score.

## Closest technical pressure

### Nondeterministic semantics and compiler proofs

**Omnisemantics: Smooth Handling of Nondeterminism** (`omni`) develops inductive and coinductive omni judgments, relates them to ordinary semantics, and applies them to type safety and compiler proofs.  Its compiler case studies concern terminating programs, and the article explicitly leaves full correctness for programs that may crash, diverge, or perform infinitely many I/O interactions to future work.  It therefore rules out presenting nondeterminism itself, forward proof structure, or partial-correctness omnisemantics as new here.  The retained contribution is a small arithmetic interface for one reactive fairness filter under a finite-state step expander.

**Smooth, Integrated Proofs of Cryptographic Constant Time for Nondeterministic Programs and Compilers** (`constanttime`) already combines nondeterministic compiler reasoning with leakage traces.  Its semantics and compiler theorem are termination-oriented; it explicitly identifies nontermination and infinite reactivity as outside the stated model.  Consequently, merely attaching low labels to an omni judgment would not be a contribution.  The manuscript instead proves a conditional possibilistic low-trace corollary from an exact fairness contract plus a separately established run correspondence, and makes no cryptographic constant-time claim.

**Foundational Verification of Running-Time Bounds for Interactive Programs** (`metrics`) verifies costs for interactive programs under a top-level event loop.  It is the main warning against interpreting an abstract service-debt counter as physical time.  The present monitor counts semantic steps only and has no processor, cache, scheduler-cost, or wall-clock model.

### Fairness, promptness, and liveness

**Finitary Fairness** (`finitary`) establishes the finitary/bounded view of fairness and studies it at transition-system level.  **Promptness in omega-Regular Automata** (`promptness`), **From Liveness to Promptness** (`livenesspromptness`), and **Promptness and Bounded Fairness in Concurrent and Parameterized Systems** (`bounded`) place explicit bounds in automata, temporal logic, and concurrent verification.  These works prevent any claim that bounded response or granularity sensitivity is new.  The narrower result here is the complete interval of target reset bounds induced by a fixed deterministic, non-erasing expander with carried initial debt.

**Fair Operational Semantics** (`fos`) treats fairness-preserving program transformations using fair behaviors and simulations.  **Fair Simulation** (`fairsimulation`) gives a game-aware qualitative refinement relation.  **TaDA Live** (`tadalive`), **Lilo** (`lilo`), and **Lawyer** (`lawyer`) support richer compositional liveness reasoning with obligations, interference, ownership, and abstraction.  The scalar reset contract in this project neither replaces those logics nor synthesizes a scheduler strategy; it may be used only after a surrounding proof has supplied the relevant run relation and fairness annotation.

### Regular transductions and quantitative word models

**MSO Definable String Transductions and Two-Way Finite-State Transducers** (`msotransductions`) and **Expressiveness of Streaming String Transducers** (`streamingtransducers`) provide broad finite-string transduction characterizations.  **Regular Transformations of Infinite Strings** (`regularomega`) supplies the closest omega-word transformation baseline.  The project's transducer is intentionally weaker: deterministic, one-way, non-erasing, and block emitting.  No new maximal transducer class or logical characterization is claimed.

**Regular Cost Functions** (`regularcost`) and **Quantitative Languages** (`quantitative`) already organize numerical properties of words.  The gap score used here is a simple regular cost.  The supported delta is the two-endpoint exact-preimage interval for this particular bounded-reset language, together with specialized finite algorithms and witnesses.

### Refinement, open systems, and composition

**The Temporal Logic of Actions** (`tla`), **The Existence of Refinement Mappings** (`refinementmaps`), and **Forward and Backward Simulations--I** (`simulations`) establish behavior-based specification and refinement principles.  **Alternating Refinement Relations** (`alternatingrefinement`), **Interface Automata** (`interfaceautomata`), **Module Checking** (`modulechecking`), and **An Automata-Theoretic Approach to Modular Model Checking** (`modularautomata`) distinguish component and environment choices.  These sources are why the paper labels its may/must statements as path-set properties and explicitly excludes game-strategy synthesis.

**CompCert** (`compcert`) is the realistic verified-compiler baseline.  **Trace-Relating Compiler Correctness and Secure Compilation** (`trcc`) demonstrates why source and target traces may need an explicit relation.  **CSim2** (`csim2`) provides a recent simulation-based compositional verification framework.  The canonical microstep expansion in the manuscript is only an administrative graph construction; it is not a production compiler correctness theorem.

### Infinite behavior, observations, and evidence

**Interaction Trees** (`itrees`) and **Coinductive Big-Step Operational Semantics** (`coinductive`) supply established representations and proof techniques for infinite computation.  **Hyperproperties** (`hyperproperties`) and **Verifying Asynchronous Hyperproperties in Reactive Systems** (`asynchronous`) cover trace-set and asynchronous relational properties far beyond the paper's possibilistic equality corollary.  **Recognizing Safety and Liveness** (`safetyliveness`) separates finite bad prefixes from infinite continuation obligations.  **Proof-Carrying Code** (`pcc`) supplies the general producer/consumer architecture for independently checked evidence; the project's JSON packets are a much smaller instance with a handwritten Python checker, not a proof-carrying-code system.

## Twelve-paper TOPLAS pattern matrix

All twelve papers below were used as full-paper, same-venue calibration.  The matrix records the recurring article pattern requested by the research brief: motivating problem, general principle, proof or performance result, practical evidence, section narrative, bibliography scale, and the role of figures/tables.

| TOPLAS paper | Pages | Motiving problem and general principle | Proof/performance and practical evidence | Section/narrative pattern | Bibliography scale | Figure/table role and lesson carried forward |
|---|---:|---|---|---|---|---|
| *Omnisemantics* (`omni`) | 43 | Nondeterministic semantic proofs are cumbersome; quantify over outcome sets in one judgment | Coq-checked metatheory plus type-safety and compiler case studies | Four concrete frictions -> judgment definitions -> equivalences -> case studies -> related work/appendices | Moderate | Inference-rule figures and case-study diagrams carry definitions; the present paper likewise separates semantic theorem from artifact counts |
| *Finitary Fairness* (`finitary`) | 24 | Classical fairness permits unbounded delay; use a finitary/bounded condition | Characterizations and consequences for transition systems | Scheduler phenomenon -> exact definition -> relation to classical fairness -> results | Moderate | Few visuals; definitions and theorem sequencing do the work, motivating an early qualitative-versus-bounded comparison here |
| *Trace-Relating Compiler Correctness* (`trcc`) | 48 | Equality of traces is too rigid for compilation; state an explicit relation | General theorems connecting compiler conditions, trace relations, and security properties | Counterexamples -> relational framework -> property transport -> secure-compilation consequences | Extensive | Commuting diagrams and summary tables distinguish relations from consequences; the paper mirrors that separation |
| *TaDA Live* (`tadalive`) | 134 | Fine-grained blocking termination crosses abstraction boundaries; use layered obligations | Large semantic soundness development and detailed examples | Obligation intuition -> logic/model -> soundness -> derived rules -> case studies -> appendices | Extensive | Protocol/state diagrams and rule tables serve proof navigation rather than decoration; long proof details remain in appendices here |
| *Transition Predicate Abstraction and Fair Termination* (`predfair`) | 40 | Termination under fairness needs both finite abstraction and progress reasoning | Predicate abstraction, fair-termination criteria, implementation/evaluation evidence | Problem -> transition abstraction -> fairness/termination theorem -> algorithm -> experiments | Moderate | Algorithm and evaluation tables keep safety abstraction separate from liveness evidence; the endpoint/checker split follows that discipline |
| *Abstract Interpretation of Reactive Systems* (`abstractreactive`) | 39 | Abstraction should preserve existential and universal reactive properties | Preservation/optimality theorems with worked abstractions | Reactive-property taxonomy -> abstract domain/model -> preservation -> optimality -> examples/related work | Moderate | Lattice/model illustrations explain precision; this paper states exactly which observation predicates its construction preserves |
| *Model Checking and Abstraction* (`mcabstraction`) | 31 | State explosion blocks temporal verification; build property-preserving abstractions | Abstraction theorems and model-checking examples | Concrete/abstract systems -> preservation -> construction -> examples -> limitations | Moderate | Transition-system figures expose abstraction success and failure; negative boundary examples play the analogous role here |
| *Model Checking and Modular Verification* (`modularverification`) | 29 | Whole-system model checking loses modular structure; model module/environment interaction | Modular verification theorems and illustrative systems | Module semantics -> composition/environment assumptions -> algorithm -> examples | Moderate | Module diagrams make environment boundaries explicit; the manuscript therefore isolates coverage and strategy assumptions |
| *Composing Specifications* (`composingspecs`) | 60 | Safety and liveness assumptions interact under composition; make composition rules semantic | General composition theorems with specification examples | Behavior model -> safety/liveness closure -> composition -> examples/proof details | Extensive | Temporal/behavior constructions dominate; the carried debt and intermediate contract are made explicit rather than treated as metadata |
| *Compositional Specification and Verification of Distributed Systems* (`compositionaldistributed`) | 45 | Distributed components need checkable interfaces; formulate compositional proof rules | Sound compositional rules and protocol examples | Specification language -> interface conditions -> composition theorem -> examples | Moderate | Component diagrams and proof-rule tables connect interface to theorem; the paper lists six concrete integration obligations |
| *An Automata-Theoretic Approach to Modular Model Checking* (`modularautomata`) | 42 | Open modules are checked against all environments; reduce to automata games | Automata reduction, complexity results, and examples | Module trees -> automata construction -> correctness -> complexity -> comparison | Moderate | Automata figures clarify quantifier alternation; the current work explicitly refuses to infer game strategies from existential paths |
| *CSim2* (`csim2`) | 46 | Concurrent systems need scalable top-down compositional simulation | Mechanized framework plus case studies and measured verification evidence | Framework -> soundness -> decomposition workflow -> implementation/case studies -> limits | Moderate | Architecture diagrams and evidence tables separate theorem from tool results; the artifact tables here report exact finite domains without treating them as the general proof |

The matrix does not imply that all twelve papers prove the same kind of result.  It establishes the same-venue calibration set and explains what was learned from each paper rather than citing them as decoration.

## Influential and adjacent-venue calibration

### Five influential foundations

| Work | Calibration role |
|---|---|
| CompCert (`compcert`) | Separate a mathematically proved compiler theorem from implementation/evaluation claims; do not call an administrative expansion a verified compiler. |
| Hyperproperties (`hyperproperties`) | State precisely whether a property concerns individual traces or sets of traces; the noninterference corollary is possibilistic set equality only. |
| Forward and Backward Simulations (`simulations`) | Keep two behavioral directions explicit and avoid deriving reflection from a one-sided simulation. |
| Coinductive Big-Step Operational Semantics (`coinductive`) | Treat infinite behavior with established proof techniques rather than advertising coinduction itself as new. |
| Recognizing Safety and Liveness (`safetyliveness`) | Separate finite bad-prefix evidence from infinite-continuation evidence in definitions, proofs, and certificates. |

### Five adjacent recent papers

| Work | Novelty pressure |
|---|---|
| PLDI 2025 constant-time omnisemantics (`constanttime`) | Nondeterminism, compiler contracts, and leakage are already integrated for terminating semantics. |
| CPP 2026 interactive running-time verification (`metrics`) | Interactive event-loop costs are already machine-checked; semantic debt is not physical time. |
| PLDI 2023 Fair Operational Semantics (`fos`) | Fair behaviors and fairness-preserving transformations already have a general operational treatment. |
| OOPSLA 2025 Lilo (`lilo`) | Higher-order relational liveness reasoning already composes thread-local simulations. |
| OOPSLA 2026 Lawyer (`lawyer`) | Modular obligation-based liveness reasoning already handles weak-fair refinement in a rich logic. |

## Bibliography coverage and count

The paper cites **40 unique scholarly works**, all referenced in the manuscript text or comparison table.  The inventory covers:

- 14 TOPLAS articles, including the 12-paper full-text calibration set plus TLA and the classical finite-state verification article;
- foundational and recent bounded-fairness/promptness sources;
- finite- and infinite-string transduction and quantitative-language sources;
- simulation, open-system, interface, compiler-correctness, and compositional-verification sources;
- coinductive/infinite computation, trace-set security, and certificate-consumer architecture; and
- the five adjacent 2023--2026 papers most directly constraining the claim.

Forty is not presented as a magic venue threshold.  It is the smallest retained set after removing structural papers that did not support a claim and adding papers needed to close identifiable gaps.  Every retained entry has a DOI or stable source record in `external_resources.csv`; no citation was added only to increase the count.

## Supported delta and unresolved novelty risk

The literature-supported delta is deliberately narrow:

1. deterministic finite-state, non-erasing step expanders over a reset-annotated finite alphabet;
2. exact target budgets form one integer interval for each source bound and pair of initial debts;
3. both endpoints have finite algorithms, including an explicit invalid-floor completeness horizon;
4. exact and inexact fixed candidates have locally checkable evidence, with two negative directions that may overlap and a documented reporting precedence;
5. exact contracts compose under deterministic transducer composition; and
6. one canonical microstep construction turns the word contract into equality of fair low-observation sets.

No reviewed source found in this calibration states this exact combination.  That remains a bounded gap statement, not proof of priority, significance, or acceptance-worthiness.  The general proofs and the closest-work claim still require independent expert review before external submission.
