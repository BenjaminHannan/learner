"""Motivator: a fork of domain.mode.main where the model's own small head (its "inherent motivation") picks the practice.

  python -m dopamine.motivator --parent CKPT --tool sheet|rpn --out DIR --seed N --drive rule|even|edge|progress
         [--nights N] [--smoke] [--data DIR] [--threads N] [--motivator-json PATH]

rule     = domain.mode's mix rule (unchanged).   even = domain.mode --even-mix.
edge     = from day 2: practice the problems the head is least sure about, p = V(1-V), V from the latest quiz's head.
progress = from day 3: p = |V_latest - V_old|, V_old = head from `window_nights` nights earlier on the older model's features.
Day 1 (and day 2 for progress) are the plain even make_practice, exactly as domain.mode. Every change from domain.mode.main
is marked "# MOTIVATOR:". The head: logistic regression (dopamine.d0_guess.fit_logistic) of the quiz's per-question hits on the
reader's mean features of the quiz prompts (add-on ON), refit after every quiz.
"""
import argparse
import hashlib
import importlib
import json
import math
import os
import random
import time
from collections import Counter

import numpy as np
import torch

from custom_io.data import MAX_PROMPT, Dataset, collate, to_device
from custom_io.models import load_model
from domain.mode import (CONST_PATH, LEARNED, PRACTICE_OVERDRAW, SMOKE, SMOKE_UPDATES, AddOn, Log, build_diary, check_agree,
                         draft, fresh_replay, git_info, greedy, guard, lmax_of, make_mix, make_practice, make_quiz, save_ckpt,
                         train_night, try_day)
from dopamine.d0_guess import fit_logistic

HERE = os.path.dirname(os.path.abspath(__file__))
MOT_PATH = os.path.join(HERE, 'motivator.json')
P_FLOOR = 1e-12


# ---------- MOTIVATOR: new helpers ----------

def quiz_eval_hits(m, quiz, kinds):
    """Same numbers as domain.mode.quiz_eval, plus the per-question hits. -> (per kind, pooled, hits)."""
    res = greedy(m, [q['prompt'] for q in quiz])
    hits = [int(a == q['value']) for (_, a), q in zip(res, quiz)]
    per = {}
    for k in kinds:
        h = [x for x, q in zip(hits, quiz) if q['kind'] == k]
        per[k] = sum(h) / len(h) if h else 0.0
    return per, sum(hits) / max(len(hits), 1), hits


def reader_features(m, prompts, bs=128):
    """Mean of the reader's features over each prompt's letters (as domain.route.features, m.read(talker=True)).
    Does not touch the add-on switch: whatever the add-on's .on is, the hooks follow it (here: on). -> numpy [N, d]."""
    out = []
    for s in range(0, len(prompts), bs):
        chunk = prompts[s:s + bs]
        ds = Dataset([{'id': f'r{i}', 'prompt': p, 'answer': '', 'accepted': [], 'family': '', 'level': 0}
                      for i, p in enumerate(chunk)], m.vocab, strict=False)
        b = to_device(collate([ds[i] for i in range(len(chunk))]), 'cpu')
        with torch.no_grad():
            X, xm = m.read(b, talker=True)
        w = xm.float()[..., None]
        out.append((X * w).sum(1) / w.sum(1).clamp(min=1))
    return torch.cat(out).numpy()


def stable_seed(text):
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)


def es_pick(p, n, explore, rs):
    """Choose n distinct indices of p: round(explore*n) uniformly at random, the rest by weighted sampling without
    replacement proportional to p (Efraimidis-Spirakis keys u^(1/p); compared as log(u)/p). -> sorted list of indices."""
    p = np.maximum(np.asarray(p, dtype=np.float64), P_FLOOR)
    N = len(p)
    n = min(n, N)
    n_exp = min(n, int(round(explore * n)))
    exp_idx = rs.choice(N, n_exp, replace=False) if n_exp else np.array([], dtype=int)
    rest = np.setdiff1d(np.arange(N), exp_idx)
    n_w = n - n_exp
    if n_w:
        u = rs.uniform(size=len(rest))
        keys = np.log(np.maximum(u, 1e-300)) / p[rest]   # larger key = picked first
        top = rest[np.argsort(-keys, kind='stable')[:n_w]]
    else:
        top = np.array([], dtype=int)
    return sorted(int(i) for i in list(exp_idx) + list(top))


def load_old_features(path, prompts):
    """Reader features of `prompts` from a saved model (merged add-on, so no hooks). The global torch RNG is put back
    afterwards, so loading a model never changes later random draws."""
    st = torch.get_rng_state()
    try:
        mo = load_model(guard(path)).eval()
        return reader_features(mo, prompts)
    finally:
        torch.set_rng_state(st)


def draft_pool(tool, kinds, ex, n, rng, ctx):
    """n accepted problems, an even share over kinds, no duplicate inside the pool and none already in ctx['seen'] (draft
    checks that). Nothing is added to ctx['seen'] here. -> (items, disc, tries, edits)."""
    items, disc, tries, cap, edits, have = [], Counter(), 0, PRACTICE_OVERDRAW * n, Counter(), set()
    while len(items) < n and tries < cap:
        tries += 1
        kind = rng.choices(kinds, weights=[1.0] * len(kinds))[0]
        item, why = draft(tool, ex[kind], kind, rng, ctx, edits=edits)
        if item is None:
            disc[why] += 1
            continue
        if item['prompt'] in have:
            disc['pool_dup'] += 1
            continue
        have.add(item['prompt'])
        items.append(item)
    return items, disc, tries, edits


def motivated_practice(tool, kinds, ex, n, rng, ctx, seed, night, drive, heads, out, mot, m, log, parent):
    """A day with a signal. heads[k] = fitted head of quiz k. -> (items, disc, tries, edits), like make_practice."""
    pool, disc, tries, edits = draft_pool(tool, kinds, ex, mot['pool_factor'] * n, rng, ctx)
    prompts = [it['prompt'] for it in pool]
    k = night - 1                                 # the latest quiz
    F = reader_features(m, prompts)               # current model, add-on on
    V = heads[k](F)
    if drive == 'edge':
        p = V * (1 - V)
    else:
        ko = k - mot['window_nights']
        path = parent if ko == 0 else os.path.join(out, f'night_{ko}', 'checkpoint.pt')
        Vo = heads[ko](load_old_features(path, prompts))
        p = np.abs(V - Vo)
    rs = np.random.RandomState(stable_seed(f'{seed}-pick-{night}'))
    idx = es_pick(p, n, mot['explore'], rs)
    chosen = [pool[i] for i in idx]
    for it in chosen:
        ctx['seen'].add(it['prompt'])
    pk = np.array([it['kind'] for it in pool])
    log('motivator_pick', day=night, drive=drive, head_from_quiz=k, pool=len(pool), chosen=len(chosen),
        chosen_per_kind=dict(Counter(it['kind'] for it in chosen)),
        mean_p_chosen=round(float(p[idx].mean()), 5), mean_p_pool=round(float(p.mean()), 5),
        mean_V_chosen=round(float(V[idx].mean()), 4), mean_V_pool=round(float(V.mean()), 4),
        per_kind_mean_V={kk: round(float(V[pk == kk].mean()), 4) for kk in kinds if (pk == kk).any()},
        pool_tries=tries, pool_discards=dict(disc))
    return chosen, disc, tries, edits


def parse_args(argv=None):
    a = argparse.ArgumentParser(description='Domain mode with a learned motivator choosing the practice.')
    a.add_argument('--parent', required=True)
    a.add_argument('--tool', required=True, choices=['sheet', 'rpn'])
    a.add_argument('--out', required=True)
    a.add_argument('--seed', type=int, required=True)
    a.add_argument('--smoke', action='store_true')
    a.add_argument('--data', default=None)
    a.add_argument('--threads', type=int, default=4)
    a.add_argument('--even-mix', action='store_true')
    a.add_argument('--fixed-nights', type=int, default=None)
    a.add_argument('--drive', choices=['rule', 'even', 'edge', 'progress', 'informed'], default='rule')   # MOTIVATOR: informed = even over --informed-kinds
    a.add_argument('--informed-kinds', default=None, help='comma-separated kind names; required for --drive informed')   # MOTIVATOR:
    a.add_argument('--day-problems', type=int, default=None, help='override cons[day_problems] (practice per night)')   # MOTIVATOR:
    a.add_argument('--nights', type=int, default=None, help='run exactly N nights (no early stop; the stop rule is still logged)')   # MOTIVATOR:
    a.add_argument('--motivator-json', default=MOT_PATH)   # MOTIVATOR:
    return a.parse_args(argv)


def main(argv=None):
    from custom_io.data import DEFAULT_DATA
    a = parse_args(argv)
    if a.data is None:
        a.data = os.environ.get('CUSTOM_IO_DATA', DEFAULT_DATA)
    torch.set_num_threads(a.threads)
    T, t_run = Counter(), time.time()
    raw = open(CONST_PATH, 'rb').read()
    csha = hashlib.sha256(raw).hexdigest()
    cons = json.loads(raw)
    mot = json.load(open(a.motivator_json))   # MOTIVATOR:
    if mot['head_C'] is None:                 # MOTIVATOR:
        assert a.smoke, 'motivator.json head_C is not set (only --smoke may default it to 0.1)'
        mot['head_C'] = 0.1
    if a.smoke:
        cons.update(SMOKE)
    if a.day_problems is not None:   # MOTIVATOR: after the smoke constants, so an explicit value wins; every use below reads cons['day_problems']
        assert a.day_problems > 0, '--day-problems must be positive'   # MOTIVATOR:
        cons['day_problems'] = a.day_problems   # MOTIVATOR:
    assert (a.drive == 'informed') == (a.informed_kinds is not None), '--informed-kinds goes with (and only with) --drive informed'   # MOTIVATOR:
    rule_max_nights = cons['max_nights']      # MOTIVATOR: the max the plain rule would have used
    if a.fixed_nights:
        assert a.even_mix, '--fixed-nights is for the even-mix control only'
        cons['max_nights'] = max(cons['max_nights'], a.fixed_nights)
    if a.nights:                              # MOTIVATOR: exactly N nights, also in smoke
        cons['max_nights'] = a.nights
    even_mix = a.even_mix or a.drive == 'even'   # MOTIVATOR:
    commit, dirty = git_info()
    log = Log(a.out)
    parent = guard(a.parent)
    log('start', parent=parent, tool=a.tool, seed=a.seed, smoke=a.smoke, constants_sha256=csha, git_commit=commit,
        git_dirty_files=dirty, constants=cons, smoke_updates=SMOKE_UPDATES if a.smoke else None, data=a.data,
        even_mix_control=even_mix, fixed_nights_control=a.fixed_nights, drive=a.drive, nights=a.nights, motivator=mot,
        **({} if a.day_problems is None else dict(day_problems_override=a.day_problems)),
        **({} if a.informed_kinds is None else dict(informed_kinds=a.informed_kinds)))   # MOTIVATOR: drive, nights, motivator, day_problems_override, informed_kinds

    tool = importlib.import_module(f'domain.tools.{a.tool}')
    assert tool.NAME == a.tool, (tool.NAME, a.tool)
    helps = tool.help()
    kinds = [h['kind'] for h in helps]
    assert len(set(kinds)) == len(kinds), 'one help example per kind'
    ex = {h['kind']: h['prompt'] for h in helps}
    lmax = lmax_of(helps, cons['digit_len_extra'])
    log('help', kinds=kinds, examples=ex, lmax=lmax)
    log('deviation', id='A2', no_row_form_ops=['cmp', 'mod'])

    torch.manual_seed(a.seed)
    ck = torch.load(parent, map_location='cpu', weights_only=True)
    torch.manual_seed(a.seed)
    m = load_model(parent).eval()
    addon = None
    ctx = dict(vchars=set(ck['chars']), cons=cons, seen=set(), quiz_set=set(), lmax=lmax)
    write_row = lambda **kw: log.write('row', **kw)

    t = time.time()
    train = guard(os.path.join(a.data, 'train.jsonl'))
    pool = []
    with open(train) as f:
        for line in f:
            p = json.loads(line)['prompt']
            if len(p) <= MAX_PROMPT and set(p) <= ctx['vchars']:
                pool.append(p)
    pool = list(dict.fromkeys(pool))
    random.Random(f'{a.seed}-diary').shuffle(pool)
    diary, check, pool_pos = build_diary(m, pool, cons, ctx, log, write_row)
    pm = load_model(parent).eval() if cons['replay_fresh'] else None
    if cons['addon']:
        addon = AddOn(m, cons['addon_rank'], cons['addon_alpha'], seed=a.seed)
        addon.on = True
        log('addon', mode=cons['addon'], rank=cons['addon_rank'], alpha=cons['addon_alpha'], lr=cons['addon_lr'],
            params=addon.n_params(), layers=len(addon.layers))
    T['diary'] += time.time() - t
    assert len(diary) > 0, 'no diary rows'
    assert check, 'empty check set: agreement would read 0 and every night would be undone'

    t = time.time()
    quiz = make_quiz(tool, kinds, ex, cons['quiz'], random.Random(f'{a.seed}-quiz'), ctx, log)
    T['quiz_make'] += time.time() - t

    use_head = a.drive in ('edge', 'progress')   # MOTIVATOR: rule/even never touch the head, so they run exactly as domain.mode
    heads, quiz_prompts = {}, [q['prompt'] for q in quiz]   # MOTIVATOR:

    def fit_head(k, hits):   # MOTIVATOR: the competence head after quiz k, add-on ON (assert), features of the quiz prompts
        if addon is not None:
            assert addon.on, 'the add-on must be on when the head reads the quiz'
        t_h = time.time()
        F, y = reader_features(m, quiz_prompts), np.array(hits)
        heads[k] = fit_logistic(F, y, C=mot['head_C'])
        Vq = heads[k](F)
        log('motivator_head', k=k, n=len(y), quiz_hit_rate=round(float(y.mean()), 4), feat_dim=int(F.shape[1]),
            C=mot['head_C'], mean_V_on_quiz=round(float(np.mean(Vq)), 4), head_secs=round(time.time() - t_h, 1))
        T['head'] += time.time() - t_h

    t = time.time()
    per, pooled, hits0 = quiz_eval_hits(m, quiz, kinds)   # MOTIVATOR: same numbers as quiz_eval, plus hits
    T['quiz'] += time.time() - t
    hist_k, hist_p = [per], [pooled]
    log('quiz', when='before_night_1', pooled=round(100 * pooled, 2), per_kind={k: round(v, 4) for k, v in per.items()})
    if use_head:
        fit_head(0, hits0)   # MOTIVATOR:

    share = {k: 1 / len(kinds) for k in kinds}
    if a.drive == 'informed':   # MOTIVATOR: even over the listed kinds, 0 elsewhere, every day (no head, no pool)
        ik = [x.strip() for x in a.informed_kinds.split(',')]   # MOTIVATOR:
        assert ik and len(set(ik)) == len(ik) and all(x in kinds for x in ik), ('--informed-kinds must be distinct real kinds', ik, kinds)   # MOTIVATOR:
        share = {k: (1 / len(ik) if k in ik else 0.0) for k in kinds}   # MOTIVATOR:
    all_practice = []
    prog = {k: 0.0 for k in kinds}
    visits, undo_prev, stop, night, last_ck = cons['visits_per_new_row'], False, None, 0, None
    for night in range(1, cons['max_nights'] + 1):
        t = time.time()
        rng = random.Random(f'{a.seed}-day-{night}')
        first_signal = {'edge': 2, 'progress': 1 + mot['window_nights']}.get(a.drive)   # MOTIVATOR: edge day 2, progress day 3 (needs V from k-w >= 0)
        if use_head and night >= first_signal:   # MOTIVATOR:
            items, disc, tries, edits = motivated_practice(tool, kinds, ex, cons['day_problems'], rng, ctx, a.seed, night,
                                                           a.drive, heads, a.out, mot, m, log, parent)
            signal = True
        else:
            items, disc, tries, edits = make_practice(tool, kinds, ex, share, cons['day_problems'], rng, ctx)
            signal = False
        log('motivator_day', day=night, drive=a.drive, signal=signal)   # MOTIVATOR:
        T['practice'] += time.time() - t
        log('practice', day=night, n=len(items), tries=tries, kept_rate=round(len(items) / tries, 4) if tries else None,
            share={k: round(v, 4) for k, v in share.items()}, progress={k: round(v, 4) for k, v in prog.items()},
            kept=dict(Counter(i['kind'] for i in items)), discards=dict(disc),
            edits_drawn=dict(edits), edits_kept=dict(Counter(e for i in items for e in i['edits'])))
        if len(items) < cons['day_problems']:
            log('practice_short', day=night, n=len(items), wanted=cons['day_problems'])

        t = time.time()
        new = try_day(m, tool, items, kinds, cons, log, night, write_row)
        all_practice += new
        T['try'] += time.time() - t

        n_new = len(new)
        vis = visits / 2 if undo_prev else visits
        if a.smoke:
            updates = SMOKE_UPDATES if n_new else 0
        else:
            updates = math.ceil(vis * n_new / (cons['batch'] * (1 - cons['replay_share']))) if n_new else 0
        log('night_plan', night=night, new_rows=n_new, visits_per_new_row=vis, updates=updates, halved_after_undo=undo_prev)
        snap = {k: v.detach().clone() for k, v in m.state_dict().items()}
        asnap = addon.snapshot() if addon is not None else None
        t = time.time()
        if addon is not None and cons['addon'] == 'per_tool':
            addon.on = False
        before = check_agree(m, check)
        if addon is not None:
            addon.on = True
        T['check'] += time.time() - t
        t = time.time()
        rep = diary
        if cons['replay_fresh'] and updates:
            need = updates * (cons['batch'] - int(round(cons['batch'] * (1 - cons['replay_share']))))
            t2 = time.time()
            rep, pool_pos, rdisc = fresh_replay(pm, pool, pool_pos, need, cons, ctx, write_row, night)
            log('replay_fresh', night=night, need=need, n=len(rep), pool_pos=pool_pos, discards=dict(rdisc),
                gen_secs=round(time.time() - t2, 1))
            if len(rep) < need:
                log('replay_short', night=night, n=len(rep), need=need)
            if not rep:
                rep = diary
        picks = []
        losses = train_night(m, new, rep, updates, cons, seed=a.seed * 1000 + night,
                             fresh=cons['replay_fresh'] and rep is not diary, picks=picks, addon=addon) if updates else []
        if picks:
            log('replay_pick', night=night, rounds=picks)
        T['train'] += time.time() - t
        t = time.time()
        if addon is not None and cons['addon'] == 'per_tool':
            addon.on = False
        agree = check_agree(m, check)
        if addon is not None:
            addon.on = True
        T['check'] += time.time() - t
        drop = before - agree
        undo = (100.0 - agree if cons['undo_total'] else drop) > cons['undo_drop_points']
        if undo:
            m.load_state_dict(snap)
            if addon is not None:
                addon.restore(asnap)
            m.eval()
        undo_prev = undo
        log('check', night=night, agreement_before=round(before, 2), agreement=round(agree, 2), drop=round(drop, 2),
            undo=undo, rows_dropped=n_new if undo else 0)

        t = time.time()
        path = os.path.join(a.out, f'night_{night}', 'checkpoint.pt')
        save_ckpt(ck, m, path, addon)
        T['save'] += time.time() - t
        last_ck = path

        t = time.time()
        per, pooled, hits_n = quiz_eval_hits(m, quiz, kinds)   # MOTIVATOR: hits too
        T['quiz'] += time.time() - t
        hist_k.append(per)
        hist_p.append(pooled)
        log('night', night=night, updates=updates, loss_first10=round(float(np.mean(losses[:10])), 4) if losses else None,
            loss_last10=round(float(np.mean(losses[-10:])), 4) if losses else None, undone=undo, checkpoint=path,
            quiz_pooled=round(100 * pooled, 2), quiz_per_kind={k: round(v, 4) for k, v in per.items()})
        if use_head:
            fit_head(night, hits_n)   # MOTIVATOR: addon.on is True here (restored after every check)

        mastered_all = all(per[k] >= cons['mastered'] for k in kinds)
        rise = (hist_p[night] - hist_p[night - 2]) * 100 if night >= 2 else None
        if a.fixed_nights:
            stop = 'fixed_nights_control' if night >= a.fixed_nights else None
        elif mastered_all:
            stop = 'all_kinds_mastered'
        elif rise is not None and rise < cons['stop_min_rise_points']:
            stop = 'quiz_rise_below_%g_over_2_nights' % cons['stop_min_rise_points']
        elif night == rule_max_nights:   # MOTIVATOR: the plain rule's max (cons['max_nights'] may be overridden by --nights)
            stop = 'max_nights'
        log('stop_check', night=night, rise_over_2_nights_points=None if rise is None else round(rise, 3),
            mastered_all=mastered_all, stop=stop)
        if a.nights:   # MOTIVATOR: exactly N nights; the stop above is only logged
            if night >= a.nights:
                stop = 'nights_reached'
                break
            stop = None
        elif stop:
            break
        if a.drive == 'rule':   # MOTIVATOR: edge/progress/even/informed keep the even share (the motivator ignores the share on signal days)
            share, prog = make_mix(kinds, hist_k, night, cons)
        if even_mix:
            share = {k: 1 / len(kinds) for k in kinds}
        log('mix', for_day=night + 1, share={k: round(v, 4) for k, v in share.items()}, progress={k: round(v, 4) for k, v in prog.items()})

    final = hist_k[-1]
    if addon is not None and cons['addon'] == 'per_tool':
        from domain import route
        addon.on = False
        pos = sorted({it['prompt'] for it in all_practice})
        gate, gacc = route.train_gate(route.features(m, pos), route.features(m, [r['prompt'] for r in diary]))
        addon.on = True
        torch.save(gate.state, os.path.join(a.out, 'gate.pt'))
        log('gate', pos=len(pos), neg=len(diary), train_acc=round(gacc, 4), path=os.path.join(a.out, 'gate.pt'))
    summary = dict(parent=parent, tool=a.tool, seed=a.seed, smoke=a.smoke, even_mix_control=even_mix, nights_run=night, stop_reason=stop,
                   addon=cons['addon'], drive=a.drive, motivator=mot, nights_arg=a.nights,
                   day_problems_override=a.day_problems, informed_kinds=a.informed_kinds,   # MOTIVATOR:
                   quiz_pooled_history=[round(100 * p, 2) for p in hist_p],
                   quiz_per_kind_history=[{k: round(v, 4) for k, v in h.items()} for h in hist_k],
                   quiz_per_kind_final={k: round(v, 4) for k, v in final.items()},
                   kinds_learned=[k for k in kinds if final[k] >= LEARNED],
                   kinds_not_learned=[k for k in kinds if final[k] < LEARNED],
                   final_checkpoint=last_ck, constants_sha256=csha, git_commit=commit,
                   seconds={k: round(v, 1) for k, v in T.items()}, total_seconds=round(time.time() - t_run, 1))
    with open(os.path.join(a.out, 'summary.json'), 'w') as f:
        json.dump(summary, f, indent=1)
    log('done', nights_run=night, stop_reason=stop, final_checkpoint=last_ck, total_seconds=summary['total_seconds'])


if __name__ == '__main__':
    main()
