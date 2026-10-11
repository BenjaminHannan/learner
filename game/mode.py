"""Game mode (GW-S): a model learns the Crafter game by itself, with domain mode's loop.

Plan: /mnt/project-files/game-world/PLAN-AND-MARKS-2026-10-10.md.

  python -m game.mode --parent CKPT --out DIR --seed N [--smoke] [--data DIR] [--threads N] [--full-model] [--picker greedy|sample] [--quiz-picker top|sample]

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
from game import play

FAMILY = 'game_crafter'
SMOKE = dict(episodes_per_day=4, quiz_worlds=2, episode_cap=60, diary=128, check=64, max_nights=2)
SMOKE_UPDATES = 20
SK200K = '/tmp/claude-0/-home-user-learner/a35c4c05-cfae-5dd3-a5ce-480213b76700/scratchpad/sk200k'
GATE_MAX = 4096


def keep_windows(unlocks, credit_window):
    """The keep rule. unlocks = [(step, name)] in order. For each unlock at step t keep steps
    max(prev, t - credit_window + 1) .. t, prev = previous kept unlock's step + 1 (0 at the start), so windows never overlap.
    -> [(step, unlock name, unlock step)]. choice: a second unlock on the same step has an empty window (prev > t)."""
    out, prev = [], 0
    for t, name in unlocks:
        for s in range(max(prev, t - credit_window + 1), t + 1):
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


def play_worlds(m, run_seed, day, n, cons, log_steps, picker='greedy'):
    """picker: 'greedy' (the written answer), 'top' or 'sample' (the model's odds over the 17 moves, play.move_policy)."""
    seeds, acts = world_seeds(run_seed, day, n)
    return play.play(play.picked_policy(m, picker), seeds, acts, cons['explore'], cons['episode_cap'], log_steps=log_steps)


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


def keep_rows(m, eps, cons, day, write_row):
    """Rows from the kept steps of each episode. -> (rows, by source, by unlock name, refusals by reason)."""
    rows, by_src, by_name, refused = [], Counter(), Counter(), Counter()
    for e in eps:
        for s, name, t in keep_windows(e['unlocks'], cons['credit_window']):
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
    return rows, by_src, by_name, refused


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
    a.add_argument('--full-model', action='store_true', help='diagnostic: no add-on, the whole model trains')
    return a.parse_args(argv)


def main(argv=None):
    a = parse_args(argv)
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
    commit, dirty = dm.git_info()
    log = dm.Log(a.out)
    parent = dm.guard(a.parent)
    log('start', parent=parent, seed=a.seed, smoke=a.smoke, full_model=a.full_model, picker=a.picker, quiz_picker=a.quiz_picker, domain_constants=json.loads(draw),
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

    quiz_picker = a.quiz_picker if a.picker == 'sample' else 'greedy'

    def quiz(night):
        t = time.time()
        eps = play_worlds(m, a.seed, 0, cons['quiz_worlds'], cons, log_steps=True, picker=quiz_picker)
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
    for night in range(1, cons['max_nights'] + 1):
        t = time.time()
        eps = play_worlds(m, a.seed, night, cons['episodes_per_day'], cons, log_steps=True, picker=a.picker)
        T['play'] += time.time() - t
        mp = os.path.join(a.out, 'moves', f'day_{night}.jsonl.gz')
        log('moves', path=mp, lines=write_moves(mp, eps), kind='practice')
        st = episode_stats(eps)
        game_steps += st['steps']
        t = time.time()
        new, by_src, by_name, refused = keep_rows(m, eps, cons, night, write_row)
        T['keep'] += time.time() - t
        all_rows += new
        rows_per_night.append(len(new))
        log('day', night=night, episodes=st['episodes'], steps=st['steps'], mean_length=st['mean_length'], deaths=st['deaths'],
            unlocks=st['unlocks'], source_share=st['source_share'], rows_by_source=dict(by_src),
            rows_by_unlock=dict(sorted(by_name.items())), refusals=dict(refused))

        n_new = len(new)
        vis = cons['visits_per_new_row'] / 2 if undo_prev else cons['visits_per_new_row']
        if a.smoke:
            updates = SMOKE_UPDATES if n_new else 0
        else:
            updates = math.ceil(vis * n_new / (cons['batch'] * (1 - cons['replay_share']))) if n_new else 0
        log('night_plan', night=night, new_rows=n_new, visits_per_new_row=vis, updates=updates, halved_after_undo=undo_prev)
        snap = {k: v.detach().clone() for k, v in m.state_dict().items()}
        asnap = addon.snapshot() if addon is not None else None

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
        losses = dm.train_night(m, new, diary, updates, cons, seed=a.seed * 1000 + night, addon=addon) if updates else []
        T['train'] += time.time() - t
        agree = agreement()
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
        last_ck = os.path.join(a.out, f'night_{night}', 'checkpoint.pt')
        dm.save_ckpt(ck, m, last_ck, addon)
        T['save'] += time.time() - t
        pq, sq = quiz(night)
        hist.append(pq)
        quiz_steps += sq
        log('night', night=night, updates=updates, loss_first10=round(float(np.mean(losses[:10])), 4) if losses else None,
            loss_last10=round(float(np.mean(losses[-10:])), 4) if losses else None, undone=undo, checkpoint=last_ck,
            quiz=round(pq, 3))

        rise = hist[night] - hist[night - 2] if night >= 2 else None
        if rise is not None and rise < cons['stop_min_rise_points']:
            stop = 'quiz_rise_below_%g_over_2_nights' % cons['stop_min_rise_points']
        elif night == cons['max_nights']:
            stop = 'max_nights'
        log('stop_check', night=night, rise_over_2_nights_points=None if rise is None else round(rise, 3), stop=stop)
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
    summary = dict(parent=parent, seed=a.seed, smoke=a.smoke, full_model=a.full_model, picker=a.picker, quiz_picker=a.quiz_picker, nights_run=night, stop_reason=stop,
                   quiz_history=[round(p, 3) for p in hist], rows_per_night=rows_per_night, game_steps=game_steps,
                   quiz_steps=quiz_steps, final_checkpoint=last_ck, domain_constants_sha256=dsha, game_constants_sha256=gsha,
                   git_commit=commit, seconds={k: round(v, 1) for k, v in T.items()}, total_seconds=round(time.time() - t_run, 1))
    with open(os.path.join(a.out, 'summary.json'), 'w') as f:
        json.dump(summary, f, indent=1)
    log('done', nights_run=night, stop_reason=stop, final_checkpoint=last_ck, total_seconds=summary['total_seconds'])


if __name__ == '__main__':
    main()
