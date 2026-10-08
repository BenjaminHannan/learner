"""T1S = T1 + span copy, the one link fix after the T1 screen (MARKS-D0-T1-2026-10-07.md Amendment 3, PASS-MARKS.md addendum 22), judged
exactly as sealed: T1S (model 'tool', cfg {"span_copy": true}) on seeds 200 and 201, against q33's plain B2 and q40's T1 of the same seed.
python3 -m custom_io.analyze_t1s --results custom_io/results/33-pc-confirm-b2 custom_io/results/40-vast-t1 custom_io/results/50-vast-t1s \
    --wc custom_io/results/51-vast-wc-t1 custom_io/results/52-vast-wc-t1s
write_copy is read as amended by Amendment 4 (6:10 PM ET, sealed before any re-screen result): only UNAMBIGUOUS copies count (the WC.json of
custom_io/rescore_wc.py, Tool.write_copy_u, for T1S and for T1's checkpoints re-scored once with the same scorer); every cell needs n >= 200, and a
cell below that is reported but cannot pass or fail by itself; ambiguous copies are reported apart, never counted; the old unfiltered numbers
are printed beside.
R1 write_copy exact copy >= 99 for operand AND answer at EACH length 1-9 separately, both seeds.
R2 pooled-5 T1S - B2 >= -2.0 on both seeds. R3 chain-5 >= 95 on both seeds, and no length 1-3 write_copy cell below T1's of the same seed.
R4 tool off (noexec program set) < 5 and call accuracy free run >= 98, both seeds.
Pass = R1-R4: then the 6-seed confirm with marks 1-6 as amended (Amendment 2; analyze_t1's confirm, T1S in T1's place) and H1 on these
checkpoints. Proved wrong for this fix (Amendment 5, 6:50 PM ET, read by path): an OPERAND cell at 4-9 digits below 90 on either seed. Operand
cells all >= 90 but an answer cell at 4-9 below 90: "NOT SHOWN: answer selection" (the next single change, sealed: a learned entry-index signal
on the span pointer's keys). Otherwise (some cell 90-99, or R2-R4): not shown.
A run counts only if status ok, the q33 recipe and the right size; a missing or invalid run: NOT JUDGED."""
import argparse, json, os, re
from custom_io import analyze_t1 as A
from custom_io.analyze import P5, C5, g, load, sub

SEEDS = [200, 201]
LENS = range(1, 10)
MIN_N = 200
ARMS = {'T1S': ('tool', {'span_copy': True}, 3311060), 'T1': A.ARMS['T1'], 'B2': A.ARMS['B2']}
# --arm T1SI: Amendment 5's single next change (T1S + the entry-index term on the span keys), judged in T1S's place with R1-R4 unchanged
NEXT = {'T1SI': ('tool', {'span_copy': True, 'span_idx': True}, 3311572),
        # --arm T1SD: Amendment 7's start-pointer change (T1SI + the distance-from-end table), judged by Amendment 7's marks (screen7)
        'T1SD': ('tool', {'span_copy': True, 'span_idx': True, 'span_end': True}, 3314132),
        # --arm T1SDR: Amendment 8's change (T1SD + drawn-result drills, ans_drill 0.25), judged by Amendment 8's marks (screen8), R5 against T1SD
        'T1SDR': ('tool', {'span_copy': True, 'span_idx': True, 'span_end': True, 'ans_drill': 0.25}, 3314132)}
MIN_N7 = 1000
NUM = re.compile(r'-?\d+')


def as_t1s(d, arm):
    """{(arm, seed): x} with `arm`'s entries in T1S's slot (the arm judged), every other T1S entry dropped."""
    return {(('T1S' if a == arm else a), s): x for (a, s), x in d.items() if a != 'T1S' or arm == 'T1S'}


def valid(r, arm):
    model, cfg, n = ARMS[arm]
    c = g(r, 'config') or {}
    bad = [f'{k}={c.get(k)!r} (want {v!r})' for k, v in A.RECIPE.items() if c.get(k) != v]
    if c.get('model') != model or (c.get('cfg') or {}) != cfg:
        bad.append(f"model {c.get('model')} cfg {c.get('cfg')} (want {model} {cfg})")
    if r.get('steps') != A.RECIPE['steps']:
        bad.append(f"trained {r.get('steps')} steps")
    if r.get('n_params') != n:
        bad.append(f"n_params {r.get('n_params')} (want {n})")
    return bad


def old_cells(r):
    """The old (unfiltered) write_copy of a RESULT.json by length -> {'operand': {L: (pct or None, n)}, 'answer': {...}}, printed beside only."""
    wc = g(r, 'extra', 'write_copy') or {}
    out = {}
    for side, key in (('operand', 'op_by_len'), ('answer', 'ans_by_len')):
        by = wc.get(key) or {}
        out[side] = {L: ((100 * by[str(L)][1] / by[str(L)][0]) if by.get(str(L)) and by[str(L)][0] else None, (by.get(str(L)) or [0])[0]) for L in LENS}
    return out


def wc_cells(w, amb=False):
    """A WC.json (rescore_wc) -> {'operand': {L: (pct or None, n)}, 'answer': {...}}: the unambiguous cells (or the ambiguous ones)."""
    u = (w or {}).get('write_copy_u') or {}
    return {side: {L: ((u.get(side + ('_ambiguous' if amb else '')) or {}).get(str(L), {}).get('exact'),
                       (u.get(side + ('_ambiguous' if amb else '')) or {}).get(str(L), {}).get('n', 0)) for L in LENS} for side in ('operand', 'answer')}


def load_wc(dirs):
    """{(arm, seed): WC.json} from every <arm>_s<seed>/WC.json under dirs."""
    out = {}
    for d in dirs or []:
        for root, _, fs in os.walk(d):
            m = re.match(r'^(.+)_s(\d+)$', os.path.basename(root))
            if 'WC.json' in fs and m:
                out[(m.group(1), int(m.group(2)))] = json.load(open(os.path.join(root, 'WC.json')))
    return out


def wc_problems(w, arm, run, min_n=MIN_N):
    """A WC.json counts only if it scored this arm's checkpoint (same name, cfg, size and step as its run) with the Amendment 4 scorer."""
    if w is None:
        return [f'{arm} WC.json missing']
    model, cfg, n = ARMS[arm]
    bad = []
    if w.get('name') != model or (w.get('cfg') or {}) != cfg or w.get('n_params') != n:
        bad.append(f"{arm} WC.json: model {w.get('name')} cfg {w.get('cfg')} n_params {w.get('n_params')}")
    if w.get('step') != run.get('steps'):
        bad.append(f"{arm} WC.json: checkpoint step {w.get('step')} vs run {run.get('steps')}")
    if (w.get('write_copy_u') or {}).get('min_n') != min_n:
        bad.append(f"{arm} WC.json: min_n {(w.get('write_copy_u') or {}).get('min_n')}")
    return bad


def screen(runs, wcs):
    probs, F = {}, {}
    for s in SEEDS:
        a, t1, b2 = runs.get(('T1S', s)), runs.get(('T1', s)), runs.get(('B2', s))
        p = []
        for arm, r in (('T1S', a), ('T1', t1), ('B2', b2)):
            p += [f'{arm} missing'] if r is None else [f'{arm}: {x}' for x in valid(r, arm)]
        if not p:
            p += wc_problems(wcs.get(('T1S', s)), 'T1S', a) + wc_problems(wcs.get(('T1', s)), 'T1', t1)
        probs[s] = p
        if p:
            continue
        ex = g(a, 'extra') or {}
        F[s] = dict(d_pooled5=sub(P5(a), P5(b2)), t1s_pooled5=P5(a), t1_pooled5=P5(t1), b2_pooled5=P5(b2), chain5=C5(a), t1_chain5=C5(t1),
                    copy=wc_cells(wcs[('T1S', s)]), t1_copy=wc_cells(wcs[('T1', s)]), copy_ambiguous=wc_cells(wcs[('T1S', s)], True),
                    t1_copy_ambiguous=wc_cells(wcs[('T1', s)], True), old_copy=old_cells(a), t1_old_copy=old_cells(t1),
                    passes=dict(T1S=wcs[('T1S', s)]['write_copy_u']['passes'], T1=wcs[('T1', s)]['write_copy_u']['passes']), tool_off=g(ex, 'noexec', 'program_families'), call_free=g(ex, 'op_acc', 'free_run', 'call'),
                    call_tf=g(ex, 'op_acc', 'teacher_forced', 'call'), free_program=g(ex, 'op_acc', 'free_run', 'program'),
                    span_use=ex.get('span_use'), swap_match=g(ex, 'opswap', 'swap_match'),
                    write_copy_n=dict(path_changed=g(ex, 'write_copy', 'path_changed'), too_long=g(ex, 'write_copy', 'too_long')))
    out = dict(seeds=SEEDS, problems=probs, judged=len(F) == len(SEEDS))
    if not out['judged']:
        out['verdict'] = 'NOT JUDGED'
        return out
    ok_cell = lambda c, lo: c[0] is not None and c[1] >= MIN_N and c[0] >= lo
    short = [(s, side, L, f['copy'][side][L][1]) for s, f in F.items() for side in ('operand', 'answer') for L in LENS if f['copy'][side][L][1] < MIN_N]
    r1 = {s: {side: {L: dict(exact=f['copy'][side][L][0], n=f['copy'][side][L][1]) for L in LENS} for side in ('operand', 'answer')} for s, f in F.items()}
    r3_cells = {s: {side: {L: dict(T1S=f['copy'][side][L][0], T1=f['t1_copy'][side][L][0]) for L in (1, 2, 3)} for side in ('operand', 'answer')}
                for s, f in F.items()}
    m = {'R1 write_copy exact copy >= 99, operand AND answer, EACH length 1-9, both seeds': dict(
             value=r1, ok=all(ok_cell(f['copy'][side][L], 99) for f in F.values() for side in ('operand', 'answer') for L in LENS)),
         'R2 pooled-5 T1S - B2 >= -2.0 on both seeds': dict(value={s: f['d_pooled5'] for s, f in F.items()},
                                                             ok=all(f['d_pooled5'] is not None and f['d_pooled5'] >= -2.0 for f in F.values())),
         'R3 chain-5 >= 95 on both seeds, and no length 1-3 write_copy cell below T1\'s (same seed)': dict(
             value=dict(chain5={s: f['chain5'] for s, f in F.items()}, cells=r3_cells),
             ok=all(f['chain5'] is not None and f['chain5'] >= 95 for f in F.values()) and all(
                 f['copy'][side][L][0] is not None and f['copy'][side][L][1] >= MIN_N
                 and (f['t1_copy'][side][L][0] is None or f['copy'][side][L][0] >= f['t1_copy'][side][L][0])
                 for f in F.values() for side in ('operand', 'answer') for L in (1, 2, 3))),
         'R4 tool off < 5 and call accuracy free run >= 98, both seeds': dict(
             value={s: dict(tool_off=f['tool_off'], call_free=f['call_free']) for s, f in F.items()},
             ok=all(f['tool_off'] is not None and f['tool_off'] < 5 and f['call_free'] is not None and f['call_free'] >= 98 for f in F.values()))}
    low = [(s, side, L, f['copy'][side][L][0]) for s, f in F.items() for side in ('operand', 'answer') for L in range(4, 10)
           if f['copy'][side][L][1] >= MIN_N and f['copy'][side][L][0] < 90]
    low_op = [x for x in low if x[1] == 'operand']
    out.update(marks=m, facts=F, proved_wrong=bool(low_op), proved_wrong_cells=low_op, below_90_cells=low, short_cells=short)
    if all(x['ok'] for x in m.values()):
        out['verdict'] = 'PASS: run the 6-seed confirm (marks 1-6 as amended) and H1 on these checkpoints'
    elif low_op:
        out['verdict'] = 'PROVED WRONG: span copy stands falsified; next = the diagnostic fine-tune on 4-9 digit rows'
    elif low:
        out['verdict'] = 'NOT SHOWN: answer selection (operand copy holds >= 90; next = the learned entry-index signal on the span keys, Amendment 5)'
    elif short:
        out['verdict'] = f'NOT JUDGED on R1/R3: {len(short)} cells below n = {MIN_N} (add test rows of those lengths)'
    else:
        out['verdict'] = 'NOT SHOWN: one more change, named from the per-length table'
    return out


def screen7(runs, wcs):
    """Amendment 7 (+ Clarification 7a) for T1SD, in T1S's slot: R1 per side and seed, the unweighted mean of the nine length cells >= 99 AND
    every cell >= 97, n >= 1000 per cell (reading (a), all nine >= 99, printed beside, not a mark); R2 pooled-5 - B2 >= -2.0; R3 1-3 digit
    operand and answer cells >= 99 and no more than 1.0 below T1's Amendment 4 re-score; R4 tool off < 5 and free-run call accuracy >= 98;
    S2 chain-5 >= 95. Proved wrong: any operand or answer cell at 4-9 digits < 90 on either seed."""
    probs, F = {}, {}
    for s in SEEDS:
        a, t1, b2 = runs.get(('T1S', s)), runs.get(('T1', s)), runs.get(('B2', s))
        p = []
        for arm, r in (('T1S', a), ('T1', t1), ('B2', b2)):
            p += [f'{arm} missing'] if r is None else [f'{arm}: {x}' for x in valid(r, arm)]
        if not p:
            p += wc_problems(wcs.get(('T1S', s)), 'T1S', a, MIN_N7) + wc_problems(wcs.get(('T1', s)), 'T1', t1)
        probs[s] = p
        if p:
            continue
        ex = g(a, 'extra') or {}
        F[s] = dict(d_pooled5=sub(P5(a), P5(b2)), t1s_pooled5=P5(a), t1_pooled5=P5(t1), b2_pooled5=P5(b2), chain5=C5(a), t1_chain5=C5(t1),
                    copy=wc_cells(wcs[('T1S', s)]), t1_copy=wc_cells(wcs[('T1', s)]), copy_ambiguous=wc_cells(wcs[('T1S', s)], True),
                    old_copy=old_cells(a), t1_old_copy=old_cells(t1),
                    passes=dict(T1S=wcs[('T1S', s)]['write_copy_u']['passes'], T1=wcs[('T1', s)]['write_copy_u']['passes']),
                    tool_off=g(ex, 'noexec', 'program_families'), call_free=g(ex, 'op_acc', 'free_run', 'call'),
                    call_tf=g(ex, 'op_acc', 'teacher_forced', 'call'), span_use=ex.get('span_use'))
    out = dict(seeds=SEEDS, problems=probs, judged=len(F) == len(SEEDS), marks_source='Amendment 7 + Clarification 7a')
    if not out['judged']:
        out['verdict'] = 'NOT JUDGED'
        return out
    sides = ('operand', 'answer')
    short = [(s, side, L, f['copy'][side][L][1]) for s, f in F.items() for side in sides for L in LENS
             if f['copy'][side][L][0] is None or f['copy'][side][L][1] < MIN_N7]
    r1 = {}
    for s, f in F.items():
        for side in sides:
            v = [f['copy'][side][L][0] for L in LENS]
            full = all(x is not None for x in v)
            r1[(s, side)] = dict(mean=sum(v) / len(v) if full else None, worst=min(v) if full else None,
                                 all_99=full and min(v) >= 99, ok=full and sum(v) / len(v) >= 99 and min(v) >= 97)
    r3 = {(s, side, L): dict(T1SD=f['copy'][side][L][0], T1=f['t1_copy'][side][L][0],
                             ok=f['copy'][side][L][0] is not None and f['copy'][side][L][0] >= 99
                             and (f['t1_copy'][side][L][0] is None or f['copy'][side][L][0] >= f['t1_copy'][side][L][0] - 1.0))
          for s, f in F.items() for side in sides for L in (1, 2, 3)}
    key = lambda d: {f'{k[0]} {" ".join(str(x) for x in k[1:])}': v for k, v in d.items()}
    m = {'R1 per side and seed: mean of the nine length cells >= 99 and every cell >= 97 (n >= 1000 per cell)': dict(
             value=key(r1), ok=not short and all(x['ok'] for x in r1.values())),
         'R2 pooled-5 T1SD - B2 >= -2.0 on both seeds': dict(value={s: f['d_pooled5'] for s, f in F.items()},
                                                              ok=all(f['d_pooled5'] is not None and f['d_pooled5'] >= -2.0 for f in F.values())),
         'R3 1-3 digit operand and answer cells >= 99 and no more than 1.0 below T1\'s re-score': dict(
             value=key(r3), ok=not short and all(x['ok'] for x in r3.values())),
         'R4 tool off < 5 and call accuracy free run >= 98, both seeds': dict(
             value={s: dict(tool_off=f['tool_off'], call_free=f['call_free']) for s, f in F.items()},
             ok=all(f['tool_off'] is not None and f['tool_off'] < 5 and f['call_free'] is not None and f['call_free'] >= 98 for f in F.values())),
         'S2 chain-5 >= 95 on both seeds': dict(value={s: f['chain5'] for s, f in F.items()},
                                                ok=all(f['chain5'] is not None and f['chain5'] >= 95 for f in F.values()))}
    low = [(s, side, L, f['copy'][side][L][0]) for s, f in F.items() for side in sides for L in range(4, 10)
           if f['copy'][side][L][0] is not None and f['copy'][side][L][1] >= MIN_N7 and f['copy'][side][L][0] < 90]
    out.update(marks=m, facts=F, reading_a_all_cells_99=key({k: v['all_99'] for k, v in r1.items()}), proved_wrong=bool(low),
               proved_wrong_cells=low, below_90_cells=low, short_cells=short)
    if all(x['ok'] for x in m.values()):
        out['verdict'] = 'PASS: the 6-seed confirm (marks 1-6, Amendment 2) runs on T1SD; H1 queues behind that pass'
    elif low and any(x[:3] == (201, 'operand', 8) for x in low):
        out['verdict'] = ('PROVED WRONG on the same s201 8-digit operand cell again: next = two more seeds of the unchanged T1SI recipe '
                          '(is s201 an outlier?), before touching the design')
    elif low:
        out['verdict'] = 'PROVED WRONG: a 4-9 digit cell below 90 (Amendment 7)'
    elif short:
        out['verdict'] = f'NOT JUDGED on R1/R3: {len(short)} cells below n = {MIN_N7} (more scorer passes)'
    else:
        out['verdict'] = 'NOT SHOWN: one more change, named from a miss breakdown of the failing cell, run before building it'
    return out


def load_preds(dirs, split='in_dist'):
    """{(arm, seed): {row id: prediction}} from <arm>_s<seed>/PREDS.json under dirs."""
    out = {}
    for d in dirs:
        for root, _, fs in os.walk(d):
            m = re.match(r'^(.+)_s(\d+)$', os.path.basename(root))
            if m and 'PREDS.json' in fs:
                out[(m.group(1), int(m.group(2)))] = json.load(open(os.path.join(root, 'PREDS.json'))).get(split) or {}
    return out


def natural(preds, rows):
    """The drill-free check's numbers on the natural in_dist set: exact on rows whose gold answer is a number (R5's reading), on every row,
    and per answer length (printed beside) -> dict, or None when the predictions do not cover the rows."""
    from custom_io.evalx import is_hit
    if not preds or set(preds) != set(rows):
        return None
    pc = lambda v: dict(n=len(v), exact=round(100 * sum(v) / len(v), 2) if v else None)
    hit = {i: is_hit(p, rows[i]) for i, p in preds.items()}
    num = [i for i in rows if NUM.fullmatch(rows[i]['answer'])]
    by = {}
    for i in num:
        by.setdefault(len(rows[i]['answer'].lstrip('-')), []).append(hit[i])
    return dict(numbers=pc([hit[i] for i in num]), all=pc(list(hit.values())), by_length={str(k): pc(v) for k, v in sorted(by.items())})


def screen8(runs, wcs, preds, rows):
    """Amendment 8 for T1SDR (T1SD + drawn-result drills), in T1S's slot: R1 per Clarification 7a, R2, R3 as Amendment 7, R4, S2 (screen7's
    code), and R5: the drill-free natural check, per seed, exact on the in_dist rows whose gold answer is a number drops <= 1.0 vs T1SD of
    the same seed (all rows and the per-length cells printed beside, not marks). Proved wrong: any operand or answer cell at 4-9 digits < 90
    on either seed. A hair miss (R1 the only failing mark, every cell >= 97, each failing mean in 98.5-99): seeds 202-203 of the same recipe."""
    out = screen7(runs, wcs)
    out['marks_source'] = 'Amendment 8 (R1 per Clarification 7a; R3 as Amendment 7; new R5 against T1SD)'
    nat = {s: dict(T1SDR=natural(preds.get(('T1S', s)), rows), T1SD=natural(preds.get(('T1SD', s)), rows)) for s in SEEDS}
    refbad = {s: (['T1SD missing'] if runs.get(('T1SD', s)) is None else [f'T1SD: {x}' for x in valid(runs[('T1SD', s)], 'T1SD')])
              + [f'{k} PREDS do not cover the in_dist rows' for k, v in nat[s].items() if v is None] for s in SEEDS}
    out['problems'] = {s: out['problems'].get(s, []) + refbad[s] for s in SEEDS}
    if not out['judged'] or any(refbad.values()):
        out.update(judged=False, verdict='NOT JUDGED')
        return out
    d = {s: round(nat[s]['T1SDR']['numbers']['exact'] - nat[s]['T1SD']['numbers']['exact'], 2) for s in SEEDS}
    out['marks']['R5 natural (drill-free) in_dist number-answer exact, T1SDR - T1SD >= -1.0 on both seeds'] = dict(
        value=d, ok=all(x >= -1.0 for x in d.values()))
    out['natural'] = nat
    m, low, short = out['marks'], out['proved_wrong_cells'], out['short_cells']
    r1k = next(k for k in m if k.startswith('R1'))
    fails = [k for k, x in m.items() if not x['ok']]
    r1 = m[r1k]['value']
    hair = (fails == [r1k] and not short and all(v['worst'] is not None and v['worst'] >= 97 for v in r1.values())
            and all(v['mean'] >= 98.5 for v in r1.values() if not v['ok']))
    if not fails:
        out['verdict'] = 'PASS: the 6-seed confirm (marks 1-6, Amendment 2) runs on T1SDR; H1 queues behind that pass'
    elif low:
        out['verdict'] = 'PROVED WRONG: a 4-9 digit cell below 90 (Amendment 8)'
    elif short:
        out['verdict'] = f'NOT JUDGED on R1/R3: {len(short)} cells below n = {MIN_N7} (more scorer passes)'
    elif hair:
        out['verdict'] = ('NOT SHOWN by a hair (R1 only: every cell >= 97, a mean in 98.5-99): run seeds 202-203 of the same recipe '
                          '(Amendment 8 item 7), no new change, no mark moves')
    else:
        out['verdict'] = ('NOT SHOWN: a miss breakdown first, then at most one more change (the entries-back table on the answer keys is the '
                          'only one named)')
    return out


def confirm(runs):
    """Marks 1-6 as amended (Amendment 2), analyze_t1's own code with T1S in T1's place."""
    rr = {('T1', s): r for (arm, s), r in runs.items() if arm == 'T1S'}
    rr.update({k: r for k, r in runs.items() if k[0] == 'B2'})
    keep = A.ARMS['T1']
    A.ARMS['T1'] = ARMS['T1S']
    try:
        return A.confirm(rr)
    finally:
        A.ARMS['T1'] = keep


def fmt(v):
    return '-' if v is None else f'{v:.1f}' if isinstance(v, float) else str(v)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', nargs='+', required=True)
    ap.add_argument('--wc', nargs='+', default=[], help='dirs holding <arm>_s<seed>/WC.json from custom_io/rescore_wc.py (Amendment 4)')
    ap.add_argument('--arm', default='T1S', choices=['T1S'] + sorted(NEXT))
    ap.add_argument('--out', default=None, help='default custom_io/results/<arm>-ANALYSIS.json')
    ap.add_argument('--dev', default=None, help='T1SDR (R5): the dev set the runs were evaluated on (its dev/in_dist.jsonl)')
    a = ap.parse_args(argv)
    a.out = a.out or f'custom_io/results/{a.arm}-ANALYSIS.json'
    if a.arm != 'T1S':
        ARMS['T1S'] = NEXT[a.arm]
    runs, skipped = load(a.results)
    runs = as_t1s(runs, a.arm)
    wcs = as_t1s(load_wc(a.wc), a.arm)
    if a.arm == 'T1SDR':
        from custom_io.data import load_rows
        ARMS['T1SD'] = NEXT['T1SD']
        rows = {r['id']: r for r in load_rows(os.path.join(a.dev, 'dev', 'in_dist.jsonl'))} if a.dev else {}
        sc = screen8(runs, wcs, as_t1s(load_preds(a.results), a.arm), rows)
    else:
        sc = (screen7 if a.arm == 'T1SD' else screen)(runs, wcs)
    res = dict(arm=a.arm, arm_spec=ARMS['T1S'], screen=sc, confirm=confirm(runs), skipped=skipped)
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    json.dump(res, open(a.out, 'w'), indent=1, default=str)
    sc = res['screen']
    head = {'T1S': '# T1S: T1 + span copy (Amendment 3, PASS-MARKS.md addendum 22)',
            'T1SI': '# T1SI: T1S + the entry-index term on the span keys (Amendment 5; judged in the T1S columns below, R1-R4 unchanged)',
            'T1SD': '# T1SD: T1SI + the distance-from-end table on the span keys (Amendment 7 marks + Clarification 7a; T1SD in the T1S columns below)',
            'T1SDR': '# T1SDR: T1SD + drawn-result drills, ans_drill 0.25 (Amendment 8 marks; T1SDR in the T1S columns below)'}[a.arm]
    new7 = a.arm in ('T1SD', 'T1SDR')
    mn = MIN_N7 if new7 else MIN_N
    L = [head, '', f"## Re-screen, seeds 200-201: {sc['verdict']}", '']
    if not sc['judged']:
        L += [f"- missing or invalid: {({s: p for s, p in sc['problems'].items() if p})}"]
    else:
        L += [f"- {k}: {'pass' if x['ok'] else 'FAIL'}" for k, x in sc['marks'].items()]
        if new7:
            r1 = next(x for k, x in sc['marks'].items() if k.startswith('R1'))['value']
            L += [f"- R1 per side and seed: " + '; '.join(f"{k}: mean {fmt(v['mean'])}, worst {fmt(v['worst'])}" for k, v in r1.items()),
                  f"- reading (a), all nine cells >= 99 (printed beside, not a mark): {sc['reading_a_all_cells_99']}",
                  f"- proved-wrong cells (operand or answer, length 4-9 below 90, n >= {mn}): {sc['proved_wrong_cells'] or 'none'}"]
            for s, x in (sc.get('natural') or {}).items():
                L += [f"- natural in_dist, seed {s} (R5 = number answers; all rows and per-length cells beside, not marks): "
                      f"T1SDR {x['T1SDR']['numbers']['exact']} vs T1SD {x['T1SD']['numbers']['exact']} (n {x['T1SD']['numbers']['n']}); all rows "
                      f"{x['T1SDR']['all']['exact']} vs {x['T1SD']['all']['exact']}; by length " + ', '.join(
                          f"{k}: {v['exact']} vs {x['T1SD']['by_length'][k]['exact']} (n {v['n']})" for k, v in x['T1SDR']['by_length'].items())]
        else:
            L += [f"- proved-wrong cells (operand, length 4-9 below 90, n >= {mn}): {sc['proved_wrong_cells'] or 'none'}",
                  f"- every cell at 4-9 digits below 90 (operand or answer): {sc['below_90_cells'] or 'none'}"]
        L += [f"- cells below n = {mn} (cannot pass or fail by themselves): {sc['short_cells'] or 'none'}", '']
        for s, f in sc['facts'].items():
            L += [f'### Seed {s}: pooled-5 T1S {fmt(f["t1s_pooled5"])} vs B2 {fmt(f["b2_pooled5"])} ({f["d_pooled5"]:+.2f}), T1 {fmt(f["t1_pooled5"])}; '
                  f'chain-5 {fmt(f["chain5"])} (T1 {fmt(f["t1_chain5"])}); tool off {fmt(f["tool_off"])}; call acc free {fmt(f["call_free"])} '
                  f'(teacher-forced {fmt(f["call_tf"])}); span use {f["span_use"]}', '',
                  '| digits | ' + ' | '.join(str(x) for x in LENS) + ' |', '|---|' + '---|' * len(LENS)]
            for side in ('operand', 'answer'):
                L += [f'| {side} T1S (unambiguous, n) | ' + ' | '.join(f"{fmt(f['copy'][side][x][0])} ({f['copy'][side][x][1]})" for x in LENS) + ' |',
                      f'| {side} T1 re-scored (unambiguous, n) | ' + ' | '.join(f"{fmt(f['t1_copy'][side][x][0])} ({f['t1_copy'][side][x][1]})" for x in LENS) + ' |',
                      f'| {side} T1S ambiguous, not counted | ' + ' | '.join(f"{fmt(f['copy_ambiguous'][side][x][0])} ({f['copy_ambiguous'][side][x][1]})" for x in LENS) + ' |',
                      f'| {side} T1S old scorer | ' + ' | '.join(fmt(f['old_copy'][side][x][0]) for x in LENS) + ' |',
                      f'| {side} T1 old scorer | ' + ' | '.join(fmt(f['t1_old_copy'][side][x][0]) for x in LENS) + ' |']
                L = L if not new7 else [x.replace(f'| {side} T1S ', f'| {side} {a.arm} ') for x in L]
            L += [f"Scorer passes: {f['passes']}", '']
    L += [f"## 6-seed confirm (marks 1-6 as amended): {res['confirm']['verdict']}", '']
    md = os.path.join(os.path.dirname(a.out) or '.', f'RESULTS-{a.arm}.md')
    open(md, 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))
    return res


if __name__ == '__main__':
    main()
