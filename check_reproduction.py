"""Compare deterministic scientific outputs; resource measurements are excluded."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def selected(root: Path) -> dict[str, Path]:
    names = {p.name: p for p in root.glob('*.csv')}
    for name in ('summary.json', 'small-models.json', 'boundary-certificates.json'):
        path = root / name
        if not path.is_file():
            raise ValueError(f'Missing required result: {path}')
        names[name] = path
    for directory in ('certificates', 'contract-certificates', 'decision-certificates'):
        for path in (root / directory).glob('*.json'):
            names[directory + '/' + path.name] = path
        if not any(n.startswith(directory + '/') for n in names):
            raise ValueError(f'No certificate packets under {root / directory}')
    if any(root.glob('*mismatches.json')):
        raise ValueError(f'A mismatch report exists under {root}')
    return names


def compare(expected: Path, actual: Path) -> dict:
    left, right = selected(expected), selected(actual)
    if set(left) != set(right):
        raise ValueError(f'Result file sets differ: {sorted(set(left) ^ set(right))}')
    required_stages = {'expansion', 'monitor', 'graphs', 'bisimulation', 'saturation',
                       'boundaries', 'public-budget', 'composition',
                       'classify0', 'classify1', 'classify2', 'classify3', 'classify4',
                       'regular-one-bit', 'regular-blocks', 'regular-annotated',
                       'regular-certificates', 'regular-decisions', 'regular-composition', 'annotated-composition',
                       'canonical-expansions', 'annotated-expansions'}
    for side in (left, right):
        if set(json.loads(side['summary.json'].read_text())) != required_stages:
            raise ValueError('Summary is not a complete 22-stage scientific run')
    for name in sorted(left):
        if name.endswith('.json'):
            equal = json.loads(left[name].read_text()) == json.loads(right[name].read_text())
        else:
            equal = left[name].read_bytes() == right[name].read_bytes()
        if not equal:
            raise ValueError(f'Deterministic output differs: {name}')
    return {'matched_scientific_files': len(left), 'mismatches': 0,
            'resource_comparison': 'excluded: CPU, wall time and peak RSS are machine-dependent'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('expected', type=Path)
    parser.add_argument('actual', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(compare(args.expected, args.actual), sort_keys=True))
    except (OSError, ValueError, TypeError) as exc:
        print(f'FAIL: {exc}')
        return 2
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
