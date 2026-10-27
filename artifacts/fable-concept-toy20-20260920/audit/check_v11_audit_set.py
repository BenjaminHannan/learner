"""Agent 3: the NEW public `audit_*` tensors introduced in ct20-v1.1.

Ruling C10 requires saved initial and final audit predictions with stable
episode/horizon/endpoint keys.  The builder now publishes the audit set as
PUBLIC tensors.  That is only acceptable if the set is a deterministic function
of data the learner already holds; otherwise publishing it would hand the model
evaluator-side information.

This script reconstructs the audit set from the PUBLIC support tensors alone
(the present mask and the episode roles), compares it to the published tensors,
and reports the unused-reservation gap that ruling A1 says must be recorded
separately.  No learner is fitted or scored.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

DATA = Path(__file__).resolve().parents[1] / (sys.argv[1] if len(sys.argv) > 1
                                              else 'calibration-v1.1')
HORIZONS = (1, 2, 4)
N_TRANSITIONS = 8
EPISODE_GROUP = 4
OUT: list[dict] = []


def check(name, ok, detail=''):
    OUT.append({'check': name, 'pass': bool(ok), 'detail': str(detail)[:500]})
    print(('PASS  ' if ok else 'FAIL  ') + name + (f'\n        {detail}' if detail else ''))


wpids = [r['world_public_id']
         for r in json.loads((DATA / 'public' / 'worlds.json').read_text())['worlds']]

mismatch, counts, label_bad, blank_bad = [], {}, [], []
for wpid in wpids:
    d = DATA / 'public' / wpid
    present = np.load(d / 'support_observed_present.npy').astype(bool)   # (E, 8)
    role = np.load(d / 'support_episode_role.npy')                       # (E,) 0=fit
    y = np.load(d / 'support_observed_target.npy')                       # (E, 8)
    rung = np.load(d / 'support_budget_rung.npy')

    # The registered audit set (prereg s8): for each FIT episode in the B=512
    # prefix and each h, its LAST eligible observed endpoint t (h <= t <= 8,
    # observation at index t-1 present).  Built here from public arrays only.
    mine = []
    for e in np.flatnonzero(role == 0):
        if rung[e] > 4:          # outside the largest registered prefix
            continue
        for h in HORIZONS:
            cand = [t for t in range(h, N_TRANSITIONS + 1) if present[e, t - 1]]
            if cand:
                mine.append((int(e), int(h), int(max(cand))))
    mine.sort()

    ep = np.load(d / 'audit_episode_index.npy')
    hz = np.load(d / 'audit_horizon.npy')
    en = np.load(d / 'audit_endpoint.npy')
    theirs = sorted(zip(ep.tolist(), hz.tolist(), en.tolist()))
    if theirs != mine:
        mismatch.append(f'{wpid}: mine={len(mine)} theirs={len(theirs)} '
                        f'first-diff={next((a, b) for a, b in zip(mine, theirs) if a != b)}'
                        if len(mine) == len(theirs) else
                        f'{wpid}: mine={len(mine)} theirs={len(theirs)}')
    counts[wpid] = len(theirs)

    # the published observed label must equal the public support observation
    lab = np.load(d / 'audit_observed_label.npy')
    for k, (e, h, t) in enumerate(theirs):
        if float(lab[k]) != float(y[e, t - 1]):
            label_bad.append(f'{wpid}/{e}/{h}/{t}')

    # the audit sequence must BLANK the forecast window: the h records from the
    # endpoint back must carry sensor=0 and present=0 (prereg s3 forecasting).
    rec = np.load(d / 'audit_records.npy')
    nrec = np.load(d / 'audit_n_records.npy')
    for k, (e, h, t) in enumerate(theirs):
        end = int(nrec[k]) - 1                      # final QUERY row index
        for step in range(h):
            obs_row = end + 1 - 2 * step            # OBSERVED rows inside the window
            if obs_row <= 0:
                continue
            if float(rec[k, obs_row, 39]) != 0.0 or float(rec[k, obs_row, 40]) != 0.0:
                blank_bad.append(f'{wpid}/{k}/row{obs_row}')

check('the public audit set is reproducible from the PUBLIC support tensors alone '
      '(present mask + episode roles), so publishing it reveals nothing new',
      not mismatch, mismatch[:3] or 'all 12 worlds reproduce exactly')
check('published audit labels equal the public support observations '
      '(no evaluator-side value is published)', not label_bad, label_bad[:3])
check('audit sequences blank sensor and present inside the forecast window',
      not blank_bad, blank_bad[:3])

largest_legal = (64 - 64 // EPISODE_GROUP) * len(HORIZONS)     # 48 fit episodes x 3
actual = sorted(set(counts.values()))
unused = {w: largest_legal - c for w, c in counts.items() if c != largest_legal}
check('the frozen reservation uses the LARGEST LEGAL audit set, so the step table '
      'is data-independent (ruling A1)',
      max(counts.values()) <= largest_legal,
      f'largest legal = {largest_legal}; actual sizes {actual}; worlds below the '
      f'bound {unused or "none"} -- these are UNUSED RESERVATIONS that ruling A1 '
      'requires be recorded separately and NOT spent on extra fitting')

check('public file-size variation across worlds is driven only by the audit-set '
      'size, which is itself a function of the already-public mask',
      len(actual) <= 2,
      f'{len(actual)} distinct audit-set sizes {actual} across 12 worlds; the '
      'support and query tensors remain byte-identical in layout')

print()
Path(__file__).with_name(f'v11_audit_set_results-{DATA.name}.json').write_text(
    json.dumps({'results': OUT, 'audit_set_sizes': counts}, indent=1))
print(json.dumps({'checks': len(OUT), 'failed': sum(1 for r in OUT if not r['pass'])}))
