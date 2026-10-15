"""GW-O (addendum A29): one-step lookahead labels on the model's own visited states. An instrument, not a method: it copies the world.

For every step of a saved game the world is replayed from its seed with the executed moves; before each executed move the world is copied once per move
word and the word is applied to its copy. A word is a label for that step if it makes an achievement count rise that was zero before in the game (the
game's own first-unlock +1). One label word is picked at random among several; no label word, no row. Nothing about the view text is used.
"""
import copy
import multiprocessing as mp
from collections import Counter

import crafter
import numpy as np

from game import play
from game.crafter_text import TextEnv


def label_words(env):
    """{word index: sorted achievement names that rise from zero if that word is applied now}. env is not changed."""
    out = {}
    for a in range(play.N_ACTIONS):
        e = copy.deepcopy(env)
        _, _, _, info = crafter.Env.step(e, a)
        new = sorted(n for n, c in info['achievements'].items() if c > 0 and n not in env._unlocked)
        if new:
            out[a] = new
    return out


def pick_word(seed, step, labs):
    """The label word of a step with several: uniform, seeded by the world seed and the step."""
    keys = sorted(labs)
    return keys[int(np.random.default_rng([int(seed), int(step), 29]).integers(len(keys)))]


def label_game(game, cap):
    """Replay one saved game (dict with seed, views, actions). -> list of rows dict(view, action, type, seg_len, ties, step).
    Asserts that the replay reproduces every saved view."""
    assert not play.is_sealed(game['seed']), 'a sealed world in game/lookahead.py'
    env = TextEnv(seed=int(game['seed']), length=int(cap))
    view = env.reset()
    rows = []
    for j, act in enumerate(game['actions']):
        assert view == game['views'][j], (game['seed'], j)
        labs = label_words(env)
        if labs:
            w = pick_word(game['seed'], j, labs)
            rows.append(dict(view=view, action=w, type=labs[w][0], seg_len=0, ties=len(labs), step=j))
        view, _, _, _ = env.step(act)
    return rows


def _job(args):
    return label_game(*args)


def label_games(games, cap, workers=2):
    """-> (rows of all games in game order, stats). A pool of `workers` processes (1 = in this process)."""
    jobs = [(g, cap) for g in games]
    if workers > 1:
        with mp.get_context('fork').Pool(workers) as pool:
            per_game = pool.map(_job, jobs, chunksize=4)
    else:
        per_game = [_job(j) for j in jobs]
    rows = [r for rs in per_game for r in rs]
    steps = sum(len(g['actions']) for g in games)
    stats = dict(states=steps, labelled=len(rows), ties=sum(r['ties'] > 1 for r in rows),
                 by_word=dict(Counter(play.WORDS[r['action']] for r in rows).most_common()),
                 by_type=dict(Counter(r['type'] for r in rows).most_common()))
    return rows, stats
