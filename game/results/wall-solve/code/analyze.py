"""Steps 2 and 3 on the saved play files of one seed: Z8 (census of the GW-F rows under the A26 and A27 rules, built with the committed
game.imitate / game.census_ready functions) and Z7 (the model's top-1 on its own visited map-dependent views).
python analyze.py SEED [--root DIR]  -> ROOT/s{run_seed}/result.json"""
import argparse
import glob
import gzip
import json
import os
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from game import census_ready, imitate, oracle, play

W = play.WORDS


def load(out):
    games, lps, day_of_game = [], [], []
    for d in common.DAYS:
        p = f'{out}/play-d{d}.json.gz'
        if not os.path.exists(p):
            continue
        with gzip.open(p, 'rt') as f:
            gs = json.load(f)
        z = np.load(f'{out}/play-d{d}.lp.npz')
        assert z['lp'].shape[0] == sum(g['length'] for g in gs) == int(z['lengths'].sum())
        games += gs
        lps.append(z['lp'])
        day_of_game += [d] * len(gs)
    return games, np.concatenate(lps), day_of_game


def z8(games):
    res = dict(census=census_ready.one_round(games))    # A26 / A27 / FIRST26 / FIRST27 blocks plus V, E, exactly as census_ready
    sample = [dict(view=v, action=a) for g in games[:50] for v, a in zip(g['views'], g['actions'])][:20000]   # as imitate.run
    for name, rare in (('A26', 0), ('A27', 100)):
        segs = [s for gi, g in enumerate(games) for s in imitate.segments(g['events'], gi)]
        kept, thr = imitate.keep_segments(segs, rare)
        weights = imitate.type_weights(Counter(s['type'] for s in segs))
        rows = imitate.rows_of(kept, games, weights)
        c = res['census'][name]
        assert c.get('rows', 0) == len(rows), (name, c.get('rows'), len(rows))
        st = imitate.iteration_stats(1, 1.0, games, segs, kept, thr, rows, 0, 0, [], sample, 0.0, 0.0)
        for k in ('temp', 'loss_first', 'loss_last', 'updates', 'train_rows', 'buffer_before', 'seconds_play', 'seconds_train'):
            st.pop(k)    # not meaningful: no training here
        st['rare_below'] = rare
        st['weights'] = {k: round(v, 5) for k, v in sorted(weights.items())}
        res[name] = st
    return res


def agree(mask, hit):
    n = int(mask.sum())
    return dict(views=n, agreement=round(float(hit[mask].sum()) / n, 4) if n else None)


def z7(games, lp, day_of_game, held_ref):
    views = [v for g in games for v in g['views']]
    acts = np.array([a for g in games for a in g['actions']])
    answers = [w for g in games for w in g['answers']]
    srcs = np.array([s for g in games for s in g['sources']])
    game_ix = np.concatenate([[i] * g['length'] for i, g in enumerate(games)])
    day = np.array([day_of_game[i] for i in game_ix])
    cache = {}
    labs = []
    for v in views:
        if v not in cache:
            cache[v] = oracle.label(v)
        labs.append(cache[v])
    lab_w = np.array([W.index(w) for w, _ in labs])
    reason = np.array([r for _, r in labs])
    S = np.isin(reason, ('nav', 'act'))
    top1 = lp.argmax(1)
    hit_top = top1 == lab_w
    hit_exec = acts == lab_w
    hit_samp = np.array([W.index(a) if a in W else -1 for a in answers]) == lab_w
    seen, uniq = set(), np.zeros(len(views), bool)
    for i, v in enumerate(views):
        if v not in seen:
            seen.add(v)
            uniq[i] = True
    sets = {'first200_days01': day <= 1, 'all400': np.ones(len(views), bool)}
    sets = {k: v for k, v in sets.items() if v.any()}
    out = dict(reasons_all=dict(Counter(reason.tolist())), held_out=held_ref, sets={})
    for name, sel in sets.items():
        o = dict(games=int(len(set(game_ix[sel].tolist()))), steps=int(sel.sum()),
                 reasons=dict(Counter(reason[sel].tolist())))
        for tag, extra in (('visits', np.ones(len(views), bool)), ('unique_views', uniq)):
            mS = sel & S & extra
            blk = dict(top1=agree(mS, hit_top), executed=agree(mS, hit_exec), sampled_word=agree(mS, hit_samp),
                       own_steps_executed=agree(mS & (srcs == 'own'), hit_exec),
                       top1_nav=agree(sel & extra & (reason == 'nav'), hit_top), top1_act=agree(sel & extra & (reason == 'act'), hit_top),
                       top1_all_reasons=agree(sel & extra, hit_top))
            if held_ref and blk['top1']['agreement'] is not None:
                blk['top1_minus_heldout_S_points'] = round(100 * (blk['top1']['agreement'] - held_ref['accuracy_subset']), 2)
            o[tag] = blk
        out['sets'][name] = o
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('seed', type=int)
    ap.add_argument('--root', default=common.Z)
    ap.add_argument('--allow-partial', action='store_true', help='smoke only: do not require 400 games over days 0..3')
    a = ap.parse_args()
    out = common.outdir(a.seed, a.root)
    games, lp, dog = load(out)
    if not a.allow_partial:
        assert sorted(set(dog)) == list(common.DAYS) and len(games) == 400, ('partial data', sorted(set(dog)), len(games))
    held = None
    if os.path.exists(f'{out}/repro.json'):
        with open(f'{out}/repro.json') as f:
            held = {k: v for k, v in json.load(f).items() if k in ('accuracy_subset', 'accuracy_all', 'a23_accuracy_subset', 'pass')}
    res = dict(model_seed=a.seed, run_seed=common.RUN_SEED[a.seed], games=len(games), steps=int(lp.shape[0]), days=sorted(set(dog)),
               z8=z8(games), z7=z7(games, lp, dog, held),
               primary_readings=dict(
                   z7='z7.sets.first200_days01.visits (every visited view of the first 200 games, days 0-1; top1_minus_heldout_S_points). '
                      'unique_views and all400 are secondary. Fixed before any number was seen.',
                   oracle_agreement_all_played_moves_nav_act='z7.sets.all400.visits.executed (all 400 games); z8.A2x.oracle_agreement_all_played is imitate\'s 50-game, <=20,000-view sample.'))
    with open(f'{out}/result.json', 'w') as f:
        json.dump(res, f, indent=1)
    print('wrote', f'{out}/result.json', 'games', len(games), 'steps', res['steps'])


if __name__ == '__main__':
    main()
