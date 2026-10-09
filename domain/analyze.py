"""Analysis of one domain-mode run: marks DM1-DM5 and the A8 self-knowledge numbers (design sec. 5; addenda A2, A6-A8).

  python -m domain.analyze --run RUN_DIR --parent PARENT_CKPT --panel PANEL.jsonl --dev DEV_IN_DIST.jsonl --out OUT_DIR [--threads N]

Reads RUN_DIR/log.jsonl, RUN_DIR/summary.json and RUN_DIR/night_K/checkpoint.pt. Never writes to RUN_DIR.
- Scores the parent (night 0) and every night on the sealed panel (domain/score.py; scoring only).
- Harm check: the parent against the final checkpoint on the skills DEV in_dist file (domain/harm.py).
- DM4: domain/audit.py on the run (its exit code and JSON), and the log's constants_sha256 against domain/constants.json.
- Writes OUT_DIR/RESULT.json and OUT_DIR/RESULT.md and prints RESULT.md.
Per-checkpoint results are cached in OUT_DIR/cache/, keyed by file hashes, so a rerun reuses them.
One run is given per call, so every seed-based mark is one seed only and is labelled that way.
"""
import argparse
import contextlib
import hashlib
import importlib
import io
import json
import math
import os
import time
from collections import Counter

import torch

from custom_io.data import load_rows
from domain import audit, harm, score
from domain.mode import NO_ROW_FORM

HERE = os.path.dirname(os.path.abspath(__file__))
CONST_PATH = os.path.join(HERE, 'constants.json')
KNOWN_EVENTS = frozenset({'start', 'help', 'deviation', 'row', 'diary', 'quiz_built', 'quiz_short', 'quiz', 'practice',
                          'practice_short', 'try', 'night_plan', 'check', 'night', 'stop_check', 'mix', 'done'})

# Marks (design sec. 5 table; addenda A2, A6-A8). Values are percentage points.
DM1_PASS, DM1_PROVED = 30.0, 10.0      # near, After minus Before: pass >= +30; proved wrong < +10
DM2_PASS, DM2_LOW = 10.0, 2.0          # far: pass >= +10; "<= +2 on both seeds" is proved wrong (needs two seeds)
DM3_PROVED = 5.0                       # in_dist drop > 5 is proved wrong (the pass rule is harm.py's)
DM5_BACK, DM5_RISE, DM5_PROVED = 3.0, 3.0, 5.0
DM5_PAST_BEST = 4                      # proved wrong: runs >= 4 nights past the best night with DM3 failing (design table)


# ---------- small helpers ----------

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def read_log(run_dir):
    with open(os.path.join(run_dir, 'log.jsonl'), encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def cached(path, fp, compute):
    """-> (result, from_cache). An entry is used only when its fingerprint (file hashes) matches exactly."""
    if os.path.exists(path):
        try:
            with open(path, encoding='utf-8') as f:
                blob = json.load(f)
            if blob.get('fingerprint') == fp:
                return blob['result'], True
        except (OSError, ValueError):
            pass  # unreadable entry: recompute and overwrite
    result = compute()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(dict(fingerprint=fp, result=result), f)
    os.replace(tmp, path)
    return result, False


def pooled(rows, kinds, split):
    """Pooled accuracy (percent) over the rows of `kinds` in `split`. None when there are no such rows."""
    hs = [r['hit'] for r in rows if r['kind'] in kinds and r['split'] == split]
    return round(100.0 * sum(hs) / len(hs), 6) if hs else None


def sg(x, nd=2):
    return '-' if x is None else f'{x:+.{nd}f}'


def pc(x, nd=2):
    return '-' if x is None else f'{x:.{nd}f}'


# ---------- statistics and rules (pure functions, unit-tested in domain/tests/test_analyze.py) ----------

def ranks(xs):
    """1-based ranks; tied values get the average of the positions they occupy."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    out = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return out


def spearman(x, y):
    """Spearman rank correlation: Pearson correlation of the average ranks (ties handled). None when undefined."""
    assert len(x) == len(y), 'spearman needs two lists of equal length'
    n = len(x)
    if n < 2:
        return None
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / n, sum(ry) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx == 0 or syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def dm1_rule(d):
    """d = near(After) - near(Before), points. PASS >= +30; PROVED WRONG < +10; else FAIL."""
    d = round(d, 6)
    verdict = 'PASS' if d >= DM1_PASS else ('PROVED WRONG' if d < DM1_PROVED else 'FAIL')
    return dict(value=d, bar='pass >= +30; proved wrong < +10', verdict=verdict)


def dm2_rule(d):
    """d = far(After) - far(Before), points. PASS >= +10; else FAIL. "<= +2 on both seeds" needs a second seed, so one
    seed can only report it (note), never prove it wrong."""
    d = round(d, 6)
    verdict = 'PASS' if d >= DM2_PASS else 'FAIL'
    note = '<= +2 on this seed: PROVED WRONG needs seed 201 also <= +2 (one seed only)' if d <= DM2_LOW else ''
    return dict(value=d, bar='pass >= +10; "<= +2 on both seeds" is proved wrong', verdict=verdict, note=note)


def dm3_rule(harm_res):
    """harm_res: harm.harm_measure output. PROVED WRONG if the in_dist drop > 5; PASS if harm.py passes; else FAIL."""
    drop = round(harm_res['in_dist_drop'], 6)
    if drop > DM3_PROVED:
        verdict = 'PROVED WRONG'
    elif harm_res['passes']:
        verdict = 'PASS'
    else:
        verdict = 'FAIL'
    return dict(value=drop, bar='pass: in_dist drop <= 1.5 and no family fired; proved wrong: drop > 5',
                verdict=verdict, fired=harm_res['fired'])


def dm5_rule(curve, back=DM5_BACK, rise=DM5_RISE, proved=DM5_PROVED, dm3_not_pass=False):
    """curve: the scored near score (percent) at night 0 (the parent), 1, ..., N (the stop night), N >= 1.
    PASS: score(N) >= max over 0..N minus `back`, and score(N) - score(N-1) <= `rise`.
    PROVED WRONG: score(N) - score(N-1) > `proved`, or the stop is >= DM5_PAST_BEST nights past the best night while DM3
    is not a PASS (design sec. 5 table: "runs >= 4 nights past its best with DM3 failing").
    Nights after N do not exist, so "would it have kept rising" is not measured."""
    n = len(curve) - 1
    assert n >= 1, 'DM5 needs at least one night after the parent'
    s_n, s_prev = round(curve[n], 6), round(curve[n - 1], 6)
    best = round(max(curve), 6)
    best_night = max(i for i, v in enumerate(curve) if round(v, 6) == best)
    d = round(s_n - s_prev, 6)
    ok_best = round(s_n - (best - back), 6) >= 0
    ok_rise = d <= rise
    past = n - best_night
    if d > proved or (past >= DM5_PAST_BEST and dm3_not_pass):
        verdict = 'PROVED WRONG'
    elif ok_best and ok_rise:
        verdict = 'PASS'
    else:
        verdict = 'FAIL'
    return dict(stop_night=n, score_stop=s_n, score_prev=s_prev, best=best, best_night=best_night,
                nights_past_best=past, rise_last_night=d, score_at_least_best_minus_3=ok_best,
                rise_at_most_3=ok_rise, dm3_not_pass=dm3_not_pass, verdict=verdict,
                rule=f'pass: score(N) >= best - 3 and rise <= 3; proved wrong: rise > 5, or >= {DM5_PAST_BEST} nights '
                     'past the best with DM3 not passing')


# ---------- scoring with cache ----------

def score_one(ckpt, label, rows, panel_sha, cache_dir):
    csha = sha256_file(ckpt)
    fp = dict(kind='score', ckpt_sha256=csha, panel_sha256=panel_sha)
    path = os.path.join(cache_dir, f'score_{csha[:16]}_{panel_sha[:8]}.json')
    return cached(path, fp, lambda: score.score(ckpt, rows, label))


def in_dist_one(ckpt, rows, dev_sha, cache_dir):
    csha = sha256_file(ckpt)
    fp = dict(kind='in_dist', ckpt_sha256=csha, dev_sha256=dev_sha)
    path = os.path.join(cache_dir, f'in_dist_{csha[:16]}_{dev_sha[:8]}.json')

    def compute():
        hits, exact = harm.in_dist_hits(ckpt, rows)
        return dict(hits=hits, exact=exact)
    return cached(path, fp, compute)


# ---------- the run's kinds (A2) ----------

def scored_kinds(tool, events):
    """A2: a kind is unscored when its help working (tool.evaluate on its help prompt) uses an op with no row form."""
    dev = [e for e in events if e['event'] == 'deviation']
    if dev:
        ops, source = set(dev[0]['no_row_form_ops']), 'run log deviation event (A2)'
    else:
        ops, source = set(NO_ROW_FORM), 'domain.mode.NO_ROW_FORM (the run log has no deviation event)'
    kinds, scored, unscored = [], [], {}
    for h in tool.help():
        kinds.append(h['kind'])
        used = sorted({s[0] for s in tool.evaluate(h['prompt'])['steps']})
        bad = sorted(set(used) & ops)
        if bad:
            unscored[h['kind']] = dict(ops=used, no_row_form=bad)
        else:
            scored.append(h['kind'])
    return kinds, scored, unscored, sorted(ops), source


# ---------- main ----------

def parse_args(argv=None):
    a = argparse.ArgumentParser(description='Analyse one domain-mode run: marks DM1-DM5 and the A8 numbers.')
    a.add_argument('--run', required=True, help='the run folder (log.jsonl, summary.json, night_K/checkpoint.pt)')
    a.add_argument('--parent', required=True, help='the parent checkpoint (night 0)')
    a.add_argument('--panel', required=True, help='the sealed panel jsonl for the run tool (scoring only)')
    a.add_argument('--dev', required=True, help='the skills DEV in_dist jsonl (harm check)')
    a.add_argument('--out', required=True, help='folder for RESULT.json, RESULT.md and cache/ (new or existing)')
    a.add_argument('--threads', type=int, default=1)
    return a.parse_args(argv)


def main(argv=None):
    a = parse_args(argv)
    torch.set_num_threads(a.threads)
    T, t_all = {}, time.time()
    run, out = os.path.abspath(a.run), os.path.abspath(a.out)
    cache_dir = os.path.join(out, 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    notes = []

    events = read_log(run)
    with open(os.path.join(run, 'summary.json'), encoding='utf-8') as f:
        summary = json.load(f)
    tool = importlib.import_module(f'domain.tools.{summary["tool"]}')
    kinds, scored, unscored, ops, dev_source = scored_kinds(tool, events)
    print('kinds (help order):', ', '.join(kinds), flush=True)
    print(f'SCORED KINDS ({len(scored)}), used for DM1/DM2/DM5/DM6: ' + ', '.join(scored), flush=True)
    print(f'UNSCORED (A2: working uses {ops}): ' + ', '.join(f'{k} {v["ops"]}' for k, v in unscored.items()), flush=True)

    # checkpoints: night 0 = parent, night K = run/night_K/checkpoint.pt, final = summary's final_checkpoint
    N = int(summary['nights_run'])
    nights = dict(score.night_checkpoints(run))
    missing = [k for k in range(1, N + 1) if k not in nights]
    assert not missing, f'missing night checkpoints {missing}'
    extra = sorted(k for k in nights if k > N)
    if extra:
        notes.append(f'night checkpoints after nights_run={N} were ignored: {extra}')
    fin = summary.get('final_checkpoint')
    if not fin or not os.path.exists(fin):
        notes.append(f'summary final_checkpoint not on disk ({fin}); used the night_{N} file in the run folder')
        fin = nights[N]
    if os.path.realpath(fin) != os.path.realpath(nights[N]):
        notes.append('summary final_checkpoint is not the run folder night_%d file (path differs)' % N)
    if os.path.realpath(a.parent) != os.path.realpath(summary.get('parent', a.parent)):
        notes.append(f'--parent differs from the run summary parent ({summary.get("parent")})')
    ckpt = {0: a.parent}
    ckpt.update({k: nights[k] for k in range(1, N)})
    ckpt[N] = fin

    # step 1: score the parent and every night on the sealed panel (cached per checkpoint)
    t = time.time()
    panel_rows = score.load_panel(a.panel)
    panel_sha = sha256_file(a.panel)
    scores = {}
    for k in range(0, N + 1):
        label = 'parent' if k == 0 else f'night_{k}'
        t1 = time.time()
        res, hit = score_one(ckpt[k], label, panel_rows, panel_sha, cache_dir)
        scores[k] = res
        print(f'{label}: overall {res["overall"]} near {res["by_split"].get("near")} far {res["by_split"].get("far")} '
              f'({"cache" if hit else "scored"}, {time.time() - t1:.1f} s)', flush=True)
    T['score_panel'] = round(time.time() - t, 1)

    near_curve = [pooled(scores[k]['rows'], scored, 'near') for k in range(N + 1)]
    far0, farN = pooled(scores[0]['rows'], scored, 'far'), pooled(scores[N]['rows'], scored, 'far')
    n_near = sum(1 for r in panel_rows if r['split'] == 'near' and r['kind'] in scored)
    n_far = sum(1 for r in panel_rows if r['split'] == 'far' and r['kind'] in scored)
    print('scored near curve (night 0..N):', near_curve, flush=True)

    # DM1, DM2 (scored kinds, final minus parent)
    dm1 = dm1_rule(near_curve[N] - near_curve[0])
    dm1['hair_miss_met'] = round(dm1['value'] + 100.0 / n_near, 6) >= DM1_PASS
    dm1['seed'] = summary['seed']
    dm1['before'], dm1['after'] = near_curve[0], near_curve[N]
    dm2 = dm2_rule(farN - far0)
    dm2['hair_miss_met'] = round(dm2['value'] + 100.0 / n_far, 6) >= DM2_PASS
    dm2['before'], dm2['after'] = far0, farN
    dm2['seed'] = summary['seed']

    # DM3: harm check on the skills DEV in_dist file (parent against final)
    t = time.time()
    dev_sha = sha256_file(a.dev)
    dev_rows = load_rows(a.dev)
    ref, _ = in_dist_one(a.parent, dev_rows, dev_sha, cache_dir)
    aft, _ = in_dist_one(fin, dev_rows, dev_sha, cache_dir)
    harm_res = harm.harm_measure(ref['hits'], aft['hits'], dev_rows, family_drop=5.0, in_dist_drop=1.5)
    dm3 = dm3_rule(harm_res)
    T['harm'] = round(time.time() - t, 1)
    print('DM3 in_dist parent', round(harm_res['in_dist_a'], 2), 'final', round(harm_res['in_dist_b'], 2),
          'drop', round(harm_res['in_dist_drop'], 2), 'fired', harm_res['fired'], flush=True)

    # DM4: audit (exit code and JSON) and the constants hash
    t = time.time()
    panel_dir = os.path.dirname(os.path.abspath(a.panel))
    buf, rc, audit_rep = io.StringIO(), None, None
    try:
        with contextlib.redirect_stdout(buf):
            rc = audit.main([run, '--panel', panel_dir])
        audit_rep = json.loads(buf.getvalue())
    except (OSError, ValueError, KeyError) as e:
        notes.append(f'DM4 audit could not run: {type(e).__name__}: {e}')
    const_sha = sha256_file(CONST_PATH)
    start = [e for e in events if e['event'] == 'start']
    log_sha = start[0].get('constants_sha256') if start else None
    const_ok = log_sha == const_sha
    unknown = sorted({e['event'] for e in events} - KNOWN_EVENTS)
    if audit_rep is not None and audit_rep['panel_overlap']:
        dm4_verdict = 'PROVED WRONG'                       # any row from our panel
    elif log_sha is not None and not const_ok:
        dm4_verdict = 'PROVED WRONG'                       # the run used constants other than the shared file (per-domain setting)
    elif rc == 0 and const_ok:
        dm4_verdict = 'PASS'
    else:
        dm4_verdict = 'FAIL'                               # audit exit nonzero (zero-step, bad source) or no start event
    dm4 = dict(verdict=dm4_verdict, audit_exit=rc, audit=audit_rep, log_constants_sha256=log_sha,
               constants_file_sha256=const_sha, constants_match=const_ok,
               summary_constants_match=summary.get('constants_sha256') == const_sha,
               unknown_events=unknown,
               bar='pass: audit exits clean and log constants hash = domain/constants.json; proved wrong: any panel row '
                   'or a constants hash that differs from the file (per-domain setting)')
    T['audit'] = round(time.time() - t, 1)

    # DM5: scored near curve, stop night N = nights_run
    dm5 = dm5_rule(near_curve, dm3_not_pass=dm3['verdict'] != 'PASS')
    dm5['curve'] = near_curve
    dm5['note'] = ('nights after the stop (N=%d) do not exist, so "would it have kept rising" is not measured' % N)

    # A8 R2 (self-knowledge across all kinds) and R3 (wasted practice)
    quiz_final = summary['quiz_per_kind_final']
    hist = summary['quiz_per_kind_history']
    assert set(quiz_final) == set(kinds), 'quiz kinds differ from the help kinds'
    near_final_all = {k: scores[N]['by_kind_split'][k]['near'] for k in kinds}
    r2 = spearman([quiz_final[k] for k in kinds], [near_final_all[k] for k in kinds])
    practice = [e for e in events if e['event'] == 'practice']
    last_p = practice[-1]
    share_last = last_p['share']
    kept_last = last_p.get('kept', {})
    never_rose = [k for k in kinds if len(hist) > 1 and max(h[k] for h in hist[1:]) <= hist[0][k]]
    r3 = round(100.0 * sum(share_last.get(k, 0.0) for k in never_rose), 2)
    a8 = dict(R2_spearman=None if r2 is None else round(r2, 4), R2_n=len(kinds),
              R3_wasted_share_pct=r3, R3_kinds=never_rose, R1='not computed here (needs the even-mix control run)')

    # per-kind table
    own, tool_rows, own_not = Counter(), Counter(), Counter()
    for e in events:
        if e['event'] == 'try':
            for k, d in e['per_kind'].items():
                own[k] += d.get('own', 0)
                tool_rows[k] += d.get('tool', 0)
                own_not[k] += d.get('own_not_tool_working', 0)
    undone = {e['night'] for e in events if e['event'] == 'check' and e['undo']}
    undo_rows = Counter(e['kind'] for e in events if e['event'] == 'row' and e.get('day') in undone)
    per_kind = []
    for k in kinds:
        s0, sN = scores[0]['by_kind_split'][k], scores[N]['by_kind_split'][k]
        per_kind.append(dict(kind=k, scored=k in scored, near0=s0['near'], nearN=sN['near'], far0=s0['far'], farN=sN['far'],
                             quiz0=round(100 * hist[0][k], 2), quizN=round(100 * hist[-1][k], 2),
                             share_last_pct=round(100 * share_last.get(k, 0.0), 2), kept_last=kept_last.get(k, 0),
                             undo_rows=undo_rows.get(k, 0), own_rows=own[k], tool_rows=tool_rows[k],
                             own_not_tool=own_not[k]))
    if unknown:
        notes.append(f'log has event types outside the mode list: {unknown}')
    notes.append(f'undone nights: {sorted(undone) or "none"} (the check events in the log hold each night\'s drop)')

    T['total'] = round(time.time() - t_all, 1)
    res = dict(run=run, tool=summary['tool'], seed=summary['seed'], smoke=summary['smoke'], parent=a.parent,
               final_checkpoint=fin, nights_run=N, stop_reason=summary['stop_reason'],
               panel=dict(path=a.panel, sha256=panel_sha, n=len(panel_rows), n_near_scored=n_near, n_far_scored=n_far),
               dev=dict(path=a.dev, sha256=dev_sha, n=len(dev_rows)),
               kinds=dict(all=kinds, scored=scored, unscored=unscored, no_row_form_ops=ops, source=dev_source),
               marks=dict(DM1=dm1, DM2=dm2, DM3=dm3, DM4=dm4, DM5=dm5),
               dm3_detail=dict(in_dist_parent=round(harm_res['in_dist_a'], 4), in_dist_final=round(harm_res['in_dist_b'], 4),
                               in_dist_drop=round(harm_res['in_dist_drop'], 4), fired=harm_res['fired'],
                               families={f: {k2: (round(v, 4) if isinstance(v, float) else v) for k2, v in d.items()}
                                         for f, d in harm_res['families'].items()}),
               dm5_curve=near_curve, a8=a8, per_kind=per_kind,
               learned=summary.get('kinds_learned'), not_learned=summary.get('kinds_not_learned'),
               notes=notes, one_seed_only=True, timings=T)
    with open(os.path.join(out, 'RESULT.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1, default=str)
    md = render_md(res)
    with open(os.path.join(out, 'RESULT.md'), 'w', encoding='utf-8') as f:
        f.write(md)
    print(md, flush=True)
    print('wrote', os.path.join(out, 'RESULT.json'), 'and', os.path.join(out, 'RESULT.md'), flush=True)
    print('timings (s):', json.dumps(T), flush=True)
    return res


def render_md(res):
    m, d4, d5 = res['marks'], res['marks']['DM4'], res['marks']['DM5']
    seed = res['seed']
    lines = [f'# Domain run analysis: {res["tool"]} seed {seed}{" (smoke)" if res["smoke"] else ""}', '',
             f'- Run: `{res["run"]}`', f'- Parent: `{res["parent"]}`', f'- Final: `{res["final_checkpoint"]}` (night {res["nights_run"]}, stop: {res["stop_reason"]})',
             f'- One seed only (seed {seed}). Seed-based bars say so.',
             f'- Scored kinds ({len(res["kinds"]["scored"])}): ' + ', '.join(res['kinds']['scored']),
             f'- Unscored, A2 ({res["kinds"]["source"]}; ops {res["kinds"]["no_row_form_ops"]}): ' +
             (', '.join(f'{k} {v["ops"]}' for k, v in res['kinds']['unscored'].items()) or 'none'), '',
             '## Marks', '', '| Mark | Value | Bar | Verdict |', '|---|---|---|---|',
             f'| DM1 near, scored kinds (After minus Before) | {sg(m["DM1"]["value"])} pts ({pc(m["DM1"]["before"])} -> {pc(m["DM1"]["after"])}) | '
             f'{m["DM1"]["bar"]} (seed {seed}, one seed only) | {m["DM1"]["verdict"]} |',
             f'| DM2 far, scored kinds (After minus Before) | {sg(m["DM2"]["value"])} pts ({pc(m["DM2"]["before"])} -> {pc(m["DM2"]["after"])}) | '
             f'{m["DM2"]["bar"]} (seed {seed}, one seed only) | {m["DM2"]["verdict"]}{" (" + m["DM2"]["note"] + ")" if m["DM2"]["note"] else ""} |',
             f'| DM3 harm: in_dist drop | {sg(m["DM3"]["value"])} pts (fired: {", ".join(m["DM3"]["fired"]) or "none"}) | '
             f'{m["DM3"]["bar"]} | {m["DM3"]["verdict"]} |',
             f'| DM4 audit and constants | rows {d4["audit"]["rows"] if d4["audit"] else "?"}, panel overlap '
             f'{len(d4["audit"]["panel_overlap"]) if d4["audit"] else "?"}, zero-step {len(d4["audit"]["zero_steps"]) if d4["audit"] else "?"}, '
             f'bad source {len(d4["audit"]["bad_source"]) if d4["audit"] else "?"}; audit exit {d4["audit_exit"]}; '
             f'constants hash match {d4["constants_match"]} | {d4["bar"]} | {d4["verdict"]} |',
             f'| DM5 stop night N={d5["stop_night"]} | score(N) {pc(d5["score_stop"])}, best {pc(d5["best"])} (night {d5["best_night"]}), '
             f'rise over last night {sg(d5["rise_last_night"])} | {d5["rule"]} | {d5["verdict"]} |', '',
             f'- Ben\'s hair-miss rule (one question = {100.0 / res["panel"]["n_near_scored"]:.2f} pts near, '
             f'{100.0 / res["panel"]["n_far_scored"]:.2f} pts far): DM1 met: {"yes" if m["DM1"]["hair_miss_met"] else "no"}; DM2 met: {"yes" if m["DM2"]["hair_miss_met"] else "no"}.',
             f'- DM3 detail: in_dist {pc(res["dm3_detail"]["in_dist_parent"])} -> {pc(res["dm3_detail"]["in_dist_final"])}; '
             f'harm.py pass = {m["DM3"]["verdict"] == "PASS"}.',
             f'- DM5 nights after the stop do not exist: "would it have kept rising" is not measured. Rise is the scored near '
             f'score, not the quiz.',
             f'- DM4 also needs no person step in the log: every event type in the log is one the mode writes ({"yes" if not d4["unknown_events"] else "no, unknown: " + ", ".join(d4["unknown_events"])}). Checked by event type only.',
             f'- Learned (summary, reported): {res["learned"]}. Not learned: {res["not_learned"]}.', '',
             '## DM5 curve (scored near, pooled, percent)', '', '| night | near | change |', '|---|---|---|']
    for k, v in enumerate(res['dm5_curve']):
        ch = '' if k == 0 else sg(v - res['dm5_curve'][k - 1])
        lines.append(f'| {k}{" (parent)" if k == 0 else ""} | {pc(v)} | {ch} |')
    lines += ['', '## Per kind (undo rows: this kind\'s training rows from nights that were undone; try counts from the try events)', '',
              '| kind | scored | near parent -> final | far parent -> final | own quiz night 0 -> last | last-day mix share | last-day kept | undo rows | try own / tool |',
              '|---|---|---|---|---|---|---|---|---|']
    for r in res['per_kind']:
        lines.append(f'| {r["kind"]} | {"yes" if r["scored"] else "no (A2)"} | {pc(r["near0"])} -> {pc(r["nearN"])} | '
                     f'{pc(r["far0"])} -> {pc(r["farN"])} | {pc(r["quiz0"])} -> {pc(r["quizN"])} | {pc(r["share_last_pct"])}% | '
                     f'{r["kept_last"]} | {r["undo_rows"]} | {r["own_rows"]} / {r["tool_rows"]} |')
    a8 = res['a8']
    lines += ['', '## A8 (reported, not gated)', '',
              f'- R2 self-knowledge (Spearman, {a8["R2_n"]} kinds, own final quiz vs panel near at the final night): {a8["R2_spearman"]}.',
              f'- R3 wasted practice: {a8["R3_wasted_share_pct"]}% of the last day\'s mix went to kinds whose own quiz never rose '
              f'above night 0: {", ".join(a8["R3_kinds"]) or "none"}.',
              f'- R1 pick gain: {a8["R1"]}.', '', '## Notes', '']
    lines += [f'- {n}' for n in res['notes']] or ['- none']
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    main()
