"""The talker's reporting lines (talker thread, G2f; talker/G2F-BUILD-SPEC-2026-10-11.md sec. 5; marks: talker/MARKS-TALKER-CHECKS-2026-10-11.md). Read-only: nothing here trains.

Ben's rule 2: "the talker shouldn't get a pointer from the thinker, it just transcribes the thoughts of the thinker ... It literally is a math to language translator." These functions
ask, on dev rows, whether the written lines are right and where the answer came from. They need only B3G2's public interface (run, state_of, talk, generate; run's `records`
[(round, call text, reply)] per row), so they also serve b3at, b3 group 1 (its `calls` [(round, op, a, b, reply)] stand in for `records`) and, for R2's final-answer split, any
model with .generate (the plain arms).

  R1  call_lines(model, rows)        operand exact-match on the WRITTEN call lines (free run, learned stop, as the evals use).
  R2  copyable_split(model, rows)    final accuracy on rows whose gold answer is copyable from the prompt or the last tool reply, and on the others; operand exact-match on the copyable rows.
  R3  scrambled_table(result, rows)  from a RESULT.json: full / shuffle_state / zero_state accuracy per family beside each family's answer-collision baseline; tk1() reads it (TK-1).

One free run feeds R1 and R2: free_runs(model, rows) -> {row id: dict(records, answer)}; pass it as `runs=` to both (B3G2.extra_evals does so) and the model runs once.
CLI (arms = checkpoints, the same dev rows for every arm):
  python -m custom_io.talker_report --run RUN_DIR [RUN_DIR ...] [--caps CAPS.json] [--data DIR] [--splits in_dist,answer] [--max N] [--gap A B]
  python -m custom_io.talker_report --result RESULT.json [--data DIR] [--split all]          (R3 and the TK-1 reading: pooled dev over all six splits by default, the in_dist reading printed beside it)"""
import argparse, contextlib, json, os, re
import torch
from custom_io.data import DEFAULT_DATA, DEV_SPLITS, Dataset, collate, to_device
from custom_io.evalx import _dev_rows, evaluate, is_hit, norm
from custom_io.models import progtext
from custom_io.models.tool import NAMES, calc

CALC = tuple(NAMES[1:])
TK1_SLACK = 5.0          # TK-1 pass: pooled shuffle_state accuracy <= pooled answer-collision baseline + 5 points
TK1_HALF = 0.5           # TK-1 proved wrong: shuffle_state accuracy >= half of the full accuracy


# ---------------------------------------------------------------- loading a checkpoint
def _ckpt(run):
    return run if run.endswith('.pt') else os.path.join(run, 'checkpoint.pt')


def caps_of_run(run):
    """The caps.json the job trained this checkpoint under, found from its run directory (a checkpoint.pt does not record them; train.py records `--caps PATH` in RESULT.json's config and
    g8a/job.py copies the caps used to caps.json in the job's results dir: next to the arm dirs for a --local job, in <tag>-pool beside the <tag>-<arm> dirs otherwise). Looked for in order:
    RESULT.json config.caps if that file still exists (a RESULT that says caps null means none: None), caps.json in the run dir, caps.json in its parent, caps.json in a '*-pool' sibling
    (only if exactly one). -> path or None. A run trained under caps does NOT reload without them: the position / place tables are sized by the caps (g8a/caps.py apply)."""
    d = os.path.dirname(os.path.abspath(_ckpt(run)))
    rf = os.path.join(d, 'RESULT.json')
    if os.path.exists(rf):
        try:
            cfg = json.load(open(rf)).get('config') or {}
        except ValueError:
            cfg = {}
        if cfg.get('caps') and os.path.exists(cfg['caps']):
            return cfg['caps']
        if 'caps' in cfg and not cfg['caps']:          # the run says it trained with no caps
            return None
    par = os.path.dirname(d)
    for f in (os.path.join(d, 'caps.json'), os.path.join(par, 'caps.json')):
        if os.path.exists(f):
            return f
    pools = [os.path.join(par, x, 'caps.json') for x in sorted(os.listdir(par)) if x.endswith('-pool')] if os.path.isdir(par) else []
    pools = [f for f in pools if os.path.exists(f)]
    return pools[0] if len(pools) == 1 else None


def load_checkpoint(run, device='cpu', caps=None):
    """custom_io.models.load_model(checkpoint) with the caps the run trained under applied FIRST (custom_io.g8a.caps.apply, as train.py does before it builds anything): `caps` is a caps.json
    path (the --caps option), else the one caps_of_run finds, else the defaults (caps.apply({}) resets what an earlier arm in this process applied). -> the model. Prints which caps were applied."""
    from custom_io.models import load_model
    caps = caps or caps_of_run(run)
    if caps:
        from custom_io.g8a import caps as _caps
        _caps.apply(json.load(open(caps)))
        print(f'caps applied from {caps}')
    else:       # caps.apply patched the module globals and nothing resets them: an earlier caps-trained arm in this process must not leak into this one
        from custom_io.g8a import caps as _caps
        _caps.apply({})
    return load_model(_ckpt(run), device)


# ---------------------------------------------------------------- running the model
def _batches(model, rows, size, device):
    """Rows (any order) -> [(row indices, collated batch on the device)], length-sorted so a batch has little padding (as evalx.evaluate)."""
    ds = Dataset(rows, model.vocab, strict=False)
    order = sorted(range(len(rows)), key=lambda i: len(rows[i]['prompt']))
    return [(order[s:s + size], to_device(collate([ds[i] for i in order[s:s + size]]), device)) for s in range(0, len(order), size)]


def _record_of(c):
    """One entry of run()'s output -> (round, call text, reply). B3G2 records are already that; a group-1 call (round, op, a, b, reply) is rendered `op a b`."""
    if len(c) == 3:
        return tuple(c)
    t, op, a, b, rep = c[:5]
    name = NAMES[op] if isinstance(op, int) and 0 <= op < len(NAMES) else str(op).lower()
    return (t, ' '.join(x for x in (name, str(a), str(b)) if x != ''), rep)


@contextlib.contextmanager
def _nullamp():
    yield


@torch.no_grad()
def free_runs(model, rows, batch_size=64, device=None, amp=None):
    """The free run the evals use (model.run with the learned stop, then model.talk on the run's state) over `rows`
    -> {row id: dict(records=[(round, call text, reply)], answer=str)}. `records` are the lines the model WROTE (notes included), in order, up to the row's stop round; `answer` is the
    final line, the same text model.generate gives. amp: a context-manager factory (train.py's), default none. A model with no run / state_of / talk is not run here (see copyable_split)."""
    device = device or next(model.parameters()).device
    was = model.training
    model.eval()
    amp = amp or _nullamp
    out = {}
    for idx, b in _batches(model, rows, batch_size, device):
        with amp():
            o = model.run(b)
            ans = model.talk(model.state_of(o), b)
        recs = o.get('records') or [[_record_of(c) for c in cs] for cs in o['calls']]
        for j, i in enumerate(idx):
            out[rows[i]['id']] = dict(records=[tuple(r) for r in recs[j]], answer=ans[j])
    model.train(was)
    return out


# ---------------------------------------------------------------- R1
def gold_calls(row):
    """The row's gold calculator calls as written (progtext.steps_of with as_written=True), notes left out: [dict(op, a, b, ...)]; [] when the row has no readable steps."""
    calls, _ = progtext.steps_of(row, True)
    return [c for c in (calls or []) if c['op'] != 'note']


def written_calls(records):
    """The calculator lines among the written lines: every line whose first word is not `note` (an unknown tool name is still a written calculator line, and counts as a wrong name) -> [(name, operand tokens, text)]."""
    out = []
    for _, txt, _rep in records:
        name, _, rest = txt.partition(' ')
        if name != 'note':
            out.append((name, rest.split(), txt))
    return out


def _tally(d, key, name, ops, line):
    c = d.setdefault(key, dict(n_gold_calls=0, name=0, operands=0, line=0))
    c['n_gold_calls'] += 1
    c['name'] += name
    c['operands'] += ops
    c['line'] += line


def _rate(k, n):
    """100 * k / n in percent; None (printed n/a) for an empty group, never a 0.0 that reads as a measurement."""
    return None if n == 0 else 100 * k / n


def _pct(c):
    n = c['n_gold_calls']
    return dict(c, name_pct=_rate(c['name'], n), operands_pct=_rate(c['operands'], n), line_pct=_rate(c['line'], n))


def row_calls(row, run):
    """-> [(name exact, operands exact, line exact)] per gold calculator call of the row, the k-th gold call against the k-th WRITTEN calculator line (none written = all False), and the
    row's number of written calculator lines. name: the first word equals the gold op. operands: the two operand tokens equal the gold a and b AS STRINGS. line: the whole text equals progtext.text(gold)."""
    gold, wr = gold_calls(row), written_calls(run['records'])
    res = []
    for k, g in enumerate(gold):
        if k >= len(wr):
            res.append((False, False, False))
            continue
        name, toks, txt = wr[k]
        res.append((name == g['op'], toks == [g['a'], g['b']], txt == progtext.text(g)))
    return res, len(wr)


def call_lines(model, rows, runs=None, batch_size=64, device=None, amp=None, per_row=False):
    """R1, operand exact-match on written call lines (sealed reporting line). Over the dev rows that have at least one gold calculator call (as-written steps), the free run writes lines;
    the k-th written calculator line is compared with the k-th gold calculator call (notes left out of both). Per gold call: `name` (first word = the gold op), `operands` (both operand
    tokens equal the gold a and b as strings), `line` (the whole text equals the gold line). A gold call with no k-th written line is a miss on all three.
    -> dict(rows (rows with gold calls), n_gold_calls, n_written_calc_lines (lines written on those rows), extra_written (written calculator lines beyond the row's gold count, summed),
    name / operands / line (counts of gold calls), name_pct / operands_pct / line_pct, pooled=..., by_family={family: same keys}) (+ per_row {id: [[name, operands, line] per gold call]} with per_row=True).
    runs: free_runs(...)'s result, to share one pass with R2."""
    runs = free_runs(model, rows, batch_size, device, amp) if runs is None else runs
    tot, fam, per = dict(n_gold_calls=0, name=0, operands=0, line=0), {}, {}
    n_rows = n_wr = extra = 0
    fx, fr, fw = {}, {}, {}
    for r in rows:
        gold = gold_calls(r)
        if not gold or r['id'] not in runs:
            continue
        res, nw = row_calls(r, runs[r['id']])
        n_rows += 1
        n_wr += nw
        e = max(0, nw - len(gold))
        extra += e
        f = r['family']
        fr[f], fw[f], fx[f] = fr.get(f, 0) + 1, fw.get(f, 0) + nw, fx.get(f, 0) + e
        per[r['id']] = [list(x) for x in res]
        for nm, op, ln in res:
            _tally(fam, f, nm, op, ln)
            for k, v in zip(('name', 'operands', 'line'), (nm, op, ln)):
                tot[k] += v
            tot['n_gold_calls'] += 1
    out = _pct(tot)
    out.update(rows=n_rows, n_written_calc_lines=n_wr, extra_written=extra,
               by_family={f: dict(_pct(c), rows=fr[f], n_written_calc_lines=fw[f], extra_written=fx[f]) for f, c in sorted(fam.items())})
    out['pooled'] = {k: out[k] for k in ('rows', 'n_gold_calls', 'n_written_calc_lines', 'extra_written', 'name', 'operands', 'line', 'name_pct', 'operands_pct', 'line_pct')}
    if per_row:
        out['per_row'] = per
    return out


# ---------------------------------------------------------------- R2
def _token_in(ans, text):
    """`ans` occurs in `text` as a whole token: not inside a longer number or word (no letter or digit directly before or after it, no `3.` before a number answer's digits or `.5` / `,5`
    after them, so '12' is not in '3.12' or '12.5' or '1,200')."""
    if ans == '':
        return False
    pat = r'(?<![A-Za-z0-9])' + re.escape(ans) + r'(?![A-Za-z0-9])'
    for m in re.finditer(pat, text):
        a, b = m.start(), m.end()
        if ans[0].isdigit() and a >= 2 and text[a - 1] in '.,' and text[a - 2].isdigit():
            continue
        if ans[-1].isdigit() and b + 1 < len(text) and text[b] in '.,' and text[b + 1].isdigit():
            continue
        return True
    return False


def last_reply(row):
    """The last gold tool reply: the real calculator reply (tool.calc) of the row's last gold calculator call, '' when it has none."""
    g = gold_calls(row)
    return calc(g[-1]['op'], g[-1]['a'], g[-1]['b']) if g else ''


def is_copyable(row):
    """R2: the gold answer appears verbatim, as a whole token, in the prompt or in the last gold tool reply."""
    ans = row['answer']
    return _token_in(ans, row['prompt']) or _token_in(ans, last_reply(row))


def copyable_split(model, rows, preds=None, runs=None, lines=None, batch_size=64, device=None, amp=None, norm=norm):
    """R2, the copyable / other split (sealed reporting line, fifth Addendum). A row is `copyable` if its gold answer appears verbatim in the prompt or in the last gold tool reply as a whole
    token (is_copyable). Final-answer accuracy is the evals' own (evalx.is_hit under `norm`), pooled and per family, on the copyable rows and on the others; `gap` = other - copyable
    (points; None when either group is empty, as is any exact with n == 0 and an operands_pct with no gold calls: printed n/a); and on the copyable rows (and the others) the operand exact-match of R1 (`operands_pct` over their gold calculator calls) when the model has a run (AT-1's reported line).
    preds: {row id: answer text} if you already have the final answers (all a plain arm needs; no operand numbers then unless runs / lines are given). runs: free_runs(...)'s result.
    lines: call_lines(..., per_row=True)'s result. With none of these the model is run: free_runs if it has run / state_of / talk, else evalx.evaluate's generate.
    -> dict(n, correct, exact, copyable=dict(n, correct, exact, by_family={f: {correct, n, exact}}, operands=dict(n_gold_calls, operands, operands_pct) or None), other=same, gap)."""
    if preds is None:
        if runs is None and all(hasattr(model, a) for a in ('run', 'state_of', 'talk')):
            runs = free_runs(model, rows, batch_size, device, amp)
        if runs is not None:
            preds = {i: v['answer'] for i, v in runs.items()}
        else:
            preds = evaluate(model, rows, batch_size, device, return_preds=True, norm=norm)['preds']
    per = (lines or {}).get('per_row')
    if per is None and runs is not None:
        per = call_lines(model, rows, runs=runs, per_row=True)['per_row']
    parts = {k: dict(n=0, correct=0, by_family={}, ops=0, calls=0) for k in ('copyable', 'other')}
    for r in rows:
        if r['id'] not in preds:
            continue
        p, hit = parts['copyable' if is_copyable(r) else 'other'], int(is_hit(preds[r['id']], r, norm))
        p['n'] += 1
        p['correct'] += hit
        c = p['by_family'].setdefault(r['family'], dict(correct=0, n=0))
        c['correct'] += hit
        c['n'] += 1
        for _, ops, _ in (per or {}).get(r['id'], []):
            p['calls'] += 1
            p['ops'] += ops
    out = {}
    for k, p in parts.items():
        out[k] = dict(n=p['n'], correct=p['correct'], exact=_rate(p['correct'], p['n']),
                      by_family={f: dict(c, exact=_rate(c['correct'], c['n'])) for f, c in sorted(p['by_family'].items())},
                      operands=None if per is None else dict(n_gold_calls=p['calls'], operands=p['ops'], operands_pct=_rate(p['ops'], p['calls'])))
    n, c = sum(p['n'] for p in parts.values()), sum(p['correct'] for p in parts.values())
    return dict(n=n, correct=c, exact=_rate(c, n), **out, gap=_sub(out['other']['exact'], out['copyable']['exact']))


def _sub(x, y):
    """x - y, None when either is None (an empty group has no rate, so no gap)."""
    return None if x is None or y is None else x - y


def arm_gap(a, b):
    """Two copyable_split results (arm a, arm b) -> a - b in points on copyable, other and all rows (+ operands on copyable when both have them)."""
    d = {k: _sub(a[k]['exact'], b[k]['exact']) for k in ('copyable', 'other')}
    d['all'] = _sub(a['exact'], b['exact'])
    oa, ob = a['copyable'].get('operands'), b['copyable'].get('operands')
    d['operands_copyable'] = None if oa is None or ob is None else _sub(oa['operands_pct'], ob['operands_pct'])
    return d


# ---------------------------------------------------------------- R3
def collision(rows, norm=norm):
    """Answer-collision baseline per family: the chance that a random OTHER row of the same family has the same (normalised) gold answer, sum_a c_a (c_a - 1) / (n (n - 1)), in percent
    -> {family: dict(n, baseline)} (baseline None for a family of fewer than 2 rows); a family of fewer than 2 rows has baseline None (no pair to collide; skipped in the pooled weighting, printed n/a). This is what a swapped-in state's answer scores by luck (shuffle_state hands each row another row's thoughts)."""
    fam = {}
    for r in rows:
        fam.setdefault(r['family'], {})
        a = norm(r['answer'])
        fam[r['family']][a] = fam[r['family']].get(a, 0) + 1
    out = {}
    for f, cs in sorted(fam.items()):
        n = sum(cs.values())
        out[f] = dict(n=n, baseline=100 * sum(c * (c - 1) for c in cs.values()) / (n * (n - 1)) if n > 1 else None)
    return out


def _fam_acc(res, splits):
    """RESULT-style {split: {by_family: {f: {correct, n}}}} -> {f: [correct, n]} summed over `splits`."""
    acc = {}
    for s in splits:
        for f, c in ((res or {}).get(s) or {}).get('by_family', {}).items():
            a = acc.setdefault(f, [0, 0])
            a[0] += c['correct']
            a[1] += c['n']
    return acc


def scrambled_table(result, rows=None, split='in_dist'):
    """R3 from a RESULT.json dict (train.py's): per family, full accuracy next to the shuffle_state and zero_state lesion accuracy (result['final_eval'] and result['lesions'][..], already
    recorded) and the family's answer-collision baseline (collision(rows)); `split` is one dev split, or 'all' for the six pooled (rows then = all six files). Everything in percent.
    -> dict(split, families={f: dict(n, full, shuffle_state, zero_state, collision)}, pooled=dict(n, full, shuffle_state, zero_state, collision)); pooled collision = the family baselines
    weighted by each family's row count in the table (the pooled hit rate a random swap within families would score); None where `rows` is not given. Note: the lesion swaps within a
    batch of evalx.evaluate (length-sorted), so the donor is not always of the same family; the same-family baseline is the mark's definition."""
    splits = DEV_SPLITS if split == 'all' else [split]
    full = _fam_acc(result.get('final_eval'), splits)
    les = {k: _fam_acc((result.get('lesions') or {}).get(k), splits) for k in ('shuffle_state', 'zero_state')}
    col = collision([r for r in (rows or [])]) if rows else {}
    pc = lambda a: None if a is None or not a[1] else 100 * a[0] / a[1]
    fams, tot = {}, dict(n=0, full=[0, 0], shuffle_state=[0, 0], zero_state=[0, 0], col=0.0, col_n=0)
    for f in sorted(full):
        row = dict(n=full[f][1], full=pc(full[f]), shuffle_state=pc(les['shuffle_state'].get(f)), zero_state=pc(les['zero_state'].get(f)), collision=col[f]['baseline'] if f in col else None)
        fams[f] = row
        tot['n'] += full[f][1]
        for k, a in (('full', full.get(f)), ('shuffle_state', les['shuffle_state'].get(f)), ('zero_state', les['zero_state'].get(f))):
            if a:
                tot[k][0] += a[0]
                tot[k][1] += a[1]
        if f in col and col[f]['baseline'] is not None:
            tot['col'] += col[f]['baseline'] * full[f][1]
            tot['col_n'] += full[f][1]
    pooled = dict(n=tot['n'], full=pc(tot['full']), shuffle_state=pc(tot['shuffle_state']), zero_state=pc(tot['zero_state']), collision=tot['col'] / tot['col_n'] if tot['col_n'] else None)
    return dict(split=split, families=fams, pooled=pooled)


def tk1(table):
    """TK-1 (marks 10-11, with the seventh Addendum's middle zone). Two clauses, both computed and both reported: the PASS clause (pooled shuffle_state accuracy at most the pooled collision
    baseline + 5 points) and the PROVED-WRONG clause (shuffle_state accuracy at least half the full accuracy). Reading: PASS only when the pass clause holds and the proved-wrong clause does
    not; PROVED WRONG only when the proved-wrong clause holds and the pass clause does not; UNCLEAR when both hold or neither does (the middle zone: reported, not a pass; with a low full
    accuracy or a high baseline the two clauses can overlap, and then neither reading is earned); 'n/a' with a missing number (or no rows for the baseline when the proved-wrong clause also fails).
    -> dict(reading, shuffle_state, full, collision, passes (the pass clause), proved_wrong (the proved-wrong clause))."""
    p = table['pooled']
    if p['shuffle_state'] is None or p['full'] is None:
        return dict(reading='n/a', **{k: p.get(k) for k in ('shuffle_state', 'full', 'collision')}, passes=None, proved_wrong=None)
    wrong = p['shuffle_state'] >= TK1_HALF * p['full'] and p['full'] > 0
    ok = p['collision'] is not None and p['shuffle_state'] <= p['collision'] + TK1_SLACK
    if ok != wrong:
        reading = 'PASS' if ok else 'PROVED WRONG'
    else:       # both clauses hold, or neither
        reading = 'UNCLEAR' if p['collision'] is not None else 'n/a (no rows for the baseline)'
    return dict(reading=reading, shuffle_state=p['shuffle_state'], full=p['full'], collision=p['collision'], passes=ok, proved_wrong=wrong)


# ---------------------------------------------------------------- the line B3G2.extra_evals carries (key `talker`)
def talker_evals(model, rows, batch_size=64, device=None, amp=None, runs=None):
    """R1 and R2 in one pass (one free run) -> dict(call_lines=call_lines(...), copyable=copyable_split(...)) for B3G2.extra_evals (key `talker`).
    runs: free runs the caller already did over `rows` ({id: dict(records, answer)}, as free_runs gives); then no second run is made."""
    runs = runs if runs is not None else free_runs(model, rows, batch_size, device, amp)
    lines = call_lines(model, rows, runs=runs, per_row=True)
    cs = copyable_split(model, rows, runs=runs, lines=lines)
    lines.pop('per_row')
    return dict(call_lines=lines, copyable=cs)


# ---------------------------------------------------------------- printing and the CLI
def _f(x, w=6):
    return ' ' * (w - 3) + 'n/a' if x is None else f'{x:{w}.1f}'


def _p(x, w=0):
    """A percent for printing: 'n/a' for None (an empty group), else one decimal and a %."""
    return ('n/a' if x is None else f'{x:.1f}%').rjust(w + (1 if x is not None else 0))


def format_split(name, s):
    L = [f'== {name}: {s["correct"]}/{s["n"]} = {_p(s["exact"])}']
    for k in ('copyable', 'other'):
        p = s[k]
        op = '' if not p['operands'] else f'   operands {p["operands"]["operands"]}/{p["operands"]["n_gold_calls"]} = {_p(p["operands"]["operands_pct"])}'
        L.append(f'  {k:9s} n={p["n"]:5d} final {p["correct"]:5d} = {_p(p["exact"], 5)}{op}')
    L.append(f'  gap (other - copyable) {"n/a" if s["gap"] is None else format(s["gap"], "+.1f")} points')
    fams = sorted(set(s['copyable']['by_family']) | set(s['other']['by_family']))
    L.append('  family                   copyable (n, %)    other (n, %)')
    for f in fams:
        a, b = s['copyable']['by_family'].get(f), s['other']['by_family'].get(f)
        L.append(f'  {f:22s} {a["n"] if a else 0:6d} {_f(a and a["exact"])}   {b["n"] if b else 0:6d} {_f(b and b["exact"])}')
    return '\n'.join(L)


def format_calls(c):
    L = [f'R1 written call lines: {c["rows"]} rows, {c["n_gold_calls"]} gold calls, {c["n_written_calc_lines"]} written calculator lines, {c["extra_written"]} extra',
         f'  name {_p(c["name_pct"])}  operands {_p(c["operands_pct"])}  line {_p(c["line_pct"])}']
    for f, v in c['by_family'].items():
        L.append(f'  {f:22s} calls {v["n_gold_calls"]:5d}  name {_f(v["name_pct"], 5)}  operands {_f(v["operands_pct"], 5)}  line {_f(v["line_pct"], 5)}  extra {v["extra_written"]}')
    return '\n'.join(L)


def format_table(t):
    L = [f'R3 scrambled thoughts ({t["split"]}); % correct   collision = chance another row of the family has the same answer', f'  {"family":22s}{"n":>6}{"full":>8}{"shuffle":>8}{"zero":>8}{"collide":>8}']
    for f, v in list(t['families'].items()) + [('POOLED', t['pooled'])]:
        L.append(f'  {f:22s}{v["n"]:6d}{_f(v["full"], 8)}{_f(v["shuffle_state"], 8)}{_f(v["zero_state"], 8)}{_f(v["collision"], 8)}')
    return '\n'.join(L)


def dev_rows(data, splits, max_per_split=None):
    """The dev rows of the named splits, de-duplicated by id, each file subsampled to max_per_split rows spread evenly (evalx.subsample)."""
    rows, seen = [], set()
    for s in splits:
        for r in _dev_rows(data, s, max_per_split):
            if r['id'] not in seen:
                seen.add(r['id'])
                rows.append(r)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--run', nargs='*', default=[], help='run dirs (each with checkpoint.pt) or checkpoint.pt paths: the arms, evaluated on the same dev rows')
    ap.add_argument('--caps', help='caps.json the checkpoints were trained under (a caps-trained model does not reload without it); default: the one the run directory records (RESULT.json config.caps or the job\'s caps.json)')
    ap.add_argument('--result', nargs='*', default=[], help='RESULT.json files: print R3 and the TK-1 reading')
    ap.add_argument('--data', default=DEFAULT_DATA)
    ap.add_argument('--splits', default='in_dist', help='comma list of dev splits (or all) for --run')
    ap.add_argument('--split', default='all', help='the dev split (or all, the default: the six pooled) of the --result table and its TK-1 reading; the in_dist table and reading are printed beside it')
    ap.add_argument('--max', type=int, help='cap rows per dev split')
    ap.add_argument('--gap', nargs=2, type=int, metavar=('A', 'B'), help='arm indexes (0-based, in --run order): print arm A minus arm B')
    ap.add_argument('--device', default='cpu')
    ap.add_argument('--batch', type=int, default=64)
    ap.add_argument('--json', help='also write everything printed to this file')
    a = ap.parse_args(argv)
    rec = {}
    if a.run:
        splits = DEV_SPLITS if a.splits == 'all' else a.splits.split(',')
        rows = dev_rows(a.data, splits, a.max)
        print(f'{len(rows)} dev rows ({",".join(splits)}); copyable rows {sum(map(is_copyable, rows))}')
        arms = []
        for p in a.run:
            m = load_checkpoint(p, a.device, a.caps)
            has_run = all(hasattr(m, x) for x in ('run', 'state_of', 'talk'))
            runs = free_runs(m, rows, a.batch, a.device) if has_run else None
            lines = call_lines(m, rows, runs=runs, per_row=True) if runs is not None else None
            sp = copyable_split(m, rows, runs=runs, lines=lines, batch_size=a.batch, device=a.device)
            arms.append(sp)
            print(format_split(p, sp))
            if lines:
                print(format_calls(lines))
                lines.pop('per_row')
            rec[p] = dict(copyable_split=sp, call_lines=lines)
        if a.gap:
            g = arm_gap(arms[a.gap[0]], arms[a.gap[1]])
            rec['gap'] = dict(a=a.run[a.gap[0]], b=a.run[a.gap[1]], **g)
            sg = lambda x: 'n/a' if x is None else f'{x:+.1f}'
            print(f'GAP {a.run[a.gap[0]]} minus {a.run[a.gap[1]]} (points): copyable {sg(g["copyable"])}  other {sg(g["other"])}  all {sg(g["all"])}'
                  + ('' if g['operands_copyable'] is None else f'  operands on copyable {sg(g["operands_copyable"])}'))
    for p in a.result:
        res = json.load(open(p))
        emax = (res.get('config') or {}).get('eval_max')     # the baseline rows are the rows the RESULT's accuracies came from: evalx's own subsample of each split at the run's eval_max
        print(p + (f'  (eval_max {emax}: baseline rows subsampled the same way)' if emax else ''))
        rec[p] = {}
        for sp, label in ((a.split, 'TK-1 (pooled dev, %s)' % ('all six splits' if a.split == 'all' else a.split)), ('in_dist', 'TK-1 in_dist (beside it, not the default reading)')):
            if sp == a.split and label.startswith('TK-1 in_dist'):
                continue
            splits = DEV_SPLITS if sp == 'all' else [sp]
            t = scrambled_table(res, dev_rows(a.data, splits, emax) if os.path.isdir(a.data) else None, sp)
            print(format_table(t))
            print(label + ':', json.dumps(tk1(t)))
            rec[p]['table' if sp == a.split else 'table_in_dist'], rec[p]['tk1' if sp == a.split else 'tk1_in_dist'] = t, tk1(t)
    if a.json:
        json.dump(rec, open(a.json, 'w'), indent=1)
    return rec


if __name__ == '__main__':
    main()
