"""Prespecified exact-language and arithmetic checks; deterministic finite domains."""
from __future__ import annotations
import itertools as it
import json
from pathlib import Path
import morphisms as m
import omega_oracle as oracle
import regular_contracts as regular
import contract_oracle as fixed_oracle
import contract_decisions as decisions
import transducers
from reference import words_up_to


def word_string(w): return ''.join(map(str,w))


def classify(bound, out, write_csv):
    words=words_up_to(3); rows=[]; floor_rows=[]; total=exact=maximum=0; mismatches=[]
    by_kind={'zero_without_reset':0,'pure_miss_one':0,'resetful_one':0}
    interval_checks = floor_checks = reflection_checks = floor_witnesses = 0
    for u,v in it.product(words,repeat=2):
        cases=equalities=peak=0
        machine = transducers.morphism(u, v)
        intervals = {}
        for c in range(17):
            for a in range(bound+1):
                for t in range(c+1):
                    predicted=m.classifies(u,v,bound,c,a,t)
                    answer,n,directions=oracle.equivalent(u,v,bound,c,a,t)
                    key = (a, t)
                    if key not in intervals:
                        intervals[key] = regular.exact_interval(machine, bound, a, t)
                    synthesized = intervals[key].contains(c)
                    interval_checks += 1
                    cases+=1; equalities+=answer; peak=max(peak,n)
                    if predicted != answer or synthesized != answer:
                        mismatches.append(dict(u=u,v=v,b=bound,c=c,a=a,t=t,
                                               predicted=predicted,synthesized=synthesized,
                                               oracle=answer,directions=directions))
        if 0 in u and 0 not in v:
            for a in range(bound+1):
                # Fixed t=0..3 includes legal and temporarily over-budget
                # target initial debts.  The latter are important because the
                # semantic floor is defined before choosing C.
                for t in range(4):
                    predicted_floor=m.invalid_floor_all_miss(u,v,bound,a,t)
                    synthesized_floor=regular.invalid_floor(machine,bound,a,t)
                    assert synthesized_floor.value==predicted_floor
                    assert predicted_floor>=1
                    before=fixed_oracle.equivalent(
                        machine,bound,predicted_floor-1,a,t)
                    at=fixed_oracle.equivalent(
                        machine,bound,predicted_floor,a,t)
                    assert not before.target_not_source
                    assert at.target_not_source
                    assert regular.invalid_safe_lasso(
                        machine,bound,a,predicted_floor-1,t) is None
                    lasso=regular.invalid_safe_lasso(
                        machine,bound,a,predicted_floor,t)
                    assert lasso is not None
                    packet={
                        'schema': decisions.SCHEMA,
                        'transducer': machine.to_json(),
                        'parameters': {
                            'source_bound': bound,
                            'target_bound': predicted_floor,
                            'source_debt': a,
                            'target_debt': t,
                        },
                        'verdict': 'inexact',
                        'direction': 'source-invalid-target-valid',
                        'prefix': list(lasso.prefix),
                        'loop': list(lasso.loop),
                    }
                    assert decisions.check(packet)
                    floor_checks += 1
                    reflection_checks += 2
                    floor_witnesses += 1
                    floor_rows.append(dict(
                        zero=word_string(u), one=word_string(v), source_bound=bound,
                        source_debt=a, target_debt=t,
                        invalid_floor=predicted_floor,
                        below_bound=predicted_floor-1,
                        below_reflection_failure=int(before.target_not_source),
                        at_reflection_failure=int(at.target_not_source),
                        witness_prefix=word_string(lasso.prefix),
                        witness_loop=word_string(lasso.loop),
                        witness_checked=1,
                    ))

        kind=('zero_without_reset' if 0 not in u else
              'pure_miss_one' if 0 not in v else 'resetful_one')
        by_kind[kind]+=equalities
        rows.append(dict(zero=word_string(u),one=word_string(v),source_bound=bound,
                         target_bound_max=16,cases=cases,exact_equalities=equalities,
                         maximum_reachable_vertices=peak,kind=kind))
        total+=cases; exact+=equalities; maximum=max(maximum,peak)
    write_csv(out/f'classify-{bound}.csv',rows)
    write_csv(out/f'stateless-floor-{bound}.csv',floor_rows)
    if mismatches:
        (out/f'classify-{bound}-mismatches.json').write_text(json.dumps(mismatches,indent=2)+'\n')
        raise AssertionError(f'{len(mismatches)} classification mismatches')
    return dict(configurations=total,exact_equalities=exact,block_pairs=len(rows),
                maximum_reachable_vertices=maximum,equalities_by_kind=by_kind,
                maximum_block_length=3,source_bound=bound,target_bound_max=16,
                mismatches=0,regular_interval_checks=interval_checks,
                invalid_floor_formula_checks=floor_checks,
                reflection_threshold_checks=reflection_checks,
                invalid_floor_lasso_witnesses=floor_witnesses,
                scope='entire omega language per finite configuration; closed form, interval synthesis and product oracle; direct R-1/R reflection checks for resetful/all-miss blocks')


def public_budget(out,write_csv):
    words=words_up_to(2)
    morphs=tuple((u,v) for u in words if 0 in u for v in words if 0 not in v)
    rows=[]; queries=feasible=0
    cache={}
    for i in range(len(morphs)):
        for j in range(i,len(morphs)):
            family=(morphs[i],morphs[j])
            for b in range(4):
                # Any exact contract must admit B misses and reject B+1 misses
                # between resets. This bound only limits exhaustive enumeration.
                upper=min(len(v)*(b+1)+m.profile(u).prefix+m.profile(u).suffix-1
                          for u,v in family)
                for a in range(b+1):
                    predicted=m.uniform_public_budget(family,b,a)
                    found=None; local_queries=0
                    for c in range(upper+1):
                        for t in range(c+1):
                            answers=[]
                            for u,v in family:
                                key=(u,v,b,c,a,t)
                                if key not in cache:
                                    cache[key]=oracle.equivalent(u,v,b,c,a,t)[0]
                                    queries+=1
                                answers.append(cache[key]); local_queries+=1
                            if all(answers):
                                found=(c,t); break
                        if found is not None: break
                    assert predicted==found, (family,b,a,predicted,found)
                    feasible+=found is not None
                    rows.append(dict(first_zero=word_string(family[0][0]),
                                     first_one=word_string(family[0][1]),
                                     second_zero=word_string(family[1][0]),
                                     second_one=word_string(family[1][1]),source_bound=b,
                                     source_debt=a,search_bound_max=upper,
                                     feasible=int(found is not None),
                                     target_bound=found[0] if found else '',
                                     target_debt=found[1] if found else '',
                                     oracle_lookups=local_queries))
    write_csv(out/'public-budget.csv',rows)
    return dict(family_configurations=len(rows),morphisms=len(morphs),feasible=feasible,
                infeasible=len(rows)-feasible,distinct_oracle_calls=queries,
                selection='unordered pairs with repetition; blocks <=2; B=0..3; all a',
                bound_search='complete up to necessary interior upper bound')


def composition(out,write_csv):
    words=words_up_to(3)
    morphs=tuple((u,v) for u in words if 0 in u for v in words if 0 not in v)
    rows=[]; accepted=excluded=queries=peak=0
    cache={}
    for i,(u,v) in enumerate(morphs):
        p=m.profile(u); d=len(v)
        for j,(U,V) in enumerate(morphs):
            P=m.profile(U); e=len(V)
            zu=m.substitute(u,U,V); zv=m.substitute(v,U,V); qp=m.profile(zu)
            assert qp.prefix==e*p.prefix+P.prefix
            assert qp.suffix==e*p.suffix+P.suffix
            assert len(zv)==e*d and 0 not in zv
            internal=max(P.internal,P.suffix+e*p.internal+P.prefix) if p.zeros>=2 else P.internal
            assert qp.internal==internal
            pair_accepted=pair_excluded=0
            for b in range(4):
                for a in range(b+1):
                    for tau in range(d):
                        for sigma in range(e):
                            try:
                                c,t=m.canonical_parameters(u,v,b,a,tau)
                                D,T=m.canonical_parameters(U,V,c,t,sigma)
                            except ValueError:
                                pair_excluded+=1; continue
                            direct=m.canonical_parameters(zu,zv,b,a,e*tau+sigma)
                            assert direct==(D,T)
                            assert m.classifies(zu,zv,b,D,a,T)
                            key=(zu,zv,b,D,a,T)
                            if key not in cache:
                                cache[key]=oracle.equivalent(zu,zv,b,D,a,T)
                                queries+=1
                            answer,n,_=cache[key]
                            assert answer; peak=max(peak,n); pair_accepted+=1
            accepted+=pair_accepted; excluded+=pair_excluded
            rows.append(dict(first_zero=word_string(u),first_one=word_string(v),
                             second_zero=word_string(U),second_one=word_string(V),
                             composite_zero=word_string(zu),composite_one=word_string(zv),
                             prefix=qp.prefix,suffix=qp.suffix,internal_gap=qp.internal,
                             tested=pair_accepted,internal_gap_exclusions=pair_excluded))
    write_csv(out/'composition.csv',rows)
    return dict(morphisms=len(morphs),ordered_pairs=len(rows),tested=accepted,
                internal_gap_exclusions=excluded,distinct_oracle_calls=queries,
                maximum_reachable_vertices=peak,source_bound_max=3,
                scope='all initial debts and both permitted slacks; block length <=3 per pass')
