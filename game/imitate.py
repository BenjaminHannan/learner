"""GW-F (addendum A26): iterated fastest-segment self-imitation. The model plays practice games, every rise of an achievement counter is an
event, the moves between consecutive events are segments, the fastest 30% of each event type's segments (at most 12 moves) are kept, weighted by
rarity, and the add-on is trained to copy them. Then it plays again with the new add-on. No hand-written labeller: the only signal is the game's own
achievement counters and the model's own play (game.oracle is used only to report how the kept moves compare with it).

  python -m game.imitate run --parent CKPT --seed S --run-seed R --t0 T0 --out DIR [--iterations 24] [--threads 2] [--smoke]

Practice worlds only (run seeds 394 and 395); never a sealed world. Resumable: games are saved per chunk of 100 worlds, the loop state after every
iteration; a restarted run continues from them.
"""
import argparse
import gzip
import json
import math
import os
import random
import time
from collections import Counter

import numpy as np
import torch
from crafter import constants as crafter_constants

from game import lookahead, oracle, pg, play
from game.crafter_text import TextEnv, parse_action

EVENT_TYPES = tuple(crafter_constants.achievements)
KEEP_FRAC, MAX_LEN, W_RATIO, BUFFER_CAP = 0.3, 12, 20.0, 20_000
EPOCHS, LR, MINIBATCH, CHUNK = 3, 1e-3, 256, 64
CHUNKS, GAMES_PER_CHUNK = 4, 100          # 400 games an iteration: 4 practice "days" of 100 worlds
SNAPSHOTS = (3, 8, 16, 20, 24)                 # iterations whose merged checkpoint is saved for sealed scoring
ACT_TAG = 9


# DRAFT pending coordinator review (GW-LS): day_offset, run seeds 398 / 399 and --day-offset are the only changes for GW-LS.
def day_of(k, c, day_offset=0):
    """Practice day of chunk c (0..3) of iteration k (1-based): 4(k-1) + c + day_offset, always < 100 for k <= 24 (offset 0).
    GW-LS (day_offset 4) plays days 4..35; days 0-3 of run seeds 398 / 399 were the Z8 games."""
    return CHUNKS * (k - 1) + c + day_offset


# ---------- pure parts (tested) ----------

def segments(events, game):
    """events: [(step, type)] of one game. -> one dict per (event step, type): the moves since the previous event of any type (or the start),
    inclusive of the event's own move. length = end - prev_end; start = prev_end + 1."""
    by_step = {}
    for t, name in events:
        by_step.setdefault(t, []).append(name)
    out, prev = [], -1
    for t in sorted(by_step):
        for name in sorted(set(by_step[t])):
            out.append(dict(type=name, game=game, start=prev + 1, end=t, length=t - prev))
        prev = t
    return out


def keep_segments(segs, rare_below=0):
    """Per event type: sort by (length, game, end), take the first ceil(KEEP_FRAC n), drop those longer than MAX_LEN.
    A27 (rare_below > 0): a type with fewer than rare_below segments keeps every segment of at most MAX_LEN moves.
    -> (kept segments, {type: longest kept length})."""
    by = {}
    for s in segs:
        by.setdefault(s['type'], []).append(s)
    kept, thr = [], {}
    for ty in sorted(by):
        ss = sorted(by[ty], key=lambda s: (s['length'], s['game'], s['end']))
        take = ss if len(ss) < rare_below else ss[:math.ceil(KEEP_FRAC * len(ss))]
        sel = [s for s in take if s['length'] <= MAX_LEN]
        if sel:
            thr[ty] = max(s['length'] for s in sel)
            kept += sel
    return kept, thr


def type_weights(counts):
    """{type: n segments before the keep step} -> {type: n^(-1/2) raised to at least (largest weight)/W_RATIO}."""
    w = {t: n ** -0.5 for t, n in counts.items() if n > 0}
    if not w:
        return {}
    floor = max(w.values()) / W_RATIO
    return {t: max(v, floor) for t, v in w.items()}


def rows_of(kept, games, weights):
    """Training rows of the kept segments: one per (game, step); a step on several kept segments (same event step, several types) takes the largest weight.
    -> [dict(view, action, weight, type, seg_len)]."""
    best = {}
    for s in kept:
        g = games[s['game']]
        for j in range(s['start'], s['end'] + 1):
            w = weights[s['type']]
            if (s['game'], j) not in best or w > best[(s['game'], j)]['weight']:
                best[(s['game'], j)] = dict(view=g['views'][j], action=g['actions'][j], weight=w, type=s['type'], seg_len=s['length'])
    return [best[k] for k in sorted(best)]


def prune_buffer(buffer, thr):
    """Drop buffer rows of a type with a kept segment this iteration whose segment is longer than that type's longest kept length now."""
    return [r for r in buffer if r['type'] not in thr or r['seg_len'] <= thr[r['type']]]


def training_set(new, buffer, rng):
    """New rows plus a uniform sample of buffer rows of the same size (all of them if fewer). -> list of rows."""
    k = min(len(new), len(buffer))
    return list(new) + (rng.sample(buffer, k) if k else [])


def normalise(weights):
    m = sum(weights) / len(weights)
    return [w / m for w in weights]


# ---------- playing ----------

def play_games(policy, seeds, act_seeds, explore, cap):
    """The lockstep episodes of game.play.play (same act rule: one uniform number and one random action per step from default_rng(act_seed),
    sampling uniform from default_rng([*act_seed, 1])), keeping every view and executed move and every rise of an achievement counter.
    policy(prompts, us) -> words. -> one dict per game: seed, views, actions, events [(step, type)], first {type: step}, length, end."""
    assert not any(play.is_sealed(s) for s in seeds), 'a sealed world in game/imitate.py'
    envs = [TextEnv(seed=int(s), length=int(cap)) for s in seeds]
    rngs = [np.random.default_rng(a) for a in act_seeds]
    srngs = [np.random.default_rng([*a, 1]) for a in act_seeds]
    texts = [e.reset() for e in envs]
    games = [dict(seed=int(s), views=[], actions=[], events=[], first={}, length=0, end=None) for s in seeds]
    last = [dict() for _ in envs]
    live = list(range(len(envs)))
    while live:
        answers = policy([texts[i] for i in live], [srngs[i].random() for i in live])
        nxt = []
        for i, ans in zip(live, answers):
            u, r = rngs[i].random(), int(rngs[i].integers(play.N_ACTIONS))
            a = parse_action(ans)
            act = r if (a is None or u < explore) else a
            g = games[i]
            g['views'].append(texts[i])
            g['actions'].append(act)
            texts[i], _, done, info = envs[i].step(act)
            t = g['length']
            g['length'] = t + 1
            for name, count in sorted(info['achievements'].items()):
                if count > last[i].get(name, 0):
                    g['events'].append((t, name))
                    g['first'].setdefault(name, t)
            last[i] = dict(info['achievements'])
            if done:
                g['end'] = 'dead' if info['inventory']['health'] <= 0 else 'cap'
            else:
                nxt.append(i)
        live = nxt
    return games


def label_chunks(games, k, out, chunks, per_chunk, cap, workers):
    """One-step lookahead rows (game.lookahead) of an iteration's games, chunk by chunk (each chunk saved when labelled, so a restart loses at most one).
    -> (rows, stats)."""
    rows, parts = [], []
    for c in range(chunks):
        path = os.path.join(out, f'labels-{k}-{c}.json.gz')
        if os.path.exists(path):
            with gzip.open(path, 'rt') as f:
                part = json.load(f)
        else:
            rs, st = lookahead.label_games(games[c * per_chunk:(c + 1) * per_chunk], cap, workers)
            part = dict(rows=rs, stats=st)
            tmp = path + '.tmp'
            with gzip.open(tmp, 'wt') as f:
                json.dump(part, f)
            os.replace(tmp, path)
        rows += part['rows']
        parts.append(part['stats'])
    stats = dict(states=sum(p['states'] for p in parts), labelled=sum(p['labelled'] for p in parts), ties=sum(p['ties'] for p in parts),
                 by_word=dict(sum((Counter(p['by_word']) for p in parts), Counter()).most_common()),
                 by_type=dict(sum((Counter(p['by_type']) for p in parts), Counter()).most_common()))
    return rows, stats


def _games_path(out, k, c):
    return os.path.join(out, f'play-{k}-{c}.json.gz')


def play_iteration(m, k, run_seed, temp, out, chunks, per_chunk, cap, explore, bs=64, day_offset=0):
    """The iteration's games, chunk by chunk (each chunk saved when played, so a restart loses at most one chunk). -> list of games."""
    games = []
    pol = play.move_policy(m, 'sample', bs=bs, temp=temp)
    for c in range(chunks):
        path = _games_path(out, k, c)
        if os.path.exists(path):
            with gzip.open(path, 'rt') as f:
                games += json.load(f)
            continue
        day = day_of(k, c, day_offset)
        seeds = [play.practice_seed(run_seed, day, i) for i in range(per_chunk)]
        acts = [[ACT_TAG, run_seed, day, i] for i in range(per_chunk)]
        chunk = play_games(pol, seeds, acts, explore, cap)
        tmp = path + '.tmp'
        with gzip.open(tmp, 'wt') as f:
            json.dump(chunk, f)
        os.replace(tmp, path)
        games += chunk
    return games


# ---------- training ----------

def train_rows(m, addon, opt, gen, rows, epochs=EPOCHS):
    """Weighted cross entropy of the executed word under the softmax of the 17 word log-probs (T = 1). Minibatch MINIBATCH in chunks of CHUNK,
    summed gradients, clip pg.MAX_GRAD_NORM. -> list of minibatch losses."""
    n = len(rows)
    views = [r['view'] for r in rows]
    labels = torch.tensor([r['action'] for r in rows])
    w = torch.tensor(normalise([r['weight'] for r in rows]), dtype=torch.float32)
    params, losses = addon.params(), []
    for _ in range(epochs):
        order = torch.randperm(n, generator=gen)
        for i in range(0, n, MINIBATCH):
            ix = order[i:i + MINIBATCH]
            opt.zero_grad(set_to_none=True)
            mb = 0.0
            for c in range(0, len(ix), CHUNK):
                cx = ix[c:c + CHUNK]
                lg = play.move_logprobs_grad(m, [views[j] for j in cx.tolist()])
                logp = torch.log_softmax(lg.float(), -1)
                loss = (torch.nn.functional.nll_loss(logp, labels[cx], reduction='none') * w[cx]).sum() / len(ix)
                loss.backward()
                mb += float(loss.detach())
            torch.nn.utils.clip_grad_norm_(params, pg.MAX_GRAD_NORM)
            opt.step()
            losses.append(mb)
    return losses


def ready_stats(games):
    """A27 instrument (harness only, never a teacher): a pickaxe-ready state has a table within one cell (3x3), wood >= 1 and no wood pickaxe.
    -> games that reach one, ready states, and the share of moves played in them that were `wpick`."""
    wpick = play.WORDS.index('wpick')
    n_games = n_states = n_wpick = 0
    for g in games:
        hit = False
        for v, a in zip(g['views'], g['actions']):
            pv = oracle.parse_view(v)
            inv = pv.items.get
            if inv('wood', 0) >= 1 and not inv('wood_pickaxe', 0) and any(oracle._cell(pv, x, y) == 't' for x in (-1, 0, 1) for y in (-1, 0, 1)):
                hit = True
                n_states += 1
                n_wpick += a == wpick
        n_games += hit
    return dict(ready_games=n_games, ready_states=n_states, wpick_share=round(n_wpick / n_states, 4) if n_states else None)


# ---------- the loop ----------

def iteration_stats(k, temp, games, segs, kept, thr, rows_new, n_train, n_buffer, losses, rows_all_sample, secs_play, secs_train):
    first = Counter(n for g in games for n in g['first'])
    events = Counter(n for g in games for _, n in g['events'])
    seg_n = Counter(s['type'] for s in segs)
    kept_n = Counter(s['type'] for s in kept)
    rows_by = Counter(r['type'] for r in rows_new)

    def agree(rs):
        pairs = [(r['action'], oracle.label(r['view'])) for r in rs]
        pairs = [(a, lab) for a, lab in pairs if lab[1] in ('nav', 'act')]
        return dict(views=len(pairs), agreement=round(sum(play.WORDS[a] == lab[0] for a, lab in pairs) / len(pairs), 4) if pairs else None)

    return dict(iteration=k, temp=temp, games=len(games), mean_unlocks=round(sum(len(g['first']) for g in games) / len(games), 3),
                mean_length=round(sum(g['length'] for g in games) / len(games), 1), ends=dict(Counter(g['end'] for g in games)),
                games_with=dict(sorted(first.items())), g_wood=first['collect_wood'], g_table=first['place_table'],
                g_pick=first['make_wood_pickaxe'], g_stone=first['collect_stone'],
                events=dict(sorted(events.items())), segments=dict(sorted(seg_n.items())), kept_segments=dict(sorted(kept_n.items())),
                kept_rows=dict(sorted(rows_by.items())), longest_kept=thr, new_rows=len(rows_new), train_rows=n_train, buffer_before=n_buffer,
                loss_first=round(losses[0], 4) if losses else None, loss_last=round(losses[-1], 4) if losses else None, updates=len(losses),
                oracle_agreement_kept=agree(rows_new), oracle_agreement_all_played=agree(rows_all_sample),
                ready=ready_stats(games), seconds_play=round(secs_play, 1), seconds_train=round(secs_train, 1))


def run(parent, seed, run_seed, t0, out, iterations=24, smoke=False, bs=64, rare_below=0, label_rule='segments', epochs=EPOCHS, workers=2,
        day_offset=0):
    from custom_io.models import load_model
    from domain import mode as dm
    assert run_seed in (394, 395, 396, 397, 398, 399) or smoke, run_seed       # 398 / 399: GW-LS only (WALL-SOLVE-RESULT section 3)
    assert run_seed not in (398, 399) or smoke or day_offset >= 4, 'run seeds 398 / 399: days 0-3 were the Z8 games'
    assert label_rule in ('segments', 'lookahead'), label_rule
    chunks, per_chunk, cap = (1, 3, 40) if smoke else (CHUNKS, GAMES_PER_CHUNK, play.load_constants()[0]['episode_cap'])
    explore = play.load_constants()[0]['explore']
    os.makedirs(out, exist_ok=True)
    with open(dm.CONST_PATH) as f:
        cons = json.load(f)
    ck = torch.load(parent, map_location='cpu', weights_only=True)
    torch.manual_seed(seed)
    m = load_model(parent).eval()
    addon = dm.AddOn(m, cons['addon_rank'], cons['addon_alpha'], seed=seed)
    addon.on = True
    opt = torch.optim.Adam(addon.params(), lr=LR)
    gen = torch.Generator().manual_seed(seed)
    rng = random.Random(seed)
    buffer, done_k, history = [], 0, []
    spath = os.path.join(out, 'state.pt')
    if os.path.exists(spath):
        st = torch.load(spath, map_location='cpu', weights_only=False)
        assert (st['parent'], st['seed'], st['run_seed'], st['t0'], st.get('day_offset', 0)) == (parent, seed, run_seed, t0, day_offset), 'state.pt is from another run'
        addon.restore(st['addon'])
        opt.load_state_dict(st['opt'])
        gen.set_state(st['gen'])
        rng.setstate(st['rng'])
        buffer, done_k, history = st['buffer'], st['k'], st['history']
    for k in range(done_k + 1, iterations + 1):
        temp = t0 if k == 1 else 1.0
        t1 = time.time()
        games = play_iteration(m, k, run_seed, temp, out, chunks, per_chunk, cap, explore, bs, day_offset)
        t2 = time.time()
        la_stats = None
        if label_rule == 'lookahead':
            rows_new, la_stats = label_chunks(games, k, out, chunks, per_chunk, cap, workers)
            weights = type_weights(Counter(r['type'] for r in rows_new))
            for r in rows_new:
                r['weight'] = weights[r['type']]
            segs, kept, thr = [], [], {}
        else:
            segs = [s for gi, g in enumerate(games) for s in segments(g['events'], gi)]
            kept, thr = keep_segments(segs, rare_below)
            weights = type_weights(Counter(s['type'] for s in segs))
            rows_new = rows_of(kept, games, weights)
        buffer = prune_buffer(buffer, thr)
        train_set = training_set(rows_new, buffer, rng)
        losses = train_rows(m, addon, opt, gen, train_set, epochs) if train_set else []
        n_buffer = len(buffer)
        buffer = (buffer + rows_new)[-BUFFER_CAP:]
        t3 = time.time()
        sample = [dict(view=v, action=a) for g in games[:50] for v, a in zip(g['views'], g['actions'])][:20000]
        stats = iteration_stats(k, temp, games, segs, kept, thr, rows_new, len(train_set), n_buffer, losses, sample, t2 - t1, t3 - t2)
        if la_stats is not None:
            stats['lookahead'] = la_stats
        history.append(stats)
        with open(os.path.join(out, f'iter-{k}.json'), 'w') as f:
            json.dump(stats, f, indent=1)
        print(k, {x: stats[x] for x in ('mean_unlocks', 'g_wood', 'g_table', 'g_pick', 'g_stone', 'new_rows', 'train_rows', 'ready', 'seconds_play', 'seconds_train')}, flush=True)
        if k in SNAPSHOTS or k == iterations:
            m.eval()
            dm.save_ckpt(ck, m, os.path.join(out, f'checkpoint-iter{k}.pt'), addon)
        tmp = spath + '.tmp'
        torch.save(dict(parent=parent, seed=seed, run_seed=run_seed, t0=t0, day_offset=day_offset, k=k, addon=addon.snapshot(), opt=opt.state_dict(), gen=gen.get_state(),
                        rng=rng.getstate(), buffer=buffer, history=history), tmp)
        os.replace(tmp, spath)
    return history


def main(argv=None):
    ap = argparse.ArgumentParser(description='GW-F: iterated fastest-segment self-imitation (A26).')
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run')
    r.add_argument('--parent', required=True)
    r.add_argument('--seed', type=int, required=True)
    r.add_argument('--run-seed', type=int, required=True)
    r.add_argument('--t0', type=float, required=True, help='temperature of iteration 1 (the untrained parent), later iterations use 1.0')
    r.add_argument('--out', required=True)
    r.add_argument('--iterations', type=int, default=24)
    r.add_argument('--threads', type=int, default=2)
    r.add_argument('--smoke', action='store_true')
    r.add_argument('--label-rule', choices=('segments', 'lookahead'), default='segments', help='A29: lookahead = one-step first-unlock labels (an instrument)')
    r.add_argument('--epochs', type=int, default=EPOCHS)
    r.add_argument('--workers', type=int, default=2, help='processes for the lookahead replay-and-fork')
    r.add_argument('--keep-rare-below', type=int, default=0, help='A27: types with fewer segments than this keep every segment of at most 12 moves (0 = the A26 rule)')
    r.add_argument('--day-offset', type=int, default=0, help='GW-LS: chunk c of iteration k plays practice day 4(k-1)+c+offset (0 = every earlier run)')
    a = ap.parse_args(argv)
    torch.set_num_threads(a.threads)
    run(a.parent, a.seed, a.run_seed, a.t0, a.out, a.iterations, a.smoke, rare_below=a.keep_rare_below, label_rule=a.label_rule, epochs=a.epochs, workers=a.workers,
        day_offset=a.day_offset)


if __name__ == '__main__':
    main()
