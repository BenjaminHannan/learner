"""Agent 3 independent generator checks.  Compares the frozen calibration files
against audit/independent_oracle.py.  Reads calibration files only (structural /
leak checks); fits, scores or evaluates no learner on them."""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import independent_oracle as O   # noqa: E402

# `python check_generator.py calibration-v1.1` audits the regenerated build.
DATA = Path(__file__).resolve().parents[1] / (sys.argv[1] if len(sys.argv) > 1
                                              else 'calibration')
O.B1_PANEL_EXCLUSION = DATA.name.endswith('v1.1')
print(f'# data={DATA.name}  B1_PANEL_EXCLUSION={O.B1_PANEL_EXCLUSION}')
RESULTS = []


def check(name, ok, detail=''):
    RESULTS.append({'check': name, 'pass': bool(ok), 'detail': str(detail)[:400]})
    print(('PASS  ' if ok else 'FAIL  ') + name + ('' if ok else '  -- ' + str(detail)[:300]))


def jload(p):
    return json.loads(Path(p).read_text())


cfg = jload(DATA / 'private' / 'world_config.json')
index = jload(DATA / 'public' / 'worlds.json')

# ---------------------------------------------------------------- 1. world tuples
mine = {w.wpid: w for w in O.pilot_worlds()}
bad = []
for wpid, row in cfg.items():
    w = mine.get(wpid)
    if w is None:
        bad.append((wpid, 'no independent world reproduces this alias'))
        continue
    if w.family != row['family'] or w.split != row['outer_split'] or w.index != row['world_index']:
        bad.append((wpid, 'identity mismatch'))
    for k, v in row['coefficients'].items():
        if abs(w.coef[k] - v) > 0:
            bad.append((wpid, f'coefficient {k}'))
    if w.wid != row['world_id'] or w.wid_np != row['world_id_without_permutation']:
        bad.append((wpid, 'world_id'))
    if {O.VERBS[i]: p for i, p in enumerate(w.perm)} != row['verb_to_public']:
        bad.append((wpid, 'verb map'))
check('world tuples reproduce from the registered namespace (independent derivation)',
      not bad and len(cfg) == 12, bad[:4])

# ---------------------------------------------------------------- 2. collisions
everything = O.all_worlds()
full = [w.wid for w in everything]
nop = [w.wid_np for w in everything]
alias = [w.wpid for w in everything]
N_REGISTERED_WORLDS = sum(sum(v.values()) for v in O.POOLS.values())   # 6 + 6 + 24 = 36
check('cross-split tuple / permutation-free / alias disjointness over train+validation+final',
      len(set(full)) == len(full) == N_REGISTERED_WORLDS
      and len(set(nop)) == len(nop) and len(set(alias)) == len(alias),
      f'{len(full)} registered worlds (expected {N_REGISTERED_WORLDS}), {len(set(full))} distinct '
      f'tuples, {len(set(nop))} permutation-free, {len(set(alias))} aliases')

# ---------------------------------------------------------------- 3. per-world support
fail = {k: [] for k in ('support_records', 'latent', 'noise_free', 'noise', 'observed',
                        'masks', 'reserved_grammar', 'nesting', 'roles',
                        'conservation_contact', 'no_hidden_storage', 'reset_scope',
                        'determinism_of_response')}
mask_pairs = []
panel1_reserved = 0
ordinary_total = 0
ordinary_contaminated = []
for wpid, row in sorted(cfg.items()):
    w = mine[wpid]
    pub = {p.stem: np.load(p) for p in sorted((DATA / 'public' / wpid).glob('*.npy'))}
    pri = {p.stem: np.load(p) for p in sorted((DATA / 'private' / wpid).glob('*.npy'))}
    eps = [O.discovery_episode(w, i) for i in range(64)]

    # 3a. latent / responses / noise / observed reproduce exactly
    lat = np.stack([e['latent'] for e in eps])
    if not np.array_equal(lat, pri['support_latent']):
        fail['latent'].append(wpid)
    if np.abs(np.stack([e['nf'] for e in eps]) - pri['support_truth_noise_free']).max() != 0:
        fail['noise_free'].append(wpid)
    if np.abs(np.stack([e['noise'] for e in eps]) - pri['support_truth_noise']).max() != 0:
        fail['noise'].append(wpid)
    obs32 = np.stack([e['observed'] for e in eps]).astype('<f4')
    if not np.array_equal(obs32, pub['support_observed_target']):
        fail['observed'].append(wpid)
    if not np.array_equal(np.stack([e['present'] for e in eps]).astype(np.uint8),
                          pub['support_observed_present']):
        fail['masks'].append(wpid)

    # 3b. rebuild the 17x44 public records from my own tokenizer
    rec = np.zeros((64, 17, 44), dtype=np.float64)
    for n, e in enumerate(eps):
        flat = e['p'].reshape(-1)
        rec[n, :, 0:24] = flat
        rec[n, 0, 33 + 4] = 1.0          # RESET destination = NONE
        rec[n, 0, 41 + 0] = 1.0
        for t, (verb, i, j, dose) in enumerate(e['acts']):
            for rowix, rt, sens, pres in ((1 + 2 * t, 1, 0.0, 0.0),
                                          (2 + 2 * t, 2, float(e['observed'][t]),
                                           1.0 if e['present'][t] else 0.0)):
                rec[n, rowix, 24 + w.perm[verb]] = 1.0
                rec[n, rowix, 29 + i] = 1.0
                rec[n, rowix, 33 + (4 if j is None else j)] = 1.0
                rec[n, rowix, 38] = float(dose)
                rec[n, rowix, 39] = sens
                rec[n, rowix, 40] = pres
                rec[n, rowix, 41 + rt] = 1.0
    if not np.array_equal(rec.astype('<f4'), pub['support_records']):
        fail['support_records'].append(wpid)

    # 3c. reserved-composition grammar
    if any(O.has_reserved([a[0] for a in e['acts']]) for e in eps):
        fail['reserved_grammar'].append(wpid)
    if not np.array_equal(np.asarray([e['attempts'] for e in eps], dtype=np.int32),
                          pri['support_action_attempts']):
        fail['reserved_grammar'].append(wpid + '/attempts')

    # 3d. nesting + 3:1 roles
    rung, role = pub['support_budget_rung'], pub['support_episode_role']
    ok = True
    for r, b in enumerate((32, 64, 128, 256, 512)):
        pre = np.flatnonzero(rung <= r)
        ok &= np.array_equal(pre, np.arange(b // 8))
        ok &= int((role[pre] == 1).sum()) == (b // 8) // 4
        ok &= int((role[pre] == 0).sum()) == 3 * ((b // 8) // 4)
    if not ok:
        fail['nesting'].append(wpid)
    if not np.array_equal(role, np.asarray([1 if i % 4 == 3 else 0 for i in range(64)], dtype=np.int8)):
        fail['roles'].append(wpid)

    # 3e. C conservation / O-N no hidden storage / reset scope
    if w.family == 'c':
        for e in eps:
            for t, (verb, i, j, dose) in enumerate(e['acts']):
                before, after = e['latent'][t], e['latent'][t + 1]
                if verb == O.CONTACT:
                    if abs(after.sum() - before.sum()) > 1e-12:
                        fail['conservation_contact'].append(f'{wpid}/contact-sum')
                    if not np.allclose(np.delete(after, [i, j]), np.delete(before, [i, j]), atol=0):
                        fail['conservation_contact'].append(f'{wpid}/contact-scope')
                elif verb in (O.READ, O.WAIT):
                    if not np.array_equal(after, before):
                        fail['conservation_contact'].append(f'{wpid}/read-wait')
                else:                                   # pulse / invert touch one object
                    if not np.array_equal(np.delete(after, i), np.delete(before, i)):
                        fail['conservation_contact'].append(f'{wpid}/single-object-scope')
    if w.family in ('o', 'n'):
        if not (pri['support_latent'] == 0).all():
            fail['no_hidden_storage'].append(wpid + '/latent')
        # the response must be a pure function of the source object's properties
        seen = {}
        for e in eps:
            for t, (verb, i, j, dose) in enumerate(e['acts']):
                key = (tuple(np.round(e['p'][i], 15)), i)
                if key in seen and abs(seen[key] - e['nf'][t]) > 0:
                    fail['no_hidden_storage'].append(wpid + '/history-dependence')
                seen[key] = e['nf'][t]
    if not (pri['support_latent'][:, 0, :] == 0).all():
        fail['reset_scope'].append(wpid)

    # 3f. masks independent of targets
    for e in eps:
        for t in range(8):
            mask_pairs.append((bool(e['present'][t]), float(e['nf'][t])))

    # 3g. panels reproduce exactly
    tg = O.build_targets(w)
    truth = {r['record_id']: r for r in jload(DATA / 'private' / wpid / 'query_truth.json')}
    ids = jload(DATA / 'public' / wpid / 'query_record_ids.json')
    qnf = np.load(DATA / 'private' / wpid / 'query_truth_noise_free.npy')
    qny = np.load(DATA / 'private' / wpid / 'query_truth_noisy.npy')
    pbad = []
    for slot, t in enumerate(tg):
        ref = truth.get(t['record_id'])
        if ref is None or ids[slot] != t['record_id']:
            pbad.append(t['record_id'])
            continue
        for k in ('panel', 'unit', 'branch', 'horizon', 'prefix_length', 'detector_a'):
            if ref[k] != t[k]:
                pbad.append(f"{t['record_id']}/{k}")
        if abs(ref['noise_free_response'] - t['noise_free']) > 0 or abs(qnf[slot] - t['noise_free']) > 0:
            pbad.append(f"{t['record_id']}/nf")
        if abs(ref['noisy_target'] - t['noisy']) > 0 or abs(qny[slot] - t['noisy']) > 0:
            pbad.append(f"{t['record_id']}/noisy")
    if pbad:
        fail.setdefault('panels', []).append(f'{wpid}:{pbad[:3]}')
    # how many GENUINELY ORDINARY action strings contain the withheld composition.
    # Counted once per distinct drawn string: panel-1 units 0..15 (branch 'single') and
    # panel-4 ORDINARY units 0..7 (branch 'base').  Panel-2 and panel-4 units 8..15 are
    # composition units whose reserved suffix is there by construction, and the panel-4
    # 'edited' branch is an object relabelling of 'base' with an identical verb string.
    for t in tg:
        ordinary = ((t['panel'] == 1 and t['branch'] == 'single')
                    or (t['panel'] == 4 and t['unit'] < 8 and t['branch'] == 'base'))
        if ordinary and O.has_reserved([a[0] for a in t['episode']['acts']]):
            panel1_reserved += 1
            ordinary_contaminated.append(f"{wpid}/p{t['panel']}/u{t['unit']}")
    ordinary_total += 24

for name, bad_list in fail.items():
    check(f'support: {name}', not bad_list, bad_list[:3])
check('panels: all 96 targets, IDs, hash order, horizons and truths reproduce exactly',
      not fail.get('panels'), fail.get('panels', [])[:3])

pres = np.asarray([p for p, _ in mask_pairs])
vals = np.asarray([v for _, v in mask_pairs])
rate = pres.mean()
if vals.std() > 0:
    corr = float(np.corrcoef(pres.astype(float), vals)[0, 1])
else:
    corr = 0.0
check('masks independent of targets (rate ~0.75, |corr(present, noise-free)| < 0.02)',
      abs(rate - 0.75) < 0.02 and abs(corr) < 0.02, f'rate={rate:.4f} corr={corr:+.5f} n={len(vals)}')

# ---------------------------------------------------------------- 4. M truth tables
class _MW:
    family = 'm'
    coef = {'a': .4, 'beta': .3, 'g': 1.0, 'b': .2, 'c': .4}


mw = _MW()
tt_ok, tt = True, []
for bits in itertools.product((0, 1), repeat=4):
    q = np.asarray(bits, dtype=np.int64)
    for i in range(4):
        tt_ok &= O.step(mw, q, O.PULSE, i, None, +1)[i] == 1 - q[i]
        tt_ok &= O.step(mw, q, O.PULSE, i, None, -1)[i] == 0
        tt_ok &= O.step(mw, q, O.INVERT, i, None, 0)[i] == 1 - q[i]
        tt_ok &= np.array_equal(O.step(mw, q, O.READ, i, None, 0), q)
        tt_ok &= np.array_equal(O.step(mw, q, O.WAIT, i, None, 0), q)
        for j in range(4):
            if i == j:
                continue
            nxt = O.step(mw, q, O.CONTACT, i, j, 0)
            tt_ok &= nxt[j] == (q[j] ^ q[i]) and nxt[i] == q[i]
            tt_ok &= np.array_equal(np.delete(nxt, [i, j]), np.delete(q, [i, j]))
check('M truth tables: pulse+1 flip / pulse-1 clear / contact XOR into destination only / '
      'invert flip / read+wait inert, over all 16 states x all (i,j)', tt_ok,
      'equations only; no M trace, curve or score is emitted')
# M has no additive conservation law under contact (structural contrast with C)
noncons = any(O.step(mw, np.asarray(b), O.CONTACT, 0, 1, 0).sum() != sum(b)
              for b in itertools.product((0, 1), repeat=4))
check('M contact is directional and does not conserve a sum (structural contrast with C)', noncons)

# ---------------------------------------------------------------- 5. disjointness
sig_support, sig_query = set(), set()
for wpid in cfg:
    s = np.load(DATA / 'public' / wpid / 'support_records.npy')
    q = np.load(DATA / 'public' / wpid / 'query_records.npy')
    sig_support |= {s[e, 0, 0:24].tobytes() for e in range(s.shape[0])}
    sig_query |= {q[r, 0, 0:24].tobytes() for r in range(q.shape[0])}
check('support episodes disjoint from every query episode (property signatures)',
      not (sig_support & sig_query), f'{len(sig_support)} support / {len(sig_query)} query signatures')

# ct20-v1.1 ruling B1 requires this count to be 0 in the regenerated panels.
check('ct20-v1.1 B1: no genuinely-ordinary query action string contains the reserved '
      'composition (v1 data is EXPECTED to fail; recheck after regeneration)',
      panel1_reserved == 0,
      f'{panel1_reserved}/{ordinary_total} ordinary units contaminated in the v1 build '
      f'{ordinary_contaminated[:5]}; analytic expectation under free drawing '
      f'~= {ordinary_total * 5 * (1/5)**4:.2f}')

print()
print(json.dumps({'passed': sum(r['pass'] for r in RESULTS),
                  'failed': sum(not r['pass'] for r in RESULTS),
                  'ordinary_units_containing_withheld_composition': panel1_reserved,
                  'ordinary_units_total': ordinary_total}))
Path(__file__).with_name(f'generator_check_results-{DATA.name}.json').write_text(
    json.dumps({'results': RESULTS,
                'reserved_composition_in_ordinary_units': panel1_reserved,
                'ordinary_units_total': ordinary_total,
                'ordinary_units_contaminated': ordinary_contaminated}, indent=1))
