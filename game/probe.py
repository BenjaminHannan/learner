"""Labelled-views capacity probe (game-world test GW-L, addendum A22).

  python -m game.probe gen --out DIR [--smoke]
  python -m game.probe train --parent CKPT --data DIR --n N --seed S --out DIR2 [--threads 3] [--epochs E]
  python -m game.probe eval --ckpt CKPT [--ckpt CKPT ...] --data DIR --train-n N --out FILE.json [--threads 3] [--names a b ...]

gen: practice worlds only (run seeds 390 train, 391 held-out); each step takes the labeller's move (game.oracle) with chance
0.5, else a uniform random move; every visited view is recorded with its label. train: the add-on (rank 8) is trained by
cross entropy of the labelled word under the softmax of the 17 word log-probs (T = 1). eval: top-1 accuracy on the held-out
views. Never plays a sealed world.
"""
import argparse
import json
import os
import random
import time
from collections import Counter

import numpy as np
import torch

from game import oracle, pg, play
from game.crafter_text import TextEnv

TRAIN_RUN, HELD_RUN = 390, 391
TRAIN_VIEWS, HELD_VIEWS = 16_000, 2_000
SMOKE_VIEWS, SMOKE_WORLDS, SMOKE_CAP = (200, 40), 4, 200
WORLDS_PER_DAY = 64
CHANCE_ORACLE = 0.5
SHUFFLE_SEED = 0
LR, MINIBATCH, CHUNK = 1e-3, 256, 64
SUBSET = ('nav', 'act')   # S: the views whose label depends on the map


def default_epochs(n):
    return 40 if n <= 1000 else 20 if n <= 4000 else 10


def episode(seed, cap):
    """-> list of (view, word, reason) for the views of one episode (the view before each step), mixed policy."""
    assert not play.is_sealed(seed), 'a sealed world in game/probe.py'
    env = TextEnv(seed=seed, length=cap)
    rng = np.random.default_rng(seed)
    view, out, done = env.reset(), [], False
    while not done:
        word, reason = oracle.label(view)
        out.append((view, word, reason))
        u, r = rng.random(), int(rng.integers(play.N_ACTIONS))
        a = play.WORDS.index(word) if u < CHANCE_ORACLE else r
        view, _, done, _ = env.step(a)
    return out


def collect(run_seed, target, worlds_per_day, cap, exclude=()):
    """Whole days of episodes until at least `target` unique views (not in `exclude`). -> (views in order, stats)."""
    assert run_seed in (TRAIN_RUN, HELD_RUN)
    keep, seen = [], set(exclude)
    st = dict(run_seed=run_seed, days=0, worlds=0, steps=0, duplicates_dropped=0, excluded_dropped=0, seeds=[])
    day = 0
    while len(keep) < target:
        for i in range(worlds_per_day):
            seed = play.practice_seed(run_seed, day, i)
            assert not play.is_sealed(seed), seed
            st['seeds'].append(seed)
            st['worlds'] += 1
            for view, word, reason in episode(seed, cap):
                st['steps'] += 1
                if view in seen:
                    st['excluded_dropped' if view in exclude else 'duplicates_dropped'] += 1
                    continue
                seen.add(view)
                keep.append(dict(view=view, label=word, reason=reason))
        day += 1
        st['days'] = day
    return keep, st


def hist(rows, key):
    return dict(sorted(Counter(r[key] for r in rows).items()))


def write_jsonl(path, rows):
    with open(path, 'w') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')


def read_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f]


def gen(out, smoke=False, train_views=None, reuse_heldout=None):
    """train_views: a larger train set than TRAIN_VIEWS (A22's pre-registered N = 64,000 run). reuse_heldout: a folder whose
    heldout.jsonl is kept as it is (so accuracies stay comparable) and whose views are dropped from the new train set."""
    t0 = time.time()
    n_train, n_held = SMOKE_VIEWS if smoke else (TRAIN_VIEWS, HELD_VIEWS)
    n_train = train_views or n_train
    wpd = SMOKE_WORLDS if smoke else WORLDS_PER_DAY
    cap = SMOKE_CAP if smoke else play.load_constants()[0]['episode_cap']
    if reuse_heldout:
        held = read_jsonl(os.path.join(reuse_heldout, 'heldout.jsonl'))
        hs = dict(reused_from=reuse_heldout)
        train, ts = collect(TRAIN_RUN, n_train, wpd, cap, exclude={r['view'] for r in held})
        train_all = {r['view'] for r in train}
        random.Random(SHUFFLE_SEED).shuffle(train)
    else:
        train, ts = collect(TRAIN_RUN, n_train, wpd, cap)
        train_all = {r['view'] for r in train}
        held, hs = collect(HELD_RUN, n_held, wpd, cap, exclude=train_all)
        for rows in (train, held):
            random.Random(SHUFFLE_SEED).shuffle(rows)
    train, held = train[:n_train], held[:n_held]
    os.makedirs(out, exist_ok=True)
    write_jsonl(os.path.join(out, 'train.jsonl'), train)
    write_jsonl(os.path.join(out, 'heldout.jsonl'), held)
    info = dict(smoke=smoke, episode_cap=cap, chance_oracle=CHANCE_ORACLE, worlds_per_day=wpd, shuffle_seed=SHUFFLE_SEED,
                train=dict(count=len(train), unique_available=len(train_all), labels=hist(train, 'label'),
                           reasons=hist(train, 'reason'), **ts),
                heldout=dict(count=len(held), labels=hist(held, 'label'), reasons=hist(held, 'reason'), **hs),
                seconds=round(time.time() - t0, 1))
    with open(os.path.join(out, 'gen.json'), 'w') as f:
        json.dump(info, f, indent=1)
    return info


SAVE_EVERY = 25   # updates between resume files (the box restarts now and then; a restart costs at most this many updates)


def _save_resume(path, **st):
    tmp = path + '.tmp'
    torch.save(st, tmp)
    os.replace(tmp, path)


def train(parent, data, n, seed, out, epochs=None):
    """Resumable: every SAVE_EVERY updates the add-on, optimiser, shuffle state and epoch position go to OUT/resume.pt; a run started
    again with the same arguments continues from it and ends on exactly the weights an uninterrupted run would (tested)."""
    from custom_io.models import load_model
    from domain import mode as dm
    t0 = time.time()
    epochs = epochs or default_epochs(n)
    rows = read_jsonl(os.path.join(data, 'train.jsonl'))[:n]
    assert len(rows) == n, f'{data}/train.jsonl has fewer than {n} lines'
    views = [r['view'] for r in rows]
    labels = torch.tensor([play.WORDS.index(r['label']) for r in rows])
    with open(dm.CONST_PATH) as f:
        cons = json.load(f)
    ck = torch.load(parent, map_location='cpu', weights_only=True)
    torch.manual_seed(seed)
    m = load_model(parent).eval()
    addon = dm.AddOn(m, cons['addon_rank'], cons['addon_alpha'], seed=seed)
    addon.on = True
    params = addon.params()
    opt = torch.optim.Adam(params, lr=LR)
    gen_ = torch.Generator().manual_seed(seed)
    per_epoch, updates, epoch0, pos0, order, losses, hits, resumed = [], 0, 0, 0, None, [], 0, False
    os.makedirs(out, exist_ok=True)
    rpath = os.path.join(out, 'resume.pt')
    if os.path.exists(rpath):
        st = torch.load(rpath, map_location='cpu', weights_only=True)
        assert (st['n'], st['seed'], st['epochs'], st['parent']) == (n, seed, epochs, parent), 'resume.pt is from another run'
        addon.restore(st['addon'])
        opt.load_state_dict(st['opt'])
        gen_.set_state(st['gen'])
        per_epoch, updates, epoch0, pos0, order, losses, hits, resumed = (st['per_epoch'], st['updates'], st['epoch'], st['pos'],
                                                                          st['order'], st['losses'], st['hits'], True)
    for epoch in range(epoch0, epochs):
        if order is None:
            order, pos0, losses, hits = torch.randperm(n, generator=gen_), 0, [], 0
        for i in range(pos0, n, MINIBATCH):
            ix = order[i:i + MINIBATCH]
            opt.zero_grad(set_to_none=True)
            mb = 0.0
            for c in range(0, len(ix), CHUNK):   # chunks with summed gradients, as distil.run
                cx = ix[c:c + CHUNK]
                lg = play.move_logprobs_grad(m, [views[j] for j in cx.tolist()])
                logp = torch.log_softmax(lg.float(), -1)
                loss = torch.nn.functional.nll_loss(logp, labels[cx], reduction='sum') / len(ix)
                loss.backward()
                mb += float(loss.detach())
                hits += int((logp.argmax(-1) == labels[cx]).sum())
            torch.nn.utils.clip_grad_norm_(params, pg.MAX_GRAD_NORM)
            opt.step()
            updates += 1
            losses.append(mb)
            if updates % SAVE_EVERY == 0:
                _save_resume(rpath, n=n, seed=seed, epochs=epochs, parent=parent, addon=addon.snapshot(), opt=opt.state_dict(),
                             gen=gen_.get_state(), per_epoch=per_epoch, updates=updates, epoch=epoch, pos=i + MINIBATCH,
                             order=order, losses=losses, hits=hits)
        per_epoch.append(dict(loss=round(float(np.mean(losses)), 5), accuracy=round(hits / n, 4)))
        order, pos0 = None, 0
    m.eval()
    dm.save_ckpt(ck, m, os.path.join(out, 'checkpoint.pt'), addon)
    info = dict(parent=parent, n=n, epochs=epochs, seed=seed, updates=updates, lr=LR, minibatch=MINIBATCH,
                addon_rank=cons['addon_rank'], addon_alpha=cons['addon_alpha'], addon_params=addon.n_params(),
                per_epoch=per_epoch, resumed=resumed, seconds=round(time.time() - t0, 1))
    with open(os.path.join(out, 'train.json'), 'w') as f:
        json.dump(info, f, indent=1)
    if os.path.exists(rpath):
        os.remove(rpath)
    return info


def best_fixed(rows):
    """Most common label of rows, ties to the lowest word index. None for no rows."""
    c = Counter(r['label'] for r in rows)
    return max(c, key=lambda w: (c[w], -play.WORDS.index(w))) if c else None


def accuracy(rows, preds):
    return round(sum(r['label'] == p for r, p in zip(rows, preds)) / len(rows), 4) if rows else None


def evaluate(ckpts, data, train_n, names=None):
    from custom_io.models import load_model
    train_rows = read_jsonl(os.path.join(data, 'train.jsonl'))[:train_n]
    held = read_jsonl(os.path.join(data, 'heldout.jsonl'))
    sub = [i for i, r in enumerate(held) if r['reason'] in SUBSET]
    held_s = [held[i] for i in sub]
    names = names or list(ckpts)
    assert len(names) == len(ckpts)
    res = dict(heldout=len(held), subset=len(held_s), train_n=train_n, checkpoints={})
    fixed_s, fixed_all = best_fixed([r for r in train_rows if r['reason'] in SUBSET]), best_fixed(train_rows)
    res['baseline'] = dict(word_subset=fixed_s, accuracy_subset=accuracy(held_s, [fixed_s] * len(held_s)),
                           word_all=fixed_all, accuracy_all=accuracy(held, [fixed_all] * len(held)))
    for name, path in zip(names, ckpts):
        m = load_model(path).eval()
        lp = play.move_logprobs(m, [r['view'] for r in held])
        preds = [play.WORDS[int(np.argmax(row))] for row in lp]
        preds_s = [preds[i] for i in sub]
        per_word = {}
        for w in play.WORDS:
            ix = [k for k, r in enumerate(held_s) if r['label'] == w]
            if ix:
                per_word[w] = dict(count=len(ix), accuracy=round(sum(preds_s[k] == w for k in ix) / len(ix), 4))
        conf = Counter((r['label'], p) for r, p in zip(held_s, preds_s) if r['label'] != p)
        res['checkpoints'][name] = dict(
            ckpt=path, accuracy_all=accuracy(held, preds), accuracy_subset=accuracy(held_s, preds_s), per_word_subset=per_word,
            top_confusions_subset=[dict(label=a, predicted=b, count=c) for (a, b), c in
                                   sorted(conf.items(), key=lambda kv: (-kv[1], kv[0]))[:5]])
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description='Labelled-views capacity probe (GW-L).')
    sub = ap.add_subparsers(dest='cmd', required=True)
    g = sub.add_parser('gen')
    g.add_argument('--out', required=True)
    g.add_argument('--smoke', action='store_true')
    g.add_argument('--train-views', type=int, default=None, help='a larger train set (A22: the N = 64,000 run)')
    g.add_argument('--reuse-heldout', default=None, help='folder whose heldout.jsonl is kept; its views are dropped from the new train set')
    t = sub.add_parser('train')
    t.add_argument('--parent', required=True)
    t.add_argument('--data', required=True)
    t.add_argument('--n', type=int, required=True)
    t.add_argument('--seed', type=int, required=True)
    t.add_argument('--out', required=True)
    t.add_argument('--threads', type=int, default=3)
    t.add_argument('--epochs', type=int, default=None)
    e = sub.add_parser('eval')
    e.add_argument('--ckpt', action='append', required=True)
    e.add_argument('--data', required=True)
    e.add_argument('--train-n', type=int, required=True)
    e.add_argument('--out', required=True)
    e.add_argument('--threads', type=int, default=3)
    e.add_argument('--names', nargs='+')
    a = ap.parse_args(argv)
    if a.cmd == 'gen':
        info = gen(a.out, a.smoke, a.train_views, a.reuse_heldout)
        print('gen', 'train', info['train']['count'], 'heldout', info['heldout']['count'], 'seconds', info['seconds'], flush=True)
        return
    torch.set_num_threads(a.threads)
    if a.cmd == 'train':
        info = train(a.parent, a.data, a.n, a.seed, a.out, a.epochs)
        last = info['per_epoch'][-1]
        print('train n', a.n, 'epochs', info['epochs'], 'updates', info['updates'], 'loss', last['loss'], 'acc', last['accuracy'],
              'seconds', info['seconds'], flush=True)
    else:
        res = evaluate(a.ckpt, a.data, a.train_n, a.names)
        with open(a.out, 'w') as f:
            json.dump(res, f, indent=1)
        for name, r in res['checkpoints'].items():
            print(name, 'heldout all', r['accuracy_all'], 'S', r['accuracy_subset'], flush=True)


if __name__ == '__main__':
    main()
