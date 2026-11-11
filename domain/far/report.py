"""Far-transfer report for one finished domain-mode run (analysis only; no training, never writes into the run).

  python3 -m domain.far.report --run RUN --panel PANEL_V3 [--panel-v2 PANEL_V2] [--probe PROBE_JSONL]
                               [--compare CKPT ...] [--threads 2] [--out DIR]

Reads parent, final checkpoint and tool from RUN/summary.json; writes FAR.json and FAR.md to --out (default RUN/analysis).
Sections: 1 panel near/far (parent, final), trainable far; 2 far accuracy by whether the digit shape was practised;
3 practice coverage per ring; 4 sheet probe cells. Only scored kinds count. Each (checkpoint, file) is scored once.
"""
import argparse
import hashlib
import json
import os
import re
from collections import Counter

SHEET_SCORED = ('SUM', 'MAX', 'MIN', 'PRODUCT', 'cell arithmetic', 'division', 'ABS')
RPN_UNSCORED = ('a b %',)
UNTRAINABLE_OPS = ('mod', 'cmp')
SHEET_FUNCS = ('SUM', 'MAX', 'MIN', 'PRODUCT', 'ABS', 'MOD', 'COUNTIF', 'IF')


def scored(tool, kind):
    return kind in SHEET_SCORED if tool == 'sheet' else kind not in RPN_UNSCORED


def pct(k, n):
    return round(100.0 * k / n, 2) if n else None


def acc(rows, hits):
    """rows: panel rows; hits: id -> 0/1. -> {'n','hits','pct'}."""
    k = sum(hits[r['id']] for r in rows)
    return dict(n=len(rows), hits=k, pct=pct(k, len(rows)))


def shape_of(prompt):
    return re.sub(r'[0-9]+', '#', prompt)


def is_trainable(tool_mod, prompt):
    try:
        steps = tool_mod.evaluate(prompt).get('steps', [])
    except Exception:
        return True
    return not any(s[0] in UNTRAINABLE_OPS for s in steps)


def _sheet_props(prompt):
    from domain.far.coverage import parse_sheet
    m = parse_sheet(prompt)
    return dict(grid_ge5=m['grid_rows'] >= 5, range_ge5=m['max_range_cells'] >= 5,
                ref_row5plus=m['max_row_ref'] >= 5, two_kinds=bool(m['two_kinds']))


def _rpn_ops(prompt):
    from domain.far.coverage import parse_rpn
    return parse_rpn(prompt)['n_ops']


def coverage(tool, practice):
    """practice: list of (ring, prompt). Per ring and pooled."""
    out = {}
    groups = {'pooled': practice}
    for ring in sorted({r for r, _ in practice}):
        groups[f'ring{ring}'] = [x for x in practice if x[0] == ring]
    for name, items in groups.items():
        n, bad = len(items), 0
        if tool == 'sheet':
            keys = ('grid_ge5', 'range_ge5', 'ref_row5plus', 'two_kinds')
            cnt = Counter()
            for _, p in items:
                try:
                    props = _sheet_props(p)
                except Exception:
                    bad += 1
                    continue
                for k in keys:
                    cnt[k] += props[k]
            ok = n - bad
            out[name] = dict(rows=n, unparsed=bad, **{k: dict(n=cnt[k], of=ok, pct=pct(cnt[k], ok)) for k in keys})
        else:
            hist = Counter()
            for _, p in items:
                try:
                    hist[_rpn_ops(p)] += 1
                except Exception:
                    bad += 1
            ok = n - bad
            ge4 = sum(v for k, v in hist.items() if k >= 4)
            out[name] = dict(rows=n, unparsed=bad, ops_ge4=dict(n=ge4, of=ok, pct=pct(ge4, ok)),
                             ops_hist={str(k): hist[k] for k in sorted(hist)})
    return out


def read_practice(log_path):
    items = []
    with open(log_path) as f:
        for line in f:
            if '"row"' not in line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get('event') == 'row' and d.get('source') in ('own', 'tool'):
                items.append((int(d.get('ring') or 1), d['prompt']))
    return items


def sha256(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def ckpt_label(path):
    parts = os.path.normpath(path).split(os.sep)
    night = next((p for p in reversed(parts) if re.fullmatch(r'night_\d+', p)), None)
    run = parts[parts.index(night) - 1] if night else parts[-2] if len(parts) > 1 else parts[-1]
    return f'{run}/{night}' if night else run


class Scorer:
    def __init__(self):
        self.cache = {}

    def hits(self, ckpt, panel_path, rows):
        key = (os.path.realpath(ckpt), os.path.realpath(panel_path))
        if key not in self.cache:
            from domain.score import score
            res = score(ckpt, rows, ckpt_label(ckpt))
            self.cache[key] = {r['id']: r['hit'] for r in res['rows']}
        return self.cache[key]


def panel_sections(tool, tool_mod, rows, hp, hf, practice_shapes):
    """rows: scored-kind panel rows. hp/hf: parent/final hits."""
    near = [r for r in rows if r['split'] == 'near']
    far = [r for r in rows if r['split'] == 'far']
    tr = [r for r in far if is_trainable(tool_mod, r['prompt'])]
    sec1 = {}
    for split, rs in (('near', near), ('far', far), ('far_trainable', tr)):
        p, f = acc(rs, hp), acc(rs, hf)
        sec1[split] = dict(parent=p, final=f,
                           after_minus_before=None if p['pct'] is None else round(f['pct'] - p['pct'], 2))
    sec1['trainable_share_of_far'] = dict(n=len(tr), of=len(far), pct=pct(len(tr), len(far)))
    trset = {r['id'] for r in tr}
    sec2 = {}
    for name, rs in (('far', far), ('far_trainable', tr)):
        seen = [r for r in rs if shape_of(r['prompt']) in practice_shapes]
        unseen = [r for r in rs if shape_of(r['prompt']) not in practice_shapes]
        sec2[name] = dict(seen=dict(parent=acc(seen, hp), final=acc(seen, hf)),
                          not_seen=dict(parent=acc(unseen, hp), final=acc(unseen, hf)))
    return sec1, sec2


def probe_section(rows, hits_by_label):
    cells = sorted({r['split'] for r in rows})
    return {lab: {c: acc([r for r in rows if r['split'] == c], h) for c in cells} for lab, h in hits_by_label.items()}


def cell(a):
    return '-' if a is None or a['pct'] is None else f"{a['pct']:.2f} (n={a['n']})"


def render_md(R):
    L = [f"# Far-transfer report: {os.path.basename(R['run'].rstrip('/'))}", '',
         f"- run: {R['run']}", f"- tool: {R['tool']}", f"- parent: {R['parent']}", f"- final: {R['final']}"]
    for name, p in R['panels'].items():
        L.append(f"- panel {name}: {p['path']} (sha256 {p['sha256']}; scored-kind rows {p['n_rows']})")
    for name, p in R['panels'].items():
        L += ['', f'## 1. Panel {name} (percent)', '', '| split | parent | final | after - before |', '|---|---|---|---|']
        for s in ('near', 'far', 'far_trainable'):
            d = p['section1'][s]
            L.append(f"| {s} | {cell(d['parent'])} | {cell(d['final'])} | {d['after_minus_before']} |")
        t = p['section1']['trainable_share_of_far']
        L.append(f"\nTrainable share of far rows: {t['pct']} ({t['n']}/{t['of']})")
        if p.get('section2'):
            L += ['', f'## 2. Past practice, panel {name} (far rows, percent)', '',
                  '| rows | shape seen: parent | seen: final | not seen: parent | not seen: final |', '|---|---|---|---|---|']
            for s in ('far', 'far_trainable'):
                d = p['section2'][s]
                L.append(f"| {s} | {cell(d['seen']['parent'])} | {cell(d['seen']['final'])} | "
                         f"{cell(d['not_seen']['parent'])} | {cell(d['not_seen']['final'])} |")
    L += ['', '## 3. Practice coverage (own + tool rows; percent)', '']
    cov = R['coverage']
    if R['tool'] == 'sheet':
        L += ['| group | rows | grid >=5 rows | range >=5 cells | ref row >=5 | two kinds |', '|---|---|---|---|---|---|']
        for g, d in cov.items():
            L.append(f"| {g} | {d['rows']} | " + ' | '.join(
                f"{d[k]['pct']} ({d[k]['n']})" for k in ('grid_ge5', 'range_ge5', 'ref_row5plus', 'two_kinds')) + ' |')
    else:
        L += ['| group | rows | 4+ operators | operator-count histogram |', '|---|---|---|---|']
        for g, d in cov.items():
            L.append(f"| {g} | {d['rows']} | {d['ops_ge4']['pct']} ({d['ops_ge4']['n']}) | {d['ops_hist']} |")
    if R.get('probe'):
        pr = R['probe']
        cells = list(next(iter(pr['by_checkpoint'].values())))
        L += ['', f"## 4. Probe cells ({pr['path']}; percent)", '', '| checkpoint | ' + ' | '.join(cells) + ' |',
              '|---|' + '---|' * len(cells)]
        for lab, d in pr['by_checkpoint'].items():
            L.append(f'| {lab} | ' + ' | '.join(cell(d[c]) for c in cells) + ' |')
    return '\n'.join(L) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--run', required=True)
    ap.add_argument('--panel', required=True)
    ap.add_argument('--panel-v2')
    ap.add_argument('--probe')
    ap.add_argument('--compare', nargs='*', default=[])
    ap.add_argument('--threads', type=int, default=2)
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    import torch
    torch.set_num_threads(a.threads)
    from domain.score import load_panel
    from domain.tools import rpn, sheet

    summ = json.load(open(os.path.join(a.run, 'summary.json')))
    tool = summ['tool']
    tool_mod = sheet if tool == 'sheet' else rpn
    parent, final = summ['parent'], summ['final_checkpoint']
    out_dir = a.out or os.path.join(a.run, 'analysis')
    os.makedirs(out_dir, exist_ok=True)
    practice = read_practice(os.path.join(a.run, 'log.jsonl'))
    shapes = {shape_of(p) for _, p in practice}
    sc = Scorer()
    R = dict(run=a.run, tool=tool, parent=parent, final=final, panels={})
    for name, path in (('v3', a.panel), ('v2', a.panel_v2)):
        if not path:
            continue
        rows = [r for r in load_panel(path) if scored(tool, r['kind'])]
        hp, hf = sc.hits(parent, path, rows), sc.hits(final, path, rows)
        s1, s2 = panel_sections(tool, tool_mod, rows, hp, hf, shapes)
        R['panels'][name] = dict(path=path, sha256=sha256(path), n_rows=len(rows), section1=s1,
                                 section2=s2 if name == 'v3' else None)
    R['practice_shapes'] = len(shapes)
    R['coverage'] = coverage(tool, practice)
    if a.probe:
        prows = [json.loads(x) for x in open(a.probe) if x.strip()]
        prows = [r for r in prows if scored(tool, r['kind'])]
        by = {}
        for lab, ck in [(ckpt_label(final), final)] + [(ckpt_label(c), c) for c in a.compare]:
            by[lab] = sc.hits(ck, a.probe, prows)
        R['probe'] = dict(path=a.probe, sha256=sha256(a.probe), n_rows=len(prows), by_checkpoint=probe_section(prows, by))
    with open(os.path.join(out_dir, 'FAR.json'), 'w') as f:
        json.dump(R, f, indent=1)
    with open(os.path.join(out_dir, 'FAR.md'), 'w') as f:
        f.write(render_md(R))
    print('wrote', out_dir, flush=True)


if __name__ == '__main__':
    main()
