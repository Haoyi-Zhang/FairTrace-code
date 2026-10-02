"""Exact small oracles using transitive closure rather than fixed-point pruning.

No fairness.update, live, backward_reach or certificate generator is imported.
"""
from __future__ import annotations
from itertools import product


def positive_closure(graph, allowed=None):
    allowed = set(range(len(graph))) if allowed is None else set(allowed)
    rows = [sum(1 << t for t in set(graph[s]) & allowed) if s in allowed else 0
            for s in range(len(graph))]
    for k in sorted(allowed):
        for s in sorted(allowed):
            if rows[s] & (1 << k):
                rows[s] |= rows[k]
    return rows


def infinite_vertices(graph, allowed=None):
    rows = positive_closure(graph, allowed)
    cycles = sum(1 << i for i, row in enumerate(rows) if row & (1 << i))
    return frozenset(i for i, row in enumerate(rows) if row & cycles)


def queries(graph, goal):
    n = len(graph); rows = positive_closure(graph)
    viable = infinite_vertices(graph)
    avoid = infinite_vertices(graph, set(range(n)) - set(goal))
    live_goal_bits = sum(1 << g for g in set(goal) & viable)
    bad_bits = sum(1 << g for g in avoid)
    may = frozenset(s for s in range(n)
                    if ((1 << s) | rows[s]) & live_goal_bits)
    must = frozenset(s for s in viable if s not in avoid)
    recur = frozenset(s for s in viable
                      if not (((1 << s) | rows[s]) & bad_bits))
    return {'viable': viable, 'may_eventually': may,
            'must_eventually': must, 'must_recur': recur}


def window_accepts(events, obligations, bound):
    """Read a finite event word directly: every (bound+1)-window has a reset."""
    width = bound + 1
    for i in range(obligations):
        for start in range(max(0, len(events) - width + 1)):
            window = events[start:start + width]
            if all(i in ready and chosen != i for ready, chosen in window):
                return False
    return True


def longest_run_by_substrings(word):
    return max((j - i for i in range(len(word) + 1)
                for j in range(i, len(word) + 1)
                if all(x == 1 for x in word[i:j])), default=0)


def words_up_to(length):
    return tuple(w for k in range(1, length + 1) for w in product((0, 1), repeat=k))
