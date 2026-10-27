#!/usr/bin/env python3
"""Independent adversarial attacks on 19b's gates / report / DEV-PASSED path.

Disposable seeds 999001-999003 only.  No registered training or scoring is run; every
score file here is synthetic JSON.  Nothing outside this scratch folder is written.
"""
import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

import fable_novelty19b_train as B          # noqa: E402
import fable_novelty19b_data as D          # noqa: E402
import fable_novelty19_train as TR         # noqa: E402

FIX = (999001, 999002, 999003)
# The ONLY substitution: disposable seeds, in BOTH modules.  Patching just one is
# refused by check_layout_agrees ("the training and data modules disagree"), which is
# itself a defence worth recording.
B.SEEDS = FIX
D.SEEDS = FIX
GROUPS = B.groups(D)
CELLS = D.CELLS
ORDER = list(B.cell_order(D))
CONTRAST = list(GROUPS['contrast'])
TEMP = []
RESULTS = {}


def hex64(tag):
    import hashlib
    return hashlib.sha256(tag.encode()).hexdigest()


def cell_row(cell, answers, strict):
    cfg = CELLS[cell]
    return dict(cell=cell, family=B.family_of(cell), n=64,
                sides=1 + int(cfg['kind'] == 'pair'), hops=cfg['hops'],
                people=cfg['people'], terminal=cfg['terminal'],
                fixed_terminal=cfg['fixed_terminal'], kind=cfg['kind'],
                invariant=cfg['invariant'], answers=answers, strict=strict,
                mean_calls=float(cfg['hops']), over_cap=0,
                failure_shapes=None, oracle_operator=None)


def flags(strict_ones):
    return dict(unit_index=list(range(64)),
                answers=[1] * 64,
                strict=[1] * strict_ones + [0] * (64 - strict_ones),
                calls=[4] * 64)


def make_exp():
    folder = Path(tempfile.mkdtemp(prefix='gate19b-', dir=HERE))
    TEMP.append(folder)
    panels = folder / 'dev-panels'
    panels.mkdir(parents=True)
    (panels / 'manifest.json').write_text(json.dumps(dict(kind='development', n=64)))
    for seed in FIX:
        buf = folder / f'buffers-{seed}'
        buf.mkdir()
        (buf / 'manifest.json').write_text(json.dumps(
            dict(seed=seed, arms=list(B.ARMS), files={}, audit_sha256=hex64('a'))))
        (buf / 'offline-order.json').write_text(json.dumps(dict(seed=seed, updates=2000)))
        (buf / 'audit.json').write_text(json.dumps(
            dict(composite_r10_exposure=dict(zero_exposure=True))))
    return folder


def write_run(folder, name, phase, seed, arm, updates):
    run = folder / 'runs' / name
    run.mkdir(parents=True, exist_ok=True)
    ckpt = run / TR.checkpoint_name(updates)
    ckpt.write_bytes(f'not a real checkpoint {name}'.encode())
    csha = TR.sha(ckpt)
    (run / 'completion.json').write_text(json.dumps(dict(
        complete=True, checkpoint=str(ckpt), checkpoint_sha256=csha,
        arch='D', phase=phase, arm=arm, seed=seed, total_updates=updates)))
    return ckpt, csha


def score_payload(folder, name, phase, seed, arm, cells, unit_flags, panel_sha,
                  fingerprint):
    updates = TR.AWAKE_UPDATES if phase == 'awake' else B.OFFLINE_UPDATES
    ckpt, csha = write_run(folder, name, phase, seed, arm, updates)
    return dict(kind='novelty19b-score', experiment='novelty19b', arch='D', seed=seed,
                phase=phase, arm=arm, updates_done=updates, total_updates=updates,
                checkpoint=str(ckpt), checkpoint_sha256=csha,
                panels=str(folder / 'dev-panels'), panel_manifest_sha256=panel_sha,
                n_per_cell=64, eval_cap=16, registered_caps=True,
                cells=cells, unit_flags=unit_flags,
                source_fingerprint=fingerprint)


def build(control_strict_on_contrast=51, anchor_h_strict=64, tweak=None):
    """A complete, passing set of nine score files, then `tweak(folder, docs)`."""
    folder = make_exp()
    panel_sha = TR.sha(folder / 'dev-panels' / 'manifest.json')
    fp = dict(B.source_fingerprint())
    docs = {}
    for seed in FIX:
        # awake anchor
        cells = {c: cell_row(c, 64, 64) for c in ORDER}
        for c in GROUPS['retention_h']:
            cells[c] = cell_row(c, anchor_h_strict, anchor_h_strict)
        uf = {c: flags(cells[c]['strict']) for c in ORDER}
        docs[f'awake-D-s{seed}'] = score_payload(
            folder, f'awake-D-s{seed}', 'awake', seed, None, cells, uf, panel_sha, fp)
        # U8 treatment: everything full
        cells = {c: cell_row(c, 64, 64) for c in ORDER}
        uf = {c: flags(64) for c in ORDER}
        docs[f'offline-D-s{seed}-U8'] = score_payload(
            folder, f'offline-D-s{seed}-U8', 'offline', seed, 'U8', cells, uf, panel_sha, fp)
        # U5 control: lower on the three contrast cells
        cells = {c: cell_row(c, 64, 64) for c in ORDER}
        uf = {c: flags(64) for c in ORDER}
        for c in CONTRAST:
            cells[c] = cell_row(c, 64, control_strict_on_contrast)
            uf[c] = flags(control_strict_on_contrast)
        docs[f'offline-D-s{seed}-U5'] = score_payload(
            folder, f'offline-D-s{seed}-U5', 'offline', seed, 'U5', cells, uf, panel_sha, fp)
    if tweak:
        tweak(folder, docs)
    scores = folder / 'scores'
    scores.mkdir(exist_ok=True)
    for name, doc in docs.items():
        (scores / f'{name}.json').write_text(json.dumps(doc))
    return folder


def run_case(name, folder, *, expect_dev_passed):
    """`gates` then `report`, exactly as run_score.sh does."""
    row = dict(case=name)
    try:
        args = type('A', (), dict(exp=str(folder), seed_list=FIX, out=None))()
        B.gates(args)
        row['gates'] = 'ok'
    except SystemExit as exc:
        row['gates'] = f'REFUSED: {str(exc)[:180]}'
    try:
        args = type('A', (), dict(exp=str(folder), seed_list=FIX, out=None,
                                  overwrite=False))()
        payload = _quiet(lambda: B.report(args))
        rule = payload['development_rule']
        row['rule_passed'] = rule['passed']
        row['per_seed'] = {s: v['passed'] for s, v in rule['per_seed'].items()}
        row['provenance'] = rule['provenance']['passed']
        row['failed_parts'] = sorted({
            f'{s}:{p}' for s, v in rule['per_seed'].items()
            for p, q in v['parts'].items() if q['passed'] is not True})
        row['dev_passed_file'] = payload.get('dev_passed')
        row['dev_passed_problems'] = payload.get('dev_passed_problems')
    except SystemExit as exc:
        row['report'] = f'REFUSED: {str(exc)[:200]}'
    except Exception as exc:                       # noqa: BLE001 - that is the finding
        row['report'] = f'CRASH {type(exc).__name__}: {str(exc)[:160]}'
    row['DEV-PASSED.json on disk'] = (folder / 'DEV-PASSED.json').exists()
    row['as_expected'] = (row['DEV-PASSED.json on disk'] == expect_dev_passed)
    RESULTS[name] = row
    print(json.dumps(row, indent=1), flush=True)
    return row


class _Sink:
    def write(self, _):
        return None

    def flush(self):
        return None


def _quiet(fn):
    old = sys.stdout
    sys.stdout = _Sink()
    try:
        return fn()
    finally:
        sys.stdout = old


# ------------------------------------------------------------------ the attacks

run_case('control: a true full pass', build(), expect_dev_passed=True)

run_case('one bounded cell at 57/64 in one seed',
         build(tweak=lambda f, d: d[f'offline-D-s{FIX[1]}-U8']['cells'].__setitem__(
             GROUPS['bounded'][0], cell_row(GROUPS['bounded'][0], 57, 57))),
         expect_dev_passed=False)

run_case('one long cell strict 57, answers 64 (answers alone must not rescue)',
         build(tweak=lambda f, d: d[f'offline-D-s{FIX[0]}-U8']['cells'].__setitem__(
             GROUPS['long'][4], cell_row(GROUPS['long'][4], 64, 57))),
         expect_dev_passed=False)

run_case('one F cell at 60/64 (mark is 61)',
         build(tweak=lambda f, d: d[f'offline-D-s{FIX[2]}-U8']['cells'].__setitem__(
             GROUPS['retention_f'][0], cell_row(GROUPS['retention_f'][0], 60, 60))),
         expect_dev_passed=False)

run_case('one E guard cell at 57/64 strict pairs',
         build(tweak=lambda f, d: d[f'offline-D-s{FIX[0]}-U8']['cells'].__setitem__(
             GROUPS['guards'][0], cell_row(GROUPS['guards'][0], 64, 57))),
         expect_dev_passed=False)

run_case('gain of exactly 13 (boundary: must PASS)',
         build(control_strict_on_contrast=51), expect_dev_passed=True)

run_case('gain of exactly 12 (boundary: must FAIL)',
         build(control_strict_on_contrast=52), expect_dev_passed=False)


def _h_loss(loss):
    def tweak(f, d):
        cell = GROUPS['retention_h'][0]
        for seed in FIX:
            d[f'offline-D-s{seed}-U8']['cells'][cell] = cell_row(cell, 64 - loss, 64 - loss)
    return tweak


run_case('H loss of exactly 6 vs the awake anchor (must PASS)',
         build(tweak=_h_loss(6)), expect_dev_passed=True)
run_case('H loss of exactly 7 vs the awake anchor (must FAIL)',
         build(tweak=_h_loss(7)), expect_dev_passed=False)


def _drop_anchor(f, d):
    del d[f'awake-D-s{FIX[0]}']


run_case('missing endpoint: one awake anchor never scored',
         build(tweak=_drop_anchor), expect_dev_passed=False)


def _drop_control(f, d):
    del d[f'offline-D-s{FIX[1]}-U5']


run_case('missing endpoint: one U5 control never scored',
         build(tweak=_drop_control), expect_dev_passed=False)


def _nan(f, d):
    cell = GROUPS['bounded'][2]
    d[f'offline-D-s{FIX[0]}-U8']['cells'][cell] = cell_row(cell, float('nan'), float('nan'))


run_case('NaN counts in one cell', build(tweak=_nan), expect_dev_passed=False)


def _swap_arms(f, d):
    a, b = d[f'offline-D-s{FIX[0]}-U5'], d[f'offline-D-s{FIX[0]}-U8']
    a['arm'], b['arm'] = 'U8', 'U5'


run_case('swapped arm labels on one seed', build(tweak=_swap_arms), expect_dev_passed=False)


def _mixed_fp(f, d):
    doc = d[f'offline-D-s{FIX[2]}-U8']
    doc['source_fingerprint'] = dict(doc['source_fingerprint'], novelty19b_train=hex64('drift'))


run_case('mixed source fingerprints across runs', build(tweak=_mixed_fp),
         expect_dev_passed=False)


def _mixed_data_fp(f, d):
    doc = d[f'offline-D-s{FIX[1]}-U5']
    doc['source_fingerprint'] = dict(doc['source_fingerprint'],
                                     novelty19b_data=hex64('data drift'))


run_case('drifted 19b DATA script between runs', build(tweak=_mixed_data_fp),
         expect_dev_passed=False)


def _null_fp(f, d):
    d[f'awake-D-s{FIX[0]}'].pop('source_fingerprint')


run_case('one run with no source fingerprint at all', build(tweak=_null_fp),
         expect_dev_passed=False)


def _dup(f, d):
    d['offline-D-s%d-U8-copy' % FIX[0]] = copy.deepcopy(d[f'offline-D-s{FIX[0]}-U8'])


run_case('duplicated run: the same run scored twice', build(tweak=_dup),
         expect_dev_passed=False)


def _two_suites(f, d):
    d[f'offline-D-s{FIX[0]}-U8']['panel_manifest_sha256'] = hex64('other suite')


run_case('one run scored on a different panel suite', build(tweak=_two_suites),
         expect_dev_passed=False)


def _midrun(f, d):
    d[f'offline-D-s{FIX[2]}-U8']['updates_done'] = 1500


run_case('a mid-run (1,500-update) checkpoint offered as the result',
         build(tweak=_midrun), expect_dev_passed=False)


def _unit_mismatch(f, d):
    cell = CONTRAST[0]
    fl = dict(d[f'offline-D-s{FIX[0]}-U5']['unit_flags'][cell])
    fl['unit_index'] = list(range(100, 164))
    d[f'offline-D-s{FIX[0]}-U5']['unit_flags'][cell] = fl


run_case('the two arms scored on different units in a contrast cell',
         build(tweak=_unit_mismatch), expect_dev_passed=False)

# --------------------------------------------------- the lockout itself
lock = {}
folder = build()                                  # a true pass, so the flag exists
run_case('(rebuild for lockout tests)', folder, expect_dev_passed=True)
genuine = json.loads((folder / 'DEV-PASSED.json').read_text())

for label, mutate in (
        ('hand-made file, right shape, wrong schema',
         lambda doc: dict(doc, schema='novelty19-dev-passed-v1')),
        ('experiment-19 DEV-PASSED.json presented verbatim', None),
        ('one offline checkpoint entry removed',
         lambda doc: dict(doc, offline_checkpoints={
             k: v for k, v in list(doc['offline_checkpoints'].items())[1:]})),
        ('an extra checkpoint entry added',
         lambda doc: dict(doc, offline_checkpoints=dict(doc['offline_checkpoints'],
                                                        **{'D-U9-1': hex64('x')}))),
        ('checkpoint hash replaced by a non-sha string',
         lambda doc: dict(doc, offline_checkpoints=dict(
             doc['offline_checkpoints'],
             **{list(doc['offline_checkpoints'])[0]: 'PASSED'}))),
        ('dev_panels manifest hash does not match the folder on disk',
         lambda doc: dict(doc, dev_panels=dict(doc['dev_panels'],
                                               manifest_sha256=hex64('elsewhere')))),
        ('empty file', 'empty'),
):
    probe = make_exp()
    if mutate == 'empty':
        (probe / 'DEV-PASSED.json').write_text('')
    elif mutate is None:
        src = ROOT / 'artifacts' / 'fable-novelty19-replay-20260920' / 'DEV-PASSED.json'
        if not src.exists():
            lock[label] = 'experiment 19 has no DEV-PASSED.json on disk (it FAILED)'
            continue
        shutil.copyfile(src, probe / 'DEV-PASSED.json')
    else:
        doc = mutate(copy.deepcopy(genuine))
        (probe / 'DEV-PASSED.json').write_text(json.dumps(doc))
    try:
        D.validate_dev_passed(probe, seeds=FIX)
        lock[label] = 'ACCEPTED  <-- finding'
    except SystemExit as exc:
        lock[label] = f'refused: {str(exc)[:140]}'
RESULTS['lockout'] = lock
print(json.dumps(lock, indent=1), flush=True)

(HERE / 'gate-attacks-19b.json').write_text(json.dumps(RESULTS, indent=1, default=str))
bad = [k for k, v in RESULTS.items()
       if isinstance(v, dict) and v.get('as_expected') is False]
print('\nUNEXPECTED:', bad or 'none', flush=True)
for folder in TEMP:
    shutil.rmtree(folder, ignore_errors=True)
