"""Standard-library-only report over scored fable-baseline-transformer runs.

`report --root DIR` walks DIR for */score/scores.json (written by
`fable_baseline_transformer.py score`) and prints, in the same style as
`fable_dispatcher_report_v3.py`:

  1. MAIN TABLE.  Rows are the 25 frozen evaluation cells, columns are SEEDS, each
     entry `answers/strict/no_end`.  Seeds are never averaged and never pooled.
  2. The first hop length at which each seed drops below the mark (58/64 by default)
     on the 16-person cells, separately for the practised and the held-out terminal
     relation.
  3. The pair cells in full: both-twins-correct, strict, and the identical-twin-answer
     count that the irrelevant-edit cell additionally requires.
  4. The frozen operator's per-stage accuracy on each cell's audited chains, copied
     from the panel manifest -- this is a property of SYSTEM S's operator, reproduced
     here only so the two reports line up.  The baseline has no operator.
  5. BUDGET: parameters, updates, wall time, training FLOPs and scoring FLOPs per
     seed, next to System S's figures where they are known.
  6. A run inventory with the arm (mode/positions), whether the run was time-capped,
     and whether it scored the REGISTERED panel manifest.

This file imports nothing from the project: it only reads the JSON the scorer wrote.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_MARK = 58
PAIR_CELLS = ('pair-link', 'pair-value', 'pair-irrelevant')

# System S, for the budget table.  The lookup figure is the project's stated
# 6,000 updates x ~2.85e9 matmul FLOPs per update.  The dispatcher's training FLOPs
# were NOT recorded by fable_dispatcher_v3, so they are reported as unknown rather
# than guessed; its wall time IS recorded and is filled in by --dispatcher-run.
S_LOOKUP_UPDATES = 6000
S_LOOKUP_FLOPS_PER_UPDATE = 2.85e9
S_PARAMETERS = 79_316 + 15_522


def runs(root):
    found = []
    for scores in sorted(Path(root).rglob('score/scores.json')):
        summary = json.loads(scores.read_text())
        run = scores.parents[1]
        found.append(dict(run=run, score=scores.parent, label=run.name,
                          seed=summary.get('seed'), summary=summary))
    found.sort(key=lambda row: (row['summary'].get('mode', ''),
                                row['summary'].get('positions', ''),
                                row['seed'] if row['seed'] is not None else -1))
    return found


def arm(summary):
    return f'{summary.get("mode", "?")}/{summary.get("positions", "?")}'


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


def counts_of(entry, cell):
    return entry['summary'].get('cells', {}).get(cell)


def render_main(entries, order, mark):
    width = 19
    head = f'{"cell":>18}{"n":>5}{"k":>4}{"ppl":>5}' + ''.join(
        '{:>{w}}'.format(f'{arm(e["summary"])} s{e["seed"]}', w=width) for e in entries)
    out = [f'MAIN TABLE  (each entry answers/strict/no_end; mark {mark})', head, '-' * len(head)]
    for cell in order:
        pieces = []
        n = k = people = '?'
        for entry in entries:
            row = counts_of(entry, cell)
            if row is None:
                pieces.append('{:>{w}}'.format('-', w=width))
                continue
            n, k, people = row['n'], row['hops'], row['people']
            flag = '' if row['answers'] >= mark else ' *'
            pieces.append('{:>{w}}'.format(
                f'{row["answers"]}/{row["strict"]}/{row["no_end"]}{flag}', w=width))
        out.append(f'{cell:>18}{n:>5}{k:>4}{people:>5}' + ''.join(pieces))
    out.append(f'  "*" marks a cell below the mark of {mark}.  Pair cells count a unit only '
               'when BOTH twins are correct.')
    out.append('  strict = every emitted token equals the truth chain\'s results AND END is '
               'emitted right after the answer.')
    out.append('  no_end = sides that never emitted END within the 12-token budget (scored as '
               'failures).')
    return out


def render_breaks(entries, mark):
    out = ['', f'FIRST LENGTH BELOW {mark}/64',
           f'{"terminal":>12}' + ''.join(
               '{:>20}'.format(f'{arm(e["summary"])} s{e["seed"]}') for e in entries),
           '-' * (12 + 20 * len(entries))]
    for kind, suffix in (('practised', 'prac'), ('held-out', 'held')):
        pieces = []
        for entry in entries:
            first, tested = None, []
            for k in range(1, 9):
                row = counts_of(entry, f'k{k}-{suffix}')
                if row is None:
                    continue
                tested.append(k)
                if row['answers'] < mark and first is None:
                    first = k
            if not tested:
                pieces.append('{:>20}'.format('not scored'))
            elif first is None:
                pieces.append('{:>20}'.format(f'never (to k={max(tested)})'))
            else:
                pieces.append('{:>20}'.format(f'k={first}'))
        out.append(f'{kind:>12}' + ''.join(pieces))
    out.append('  16-person cells only, pairwise-distinct chains.')
    return out


def render_pairs(entries):
    out = ['', 'PAIR CELLS  (both twins correct / strict / identical twin answers / unit pass)',
           f'{"cell":>18}' + ''.join(
               '{:>26}'.format(f'{arm(e["summary"])} s{e["seed"]}') for e in entries),
           '-' * (18 + 26 * len(entries))]
    for cell in PAIR_CELLS:
        pieces = []
        for entry in entries:
            row = counts_of(entry, cell)
            pieces.append('{:>26}'.format('-' if row is None else
                                          f'{row["answers"]}/{row["strict"]}/'
                                          f'{row["identical_twin_answers"]}/{row["unit_pass"]}'))
        out.append(f'{cell:>18}' + ''.join(pieces))
    out.append('  pair-irrelevant additionally requires the two twins to give the SAME answer; '
               'that is the difference between its "both correct" and its "unit pass".')
    return out


def render_operator_audit(entries, order):
    audit = None
    for entry in entries:
        audit = entry['summary'].get('operator_audit') or audit
    if not audit:
        return []
    out = ['', 'SYSTEM S\'S FROZEN OPERATOR ON THE SAME CELLS\' TRUE CHAINS  (from the panel '
           'manifest)', f'{"cell":>18}{"stages":>10}{"correct":>10}{"perfect units":>16}',
           '-' * 54]
    for cell in order:
        row = audit.get(cell)
        if not row:
            continue
        stages = row.get('stages')
        correct = row.get('stages_correct')
        perfect = row.get('units_all_steps')
        out.append(f'{cell:>18}{str(stages):>10}{str(correct):>10}{str(perfect):>16}')
    out.append('  The baseline has no operator; this block exists so the two reports line up.')
    return out


def render_budget(entries, dispatcher_seconds=None):
    out = ['', 'BUDGET',
           f'{"run":>28}{"params":>9}{"upd":>7}{"train s":>10}{"train FLOPs":>14}'
           f'{"score s":>10}{"score FLOPs":>14}', '-' * 92]
    for entry in entries:
        s = entry['summary']
        out.append(
            f'{arm(s) + " s" + str(s.get("seed")):>28}'
            f'{s.get("parameters", "?"):>9}'
            f'{s.get("updates", "?"):>7}'
            f'{_num(s.get("training_seconds"), ".0f"):>10}'
            f'{_num(s.get("training_flops"), ".3e"):>14}'
            f'{_num(s.get("scoring_seconds"), ".0f"):>10}'
            f'{_num(s.get("inference_flops"), ".3e"):>14}')
    total = S_LOOKUP_UPDATES * S_LOOKUP_FLOPS_PER_UPDATE
    out += ['',
            f'  SYSTEM S for comparison: {S_PARAMETERS} parameters total.',
            f'  S lookup training: {S_LOOKUP_UPDATES} updates x ~{S_LOOKUP_FLOPS_PER_UPDATE:.2e} '
            f'matmul FLOPs = ~{total:.3e}.',
            '  S dispatcher training: FLOPs were never recorded by fable_dispatcher_v3 -- '
            'UNKNOWN, not estimated here.'
            + (f'  Wall time {dispatcher_seconds:.0f} s per seed.' if dispatcher_seconds else ''),
            '  FLOP convention (both sides): matmuls only, 2 FLOPs per MAC, x3 for '
            'forward+backward; embeddings, softmax, norms and the optimiser excluded.',
            '  The baseline charges PADDED positions because it executes them.']
    return out


def _num(value, spec):
    return '?' if value is None else format(value, spec)


def render_inventory(entries):
    out = ['', 'RUNS',
           f'{"path":>44}{"arm":>22}{"seed":>10}{"capped":>9}{"registered panels":>19}',
           '-' * 104]
    for entry in entries:
        s = entry['summary']
        out.append(f'{str(entry["run"])[-44:]:>44}{arm(s):>22}{str(s.get("seed")):>10}'
                   f'{str(bool(s.get("time_capped"))):>9}'
                   f'{str(bool(s.get("panel_manifest_is_registered"))):>19}')
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('report')
    p.add_argument('--root', required=True)
    p.add_argument('--mark', type=int, default=DEFAULT_MARK)
    p.add_argument('--dispatcher-run', default=None,
                   help='a v3 run directory whose training.json holds S\'s dispatcher wall time')
    args = parser.parse_args(argv)
    entries = runs(args.root)
    if not entries:
        raise SystemExit(f'no score/scores.json found under {args.root}')
    order = cell_order(entries)
    seconds = None
    if args.dispatcher_run:
        path = Path(args.dispatcher_run) / 'training.json'
        if path.is_file():
            seconds = json.loads(path.read_text()).get('seconds')
    lines = render_main(entries, order, args.mark)
    lines += render_breaks(entries, args.mark)
    lines += render_pairs(entries)
    lines += render_operator_audit(entries, order)
    lines += render_budget(entries, seconds)
    lines += render_inventory(entries)
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
