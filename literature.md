# Related theory and the bounded contract

This note records scientific comparisons for the current reset-language
interface. It does not certify priority, fulltext coverage of every reference,
or venue acceptance.

## Fairness conventions and quantifiers

Jacobs, Sakr and Zimmermann, *Promptness and Bounded Fairness in Concurrent
and Parameterized Systems* (VMCAI 2020), define global bounded fairness by
movement of every process in each bounded window; local bounded fairness
additionally assumes unconditional fairness. Their prompt property orders
quantifiers as `forall b exists k forall run`. The present interface fixes
`(B,a,t,T)` and determines each `C` by exact equality for all input words.
Its disablement/service reset convention is not unconditional process
movement: a disabled tracked action can reset without ever moving. Their
bounded-stutter and cutoff results are a baseline, not this theorem.
Primary author copy: https://people.cs.aau.dk/~mzi/publications/parapara.pdf
(Sections 3.1--4.1 were compared for these statements).

## Certifying and quantitative finite-state methods

Namjoshi, *Certifying Model Checkers* (CAV 2001, LNCS 2102, pp. 2--13),
uses invariant/rank proofs for mu-calculus/parity-game obligations and
certifies both success and failure. The live-successor/dead-rank format here
handles an explicit safety product and existential infinite continuation.
Neither local ranks nor producer/consumer separation is new here.
Primary author copy: https://kedar-namjoshi.github.io/papers/Namjoshi-CAV-2001.pdf

Linear graph algorithms are established (Tarjan, SIAM J. Comput. 1(2),
146--160, 1972, DOI 10.1137/0201010). The implemented predecessor queue and
witness links realize a stated cost bound; they do not introduce a new
fairness model. The independent fixed-bound product oracle remains
algorithmically separate. General regular-cost, quantitative-language and
omega-transduction theories cited in the manuscript are broader than this
deterministic non-erasing block interface.

## Supported mathematical interface

The written, unmechanized proofs establish:

1. exact reset-preimage bounds form one interval for fixed source/debt/control;
2. zero-free cycles and profile longest paths compute the safe ceiling;
3. a finite lasso horizon and monotone search compute the invalid floor;
4. fixed exact and inexact contracts admit local certificates or directional
   witnesses, with overlapping negative directions and forward-first reporting;
5. exact intermediate contracts compose; and
6. canonical identified microstep chains transport fair low-observation sets.

The run correspondence and annotation adequacy are separate integration
premises. The current code supplies no production compiler, scheduler game,
probabilistic/physical-time guarantee, generic cost-function theory or
foundational proof kernel. Finite campaigns and same-input implementation
cost checks validate declared authored instances, not mathematical novelty.
Independent expert novelty/soundness review remains open. See the manuscript
bibliography and scientific claim/evidence map for the broader source families.
