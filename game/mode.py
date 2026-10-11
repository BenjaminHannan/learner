"""Game mode (GW-S): a model learns the Crafter game by itself, with domain mode's loop.

Plan: /mnt/project-files/game-world/PLAN-AND-MARKS-2026-10-10.md.

  python -m game.mode --parent CKPT --out DIR --seed N [--smoke] [--data DIR] [--threads N] [--full-model] [--picker greedy|sample] [--quiz-picker top|sample] [--keep-awake-only] [--keep window|guess] [--night copy|pg]

Each night: play 64 practice worlds, keep the steps just before each unlock (the game is the checker), train the add-on
on them mixed with the model's own old answers (diary), undo if old answers drifted, then the model's own quiz.
Writes DIR/log.jsonl, DIR/night_K/checkpoint.pt, DIR/gate.pt and DIR/summary.json. Only practice worlds are ever played.
"""
import argparse
import gzip
import hashlib
import json
import math
import os
import random
import time
from collections import Counter

import numpy as np
import torch

from custom_io.data import DEFAULT_DATA, MAX_PROMPT
from custom_io.models import load_model
from domain import mode as dm
from domain import route
from game import crafter_text, guess, pg, play

FAMILY = 'game_crafter'
SMOKE = dict(episodes_per_day=4, quiz_worlds=2, episode_cap=60, diary=128, check=64, max_nights=2)
SMOKE_UPDATES = 20
SK200K = '/tmp/claude-0/-home-user-learner/a35c4c05-cfae-5dd3-a5ce-480213b76700/scratchpad/sk200k'
GATE_MAX = 4096


def keep_windows(unlocks, credit_window, asleep=None):
    """The keep rule. unlocks = [(step, name)] in order. For each unlock at step t keep steps
    max(prev, t - credit_window + 1) .. t, prev = previous kept unlock's step + 1 (0 at the start), so windows never overlap.
    -> [(step, unlock name, unlock step)]. choice: a second unlock on the same step has an empty window (prev > t).
    asleep (optional, a set of steps): those steps are dropped from the windows, which stay the same size (a move made
    asleep is replaced by 'sleep' in Crafter, so it did nothing)."""
    out, prev = [], 0
    for t, name in unlocks:
        for s in range(max(prev, t - credit_window + 1), t + 1):
            if asleep is None or s not in asleep:
                out.append((s, name, t))
        prev = max(prev, t + 1)
    return out


def world_seeds(run_seed, day, n):
    """-> (world seeds, act seeds) of the n practice worlds of `day` (day 0 = the quiz). Never sealed."""
    seeds = [play.practice_seed(run_seed, day, i) for i in range(n)]
    assert not any(play.is_sealed(s) for s in seeds), 'sealed world in a mode'
    return seeds, [[run_seed, day, i] for i in range(n)]


def episode_stats(eps):
    """Per-achievement unlock share (of episodes), mean length, deaths, source shares of steps."""
    n = max(len(eps), 1)
    un = Counter(name for e in eps for _, name in e['unlocks'])
    src = Counter()
    for e in eps:
        src.update(e['sources'])
    tot = max(sum(src.values()), 1)
    return dict(episodes=len(eps), steps=sum(e['length'] for e in eps), mean_length=round(sum(e['length'] for e in eps) / n, 2),
                deaths=sum(e['end'] == 'dead' for e in eps), unlocks=dict(sorted(un.items())),
                unlock_share={k: round(v / n, 4) for k, v in sorted(un.items())},
                source_share={k: round(src[k] / tot, 4) for k in ('own', 'explore', 'invalid')})


def play_worlds(m, run_seed, day, n, cons, log_steps, picker='greedy', temp=1.0):
    """picker: 'greedy' (the written answer), 'top' or 'sample' (the model's odds over the 17 moves, play.move_policy)."""
    seeds, acts = world_seeds(run_seed, day, n)
    return play.play(play.picked_policy(m, picker, temp=temp), seeds, acts, cons['explore'], cons['episode_cap'], log_steps=log_steps)


def write_moves(path, eps):
    """One gzip JSON line per move of every episode (needs log_steps=True). -> number of lines."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    n = 0
    with gzip.open(path, 'wt', encoding='utf-8') as f:
        for e in eps:
            by_step = {}
            for t, name in e['unlocks']:
                by_step.setdefault(t, []).append(name)
            last = len(e['steps']) - 1
            for t, (view, word, src, reward) in enumerate(e['steps']):
                f.write(json.dumps(dict(world_seed=e['seed'], act_seed=e['act_seed'], step=t, view=view, move=word, source=src,
                                        reward=reward, unlocks=by_step.get(t, []), end=e['end'] if t == last else None)) + '\n')
                n += 1
    return n


def keep_rows(m, eps, cons, day, write_row, awake_only=False):
    """Rows from the kept steps of each episode. awake_only: kept moves made while asleep are dropped.
    -> (rows, by source, by unlock name, refusals by reason, number dropped as asleep)."""
    rows, by_src, by_name, refused = [], Counter(), Counter(), Counter()
    n_asleep = 0
    for e in eps:
        zz = {s for s, st in enumerate(e['steps']) if crafter_text.asleep(st[0])} if awake_only else None
        if awake_only:
            n_asleep += len(keep_windows(e['unlocks'], cons['credit_window'])) - len(keep_windows(e['unlocks'], cons['credit_window'], zz))
        for s, name, t in keep_windows(e['unlocks'], cons['credit_window'], zz):
            prompt, word, src = e['steps'][s][:3]
            row, why = dm.make_row(m, FAMILY, prompt, word, [], cons, src, allow_zero=True)
            if row is None:
                refused[why] += 1
                continue
            rows.append(row)
            by_src[src] += 1
            by_name[name] += 1
            write_row(day=day, kind='game', id=row['id'], source=src, prompt=prompt, answer=word, steps=[],
                      world_seed=e['seed'], act_seed=e['act_seed'], step=s, unlock=name, unlock_step=t)
    return rows, by_src, by_name, refused, n_asleep


def keep_guess_rows(m, eps, cons, day, write_row, guesser, awake_only=False):
    """The learned keep rule (game/guess.py). N = what the window rule would keep this day (same awake_only); keep the N awake
    moves with the highest advantage. -> (rows, by source, by name, refusals, dropped asleep (as the window rule counts), guess info)."""
    n_old = sum(len(keep_windows(e['unlocks'], cons['credit_window'])) for e in eps)
    n_awake = sum(len(keep_windows(e['unlocks'], cons['credit_window'],
                                   {s for s, st in enumerate(e['steps']) if crafter_text.asleep(st[0])} if awake_only else None))
                  for e in eps)
    t0 = time.time()
    adv, info = guesser.day(day, eps)
    keys, awake = guess.episode_moves(eps, awake_only)
    flat = [(e, s) for e in eps for s in range(len(e['steps']))]
    pick = guess.select(adv, keys, awake, n_awake)
    info['seconds'] = round(time.time() - t0, 2)
    rows, by_src, by_name, refused = [], Counter(), Counter(), Counter()
    for i in pick:
        e, s = flat[i]
        prompt, word, src = e['steps'][s][:3]
        row, why = dm.make_row(m, FAMILY, prompt, word, [], cons, src, allow_zero=True)
        if row is None:
            refused[why] += 1
            continue
        rows.append(row)
        by_src[src] += 1
        by_name['guess'] += 1
        write_row(day=day, kind='game', id=row['id'], source=src, prompt=prompt, answer=word, steps=[],
                  world_seed=e['seed'], act_seed=e['act_seed'], step=s, unlock=None, unlock_step=None,
                  kept_by='guess', advantage=float(adv[i]))
    kept = adv[pick] if pick else np.zeros(0)
    info.update(N=n_awake, N_window_all=n_old, kept=len(pick),
                adv_mean_kept=round(float(kept.mean()), 5) if len(kept) else None,
                adv_max_kept=round(float(kept.max()), 5) if len(kept) else None,
                adv_mean_all=round(float(adv.mean()), 5) if len(adv) else None,
                adv_max_all=round(float(adv.max()), 5) if len(adv) else None)
    return rows, by_src, by_name, refused, n_old - n_awake, info


TEMP_VIEWS = 2000     # views the starting temperature is fitted on (an even subsample of the harvest games' views)
TEMP_WORLDS = 8       # harvest games: the first 8 quiz worlds


def start_temp(m, run_seed, cons, picker):
    """T0 (addendum A13): play the first TEMP_WORLDS quiz worlds at T = 1 to harvest views, subsample TEMP_VIEWS of them evenly,
    and bisect T so the parent's mean entropy of softmax(logp / T) on them is ln 17 / 2. -> (T0, info). The caller then plays the
    real night-0 quiz at T0."""
    t0 = time.time()
    eps = play_worlds(m, run_seed, 0, TEMP_WORLDS, cons, log_steps=True, picker=picker)
    views = [st[0] for e in eps for st in e['steps']]
    step = max(len(views) // TEMP_VIEWS, 1)
    views = views[::step][:TEMP_VIEWS]
    lp = play.move_logprobs(m, views)
    T, ent = pg.find_temp(lp)
    return T, dict(T0=T, entropy_target=round(math.log(play.N_ACTIONS) / 2, 6), entropy_reached=round(ent, 6),
                   entropy_at_T1=round(pg.entropy(lp), 6), views=len(views), harvest_worlds=TEMP_WORLDS,
                   harvest_picker=picker, seconds=round(time.time() - t0, 1))


def pg_day(m, eps, cons, day, write_row, guesser, awake_only=False):
    """Policy-gradient day (--night pg): advantages from the guesser (its day() call, as keep_guess_rows), asleep moves dropped when
    awake_only, the rest normalised (mean 0, std 1). Writes one 'row' event per move used. Rows here are light dicts (id, prompt,
    answer, source), not dm.make_row rows: nothing is copied, so no answer check is needed beyond answer in the 17 words.
    -> (rows, prompts, action indices, normalised advantages, by source, dropped asleep, guess info)."""
    t0 = time.time()
    adv, info = guesser.day(day, eps)
    keys, awake = guess.episode_moves(eps, awake_only)
    flat = [(e, s) for e in eps for s in range(len(e['steps']))]
    use = [i for i in range(len(flat)) if awake[i]]
    raw = adv[use]
    norm = pg.normalise(raw)
    info.update(seconds=round(time.time() - t0, 2), kept=len(use), mean_abs_adv_raw=round(float(np.abs(raw).mean()), 5) if len(use) else None)
    rows, prompts, acts, by_src = [], [], [], Counter()
    for k, i in enumerate(use):
        e, s = flat[i]
        prompt, word, src = e['steps'][s][:3]
        assert word in play.WORDS
        row = dict(id=f'pg{day}_{k}', family=FAMILY, prompt=prompt, answer=word, accepted=[word], steps=[], level=0, stage=0, source=src)
        rows.append(row)
        prompts.append(prompt)
        acts.append(play.WORDS.index(word))
        by_src[src] += 1
        write_row(day=day, kind='game', id=row['id'], source=src, prompt=prompt, answer=word, steps=[],
                  world_seed=e['seed'], act_seed=e['act_seed'], step=s, unlock=None, unlock_step=None,
                  kept_by='pg', advantage=float(adv[i]), advantage_norm=float(norm[k]))
    return rows, prompts, acts, norm, by_src, len(flat) - len(use), info


def stop_decision(rise, night, cons, fixed_nights=None):
    """(stop_reason, ignored): the stop rule's verdict; with fixed_nights it never ends the run before that night."""
    rule = None
    if rise is not None and rise < cons['stop_min_rise_points']:
        rule = 'quiz_rise_below_%g_over_2_nights' % cons['stop_min_rise_points']
    elif night == cons['max_nights']:
        rule = 'max_nights'
    if fixed_nights is None:
        return rule, False
    return ('fixed_nights' if night == fixed_nights else None), rule is not None


def parse_args(argv=None):
    a = argparse.ArgumentParser(description='Game mode (GW-S): learn Crafter by itself.')
    a.add_argument('--parent', required=True)
    a.add_argument('--out', required=True)
    a.add_argument('--seed', type=int, required=True)
    a.add_argument('--smoke', action='store_true')
    a.add_argument('--data', default=os.environ.get('CUSTOM_IO_DATA', SK200K if os.path.isdir(SK200K) else DEFAULT_DATA))
    a.add_argument('--threads', type=int, default=2)
    a.add_argument('--picker', default='greedy', choices=['greedy', 'sample'],
                   help="sample: practice games sample a move from the model's odds over the 17 moves, quiz games take the top one")
    a.add_argument('--quiz-picker', default='top', choices=['top', 'sample'], help='with --picker sample: how quiz games choose')
    a.add_argument('--keep-awake-only', action='store_true',
                   help='the keep rule drops kept moves made while the player was asleep (they did nothing)')
    a.add_argument('--keep', default='window', choices=['window', 'guess'],
                   help='window: the 8-move window before each first unlock; guess: a learned value guesser with RND curiosity picks the same number of moves')
    a.add_argument('--night', default='copy', choices=['copy', 'pg'],
                   help='copy: the night trains on the kept rows plus diary (default); pg: PPO on every awake move of the day by its advantage (needs --keep guess --picker sample)')
    a.add_argument('--nights', type=int, default=None,
                   help='play exactly this many nights; the stop rule is still logged but no longer ends the run')
    a.add_argument('--full-model', action='store_true', help='diagnostic: no add-on, the whole model trains')
    return a.parse_args(argv)


def main(argv=None):
    a = parse_args(argv)
    if a.night == 'pg':
        assert a.keep == 'guess' and a.picker == 'sample', '--night pg needs --keep guess and --picker sample'
        assert not a.full_model, '--night pg trains the add-on only'
    a.out = os.path.abspath(a.out)
    torch.set_num_threads(a.threads)
    T, t_run = Counter(), time.time()
    draw = open(dm.CONST_PATH, 'rb').read()
    dsha = hashlib.sha256(draw).hexdigest()
    gcons, graw = play.load_constants()
    gsha = hashlib.sha256(graw).hexdigest()
    cons = {**json.loads(draw), **gcons}   # choice: one dict; game keys (episodes_per_day, explore, ...) win on overlap
    if a.smoke:
        cons.update(SMOKE)
    if a.nights is not None:
        assert 1 <= a.nights <= cons['max_nights'], '--nights %d must be within 1..max_nights (%d)' % (a.nights, cons['max_nights'])
    commit, dirty = dm.git_info()
    log = dm.Log(a.out)
    parent = dm.guard(a.parent)
    log('start', parent=parent, seed=a.seed, smoke=a.smoke, full_model=a.full_model, picker=a.picker, quiz_picker=a.quiz_picker, keep_awake_only=a.keep_awake_only, keep=a.keep, night=a.night, fixed_nights=a.nights, domain_constants=json.loads(draw),
        game_constants=gcons, domain_constants_sha256=dsha, game_constants_sha256=gsha, cons_used=cons,
        smoke_updates=SMOKE_UPDATES if a.smoke else None, data=a.data, git_commit=commit, git_dirty_files=dirty)
    write_row = lambda **kw: log.write('row', **kw)

    torch.manual_seed(a.seed)
    ck = torch.load(parent, map_location='cpu', weights_only=True)
    torch.manual_seed(a.seed)
    m = load_model(parent).eval()
    ctx = dict(vchars=set(ck['chars']))

    # diary and check set, from TRAIN prompts only, exactly as domain mode builds them
    t = time.time()
    pool = []
    with open(dm.guard(os.path.join(a.data, 'train.jsonl'))) as f:
        for line in f:
            p = json.loads(line)['prompt']
            if len(p) <= MAX_PROMPT and set(p) <= ctx['vchars']:
                pool.append(p)
    pool = list(dict.fromkeys(pool))
    random.Random(f'{a.seed}-diary').shuffle(pool)
    diary, check, _ = dm.build_diary(m, pool, cons, ctx, log, write_row)
    addon = None
    if not a.full_model:
        addon = dm.AddOn(m, cons['addon_rank'], cons['addon_alpha'], seed=a.seed)
        addon.on = True
        log('addon', rank=cons['addon_rank'], alpha=cons['addon_alpha'], lr=cons['addon_lr'], params=addon.n_params())
    T['diary'] += time.time() - t
    assert diary and check, 'empty diary or check set'

    guesser = guess.Guesser(a.seed) if a.keep == 'guess' else None
    quiz_picker = a.quiz_picker if a.picker == 'sample' else 'greedy'

    temp = temp_start = 1.0   # the policy temperature: 1 for every run but --night pg (addendum A13)
    if a.night == 'pg':
        # order chosen: harvest views from the first quiz worlds at T = 1, fit T0, then play the real night-0 quiz at T0
        temp, tinfo = start_temp(m, a.seed, cons, quiz_picker)
        temp_start = temp
        log('temp', **tinfo)

    def quiz(night):
        t = time.time()
        eps = play_worlds(m, a.seed, 0, cons['quiz_worlds'], cons, log_steps=True, picker=quiz_picker, temp=temp)
        T['quiz'] += time.time() - t
        mp = os.path.join(a.out, 'moves', f'quiz_night_{night}.jsonl.gz')
        log('moves', path=mp, lines=write_moves(mp, eps), kind='quiz')
        st = episode_stats(eps)
        prog = play.progress(eps)
        log('quiz', night=night, progress=round(prog, 3), unlock_share=st['unlock_share'], mean_length=st['mean_length'])
        return prog, st['steps']

    hist, quiz_steps, game_steps, rows_per_night = [], 0, 0, []
    p0, s0 = quiz(0)
    hist.append(p0)
    quiz_steps += s0
    all_rows, undo_prev, stop, night, last_ck = [], False, None, 0, None
    for night in range(1, (a.nights or cons['max_nights']) + 1):
        t = time.time()
        eps = play_worlds(m, a.seed, night, cons['episodes_per_day'], cons, log_steps=True, picker=a.picker, temp=temp)
        T['play'] += time.time() - t
        mp = os.path.join(a.out, 'moves', f'day_{night}.jsonl.gz')
        log('moves', path=mp, lines=write_moves(mp, eps), kind='practice')
        st = episode_stats(eps)
        game_steps += st['steps']
        t = time.time()
        ginfo = None
        pginfo = None
        if a.night == 'pg':
            new, pg_prompts, pg_acts, pg_adv, by_src, n_asleep, ginfo = pg_day(m, eps, cons, night, write_row, guesser, a.keep_awake_only)
            by_name, refused = Counter({'pg': len(new)}), Counter()
        elif guesser is None:
            new, by_src, by_name, refused, n_asleep = keep_rows(m, eps, cons, night, write_row, a.keep_awake_only)
        else:
            new, by_src, by_name, refused, n_asleep, ginfo = keep_guess_rows(m, eps, cons, night, write_row, guesser, a.keep_awake_only)
        T['keep'] += time.time() - t
        if ginfo is not None:
            T['guess'] += ginfo['seconds']
            log('guess', night=night, **ginfo)
        all_rows += new
        rows_per_night.append(len(new))
        log('day', night=night, episodes=st['episodes'], steps=st['steps'], mean_length=st['mean_length'], deaths=st['deaths'],
            unlocks=st['unlocks'], source_share=st['source_share'], rows_by_source=dict(by_src),
            rows_by_unlock=dict(sorted(by_name.items())), refusals=dict(refused), dropped_asleep=n_asleep)

        n_new = len(new)
        vis = cons['visits_per_new_row'] / 2 if undo_prev else cons['visits_per_new_row']
        if a.night == 'pg':
            updates = pg.PASSES * math.ceil(n_new / pg.MINIBATCH) if n_new else 0
        elif a.smoke:
            updates = SMOKE_UPDATES if n_new else 0
        else:
            updates = math.ceil(vis * n_new / (cons['batch'] * (1 - cons['replay_share']))) if n_new else 0
        log('night_plan', night=night, new_rows=n_new, visits_per_new_row=vis, updates=updates, halved_after_undo=undo_prev)
        snap = {k: v.detach().clone() for k, v in m.state_dict().items()}
        asnap = addon.snapshot() if addon is not None else None
        temp_snap = temp

        def agreement():
            t = time.time()
            if addon is not None:
                addon.on = False   # the check prompts are old questions: add-on off
            v = dm.check_agree(m, check)
            if addon is not None:
                addon.on = True
            T['check'] += time.time() - t
            return v
        before = agreement()
        t = time.time()
        if a.night == 'pg':   # the one place the night differs: PPO on the day's moves, add-on only, no diary rows
            losses = []
            if updates:
                pginfo, losses = pg.night(m, addon, pg_prompts, pg_acts, pg_adv, cons['explore'], seed=a.seed * 1000 + night, temp=temp)
                temp = pginfo['temp_after']
                pginfo['mean_abs_adv_raw'] = ginfo['mean_abs_adv_raw']
                log('pg', night=night, **pginfo)
            m.eval()
        else:
            losses = dm.train_night(m, new, diary, updates, cons, seed=a.seed * 1000 + night, addon=addon) if updates else []
        T['train'] += time.time() - t
        agree = agreement()
        drop = before - agree
        undo = (100.0 - agree if cons['undo_total'] else drop) > cons['undo_drop_points']
        if undo:
            m.load_state_dict(snap)
            if addon is not None:
                addon.restore(asnap)
            temp = temp_snap   # T is part of the night's work: undone with it
            m.eval()
        undo_prev = undo
        log('check', night=night, agreement_before=round(before, 2), agreement=round(agree, 2), drop=round(drop, 2),
            undo=undo, rows_dropped=n_new if undo else 0)

        t = time.time()
        last_ck = os.path.join(a.out, f'night_{night}', 'checkpoint.pt')
        dm.save_ckpt(ck, m, last_ck, addon)
        if a.night == 'pg':
            with open(os.path.join(a.out, f'night_{night}', 'policy_temp.json'), 'w') as f:
                json.dump(dict(T=temp), f)
        if guesser is not None:
            guesser.save(os.path.join(a.out, f'night_{night}', 'guess.pt'))
        T['save'] += time.time() - t
        pq, sq = quiz(night)
        hist.append(pq)
        quiz_steps += sq
        log('night', night=night, updates=updates, loss_first10=round(float(np.mean(losses[:10])), 4) if losses else None,
            loss_last10=round(float(np.mean(losses[-10:])), 4) if losses else None, undone=undo, checkpoint=last_ck,
            quiz=round(pq, 3))

        rise = hist[night] - hist[night - 2] if night >= 2 else None
        stop, ignored = stop_decision(rise, night, cons, a.nights)
        log('stop_check', night=night, rise_over_2_nights_points=None if rise is None else round(rise, 3), stop=stop,
            **(dict(stop_ignored=True) if ignored else {}))
        if stop:
            break

    # the model's own switch: practised game prompts vs diary prompts, reader features with the add-on off
    t = time.time()
    if addon is not None:
        addon.on = False
        pos = sorted({r['prompt'] for r in all_rows})
        if len(pos) > GATE_MAX:
            pos = random.Random(f'{a.seed}-gate').sample(pos, GATE_MAX)
        if pos:
            gate, gacc = route.train_gate(route.features(m, pos), route.features(m, [r['prompt'] for r in diary]))
            gpath = os.path.join(a.out, 'gate.pt')
            torch.save(gate.state, gpath)
            log('gate', pos=len(pos), neg=len(diary), train_acc=round(gacc, 4), path=gpath)
        else:
            log('gate', skipped='no kept rows')
        addon.on = True
    else:
        log('gate', skipped='full-model run has no add-on')
    T['gate'] += time.time() - t
    summary = dict(parent=parent, seed=a.seed, smoke=a.smoke, full_model=a.full_model, picker=a.picker, quiz_picker=a.quiz_picker, keep_awake_only=a.keep_awake_only, keep=a.keep, night=a.night, temp_start=temp_start, temp_final=temp, nights_run=night, stop_reason=stop, fixed_nights=a.nights,
                   quiz_history=[round(p, 3) for p in hist], rows_per_night=rows_per_night, game_steps=game_steps,
                   quiz_steps=quiz_steps, final_checkpoint=last_ck, domain_constants_sha256=dsha, game_constants_sha256=gsha,
                   git_commit=commit, seconds={k: round(v, 1) for k, v in T.items()}, total_seconds=round(time.time() - t_run, 1))
    with open(os.path.join(a.out, 'summary.json'), 'w') as f:
        json.dump(summary, f, indent=1)
    log('done', nights_run=night, stop_reason=stop, final_checkpoint=last_ck, total_seconds=summary['total_seconds'])


if __name__ == '__main__':
    main()
