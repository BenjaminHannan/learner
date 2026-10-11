"""Night-1 screen: one domain-mode night on exactly the rows a finished run trained on, with one change (the protection).

  python -m mainbrain.night1 --run RUNS/sheet-s200-v4 --seed 200 --method plain|gp|kf [--energy 0.97] --out DIR [--threads 4]

Everything but the protection is v4's night 1: the parent, the 4,096-row diary and the night-1 rows (read from the run's
log), the run's constants (from its start event), mode.train_night with the same seed (AdamW lr 1e-4, batch 64, half
diary replay, clip 1.0), and the same 512-prompt forgetting check. Writes DIR/night_1/checkpoint.pt and DIR/result.json:
the check agreement, the model's own quiz, the sealed near/far panel score (scoring only) and the DEV in_dist harm measure.
"""
import argparse
import importlib
import json
import math
import os
import random
import time

import torch

from custom_io.models import load_model
from domain import harm, mode, score
from domain.analyze import pooled, read_log, scored_kinds
from mainbrain import gp, kf
from mainbrain.common import PANEL, check_set, parent_of, run_rows, train_pool


def dev_hits(ckpt, rows, cache):
    if cache and os.path.exists(cache):
        return json.load(open(cache))
    h, exact = harm.in_dist_hits(ckpt, rows)
    if cache:
        json.dump(dict(hits=h, exact=exact), open(cache, 'w'))
    return dict(hits=h, exact=exact)


def main(argv=None):
    a = argparse.ArgumentParser()
    a.add_argument('--run', required=True)
    a.add_argument('--seed', type=int, required=True)
    a.add_argument('--method', required=True, choices=['plain', 'gp', 'kf'])
    a.add_argument('--energy', type=float, default=None)
    a.add_argument('--out', required=True)
    a.add_argument('--threads', type=int, default=4)
    a.add_argument('--data', default=os.environ.get('CUSTOM_IO_DATA'))
    a.add_argument('--updates', type=int, default=None, help='default: the run plan (visits * rows / new rows per batch)')
    a.add_argument('--parent-dev-cache', default=None)
    a.add_argument('--lr', type=float, default=None, help='night lr (default: the source run constants)')
    a.add_argument('--refresh-every', type=int, default=0, help='kf only: re-measure the protected directions every N updates')
    a.add_argument('--refresh-n', type=int, default=1024, help='diary rows used for each re-measure')
    a = a.parse_args(argv)
    assert a.method == 'plain' or a.energy, '--energy is needed for gp and kf'
    torch.set_num_threads(a.threads)
    os.makedirs(a.out, exist_ok=True)
    t0, T = time.time(), {}
    say = lambda *x: print(f'[{time.time() - t0:7.1f}s]', *x, flush=True)

    events = read_log(a.run)
    cons = [e for e in events if e['event'] == 'start'][0]['constants']
    for k, v in dict(replay_pick=False, replay_fresh=False, addon=None).items():   # keys added to the constants after v4
        cons.setdefault(k, v)
    if a.lr:
        cons['lr'] = a.lr
    assert not cons.get('addon') and not cons.get('replay_fresh') and not cons.get('replay_pick'), 'source run must be a plain whole-model run'
    parent = parent_of(a.seed)
    torch.manual_seed(a.seed)
    ck = torch.load(parent, map_location='cpu', weights_only=True)
    torch.manual_seed(a.seed)
    m = load_model(parent).eval()
    rows = run_rows(a.run)
    diary, new = rows[0], rows[1]
    updates = a.updates or math.ceil(cons['visits_per_new_row'] * len(new) / (cons['batch'] * (1 - cons['replay_share'])))
    say('diary', len(diary), 'new', len(new), 'updates', updates)

    pool = train_pool(a.data, ck['chars'], a.seed)
    check = check_set(m, pool, cons['check'])
    tool = importlib.import_module('domain.tools.sheet')
    helps = tool.help()
    kinds = [h['kind'] for h in helps]
    ex = {h['kind']: h['prompt'] for h in helps}
    ctx = dict(vchars=set(ck['chars']), cons=cons, seen=set(), quiz_set=set(), lmax=mode.lmax_of(helps, cons['digit_len_extra']))
    quiz = mode.make_quiz(tool, kinds, ex, cons['quiz'], random.Random(f'{a.seed}-quiz'), ctx, lambda *x, **k: None)
    _, q0 = mode.quiz_eval(m, quiz, kinds)
    say('quiz before', round(100 * q0, 2))

    info, frozen = {}, []
    t = time.time()
    if a.method in ('gp', 'kf'):
        if a.method == 'gp':
            P, info = gp.projectors(gp.covariances(m, diary), a.energy)
            wrap = lambda mm, base: gp.GPOptimizer(mm, base, P)
        else:
            F, info = kf.factors(kf.kfac_stats(m, diary), a.energy)
            sub = diary[:a.refresh_n]
            refresh = (lambda: kf.factors(kf.kfac_stats(m, sub), a.energy)[0]) if a.refresh_every else None
            wrap = lambda mm, base: kf.KFOptimizer(mm, base, F, refresh=refresh, every=a.refresh_every)
        frozen = gp.freeze_unprojected(m)
        base_make = mode.make_opt
        mode.make_opt = lambda mm, lr: wrap(mm, base_make(mm, lr))
    T['protect_setup'] = round(time.time() - t, 1)
    say('protection', a.method, a.energy, 'frozen', len(frozen), 'setup s', T['protect_setup'])

    before = mode.check_agree(m, check)
    t = time.time()
    losses = mode.train_night(m, new, diary, updates, cons, seed=a.seed * 1000 + 1)
    T['train'] = round(time.time() - t, 1)
    after = mode.check_agree(m, check)
    _, q1 = mode.quiz_eval(m, quiz, kinds)
    path = os.path.join(a.out, 'night_1', 'checkpoint.pt')
    mode.save_ckpt(ck, m, path)
    say('trained', T['train'], 's; loss first10', round(sum(losses[:10]) / 10, 4), 'last10', round(sum(losses[-10:]) / 10, 4),
        'agreement', round(before, 2), '->', round(after, 2), 'quiz', round(100 * q1, 2))

    t = time.time()
    _, scored, _, _, _ = scored_kinds(tool, events)
    prow = score.load_panel(PANEL)
    s0 = score.score(parent, prow, 'parent')
    s1 = score.score(path, prow, 'night_1')
    near0, near1 = pooled(s0['rows'], scored, 'near'), pooled(s1['rows'], scored, 'near')
    far0, far1 = pooled(s0['rows'], scored, 'far'), pooled(s1['rows'], scored, 'far')
    per_kind = {k: dict(near0=pooled(s0['rows'], [k], 'near'), near1=pooled(s1['rows'], [k], 'near')) for k in scored}
    dev_path = os.path.join(a.data, 'dev', 'in_dist.jsonl')
    drows = harm.load_rows(dev_path)
    h0 = dev_hits(parent, drows, a.parent_dev_cache)
    h1 = dev_hits(path, drows, None)
    hm = harm.harm_measure(h0['hits'], h1['hits'], drows, family_drop=5.0, in_dist_drop=1.5)
    T['score'] = round(time.time() - t, 1)
    fam = {f: dict(a=round(v['a'], 1), b=round(v['b'], 1), drop=round(v['drop'], 2), fires=v['fires'])
           for f, v in hm['families'].items()}
    res = dict(run=a.run, seed=a.seed, method=a.method, energy=a.energy, lr=cons['lr'], refresh_every=a.refresh_every, updates=updates, new_rows=len(new), diary=len(diary),
               frozen=frozen, layers=info, loss_first10=sum(losses[:10]) / 10, loss_last10=sum(losses[-10:]) / 10,
               agreement_before=before, agreement_after=after, quiz_before=100 * q0, quiz_after=100 * q1,
               near_parent=near0, near_after=near1, near_gain=near1 - near0, far_parent=far0, far_after=far1,
               near_per_kind=per_kind, in_dist_parent=hm['in_dist_a'], in_dist_after=hm['in_dist_b'],
               in_dist_drop=hm['in_dist_drop'], fired=hm['fired'], dm3_passes=hm['passes'], families=fam,
               seconds=T, total_seconds=round(time.time() - t0, 1), checkpoint=path)
    json.dump(res, open(os.path.join(a.out, 'result.json'), 'w'), indent=1)
    say('RESULT near', round(near0, 2), '->', round(near1, 2), f'({near1 - near0:+.2f})', 'in_dist drop', round(hm['in_dist_drop'], 2),
        'fired', hm['fired'], 'DM3 pass', hm['passes'])


if __name__ == '__main__':
    main()
