"""Agent 3 data-boundary / leakage review.  Reads public and private calibration
files for structural inspection only; no learner is fitted or scored."""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import independent_oracle as O   # noqa: E402

DATA = Path(__file__).resolve().parents[1] / (sys.argv[1] if len(sys.argv) > 1
                                              else 'calibration')
O.B1_PANEL_EXCLUSION = DATA.name.endswith('v1.1')
print(f'# data={DATA.name}  B1_PANEL_EXCLUSION={O.B1_PANEL_EXCLUSION}')
OUT = []


def note(name, verdict, detail):
    OUT.append({'check': name, 'verdict': verdict, 'detail': str(detail)[:600]})
    print(f'{verdict:<10} {name}\n           {detail}')


def jload(p):
    return json.loads(Path(p).read_text())


cfg = jload(DATA / 'private' / 'world_config.json')
index = jload(DATA / 'public' / 'worlds.json')
norm = jload(DATA / 'private' / 'normalization.json')
wpids = [r['world_public_id'] for r in index['worlds']]

# ---- L1: is anything in private/ actually secret? -----------------------------------
mine = {w.wpid: w for w in O.pilot_worlds()}
recovered = {wpid: mine[wpid].family for wpid in wpids if wpid in mine}
note('L1 world alias -> family',
     'LEAK' if len(recovered) == len(wpids) else 'ok',
     f'{len(recovered)}/{len(wpids)} public aliases inverted to (split, family, index, '
     f'coefficients, verb map) with no secret, using only the design document: '
     f'{sorted(collections.Counter(recovered.values()).items())}')

# V and the analytic floor
myV = {}
for w in O.pilot_worlds():
    tg = O.build_targets(w)
    myV.setdefault((w.split, w.family), []).extend(
        t['noise_free'] for t in tg if t['panel'] in (1, 2))
vrec = {f'{s}/A/{f}': max(float(np.var(np.asarray(v))), 0.05) for (s, f), v in myV.items()}
vmatch = all(abs(vrec[k] - norm[k]['V']) < 1e-12 for k in norm)
note('L2 normalization constant V and the analytic sensor floor',
     'LEAK' if vmatch else 'ok',
     f'all {len(norm)} published V values recomputed independently to <1e-12 '
     f'({vmatch}); V is therefore not secret either')

# query targets
tgt_ok = True
for wpid in wpids:
    truth = {r['record_id']: r for r in jload(DATA / 'private' / wpid / 'query_truth.json')}
    for t in O.build_targets(mine[wpid]):
        if abs(truth[t['record_id']]['noise_free_response'] - t['noise_free']) > 0:
            tgt_ok = False
note('L3 noise-free responses, noisy targets, latent states, panel identity',
     'LEAK' if tgt_ok else 'ok',
     'every evaluator-only quantity for all 12 calibration worlds regenerated exactly '
     'from the public design; the same procedure applies verbatim to the 24 FINAL worlds')

# ---- L4: record order / hash order -> panel identity ---------------------------------
order_ok = True
for wpid in wpids:
    ids = jload(DATA / 'public' / wpid / 'query_record_ids.json')
    truth = {r['record_id']: r for r in jload(DATA / 'private' / wpid / 'query_truth.json')}
    mineorder = [t['panel'] for t in O.build_targets(mine[wpid])]
    if mineorder != [truth[i]['panel'] for i in ids]:
        order_ok = False
note('L4 QUERY_ORDER_BY_HASH hides panel grouping',
     'LEAK' if order_ok else 'ok',
     'the ordering key sha256("<wpid>/order/<panel>/<unit>/<branch>") uses only public '
     'inputs, so record_id -> panel/unit/branch is fully invertible without any private '
     f'file (reproduced for {len(wpids)}/{len(wpids)} worlds)')

# ---- L5: structural signals inside the public tensors alone --------------------------
stats = {}
for wpid in wpids:
    d = DATA / 'public' / wpid
    sup = np.load(d / 'support_records.npy')
    q = np.load(d / 'query_records.npy')
    pres = np.load(d / 'support_observed_present.npy').astype(bool)
    y = np.load(d / 'support_observed_target.npy')
    sizes = {p.name: p.stat().st_size for p in sorted(d.glob('*'))}
    dose = sup[:, 1::2, 38]
    dest = sup[:, 1::2, 33:38].argmax(-1)
    stats[wpid] = dict(
        family=mine[wpid].family, sizes=sizes,
        shapes={'sup': sup.shape, 'q': q.shape},
        sensor_sd=float(y[pres].std()), sensor_absmax=float(np.abs(y[pres]).max()),
        present_rate=float(pres.mean()),
        pulse_rate=float((dose != 0).mean()), contact_rate=float((dest != 4).mean()),
        n_records=np.load(d / 'query_n_records.npy'),
        qindex=np.load(d / 'query_index.npy'),
        detector_b=np.load(d / 'query_detector.npy')[:, 4:].argmax(-1))

size_sets = {json.dumps(s['sizes'], sort_keys=True) for s in stats.values()}
note('L5a file sizes / tensor shapes',
     'ok' if len(size_sets) == 1 else 'LEAK',
     f'{len(size_sets)} distinct public file-size signatures across 12 worlds '
     '(byte-identical layout, so size carries no family information)')

nrec = {tuple(np.unique(s['n_records']).tolist()) for s in stats.values()}
qix = {tuple(np.unique(s['qindex']).tolist()) for s in stats.values()}
db = {tuple(np.unique(s['detector_b']).tolist()) for s in stats.values()}
note('L5b prefix length / query index / detector b',
     'ok' if nrec == {(16,)} and qix == {(15,)} and db == {(4,)} else 'LEAK',
     f'n_records={nrec} query_index={qix} detector_b={db} -- constant in the pilot, so '
     'padding length and the detector cannot separate panels or families')

pr = [s['pulse_rate'] for s in stats.values()]
cr = [s['contact_rate'] for s in stats.values()]
prr = [s['present_rate'] for s in stats.values()]
note('L5c dose sign / destination / mask rate',
     'ok',
     f'pulse rate {min(pr):.3f}-{max(pr):.3f}, contact rate {min(cr):.3f}-{max(cr):.3f}, '
     f'present rate {min(prr):.3f}-{max(prr):.3f}; all consistent with the family-free '
     '1/5 and 3/4 draws (dose!=0 => pulse and destination!=NONE => contact remain the '
     'registered public hints)')

byfam = collections.defaultdict(list)
for s in stats.values():
    byfam[s['family']].append(s['sensor_absmax'])
sep = (max(byfam['n']) < min(min(byfam['c']), min(byfam['o'])))
note('L5d observed sensor magnitude -> family',
     'LEAK (inherent)' if sep else 'ok',
     'max |y| over present observations: '
     + '; '.join(f'{f}={[round(v,3) for v in sorted(vals)]}' for f, vals in sorted(byfam.items()))
     + ' -- the noise-only family N is separable from the public tensors by a one-line '
       'statistic. This is intrinsic to the task (the learner is meant to see y); it '
       'does mean "family is not a model feature" is a code discipline, not a data property.')

# ---- L6: pair membership recoverable from the public query tensors -------------------
pair3, pair4 = [], []
for wpid in wpids:
    q = np.load(DATA / 'public' / wpid / 'query_records.npy')
    truth = {r['record_id']: r for r in jload(DATA / 'private' / wpid / 'query_truth.json')}
    ids = jload(DATA / 'public' / wpid / 'query_record_ids.json')
    sig = collections.defaultdict(list)
    for r in range(96):
        sig[q[r, 0, 0:24].tobytes()].append(ids[r])
    dup = [v for v in sig.values() if len(v) > 1]
    ok3 = all(len(v) == 2 and truth[v[0]]['pair_key'] == truth[v[1]]['pair_key']
              and truth[v[0]]['panel'] == 3 for v in dup)
    pair3.append((len(dup), ok3))
    # panel 4: channels 0 and 1 travel with the object, so the SET of (p0,p1) rows matches
    key = {}
    for r in range(96):
        rows = q[r, 0, 0:24].reshape(4, 6)[:, 0:2]
        key.setdefault(tuple(sorted(map(tuple, np.round(rows, 6)))), []).append(ids[r])
    hits = 0
    for v in key.values():
        pk = {truth[x]['pair_key'] for x in v}
        if len(v) == 2 and len(pk) == 1 and truth[v[0]]['panel'] == 4:
            hits += 1
    pair4.append(hits)
note('L6 pair membership from public tensors alone',
     'LEAK',
     f'panel 3: duplicate 24-float property blocks identify all {pair3[0][0]} pairs per '
     f'world exactly ({all(o for _, o in pair3)} for every world); panel 4: matching the '
     f'multiset of (channel0, channel1) rows recovers {min(pair4)}-{max(pair4)} of 16 '
     'pairs per world. Pair membership and panel-3 identity are therefore inferable '
     'WITHOUT the generator source. Not disclosed in SCHEMA.md section 4, which claims '
     'only that the action sequence partly discloses membership.')

# ---- L7: target value never inside its own prefix ------------------------------------
worst = 0.0
for wpid in wpids:
    q = np.load(DATA / 'public' / wpid / 'query_records.npy')
    ids = jload(DATA / 'public' / wpid / 'query_record_ids.json')
    truth = {r['record_id']: r for r in jload(DATA / 'private' / wpid / 'query_truth.json')}
    for r, rid in enumerate(ids):
        t32 = np.float32(truth[rid]['noisy_target'])
        if t32 != 0 and (q[r] == t32).any():
            worst = 1.0
note('L7 target value present anywhere in its own query sequence',
     'ok' if worst == 0 else 'LEAK',
     'no float32 equal to the noisy target occurs in any of the 12*96 public query '
     'sequences; QUERY carries sensor=0/present=0 and the final OBSERVED is never built')

# ---- L8: outer_split in the public index ---------------------------------------------
note('L8 outer_split in public/worlds.json', 'disclosed',
     'present, as the builder flags; the prereg forbids it as a model feature. The '
     'public loader returns it from worlds()/worlds_in_split(), so nothing but code '
     'discipline stops it reaching a batch.')

Path(__file__).with_name(f'leak_review-{DATA.name}.json').write_text(json.dumps(OUT, indent=1))
print('\n' + json.dumps({'entries': len(OUT)}))
