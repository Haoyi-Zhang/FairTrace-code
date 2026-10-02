"""Checkable certificates for EXISTENCE of infinite paths in a finite graph.

The checker does not invoke the fixed-point solver. It checks a closed witness
successor on live vertices and a strictly decreasing rank on every other edge.
This is executable finite certificate checking, not a Rocq metatheory.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from fairness import Graph, validate_graph


def generate(graph: Graph) -> dict:
    validate_graph(graph)
    current = set(range(len(graph))); rank = {}; level = 0
    while True:
        removed = {s for s in current if not any(t in current for t in graph[s])}
        if not removed:
            break
        for s in removed:
            rank[str(s)] = level
        current -= removed; level += 1
    return {'live': sorted(current),
            'successor': {str(s): min(t for t in graph[s] if t in current)
                          for s in sorted(current)},
            'rank': rank}


def check(graph: Graph, certificate: object) -> bool:
    try:
        validate_graph(graph)
        if not isinstance(certificate, dict) or set(certificate) != {'live', 'successor', 'rank'}:
            return False
        vertices = set(range(len(graph)))
        raw_live = certificate['live']
        if not isinstance(raw_live, list) or any(type(x) is not int for x in raw_live):
            return False
        live = set(raw_live)
        if len(live) != len(raw_live) or not live <= vertices:
            return False
        successors = certificate['successor']; ranks = certificate['rank']
        if not isinstance(successors, dict) or not isinstance(ranks, dict):
            return False
        if set(successors) != {str(x) for x in live}:
            return False
        if set(ranks) != {str(x) for x in vertices - live}:
            return False
        for s in live:
            t = successors[str(s)]
            if type(t) is not int or t not in live or t not in graph[s]:
                return False
        for s in vertices - live:
            value = ranks[str(s)]
            if type(value) is not int or not 0 <= value < max(1, len(graph)):
                return False
            for t in graph[s]:
                if t in live or type(ranks[str(t)]) is not int or ranks[str(t)] >= value:
                    return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def load_json(path: Path) -> object:
    if path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError('input exceeds 8 MiB')
    def no_duplicates(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError('duplicate JSON field')
            result[k] = v
        return result
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=no_duplicates)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packet', type=Path)
    args = parser.parse_args()
    try:
        obj = load_json(args.packet)
        if not isinstance(obj, dict) or set(obj) != {'graph', 'certificate'}:
            raise ValueError('expected graph and certificate')
        graph = tuple(tuple(row) for row in obj['graph'])
        if len(graph) > 100_000:
            raise ValueError('graph exceeds vertex budget')
        valid = check(graph, obj['certificate'])
    except (OSError, ValueError, TypeError) as exc:
        print(f'INVALID: {exc}')
        return 2
    print('VALID finite infinite-path certificate' if valid else 'INVALID certificate')
    return 0 if valid else 2

if __name__ == '__main__':
    raise SystemExit(main())
