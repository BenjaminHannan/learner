"""Standard-library-only table over every scored fable-dispatcher run.

`report --root DIR` walks DIR/<arm>/seed-<n>/score/scores.json and prints one row per
(arm, seed, cell) with the raw counts and pass/fail against each cell's frozen mark.
Seeds are never averaged: every seed is listed on its own line, and a failing seed is
never hidden behind a mean.  Claims about what a result shows are not this script's job.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

CELL_ORDER = ('d1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7')


def collect(root):
    rows = []
    # the documented layout is DIR/ARM/seed-N/score/scores.json; any nesting is accepted
    for scores in sorted(Path(root).rglob('score/scores.json')):
        summary = json.loads(scores.read_text())
        run = scores.parents[1]
        arm = summary.get('arm') or run.parent.name
        label = run.parent.name
        seed = summary.get('seed')
        training = run / 'training.json'
        failure = run / 'failure.json'
        config = json.loads((training if training.exists() else failure).read_text())
        rows.append(dict(arm=arm, label=label, seed=seed, path=str(run),
                         registered_test=summary.get('registered_test'),
                         note=summary.get('note'),
                         absolute_positions=config.get('absolute_positions'),
                         operator=config.get('operator'),
                         updates=summary.get('updates'),
                         complete=config.get('complete'),
                         time_capped=summary.get('time_capped'),
                         dispatcher_parameters=summary.get('dispatcher_parameters'),
                         updates_per_second=config.get('updates_per_second'),
                         cells=summary.get('cells', {})))
    return rows


def render(rows):
    lines = []
    if not rows:
        return ['no scored runs found']
    header = (f'{"arm":<14}{"seed":>5}{"cell":>6}{"n":>5}{"mark":>6}{"answers":>9}'
              f'{"path_mark":>11}{"full_path":>11}{"oracle_op":>11}{"F_chain":>9}'
              f'{"invalid":>9}{"overcap":>9}{"pass":>7}')
    lines.append(header)
    lines.append('-' * len(header))
    for row in rows:
        for cell in CELL_ORDER:
            counts = row['cells'].get(cell)
            if not counts:
                continue
            trained = counts['trained_operator']
            oracle = counts['oracle_operator']
            chains = counts['frozen_operator_on_true_chains']
            lines.append(
                f'{row["label"]:<14}{row["seed"]!s:>5}{cell:>6}{counts["n"]:>5}'
                f'{counts["mark"]:>6}{trained["unit_pass"]:>9}'
                f'{str(counts["path_mark"]):>11}{trained["full_path"]:>11}'
                f'{oracle["unit_pass"]:>11}{chains["units_all_steps"]:>9}'
                f'{trained["invalid"]:>9}{trained["over_cap"]:>9}'
                f'{("PASS" if counts["pass"] else "FAIL"):>7}')
        lines.append(f'  {row["label"]} seed {row["seed"]}: operator={row["operator"]} '
                     f'updates={row["updates"]} complete={row["complete"]} '
                     f'time_capped={row["time_capped"]} '
                     f'absolute_positions={row["absolute_positions"]} '
                     f'params={row["dispatcher_parameters"]}')
        if row['note']:
            lines.append(f'    note: {row["note"]}')
    lines.append('')
    lines.append('answers/oracle_op/full_path are UNIT counts out of n; a pair unit counts only '
                 'when both twins are correct')
    lines.append('oracle_op = the same trained dispatcher scored with the ORACLE operator '
                 '(dispatcher quality isolated from operator errors)')
    lines.append('F_chain  = units where the frozen operator answered every step of the TRUE '
                 'chain correctly (operator errors, separable)')
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('report')
    p.add_argument('--root', required=True)
    p.add_argument('--json', default=None, help='also write the collected rows here')
    args = parser.parse_args(argv)
    rows = collect(args.root)
    print('\n'.join(render(rows)))
    if args.json:
        with Path(args.json).open('x') as handle:
            json.dump(rows, handle, indent=2, sort_keys=True)
            handle.write('\n')


if __name__ == '__main__':
    main()
