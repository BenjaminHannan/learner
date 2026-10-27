"""Standard-library-only report over scored fable-dispatcher runs, v1 table plus v2 extras.

`report --root DIR` walks DIR for */score/scores.json and prints

  1. the v1 table (unchanged, produced by `fable_dispatcher_report.render`),
  2. the call-count distribution per cell -- a histogram of 0..4 executed calls plus the
     over-cap count -- read from the run's own `score/transcripts.json`,
  3. `score/diagnosis.json` if it is there: per cell, answers / full-path / over-cap
     under each evaluation-time intervention,
  4. `score/layout.json` if it is there: per cell, the counts under each harmless
     re-layout of the dispatcher's question tensor, and whether any executed
     (subject, operation) call moved.

Sections 3 and 4 are EVALUATOR-ONLY diagnostics; they use the exact interpreter's truth
chain and are not part of any registered score.  Seeds are never averaged.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fable_dispatcher_report as R1                                       # noqa: E402

CELL_ORDER = R1.CELL_ORDER
MAX_CALLS = 4


def collect(root):
    """R1.collect, but tolerant of a score folder that is not inside its own run folder.

    A post-hoc diagnosis writes `.../diagnosis-v1/<run>/score/`, which has no
    training.json beside it; v1's collector would raise there.  The rows are the same
    shape, so `R1.render` still draws the table.
    """
    rows = []
    for scores in sorted(Path(root).rglob('score/scores.json')):
        summary = json.loads(scores.read_text())
        run = scores.parents[1]
        config = {}
        for name in ('training.json', 'failure.json'):
            if (run / name).exists():
                config = json.loads((run / name).read_text())
                break
        if not config:
            source = Path(summary.get('run', ''))
            for name in ('training.json', 'failure.json'):
                if (source / name).exists():
                    config = json.loads((source / name).read_text())
                    break
        rows.append(dict(arm=summary.get('arm') or run.parent.name, label=run.parent.name,
                         seed=summary.get('seed'), path=str(run),
                         registered_test=summary.get('registered_test'),
                         note=summary.get('note'),
                         absolute_positions=config.get('absolute_positions'),
                         operator=config.get('operator'), updates=summary.get('updates'),
                         complete=config.get('complete'),
                         time_capped=summary.get('time_capped'),
                         dispatcher_parameters=summary.get('dispatcher_parameters'),
                         updates_per_second=config.get('updates_per_second'),
                         cells=summary.get('cells', {})))
    return rows


def runs(root):
    """Every scored run under `root`, newest layout first: (label, seed, run directory)."""
    found = []
    for scores in sorted(Path(root).rglob('score/scores.json')):
        summary = json.loads(scores.read_text())
        run = scores.parents[1]
        found.append(dict(run=run, score=scores.parent, label=run.parent.name,
                          seed=summary.get('seed'), summary=summary))
    return found


def histogram_rows(entry):
    """calls 0..4 and over-cap per cell, from the run's own transcripts."""
    path = entry['score'] / 'transcripts.json'
    if not path.exists():
        return []
    transcripts = json.loads(path.read_text())
    rows = []
    for cell in CELL_ORDER:
        scored = transcripts.get(cell)
        if not scored:
            continue
        sides = scored['trained_operator']
        flat = [r for side in sides.values() for r in side]
        counts = [sum(r['calls'] == c for r in flat) for c in range(MAX_CALLS + 1)]
        rows.append(dict(cell=cell, rows=len(flat), counts=counts,
                         over_cap=sum(r['status'] == 'over_cap' for r in flat),
                         invalid=sum(r['status'] == 'invalid_action' for r in flat),
                         mean_calls=sum(r['calls'] for r in flat) / max(1, len(flat))))
    return rows


def render_histograms(entry):
    rows = histogram_rows(entry)
    if not rows:
        return []
    head = (f'{"cell":>6}{"rows":>7}' + ''.join(f'{"calls=" + str(c):>10}'
                                                for c in range(MAX_CALLS + 1))
            + f'{"over_cap":>10}{"invalid":>9}{"mean":>8}')
    out = [f'  call-count distribution  [{entry["label"]} seed {entry["seed"]}]', '  ' + head,
           '  ' + '-' * len(head)]
    for row in rows:
        out.append('  ' + f'{row["cell"]:>6}{row["rows"]:>7}'
                   + ''.join(f'{c:>10}' for c in row['counts'])
                   + f'{row["over_cap"]:>10}{row["invalid"]:>9}{row["mean_calls"]:>8.2f}')
    means = {row['cell']: row['mean_calls'] for row in rows}
    out.append('  mean calls  d1 = %s   d2 = %s'
               % tuple(f'{means[c]:.3f}' if c in means else 'n/a' for c in ('d1', 'd2')))
    return out


def render_diagnosis(entry, label='trained_operator'):
    path = entry['score'] / 'diagnosis.json'
    if not path.exists():
        return []
    report = json.loads(path.read_text())
    kinds = report['interventions']
    head = f'{"cell":>6}{"n":>5}{"sides":>7}' + ''.join(f'{k:>26}' for k in kinds)
    out = ['', f'  interventions ({label})  [{entry["label"]} seed {entry["seed"]}]'
               f'{"  POST-HOC" if report.get("post_hoc") else ""}',
           '  ' + head, '  ' + '-' * len(head)]
    for cell in CELL_ORDER:
        row = report['cells'].get(cell)
        if not row:
            continue
        cells = row[label]
        out.append('  ' + f'{cell:>6}{row["n"]:>5}{row["sides"]:>7}'
                   + ''.join('{:>26}'.format(
                       f'{cells[k]["answers"]}/{cells[k]["full_path"]}/{cells[k]["over_cap"]}')
                       for k in kinds))
    out.append('  each intervention cell reads  answers / full_path / over_cap  '
               '(answers and full_path are UNIT counts out of n; over_cap counts sides)')
    return out


def render_layout(entry, label='trained_operator'):
    path = entry['score'] / 'layout.json'
    if not path.exists():
        return []
    report = json.loads(path.read_text())
    variants = report['variants']
    head = f'{"cell":>6}{"n":>5}' + ''.join(f'{v:>20}' for v in variants)
    out = ['', f'  layout variants ({label})  [{entry["label"]} seed {entry["seed"]}]'
               f'{"  POST-HOC" if report.get("post_hoc") else ""}',
           '  ' + head, '  ' + '-' * len(head)]
    moved_anywhere = 0
    for cell in CELL_ORDER:
        row = report['cells'].get(cell)
        if not row:
            continue
        cells = row[label]
        pieces = []
        for variant in variants:
            counts = cells[variant]
            mark = '' if counts['identical_executed_calls'] else \
                f' !{counts["rows_with_moved_calls"]}'
            moved_anywhere += counts['rows_with_moved_calls']
            pieces.append('{:>20}'.format(
                f'{counts["answers"]}/{counts["full_path"]}/{counts["over_cap"]}{mark}'))
        out.append('  ' + f'{cell:>6}{row["n"]:>5}' + ''.join(pieces))
    out.append('  each variant cell reads  answers / full_path / over_cap; '
               '"!k" means k rows executed a DIFFERENT (subject, operation) call sequence')
    out.append(f'  rows whose executed calls moved under any re-layout: {moved_anywhere}')
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('report')
    p.add_argument('--root', required=True)
    p.add_argument('--json', default=None, help='also write the collected v1 rows here')
    p.add_argument('--operator-view', default='trained_operator',
                   choices=('trained_operator', 'oracle_operator'),
                   help='which operator the v2 diagnosis/layout tables report')
    args = parser.parse_args(argv)
    print('\n'.join(R1.render(collect(args.root))))
    for entry in runs(args.root):
        lines = (render_histograms(entry) + render_diagnosis(entry, args.operator_view)
                 + render_layout(entry, args.operator_view))
        if lines:
            print('')
            print('\n'.join(lines))
    if args.json:
        with Path(args.json).open('x') as handle:
            json.dump(collect(args.root), handle, indent=2, sort_keys=True)
            handle.write('\n')


if __name__ == '__main__':
    main()
