"""Finite omega-language equivalence oracle, independent of profile formulas.

Constructs reachable products of two absorbing-overflow counters.  A language
inclusion fails exactly when an accepting-side-safe reachable vertex has the
other counter overflowed and lies on, or can reach, a cycle without overflowing
the accepting side.  Cycles are detected through bitset transitive closure.
The oracle does not import morphisms, fairness, or the certificate generator.
"""
from __future__ import annotations
from reference import positive_closure

def transition(value, bits, bound):
    if value==bound+1: return value
    for bit in bits:
        value=value+1 if bit else 0
        if value>bound: return bound+1
    return value

def equivalent(u,v,b,c,a=0,t=0):
    u,v=tuple(u),tuple(v)
    if (not u or not v or max(len(u),len(v))>256
        or any(type(x) is not int or x not in (0,1) for x in u+v)
        or any(type(x) is not int or x<0 for x in (b,c,a,t))
        or a>b or b>128 or c>128):
        raise ValueError('invalid or over-budget oracle parameters')
    start=(a,min(t,c+1)); states=[start]; index={start:0}; rows=[]
    i=0
    while i<len(states):
        x,y=states[i]; targets=[]
        for bit,block in ((0,u),(1,v)):
            nxt=(transition(x,(bit,),b),transition(y,block,c))
            if nxt not in index:
                if len(states)>=4096: raise ValueError('oracle reachable-state budget exceeded')
                index[nxt]=len(states); states.append(nxt)
            targets.append(index[nxt])
        rows.append(tuple(sorted(set(targets)))); i+=1
    counterexamples=[]
    for accepting,rejecting,ab,rb in ((0,1,b,c),(1,0,c,b)):
        allowed={i for i,s in enumerate(states) if s[accepting]<=ab}
        reach=positive_closure(rows,allowed)
        cycles=sum(1<<i for i,r in enumerate(reach) if r & (1<<i))
        bad=any(s[rejecting]>rb and (reach[i]&cycles) for i,s in enumerate(states) if i in allowed)
        counterexamples.append(bad)
    return not any(counterexamples),len(states),tuple(counterexamples)
