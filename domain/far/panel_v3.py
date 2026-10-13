"""v9 (far transfer, 10-11): a fresh draw of the sealed panels, sheet.v3.jsonl and rpn.v3.jsonl, with the same generator,
counts and checks as v1 and v2 (domain/panel.py) and new seeds. v9's swap tool was chosen after the diagnosis looked at
what the far split asks for, so v9 is scored on this draw (as addendum A10 did for v2).

  python3 -m domain.far.panel_v3        (refuses to overwrite)
"""
import os

from domain import panel
from domain.tools import rpn as rpn_tool
from domain.tools import sheet as sheet_tool

V3_SHEET_SEED, V3_RPN_SEED = 91021, 91022


def main():
    names = ('sheet.v3.jsonl', 'rpn.v3.jsonl')
    for n in names:
        for p in (os.path.join(panel.OUT_DIR, n), os.path.join(panel.OUT_DIR, n + '.sha256')):
            if os.path.exists(p):
                raise SystemExit(f'refusing to overwrite {p}')
    sheet_rows, sheet_stats = panel.build_sheet(V3_SHEET_SEED)
    rpn_rows, rpn_stats = panel.build_rpn(V3_RPN_SEED)
    clash = [r['prompt'] for r in rpn_rows
             if r['split'] == 'near' and panel.digit_runs(r['prompt'].split()[1:]) == panel.RPN_HELP_RUNS[r['kind']]]
    assert not clash, clash[:5]
    old = set()
    for n in ('sheet.jsonl', 'sheet.v2.jsonl', 'rpn.jsonl', 'rpn.v2.jsonl'):
        old |= {r['prompt'] for r in panel_rows(os.path.join(panel.OUT_DIR, n))}
    print('v3 prompts also in an older draw:', sum(r['prompt'] in old for r in sheet_rows + rpn_rows))
    print('hard checks:', panel.hard_checks('sheet', sheet_rows, {h['prompt'] for h in sheet_tool.help()}),
          panel.hard_checks('rpn', rpn_rows, {h['prompt'] for h in rpn_tool.help()}))
    panel.report('sheet', sheet_rows, sheet_stats)
    panel.report('rpn', rpn_rows, rpn_stats)
    print('sha256', names[0], panel.write_panel(names[0], sheet_rows))
    print('sha256', names[1], panel.write_panel(names[1], rpn_rows))


def panel_rows(path):
    import json
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


if __name__ == '__main__':
    main()
