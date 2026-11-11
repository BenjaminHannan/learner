#!/usr/bin/env python3
"""Acceptance check of a collected 8aPTC3S rental result (RUNBOOK.md, step 6). Reads files only; no network, no GPU.

  python3 -I accept.py COLLECTED/8aPTC3S-3M-s400 [--pc-pts-result PATH_TO_g2c3s_PTS_RESULT.json] [--expect-params N]

COLLECTED/8aPTC3S-3M-s400 is the folder `vast.py collect` / `collectck` extracted (it holds RESULT.json, PTC/RESULT.json, pool_MANIFEST.json, box/).
Prints one PASS / FAIL / NOTE line per check and ends with ACCEPT or REJECT. Exit code 0 only for ACCEPT.

The checks (fixed in advance, the PC card's done_when and mark M1):
  1  top RESULT.json status == ok                       (the PC card's done_when)
  2  PTC/RESULT.json status == ok and steps == 24000
  3  the job ran arm PTC only, and its cfg has calc_train true
  4  n_params == the PC's PTS count for the same caps   (4,023,976 at 3M, from the PTC README and test_ptc; or --pc-pts-result's n_params)
  5  cap_hits total == 0                                (the calc_* counters are outside it)
  6  calc_mismatch / calc_rows <= 0.001 (0.1%), calc_rows > 0   (mark M1)
  7  final evaluation present, lesions include nocalc  (otherwise the training worked but the rental ended before the scores: a re-run would not be needed, but say so)
"""
import argparse
import json
import os
import sys

ap = argparse.ArgumentParser()
ap.add_argument('folder')
ap.add_argument('--pc-pts-result', help="the PC's 8aG2C3S RESULT.json of arm PTS (its n_params is read); default: 4,023,976")
ap.add_argument('--expect-params', type=int, default=4023976)
a = ap.parse_args()
d = a.folder
bad, notes = [], []


def load(*p):
    try:
        with open(os.path.join(d, *p), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def check(ok, what, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' | ' + str(detail) if detail != '' else ''))
    if not ok:
        bad.append(what)


top, arm = load('RESULT.json'), load('PTC', 'RESULT.json')
box = load('box.json') or {}
check(top is not None, '1 top RESULT.json exists')
check(isinstance(top, dict) and top.get('status') == 'ok', '1 top RESULT.json status ok', top and top.get('status'))
check(arm is not None, '2 PTC/RESULT.json exists')
arm = arm or {}
check(arm.get('status') == 'ok', '2 PTC status ok', arm.get('status'))
check(arm.get('steps') == 24000, '2 steps == 24000', arm.get('steps'))
arms = sorted(((top or {}).get('job') or box).get('arms', {}).keys())
cfg = (arm.get('config') or {}).get('cfg') or {}
check(arms == ['PTC'], '3 job ran arm PTC only', arms)
check(cfg.get('calc_train') is True, '3 cfg.calc_train is true', cfg.get('calc_train'))
want = a.expect_params
if a.pc_pts_result:
    pc = json.load(open(a.pc_pts_result, encoding='utf-8'))
    want = pc.get('n_params', want)
    notes.append("PC's PTS n_params read from %s: %s" % (a.pc_pts_result, want))
check(arm.get('n_params') == want, "4 trained parameter count equals the PC's PTS count", '%s vs %s' % (arm.get('n_params'), want))
ch = arm.get('cap_hits') or {}
check(ch.get('total') == 0, '5 cap_hits total == 0', ch.get('total'))
cm, cr = ch.get('calc_mismatch'), ch.get('calc_rows')
ok6 = isinstance(cm, int) and isinstance(cr, int) and cr > 0 and cm / cr <= 0.001
check(ok6, '6 calc_mismatch / calc_rows <= 0.1% and calc_rows > 0', '%s / %s = %s' % (cm, cr, (('%.5f%%' % (100.0 * cm / cr)) if cr else 'n/a')))
notes.append('calc_forced %s' % ch.get('calc_forced'))
fe = arm.get('final_eval')
ls = sorted((arm.get('lesions') or {}).keys())
check(bool(fe) and 'nocalc' in ls, '7 final_eval present and lesion nocalc present', 'final_eval %s, lesions %s' % (bool(fe), ls))
if isinstance(fe, dict):
    notes.append('final_eval keys: ' + ', '.join(sorted(fe.keys())[:12]))
pm = load('pool_MANIFEST.json') or {}
notes.append('pool: rung %s seed %s rows %s train_bytes %s train_sha256 %s (the PC writes CRLF: compare its train_bytes minus rows, and its hash after CRLF to LF; RUNBOOK.md section 7)' % (
    pm.get('rung'), pm.get('seed'), pm.get('rows'), pm.get('train_bytes'), pm.get('train_sha256')))
for f in ('code_identity.txt', 'PTC-SETUP-OK.txt'):
    try:
        notes.append('box/%s: %s' % (f, open(os.path.join(d, 'box', f), encoding='utf-8').read().strip().replace('\n', ' || ')[:900]))
    except OSError:
        notes.append('box/%s missing' % f)
for n in notes:
    print('NOTE ' + n)
print('REJECT: ' + '; '.join(bad) if bad else 'ACCEPT')
sys.exit(1 if bad else 0)
