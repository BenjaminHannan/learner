"""Post-run audit of a domain run (DM4), against the sealed panels.

The panels are read here, never by mode.py (mode.guard() refuses them). Run from the repo root:

    python3 -m domain.audit RUN_DIR [--panel DIR]

RUN_DIR/log.jsonl: every 'row' event is a training row (source own, tool or diary). The audit fails (exit 1) when:
  - a training prompt equals a prompt in a sealed panel file (sheet.jsonl or rpn.jsonl in DIR);
  - a training row has no worked steps (addendum A5: answer-only rows never train);
  - a row's source is not own, tool or diary.
It prints the row counts per source and per kind, so the training counts are on record for the design.
"""
import argparse
import json
import os
import sys
from collections import Counter

from domain.panel import OUT_DIR

PANEL_FILES = ('sheet.jsonl', 'rpn.jsonl')
SOURCES = frozenset({'own', 'tool', 'diary'})


def read_panel(panel_dir):
    """{prompt: 'file:id'} for every row of the sealed panel files in panel_dir."""
    out = {}
    for name in PANEL_FILES:
        with open(os.path.join(panel_dir, name), encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    out[r['prompt']] = f"{name}:{r['id']}"
    return out


def audit_rows(rows, panel):
    """rows: the training rows (dicts with id, source, kind, prompt, steps). panel: {prompt: where}. -> report dict."""
    overlap = [dict(id=r['id'], prompt=r['prompt'], panel=panel[r['prompt']]) for r in rows if r['prompt'] in panel]
    zero = [r['id'] for r in rows if not r['steps'] and r['source'] != 'diary']  # A9: diary = the parent's whole own output
    bad = [r['id'] for r in rows if r['source'] not in SOURCES]
    return dict(rows=len(rows), by_source=dict(Counter(r['source'] for r in rows)),
                by_source_kind={f"{s}/{k}": n for (s, k), n in sorted(Counter((r['source'], r['kind']) for r in rows).items())},
                panel_overlap=overlap, zero_steps=zero, bad_source=bad,
                ok=not (overlap or zero or bad))


def audit_run(run_dir, panel_dir=OUT_DIR):
    with open(os.path.join(run_dir, 'log.jsonl'), encoding='utf-8') as f:
        rows = [r for r in (json.loads(line) for line in f if line.strip()) if r['event'] == 'row']
    return audit_rows(rows, read_panel(panel_dir))


def main(argv=None):
    ap = argparse.ArgumentParser(description='Audit a domain run: training rows against the sealed panels (DM4).')
    ap.add_argument('run_dir')
    ap.add_argument('--panel', default=OUT_DIR, help='folder with sheet.jsonl and rpn.jsonl')
    a = ap.parse_args(argv)
    rep = audit_run(a.run_dir, a.panel)
    print(json.dumps(rep, indent=1, sort_keys=True))
    return 0 if rep['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
