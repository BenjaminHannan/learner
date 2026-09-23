"""Agent 3 INDEPENDENT oracle for concept-toy20 ct20-v1.

Written from design/v3/20-concept-toy-simulator-spec.md ONLY.  It imports nothing
from scripts/fable_concepttoy20_sim.py, so the simulator is the thing under test and
this file is the oracle -- never the other way round.

Declared conventions copied from the builder's AMBIGUITY_RULINGS (they are choices the
spec does not fix, so an "independent" derivation cannot invent them):
  * internal verb order   pulse, contact, invert, read, wait
  * action draw order     verb, source, then (contact destination | pulse dose)
  * mask draw             rng.random() < 0.75
  * episode public stream properties (4,6) uniform(-1,1) then permutation(4)
  * RESET destination one-hot = NONE
Everything else below is re-derived from the spec text.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = 'premonition/concept-toy20/v1'
VERBS = ('pulse', 'contact', 'invert', 'read', 'wait')
PULSE, CONTACT, INVERT, READ, WAIT = range(5)
RESERVED = (PULSE, CONTACT, INVERT, READ)
NOBJ, NPROP, NT = 4, 6, 8
SIGMA, PRESENT_P, CLIP = 0.03, 0.75, 2.0
COEF_RANGES = (('a', .25, .60), ('beta', .20, .45), ('g', .80, 1.20),
               ('b', .10, .40), ('c', .20, .60))
POOLS = {'train': {'c': 4, 'm': 0, 'o': 1, 'n': 1},
         'validation': {'c': 4, 'm': 0, 'o': 1, 'n': 1},
         'final': {'c': 8, 'm': 8, 'o': 4, 'n': 4}}
FAMILIES = ('c', 'm', 'o', 'n')
PANEL1_H = (1,) * 6 + (2,) * 5 + (4,) * 5
PANEL4_H = (1, 1, 1, 2, 2, 2, 4, 4)

# ct20-v1.1 ruling B1: exclude the reserved composition from every complete
# ordinary action string (panel 1 and panel-4-ordinary) and from the four-action
# PREFIX of composition units, keeping their forced suffix.  Set False to
# reproduce the original ct20-v1 panels.
#
# Note on the boundary: the forced suffix is (pulse, contact, invert, read) and
# it begins with `pulse`, so no occurrence of the reserved string can straddle
# the prefix/suffix join.  Rejecting on the prefix alone is therefore equivalent
# to rejecting on the concatenation MINUS the forced suffix itself -- which is
# what "do not reject a forced composition suffix" requires.  Rejecting on the
# whole concatenation would reject every draw forever.
B1_PANEL_EXCLUSION = True


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def rng_for(ns):
    seed = int.from_bytes(hashlib.sha256(ns.encode('utf-8')).digest()[:8], 'little', signed=False)
    return np.random.Generator(np.random.PCG64(seed))


def cjson(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False, ensure_ascii=True)


class W:
    def __init__(self, split, family, index):
        g = rng_for(f'{ROOT}/world/{split}/{family}/{index}')
        self.split, self.family, self.index = split, family, index
        self.coef = {n: float(g.uniform(lo, hi)) for n, lo, hi in COEF_RANGES}
        self.perm = tuple(int(x) for x in g.permutation(5))   # internal verb -> public id

    def meta(self, with_perm=True):
        m = {'version': 'ct20-v1', 'family': self.family, 'coefficients': self.coef}
        if with_perm:
            m['verb_to_public'] = [int(x) for x in self.perm]
        return m

    @property
    def wid(self):
        return sha(cjson(self.meta(True)))

    @property
    def wid_np(self):
        return sha(cjson(self.meta(False)))

    @property
    def wpid(self):
        return sha(self.wid + '/public-alias')[:16]


# --- the four families, written straight from spec section 2 -------------------------

def step(world, q, verb, i, j, dose):
    q = q.copy()
    f = world.family
    if f == 'c':
        if verb == PULSE:
            q[i] = min(max(q[i] + world.coef['a'] * dose, -CLIP), CLIP)
        elif verb == CONTACT:
            d = world.coef['beta'] * (q[i] - q[j])      # from the OLD state
            q[i] = q[i] - d
            q[j] = q[j] + d
        elif verb == INVERT:
            q[i] = -q[i]
    elif f == 'm':
        if verb == PULSE:
            q[i] = (1 - q[i]) if dose > 0 else 0
        elif verb == CONTACT:
            q[j] = q[j] ^ q[i]
        elif verb == INVERT:
            q[i] = 1 - q[i]
    return q


def resp(world, q, p, i):
    c = world.coef
    if world.family == 'c':
        return float(np.tanh(c['g'] * q[i] + c['b'] * p[i, 0]))
    if world.family == 'm':
        return float(np.tanh(c['g'] * (2.0 * q[i] - 1.0) + c['b'] * p[i, 0]))
    if world.family == 'o':
        return float(np.tanh(c['b'] * p[i, 0] + c['c'] * p[i, 1]))
    return 0.0


# --- streams -------------------------------------------------------------------------

def ens(wid, stream, key, leaf, attempt=None):
    base = f'{ROOT}/episode/{wid}/{stream}/{key}/{leaf}'
    return base if attempt is None else f'{base}/{attempt}'


def draw_props(wid, stream, key):
    g = rng_for(ens(wid, stream, key, 'public'))
    internal = g.uniform(-1.0, 1.0, size=(NOBJ, NPROP))
    perm = g.permutation(NOBJ)
    return internal[perm], g


def draw_one_action(g):
    verb = int(g.integers(0, 5))
    src = int(g.integers(0, NOBJ))
    dst, dose = None, 0
    if verb == CONTACT:
        others = [k for k in range(NOBJ) if k != src]
        dst = int(others[int(g.integers(0, NOBJ - 1))])
    elif verb == PULSE:
        dose = 1 if int(g.integers(0, 2)) == 1 else -1
    return (verb, src, dst, dose)


def has_reserved(verbs):
    return any(tuple(verbs[t:t + 4]) == RESERVED for t in range(len(verbs) - 3))


def draw_actions(wid, stream, key, length=NT, exclude=True):
    for attempt in range(10000):
        g = rng_for(ens(wid, stream, key, 'actions', attempt))
        acts = [draw_one_action(g) for _ in range(length)]
        if not exclude or not has_reserved([a[0] for a in acts]):
            return acts, attempt
    raise RuntimeError('rejection exhausted')


def draw_mask(wid, stream, key):
    return rng_for(ens(wid, stream, key, 'mask')).random(NT) < PRESENT_P


def draw_noise(wid, stream, key):
    return rng_for(ens(wid, stream, key, 'noise')).normal(0.0, SIGMA, size=NT)


def run_episode(world, p, acts):
    q = np.zeros(NOBJ, dtype=np.int64 if world.family == 'm' else np.float64)
    latent = [q.astype(np.float64).copy()]
    nf = np.zeros(NT)
    for t, (verb, i, j, dose) in enumerate(acts):
        q = step(world, q, verb, i, j, dose)
        latent.append(q.astype(np.float64).copy())
        nf[t] = resp(world, q, p, i)
    return np.stack(latent), nf


def discovery_episode(world, index):
    key = str(index)
    p, _ = draw_props(world.wid, 'discovery', key)
    acts, attempts = draw_actions(world.wid, 'discovery', key, exclude=True)
    present = draw_mask(world.wid, 'discovery', key)
    noise = draw_noise(world.wid, 'discovery', key)
    latent, nf = run_episode(world, p, acts)
    observed = np.where(present, nf + noise, 0.0)
    return dict(p=p, acts=acts, present=present, noise=noise, latent=latent,
                nf=nf, observed=observed, attempts=attempts)


# --- panels (spec section 4 + the builder's declared panel rulings) -------------------

def _ordinary(world, panel, unit, horizon):
    key = f'{panel}/{unit}'
    p, _ = draw_props(world.wid, 'source-query', key)
    acts, _ = draw_actions(world.wid, 'source-query', key, exclude=B1_PANEL_EXCLUSION)
    present = draw_mask(world.wid, 'source-query', key)
    noise = draw_noise(world.wid, 'source-query', key)
    latent, nf = run_episode(world, p, acts)
    return dict(p=p, acts=acts, present=present, noise=noise, nf=nf,
                prefix=NT - horizon, horizon=horizon)


def _composition(world, panel, unit, dose):
    key = f'{panel}/{unit}'
    p, g = draw_props(world.wid, 'source-query', key)
    i = int(g.integers(0, NOBJ))
    others = [k for k in range(NOBJ) if k != i]
    j = int(others[int(g.integers(0, NOBJ - 1))])
    prefix, _ = draw_actions(world.wid, 'source-query', key, length=4,
                             exclude=B1_PANEL_EXCLUSION)
    suffix = [(PULSE, i, None, dose), (CONTACT, i, j, 0), (INVERT, j, None, 0),
              (READ, j, None, 0)]
    acts = prefix + suffix
    present = draw_mask(world.wid, 'source-query', key)
    noise = draw_noise(world.wid, 'source-query', key)
    latent, nf = run_episode(world, p, acts)
    return dict(p=p, acts=acts, present=present, noise=noise, nf=nf,
                prefix=4, horizon=4)


def build_targets(world):
    """Return the 96 targets in the builder's declared hash order."""
    rows = []
    for unit, h in enumerate(PANEL1_H):
        e = _ordinary(world, 1, unit, h)
        rows.append((1, unit, 'single', e, e['acts'][NT - 1][1]))
    for unit in range(16):
        e = _composition(world, 2, unit, 1 if unit < 8 else -1)
        rows.append((2, unit, 'single', e, e['acts'][NT - 1][1]))
    for unit in range(16):
        key = f'3/{unit}'
        p, g = draw_props(world.wid, 'source-query', key)
        i = int(g.integers(0, NOBJ))
        present = draw_mask(world.wid, 'source-query', key)
        noise = draw_noise(world.wid, 'source-query', key)
        pre = [(READ, i, None, 0), (WAIT, i, None, 0), (READ, i, None, 0), (WAIT, i, None, 0)]
        for branch, suf in (('treated', [(PULSE, i, None, 1), (READ, i, None, 0),
                                         (WAIT, i, None, 0), (READ, i, None, 0)]),
                            ('control', [(WAIT, i, None, 0), (READ, i, None, 0),
                                         (WAIT, i, None, 0), (READ, i, None, 0)])):
            acts = pre + suf
            _, nf = run_episode(world, p, acts)
            rows.append((3, unit, branch,
                         dict(p=p, acts=acts, present=present, noise=noise, nf=nf,
                              prefix=4, horizon=4), i))
    for unit in range(16):
        if unit < 8:
            e = _ordinary(world, 4, unit, PANEL4_H[unit])
        else:
            e = _composition(world, 4, unit, 1 if unit < 12 else -1)
        g = rng_for(f'{ROOT}/panel/{world.wid}/4/{unit}/edit')
        sigma = g.permutation(NOBJ)
        fresh = g.uniform(-2.0, 2.0, size=(NOBJ, 4))
        ep = np.zeros_like(e['p'])
        for i in range(NOBJ):
            ep[sigma[i], 0:2] = e['p'][i, 0:2]
        ep[:, 2:6] = fresh
        eacts = [(v, int(sigma[s]), None if d is None else int(sigma[d]), dz)
                 for (v, s, d, dz) in e['acts']]
        _, enf = run_episode(world, ep, eacts)
        a = e['acts'][NT - 1][1]
        rows.append((4, unit, 'base', e, a))
        rows.append((4, unit, 'edited',
                     dict(p=ep, acts=eacts, present=e['present'], noise=e['noise'],
                          nf=enf, prefix=e['prefix'], horizon=e['horizon']),
                     int(sigma[a])))
    order = sorted(range(len(rows)),
                   key=lambda ix: sha(f'{world.wpid}/order/{rows[ix][0]}/{rows[ix][1]}/{rows[ix][2]}'))
    out = []
    for slot, ix in enumerate(order):
        panel, unit, branch, e, a = rows[ix]
        ft = e['prefix'] + e['horizon'] - 1
        out.append(dict(record_id=f'{world.wpid}-q{slot:04d}', panel=panel, unit=unit,
                        branch=branch, horizon=e['horizon'], prefix_length=e['prefix'],
                        detector_a=a, noise_free=float(e['nf'][ft]),
                        noisy=float(e['nf'][ft] + e['noise'][ft]), episode=e))
    return out


def pilot_worlds():
    return [W(s, f, i) for s in ('train', 'validation') for f in FAMILIES
            for i in range(POOLS[s][f])]


def all_worlds():
    return [W(s, f, i) for s in POOLS for f in FAMILIES for i in range(POOLS[s][f])]
