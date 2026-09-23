"""Standard-library-only report over scored fable-dispatcher v3 runs.

`report --root DIR` walks DIR for */score/scores.json (written by
`fable_dispatcher_v3.py score`) and prints

  1. MAIN TABLE.  Rows are evaluation cells, columns are SEEDS, each entry
     `answers/strict/over_cap`.  Seeds are never averaged and never pooled.
  2. The first hop length at which each seed drops below the mark (58/64 by default)
     on the 16-person cells, separately for the practised and the held-out terminal
     relation, and separately under the trained operator and the exact symbolic
     operator -- so a drop caused by the OPERATOR is visible next to a drop caused by
     the DISPATCHER.
  3. The frozen operator's own per-stage accuracy on the audited chains of each cell,
     copied from the panel manifest.  Operator errors are separable from dispatcher
     errors by construction.
  4. The call-count histogram per cell.
  5. `score/diagnosis.json` if present: per cell, answers/strict/over_cap under each
     evaluation-time intervention.  EVALUATOR-ONLY; not part of any registered score.

This file imports nothing from the project: it only reads the JSON the scorer wrote.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_MARK = 58
PAIR_CELLS = ('pair-link', 'pair-value', 'pair-irrelevant')


def runs(root):
    """Every scored run under `root`: (label, seed, score folder, summary)."""
    found = []
    for scores in sorted(Path(root).rglob('score/scores.json')):
        summary = json.loads(scores.read_text())
        run = scores.parents[1]
        found.append(dict(run=run, score=scores.parent, label=run.name,
                          seed=summary.get('seed'), summary=summary))
    found.sort(key=lambda row: (row['seed'] if row['seed'] is not None else -1, row['label']))
    return found


def cell_order(entries):
    for entry in entries:
        order = entry['summary'].get('cell_order')
        if order:
            return order
    seen = []
    for entry in entries:
        for cell in entry['summary'].get('cells', {}):
            if cell not in seen:
                seen.append(cell)
    return seen


def entry_counts(entry, cell, view):
    cells = entry['summary'].get('cells', {})
    row = cells.get(cell)
    if not row or view not in row:
        return None
    return row[view]


def render_main(entries, order, view, mark):
    seeds = [entry for entry in entries]
    width = max(14, 4 + 3 * 5)
    head = f'{"cell":>18}{"n":>5}{"k":>4}{"ppl":>5}' + ''.join(
        '{:>{w}}'.format(f'seed {e["seed"]}', w=width) for e in seeds)
    out = [f'MAIN TABLE  ({view}; each entry answers/strict/over_cap; mark {mark})',
           head, '-' * len(head)]
    for cell in order:
        pieces = []
        n = k = people = '?'
        for entry in seeds:
            counts = entry_counts(entry, cell, view)
            if counts is None:
                pieces.append('{:>{w}}'.format('-', w=width))
                continue
            row = entry['summary']['cells'][cell]
            n, k, people = row['n'], row['hops'], row['people']
            flag = '' if counts['answers'] >= mark else ' *'
            pieces.append('{:>{w}}'.format(
                f'{counts["answers"]}/{counts["strict"]}/{counts["over_cap"]}{flag}', w=width))
        out.append(f'{cell:>18}{n:>5}{k:>4}{people:>5}' + ''.join(pieces))
    out.append(f'  "*" marks a cell below the mark of {mark}.  Pair cells count a unit only '
               'when BOTH twins are correct.')
    out.append('  strict = subjects, operations, stop point AND every returned token equal '
               'the true chain.')
    return out


def render_breaks(entries, view, mark):
    """The first hop length at which each seed drops below the mark, per terminal kind."""
    out = ['', f'FIRST LENGTH BELOW {mark}/64  ({view})',
           f'{"terminal":>12}' + ''.join('{:>14}'.format(f'seed {e["seed"]}') for e in entries),
           '-' * (12 + 14 * len(entries))]
    for kind, suffix in (('practised', 'prac'), ('held-out', 'held')):
        pieces = []
        for entry in entries:
            first, tested = None, []
            for k in range(1, 9):
                counts = entry_counts(entry, f'k{k}-{suffix}', view)
                if counts is None:
                    continue
                tested.append(k)
                if counts['answers'] < mark and first is None:
                    first = k
            if not tested:
                pieces.append('{:>14}'.format('not scored'))
            elif first is None:
                pieces.append('{:>14}'.format(f'never (to k={max(tested)})'))
            else:
                pieces.append('{:>14}'.format(f'k={first}'))
        out.append(f'{kind:>12}' + ''.join(pieces))
    out.append('  16-person cells only, pairwise-distinct chains.')
    return out


def render_operator_audit(entries, order):
    entry = next((e for e in entries
                  if any('frozen_operator_on_true_chains' in row
                         for row in e['summary'].get('cells', {}).values())), None)
    if entry is None:
        return []
    head = f'{"cell":>18}{"stages":>9}{"correct":>9}{"units_all":>11}{"perfect":>9}'
    out = ['', 'FROZEN OPERATOR ON THE AUDITED TRUTH CHAINS  (from the panel manifest)',
           head, '-' * len(head)]
    for cell in order:
        row = entry['summary']['cells'].get(cell, {}).get('frozen_operator_on_true_chains')
        if not row:
            continue
        out.append(f'{cell:>18}{row["stages"]:>9}{row["stages_correct"]:>9}'
                   f'{row["units_all_steps"]:>11}{str(row["operator_perfect"]):>9}')
    out.append('  a dispatcher failure in a cell whose operator is not perfect is not '
               'necessarily the dispatcher\'s: compare the two operator views.')
    return out


def render_histograms(entry, order, cap):
    path = entry['score'] / 'transcripts.json'
    if not path.exists():
        return []
    transcripts = json.loads(path.read_text())
    buckets = list(range(cap + 1))
    head = (f'{"cell":>18}{"rows":>7}' + ''.join(f'{c:>6}' for c in buckets)
            + f'{"over_cap":>10}{"invalid":>9}{"mean":>8}')
    out = ['', f'  call-count distribution  [{entry["label"]} seed {entry["seed"]}]', '  ' + head,
           '  ' + '-' * len(head)]
    for cell in order:
        scored = transcripts.get(cell)
        if not scored:
            continue
        flat = [r for side in scored['trained_operator'].values() for r in side]
        counts = [sum(r['calls'] == c for r in flat) for c in buckets]
        out.append('  ' + f'{cell:>18}{len(flat):>7}' + ''.join(f'{c:>6}' for c in counts)
                   + '{:>10}{:>9}{:>8.2f}'.format(
                       sum(r['status'] == 'over_cap' for r in flat),
                       sum(r['status'] == 'invalid_action' for r in flat),
                       sum(r['calls'] for r in flat) / max(1, len(flat))))
    out.append('  columns are the number of operator calls the episode executed.')
    return out


def render_diagnosis(entry, order, view):
    path = entry['score'] / 'diagnosis.json'
    if not path.exists():
        return []
    report = json.loads(path.read_text())
    kinds = report['interventions']
    head = f'{"cell":>18}{"n":>5}' + ''.join(f'{k:>24}' for k in kinds)
    out = ['', f'  interventions ({view})  [{entry["label"]} seed {entry["seed"]}]  '
               'EVALUATOR-ONLY', '  ' + head, '  ' + '-' * len(head)]
    for cell in order:
        row = report['cells'].get(cell)
        if not row:
            continue
        cells = row[view]
        out.append('  ' + f'{cell:>18}{row["n"]:>5}' + ''.join('{:>24}'.format(
            f'{cells[k]["answers"]}/{cells[k]["strict"]}/{cells[k]["over_cap"]}') for k in kinds))
    out.append('  each cell reads answers/strict/over_cap.  A component is forced only while '
               'step < hops; beyond the true length the model acts freely (the v2 fix).')
    return out


def collect(root, view, mark):
    entries = runs(root)
    order = cell_order(entries)
    table = {}
    for cell in order:
        table[cell] = {str(e['seed']): entry_counts(e, cell, view) for e in entries}
    return dict(root=str(Path(root).resolve()), view=view, mark=mark, cell_order=order,
                seeds=[e['seed'] for e in entries],
                runs=[dict(label=e['label'], seed=e['seed'], run=str(e['run']),
                           panel_manifest_sha256=e['summary'].get('panel_manifest_sha256'),
                           eval_cap=e['summary'].get('eval_cap'),
                           train_cap=e['summary'].get('train_cap'),
                           train_hops=e['summary'].get('train_hops'),
                           updates=e['summary'].get('updates'),
                           ablations=e['summary'].get('ablations'),
                           call_cost=e['summary'].get('call_cost')) for e in entries],
                table=table)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('report')
    p.add_argument('--root', required=True)
    p.add_argument('--mark', type=int, default=DEFAULT_MARK)
    p.add_argument('--operator-view', default='trained_operator',
                   choices=('trained_operator', 'oracle_operator'))
    p.add_argument('--both-views', action='store_true',
                   help='print the main table and the break row under both operators')
    p.add_argument('--json', default=None)
    args = parser.parse_args(argv)

    entries = runs(args.root)
    if not entries:
        raise SystemExit(f'no score/scores.json under {args.root}')
    order = cell_order(entries)
    views = ['trained_operator', 'oracle_operator'] if args.both_views else [args.operator_view]
    head = entries[0]['summary']
    print(f'panels {head.get("panels")}')
    print(f'panel manifest sha256 {head.get("panel_manifest_sha256")}')
    print(f'train cap {head.get("train_cap")}   eval cap {head.get("eval_cap")}   '
          f'train hops {head.get("train_hops")}   train people {head.get("train_people")}   '
          f'call cost {head.get("call_cost")}   ablations {head.get("ablations")}')
    for row in entries:
        print(f'  seed {row["seed"]:<6} updates {row["summary"].get("updates")}   '
              f'{row["run"]}')
    for view in views:
        print('')
        print('\n'.join(render_main(entries, order, view, args.mark)))
        print('\n'.join(render_breaks(entries, view, args.mark)))
    print('\n'.join(render_operator_audit(entries, order)))
    for entry in entries:
        cap = entry['summary'].get('eval_cap', 16)
        lines = (render_histograms(entry, order, cap)
                 + render_diagnosis(entry, order, args.operator_view))
        if lines:
            print('\n'.join(lines))
    if args.json:
        with Path(args.json).open('x') as handle:
            json.dump(collect(args.root, args.operator_view, args.mark), handle, indent=2,
                      sort_keys=True)
            handle.write('\n')


if __name__ == '__main__':
    main()
