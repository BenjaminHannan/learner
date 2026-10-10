"""Post-run audit of a domain run (DM4), against the sealed panels.

The panels are read here, never by mode.py (mode.guard() refuses them). Run from the repo root:

    python3 -m domain.audit RUN_DIR [--panel DIR]

RUN_DIR/log.jsonl: every 'row' event is a training row (source own, tool or diary). The audit fails (exit 1) when:
  - v1 panels (sheet.jsonl, rpn.jsonl): a training prompt equals a prompt in a sealed panel file;
  - v2 panels (--panel-suffix .v2, addendum A10): more than DECONTAM_MAX_FRAC of the run tool's panel rows have a prompt
    that is also a training prompt. Those rows are dropped from scoring (analyze.py) and counted here;
  - a training row has no worked steps (addendum A5: answer-only rows never train);
  - a row's source is not own, tool or diary.
It prints the row counts per source and per kind, so the training counts are on record for the design.
"""
import argparse
import json
import os
import re
import sys
from collections import Counter

from domain.panel import OUT_DIR

SOURCES = frozenset({'own', 'tool', 'diary'})
DECONTAM_SUFFIX = '.v2'   # addendum A10: v2 panels are decontaminated (rows that are also training prompts are dropped)
DECONTAM_MAX_FRAC = 0.02  # DM4 fails when more than this share of the run tool's panel rows is dropped


def panel_files(suffix=''):
    return (f'sheet{suffix}.jsonl', f'rpn{suffix}.jsonl')


def panel_suffix(path):
    """'' for sheet.jsonl or rpn.jsonl (v1), '.v2' for sheet.v2.jsonl or rpn.v2.jsonl. Any other name is refused."""
    m = re.fullmatch(r'(?:sheet|rpn)(\.v2)?\.jsonl', os.path.basename(path))
    if not m:
        raise ValueError(f'not a sealed panel file: {path}')
    return m.group(1) or ''


def load_panel_file(path):
    with open(path, encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def read_panel(panel_dir, suffix=''):
    """{prompt: 'file:id'} for every row of the sealed panel files (of this suffix) in panel_dir."""
    out = {}
    for name in panel_files(suffix):
        for r in load_panel_file(os.path.join(panel_dir, name)):
            out[r['prompt']] = f"{name}:{r['id']}"
    return out


def decontam(panel_rows, train_prompts):
    """Addendum A10, DM4: panel rows whose exact prompt is also a training prompt of the run. -> counts by kind and split."""
    dropped = [r for r in panel_rows if r['prompt'] in train_prompts]
    n = len(panel_rows)
    return dict(n=n, dropped=len(dropped), frac=round(len(dropped) / n, 6) if n else 0.0,
                by_kind=dict(Counter(r['kind'] for r in dropped)), by_split=dict(Counter(r['split'] for r in dropped)),
                ids=[r['id'] for r in dropped])


def audit_rows(rows, panel, tool_panel_rows=None, suffix=''):
    """rows: the training rows (dicts with id, source, kind, prompt, steps). panel: {prompt: where} over the sealed files.
    tool_panel_rows and suffix '.v2': the run tool's panel rows, for the decontamination count. -> report dict."""
    overlap = [dict(id=r['id'], prompt=r['prompt'], panel=panel[r['prompt']]) for r in rows if r['prompt'] in panel]
    zero = [r['id'] for r in rows if not r['steps'] and r['source'] != 'diary']  # A9: diary = the parent's whole own output
    bad = [r['id'] for r in rows if r['source'] not in SOURCES]
    if suffix == DECONTAM_SUFFIX:
        assert tool_panel_rows is not None, 'decontamination needs the run tool panel rows'
        dec = decontam(tool_panel_rows, {r['prompt'] for r in rows})
        dm4_fail = dec['frac'] > DECONTAM_MAX_FRAC
    else:
        dec = None
        dm4_fail = bool(overlap)  # v1 panels: any row from our panel fails the audit (addendum A1)
    return dict(rows=len(rows), by_source=dict(Counter(r['source'] for r in rows)),
                by_source_kind={f"{s}/{k}": n for (s, k), n in sorted(Counter((r['source'], r['kind']) for r in rows).items())},
                panel_overlap=overlap, decontam=dec, zero_steps=zero, bad_source=bad,
                ok=not (dm4_fail or zero or bad))


def audit_run(run_dir, panel_dir=OUT_DIR, suffix=''):
    with open(os.path.join(run_dir, 'log.jsonl'), encoding='utf-8') as f:
        events = [json.loads(line) for line in f if line.strip()]
    rows = [r for r in events if r['event'] == 'row']
    tool_rows = None
    if suffix == DECONTAM_SUFFIX:
        start = [e for e in events if e['event'] == 'start']
        if not start:
            raise ValueError('no start event: the run tool is unknown')
        tool_rows = load_panel_file(os.path.join(panel_dir, f"{start[0]['tool']}{suffix}.jsonl"))
    return audit_rows(rows, read_panel(panel_dir, suffix), tool_rows, suffix)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Audit a domain run: training rows against the sealed panels (DM4).')
    ap.add_argument('run_dir')
    ap.add_argument('--panel', default=OUT_DIR, help='folder with the sealed panel files')
    ap.add_argument('--panel-suffix', default='', choices=['', DECONTAM_SUFFIX],
                    help="'' for sheet.jsonl and rpn.jsonl (v1), '.v2' for sheet.v2.jsonl and rpn.v2.jsonl")
    a = ap.parse_args(argv)
    rep = audit_run(a.run_dir, a.panel, a.panel_suffix)
    print(json.dumps(rep, indent=1, sort_keys=True))
    return 0 if rep['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
