"""Exact inverse-image classification for non-erasing binary word morphisms.

`classifies` is an executable formula, not a formal proof assistant. Its proof is
spelled out in proofs.md and compared with an independent finite omega-language
oracle. Counters start at the explicitly supplied initial debt.
"""
from __future__ import annotations
from dataclasses import dataclass
from fairness import natural

@dataclass(frozen=True)
class ResetProfile:
    prefix: int
    suffix: int
    internal: int
    zeros: int

def word(value) -> tuple[int, ...]:
    value=tuple(value)
    if not value or any(type(x) is not int or x not in (0,1) for x in value):
        raise ValueError('morphism blocks must be nonempty integer binary words')
    return value

def profile(value) -> ResetProfile:
    w=word(value); positions=[i for i,x in enumerate(w) if x==0]
    if not positions: raise ValueError('a reset profile requires at least one zero')
    return ResetProfile(positions[0],len(w)-1-positions[-1],
                        max((y-x-1 for x,y in zip(positions,positions[1:])),default=0),
                        len(positions))

def interval(zero, one, source_bound, source_debt, target_debt):
    """Feasible target bounds when the one-block has no reset; inclusive ends.

A lower endpoint greater than the upper endpoint denotes an empty interval.
"""
    u=word(zero); v=word(one)
    for x,name in ((source_bound,'source bound'),(source_debt,'source debt'),(target_debt,'target debt')):
        natural(x,name)
    if source_debt>source_bound: raise ValueError('source starts outside its bound')
    if 0 not in u or 0 in v: raise ValueError('interval requires a reset block and an all-miss block')
    p=profile(u); d=len(v); b=source_bound; a=source_debt; t=target_debt
    lo=max(p.internal,d*b+p.prefix+p.suffix,d*(b-a)+p.prefix+t)
    hi=min(d*(b+1)+p.prefix+p.suffix-1,d*(b-a+1)+p.prefix+t-1)
    return lo,hi

def invalid_floor_all_miss(zero, one, source_bound, source_debt=0, target_debt=0):
    """True invalid floor for a resetful zero-block and zero-free one-block.

    The two candidate unfair words isolate the first overflowing source gap and
    a later overflowing source gap.  Their target scores must still include the
    baseline demands forced by internal gaps of ``zero``, by repeated adjacent
    zero-blocks, and by the target initial debt.  The smaller candidate is the
    semantic invalid floor, even when the exact-contract interval is empty.
    """
    u=word(zero); v=word(one)
    for x,name in ((source_bound,'source bound'),(source_debt,'source debt'),
                   (target_debt,'target debt')):
        natural(x,name)
    if source_debt>source_bound:
        raise ValueError('source starts outside its bound')
    if 0 not in u or 0 in v:
        raise ValueError('invalid floor formula requires a reset block and an all-miss block')
    prof=profile(u); d=len(v); b=source_bound; a=source_debt; t=target_debt
    initial_overflow=max(
        prof.internal,
        prof.prefix+prof.suffix,
        t+d*(b-a+1)+prof.prefix,
    )
    repeated_overflow=max(
        prof.internal,
        t+prof.prefix,
        prof.suffix+d*(b+1)+prof.prefix,
    )
    return min(initial_overflow,repeated_overflow)


def classifies(zero, one, source_bound, target_bound, source_debt=0, target_debt=0):
    """Whether phi^{-1}(L[target_bound,target_debt]) = L[source_bound,source_debt]."""
    u=word(zero); v=word(one)
    for x,name in ((source_bound,'source bound'),(source_debt,'source debt'),
                   (target_bound,'target bound'),(target_debt,'target debt')):
        natural(x,name)
    if source_debt>source_bound: raise ValueError('source starts outside its bound')
    if target_debt>target_bound or 0 not in u: return False
    if 0 not in v:
        lo,hi=interval(u,v,source_bound,source_debt,target_debt)
        return lo<=target_bound<=hi
    if source_bound>=2: return False
    pu=profile(u); pv=profile(v); c=target_bound; t=target_debt
    if source_bound==1:
        common=max(pu.internal,pv.internal,pu.suffix+pu.prefix,
                   pu.suffix+pv.prefix,pv.suffix+pu.prefix,pu.prefix+t)
        if common>c or pv.suffix+pv.prefix<=c: return False
        return pv.prefix+t<=c if source_debt==0 else pv.prefix+t>c
    # B=0, a=0: test 0^omega and four possible first clusters of ones.
    all_zero=max(pu.prefix+t,pu.internal,pu.suffix+pu.prefix)
    initial_single=max(pv.prefix+t,pv.internal,pu.internal,pv.suffix+pu.prefix,pu.suffix+pu.prefix)
    interior_single=max(pu.prefix+t,pu.internal,pv.internal,pu.suffix+pu.prefix,
                        pu.suffix+pv.prefix,pv.suffix+pu.prefix)
    all_one=max(pv.prefix+t,pv.internal,pv.suffix+pv.prefix)
    final_ones=max(pu.prefix+t,pu.internal,pv.internal,pu.suffix+pv.prefix,pv.suffix+pv.prefix)
    return all_zero<=c and min(initial_single,interior_single,all_one,final_ones)>c

def uniform_public_budget(morphisms, source_bound, source_debt=0):
    """Lexicographically least (target bound, initial debt), or None.

This result requires each one-block to be all-miss and each zero-block to have a
reset. It ranges over ALL infinite source words, not just one program's runs.
"""
    natural(source_bound,'source bound'); natural(source_debt,'source debt')
    if source_debt>source_bound: raise ValueError('source starts outside its bound')
    morphisms=tuple(morphisms)
    if not morphisms: raise ValueError('nonempty morphism family required')
    internals=[]; initials=[]
    for u,v in morphisms:
        u=word(u); v=word(v)
        if 0 not in u or 0 in v: raise ValueError('family is not reset-faithful')
        p=profile(u); d=len(v); b=source_bound; a=source_debt
        internals.append((max(p.internal,d*b+p.prefix+p.suffix),d*(b+1)+p.prefix+p.suffix-1))
        initials.append((d*(b-a)+p.prefix,d*(b-a+1)+p.prefix-1))
    lr=max(x for x,y in internals); ur=min(y for x,y in internals)
    li=max(x for x,y in initials); ui=min(y for x,y in initials)
    if lr>ur or li>ui or li>ur: return None
    c=max(lr,li)
    t=max(0,c-ui)
    assert all(classifies(u,v,source_bound,c,source_debt,t) for u,v in morphisms)
    return c,t

def substitute(value, zero, one):
    u=word(zero); v=word(one)
    return tuple(bit for x in word(value) for bit in (u if x==0 else v))

def canonical_parameters(zero, one, bound, debt=0, slack=0):
    u=word(zero); v=word(one); p=profile(u)
    if 0 in v: raise ValueError('one block must consist of misses')
    natural(bound,'bound'); natural(debt,'debt'); natural(slack,'slack')
    if debt>bound or slack>=len(v): raise ValueError('invalid debt or mixed-radix slack')
    c=len(v)*bound+p.prefix+p.suffix+slack
    t=len(v)*debt+p.suffix
    if p.internal>c: raise ValueError('internal reset gap exceeds proposed bound')
    return c,t
