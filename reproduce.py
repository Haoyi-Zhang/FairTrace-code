"""One-worker, deterministic finite validation. No proof-assistant claims.

Run from this directory: python3 reproduce.py --output reproduced
Each stage can also be executed independently with --stage NAME.
"""
from __future__ import annotations
import argparse
import csv
import itertools as it
import json
from pathlib import Path
import resource
import time

import fairness as f
import reference as ref
import certificates as cert
import extended_checks as extended
import regular_checks as regular

BASE_STAGES = ('expansion', 'monitor', 'graphs', 'bisimulation', 'saturation', 'boundaries')
REGULAR_STAGES = ('regular-one-bit', 'regular-blocks', 'regular-annotated',
                  'regular-certificates', 'regular-decisions', 'regular-composition',
                  'annotated-composition', 'canonical-expansions', 'annotated-expansions')
STAGES = (BASE_STAGES + tuple(f'classify{b}' for b in range(5)) +
          ('public-budget','composition') + REGULAR_STAGES)

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n', encoding='utf-8')

def write_csv(path, rows):
    if not rows:
        raise ValueError('refusing empty result table')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as stream:
        w = csv.DictWriter(stream, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def expansion(out):
    rows = []; aligned_rows = []; count = 0; negatives = 0
    for b in range(3):
        for r in range(1, 4):
            words = ref.words_up_to(r)
            zeros = tuple(w for w in words if 0 in w)
            maximum = -1; witness = None; cases = 0
            for blocks in it.product(zeros, *([words] * b), zeros):
                word = tuple(it.chain.from_iterable(blocks))
                value = f.longest_miss(word)
                assert value == ref.longest_run_by_substrings(word)
                assert value <= f.transported_bound(b, r)
                cases += 1
                if value > maximum:
                    maximum = value; witness = blocks
            assert maximum == f.transported_bound(b, r)
            negative = maximum > f.transported_bound(b, r, aligned=True)
            negatives += negative; count += cases
            rows.append(dict(bound=b, expansion=r, cases=cases, maximum=maximum,
                             predicted=f.transported_bound(b, r),
                             endpoint_formula_invalid=int(negative),
                             witness=json.dumps(witness)))
            for endpoint in ('first', 'last'):
                zw = tuple(w for w in zeros if w[0 if endpoint == 'first' else -1] == 0)
                maximum2 = -1; cases2 = 0
                for blocks in it.product(zw, *([words] * b), zw):
                    v = f.longest_miss(it.chain.from_iterable(blocks))
                    maximum2 = max(maximum2, v); cases2 += 1
                    assert v <= f.transported_bound(b, r, aligned=True)
                assert maximum2 == f.transported_bound(b, r, aligned=True)
                aligned_rows.append(dict(bound=b, expansion=r, endpoint=endpoint,
                                         cases=cases2, maximum=maximum2,
                                         predicted=f.transported_bound(b, r, aligned=True)))
    identities = 0
    for b, r, s, aligned in it.product(range(4), range(1, 5), range(1, 5), (False, True)):
        assert f.transported_bound(f.transported_bound(b, r, aligned), s, aligned) == f.transported_bound(b, r*s, aligned)
        identities += 1
    write_csv(out/'expansion.csv', rows); write_csv(out/'aligned-expansion.csv', aligned_rows)
    return dict(cases=count, cells=len(rows), negative_cells=negatives,
                aligned_cases=sum(x['cases'] for x in aligned_rows),
                aligned_cells=len(aligned_rows), composition_identities=identities)

def monitor(out):
    alphabet = ((frozenset({0}), 0), (frozenset({1}), 1),
                (frozenset({0, 1}), 0), (frozenset({0, 1}), 1))
    rows = []; total = 0
    for b in range(4):
        for length in range(7):
            accepted = cases = 0
            for events in it.product(alphabet, repeat=length):
                debt = (0, 0)
                for ready, chosen in events:
                    debt = f.update(debt, ready, chosen, b)
                    if debt is None: break
                answer = debt is not None
                assert answer == ref.window_accepts(events, 2, b)
                accepted += answer; cases += 1
            total += cases
            rows.append(dict(bound=b, length=length, cases=cases, accepted=accepted))
    write_csv(out/'monitor.csv', rows)
    return dict(event_words_times_bounds=total, cells=len(rows), alphabet_size=4, max_length=6)

def small_systems():
    universe = tuple(it.product(range(2), range(2), range(2)))
    for mask in range(1 << len(universe)):
        edges = tuple(e for j, e in enumerate(universe) if mask & (1 << j))
        system = f.System((0, 1), 2, edges)
        if system.is_total(): yield mask, system

def graphs(out):
    rows = []; props = []; inputs = []; certificates = []; vertices = 0; answers = 0
    for mask, sys in small_systems():
        inputs.append(dict(id=f'm{mask:03d}', observations=list(sys.observations),
                           actions=sys.actions, edges=sys.edges))
        for b in range(4):
            p = f.monitored(sys, b); vertices += len(p.graph)
            c = cert.generate(p.graph)
            assert cert.check(p.graph, c)
            exact = ref.infinite_vertices(p.graph)
            assert f.live(p.graph) == exact == frozenset(c['live'])
            rows.append(dict(model=f'm{mask:03d}', bound=b, vertices=len(p.graph),
                             edges=sum(map(len,p.graph)), live_vertices=len(exact),
                             initial_0_live=int(p.initials[0] in exact),
                             initial_1_live=int(p.initials[1] in exact), certificate_valid=1))
            if mask in (17, 51, 85, 255) and b in (0, 1):
                name=f'm{mask:03d}-b{b}.json'
                write_json(out/'certificates'/name, dict(graph=p.graph, certificate=c))
                certificates.append(name)
            for goalmask in range(4):
                goal = frozenset(i for i,(s,d) in enumerate(p.states) if goalmask & (1 << s))
                actual = f.modes(p.graph, goal); expected = ref.queries(p.graph, goal)
                assert actual == expected
                answers += 4 * len(p.graph)
                avoid = frozenset(range(len(p.graph))) - goal
                induced = tuple(tuple(t for t in row if t in avoid) if s in avoid else ()
                                for s,row in enumerate(p.graph))
                ac = cert.generate(induced)
                assert cert.check(induced, ac)
                assert frozenset(ac['live']) == f.live(p.graph, avoid)
                row = dict(model=f'm{mask:03d}', bound=b, goal_mask=goalmask)
                for mode in ('viable','may_eventually','must_eventually','must_recur'):
                    for s,i in enumerate(p.initials): row[f'{mode}_{s}'] = int(i in actual[mode])
                props.append(row)
    write_json(out/'small-models.json', dict(states=2, actions=2, total_required=True,
                                           bounds=list(range(4)), goal_masks=list(range(4)), models=inputs))
    write_csv(out/'graphs.csv', rows); write_csv(out/'properties.csv', props)
    return dict(base_systems=len(inputs), monitored_systems=len(rows), product_vertices=vertices,
                property_scenarios=len(props), boolean_answers_compared=answers,
                main_certificates=len(rows), avoiding_certificates=len(props),
                standalone_packets=certificates)

def bisimulation(out):
    rows = []; accepted = 0; lifted = 0; nontrivial = 0
    pairs = tuple(it.product(range(2), repeat=2))
    relations = tuple(frozenset(p for i,p in enumerate(pairs) if mask & (1<<i)) for mask in range(16))
    for mask, sys in small_systems():
        for obs in it.product(range(2), repeat=2):
            s = f.System(obs, sys.actions, sys.edges)
            products = [f.monitored(s,b) for b in range(4)]
            systems = [f.System(p.observations, s.actions, p.labelled_edges) for p in products]
            for ri, rel in enumerate(relations):
                if not f.bisimulation(s,s,rel): continue
                accepted += 1
                nontrivial += any(x != y for x,y in rel)
                for p, sp in zip(products, systems):
                    lr = f.lifted_relation(p,p,rel)
                    assert f.bisimulation(sp,sp,lr)
                    lifted += 1
            rows.append(dict(model=f'm{mask:03d}', observation_0=obs[0],observation_1=obs[1],
                             accepted_relations=sum(f.bisimulation(s,s,r) for r in relations)))
    write_csv(out/'bisimulation.csv', rows)
    return dict(candidate_relations=len(rows)*16, accepted_relations=accepted,
                relations_containing_distinct_states=nontrivial, lifted_checks=lifted,
                scope='self-relations on all total two-state two-action systems and binary state observations')

def saturation(out):
    rows = []; saturated = 0
    subsets = [frozenset(i for i in range(4) if mask & (1<<i)) for mask in range(16)]
    for projection in it.product(range(2), repeat=4):
        for fm, fair in enumerate(subsets):
            sat = all(projection[i] != projection[j] or ((i in fair) == (j in fair))
                      for i,j in it.product(range(4),repeat=2))
            images = {}; factors = True
            for x in subsets:
                key = frozenset(projection[i] for i in x)
                value = frozenset(projection[i] for i in x & fair)
                if key in images and images[key] != value: factors = False
                images[key] = value
            assert sat == factors
            saturated += sat
            rows.append(dict(projection=''.join(map(str,projection)), fair_mask=fm,
                             saturated=int(sat), factors=int(factors)))
    write_csv(out/'saturation.csv', rows)
    return dict(cases=len(rows), saturated=saturated, nonsaturated=len(rows)-saturated,
                run_atoms=4, observation_atoms=2, subsets_per_case=16)

def boundaries(out):
    rows=[]
    def record(name, description, correct, false_claim):
        assert correct != false_claim
        rows.append(dict(case=name, witness=description, correct=json.dumps(correct),
                         rejected_claim=json.dumps(false_claim), detected=1))
    record('endpoint-switch', 'B=0,r=2; reset blocks 01|10', f.longest_miss((0,1,1,0)), f.transported_bound(0,2,True))
    record('erase-resets', '(01)^omega; erase each 0 block; image 1^omega', False, True)
    record('unbounded-blocks', '0 1 0 11 0 111 ... has no finite miss bound', False, True)
    # Two reset periods have the same erased low word x^omega, but different B=1 admissibility.
    record('observation-before-filter', 'periods 01 and 0110; erase 1, map 0 to x; B=1',
           f.longest_miss((0,1,1,0)*3) <= 1, f.longest_miss((0,1)*3) <= 1)
    one=f.System((0,),1,((0,0,0),)); both=f.tagged_interleaving(one,one)
    p0=f.monitored(both,0); p1=f.monitored(both,1)
    assert f.live(f.monitored(one,0).graph)
    record('local-to-global-fairness', 'two individually B=0 single-action loops; tagged interleaving B=0',
           bool(f.live(p0.graph)), True)
    assert p1.initials[0] in f.live(p1.graph)
    record('empty-fair-must', 'same two-loop product at B=0; must(True)=viable AND all(True)',
           p0.initials[0] in f.modes(p0.graph,frozenset(range(len(p0.graph))))['must_eventually'], True)
    debt=f.update((0,1),frozenset({0}),0,1)
    record('disable-reset', 'debt=(0,1), enabled={0}, serve 0, B=1', debt, (0,1))
    debt=f.update((0,0),frozenset({0,1}),0,1)
    record('reject-at-equality', 'debt=(0,0), enabled={0,1}, serve 0, B=1', debt, None)
    debt=f.update((0,1),frozenset({0,1}),0,1)
    record('clamp-overflow', 'debt=(0,1), enabled={0,1}, serve 0, B=1', debt, (0,1))
    # One scheduler action; two demonic outcomes. Existence is not an adversarial strategy.
    g=((1,2),(1,),(2,)); q=f.modes(g,frozenset({1}))
    record('path-versus-strategy', '0 -> good loop or bad loop, same scheduler action; eventually good',
           0 in q['must_eventually'], 0 in q['may_eventually'])
    # Even identity expansion admits additional target runs if B is widened.
    record('dilation-is-not-reflection', 'source period 0110 violates B=1; identity blocks allowed for r=2; target F_2(1)=4',
           f.longest_miss((0,1,1,0)*3) <= 1,
           f.longest_miss((0,1,1,0)*3) <= f.transported_bound(1,2))
    # Missing action matching: low-labelled one-state systems would appear identical.
    left=f.System((0,),2,((0,0,0),)); right=f.System((0,),2,((0,1,0),))
    record('erase-action-bisimulation', 'constant observations, only action 0 versus only action 1',
           f.bisimulation(left,right,frozenset({(0,0)})), True)
    graph=((0,),()); good=cert.generate(graph); assert cert.check(graph,good)
    mutations = {
        'missing-successor': {'live':[0], 'successor':{}, 'rank':{'1':0}},
        'fabricated-edge': {'live':[0], 'successor':{'0':1}, 'rank':{'1':0}},
        'omitted-outside-rank': {'live':[0], 'successor':{'0':0}, 'rank':{}},
        'boolean-rank': {'live':[0], 'successor':{'0':0}, 'rank':{'1':True}},
        'cyclic-descending-rank': {'live':[], 'successor':{}, 'rank':{'0':0,'1':0}},
        'duplicate-live-vertex': {'live':[0,0], 'successor':{'0':0}, 'rank':{'1':0}},
    }
    for name, c in mutations.items(): record('certificate-'+name, 'graph=0->0; vertex 1 terminal', cert.check(graph,c),True)
    write_csv(out/'boundaries.csv',rows)
    write_json(out/'boundary-certificates.json',dict(graph=graph, valid=good, invalid=mutations))
    return dict(named_negative_controls=len(rows), all_detected=True,
                note='Hand-designed witnesses, not mutation-score evidence of completeness.')

FUNCTIONS = {k: globals()[k] for k in BASE_STAGES}
for _b in range(5):
    FUNCTIONS[f'classify{_b}'] = lambda out, b=_b: extended.classify(b,out,write_csv)
FUNCTIONS['public-budget'] = lambda out: extended.public_budget(out,write_csv)
FUNCTIONS['composition'] = lambda out: extended.composition(out,write_csv)
FUNCTIONS['regular-one-bit'] = lambda out: regular.regular_one_bit(out, write_csv)
FUNCTIONS['regular-blocks'] = lambda out: regular.regular_blocks(out, write_csv)
FUNCTIONS['regular-annotated'] = lambda out: regular.regular_annotated(out, write_csv)
FUNCTIONS['regular-certificates'] = lambda out: regular.regular_certificates(out, write_csv, write_json)
FUNCTIONS['regular-decisions'] = lambda out: regular.regular_decisions(out, write_csv, write_json)
FUNCTIONS['regular-composition'] = lambda out: regular.regular_composition(out, write_csv)
FUNCTIONS['annotated-composition'] = lambda out: regular.annotated_composition(out, write_csv)
FUNCTIONS['canonical-expansions'] = lambda out: regular.canonical_expansions(out, write_csv)
FUNCTIONS['annotated-expansions'] = lambda out: regular.annotated_expansions(out, write_csv)

def main():
    if not __debug__:
        raise RuntimeError('Validation requires assertions; do not use python -O or PYTHONOPTIMIZE.')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('reproduced'))
    parser.add_argument('--stage', choices=STAGES)
    args=parser.parse_args()
    # Single process; the runner never spawns child workers or invokes a network.
    limit=3*1024**3
    soft,hard=resource.getrlimit(resource.RLIMIT_AS)
    if hard != resource.RLIM_INFINITY: limit=min(limit,hard)
    resource.setrlimit(resource.RLIMIT_AS,(limit,limit))
    args.output.mkdir(parents=True,exist_ok=True)
    summary_path=args.output/'summary.json'
    summary=json.loads(summary_path.read_text()) if args.stage and summary_path.exists() else {}
    timings=[]
    for stage in (args.stage,) if args.stage else STAGES:
        wall=time.perf_counter(); cpu=time.process_time()
        summary[stage]=FUNCTIONS[stage](args.output)
        timing=dict(stage=stage, wall_seconds=time.perf_counter()-wall,
                    cpu_seconds=time.process_time()-cpu,
                    peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    workers=1, address_space_limit_bytes=limit)
        timings.append(timing); write_json(args.output/f'{stage}-resources.json',timing)
        write_json(summary_path,summary)
        print(json.dumps(dict(stage=stage, result=summary[stage], resources=timing)),flush=True)
    return 0

if __name__=='__main__': raise SystemExit(main())
