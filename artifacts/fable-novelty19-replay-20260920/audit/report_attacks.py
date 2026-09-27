#!/usr/bin/env python3
"""Adversarial probes of `gates` / `report` / DEV-PASSED / the confirmation lockout.

Every score file here is SYNTHETIC: the point is to find out what the report will
believe.  Nothing registered is touched; everything lives under the audit scratch.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import fable_dispatcher_v3 as V3                       # noqa: E402
import fable_novelty19_data as N                       # noqa: E402
import fable_novelty19_train as TR                     # noqa: E402

PY = sys.executable
TRAIN = str(ROOT / 'scripts' / 'fable_novelty19_train.py')
S = HERE / 'scratch2'
PANELS = S / 'dev'
FAKE = S / 'attack'
H64 = 'ab' * 32

out = {}


def cell_row(cell, answers, strict):
    cfg = N.DEV_CELLS[cell]
    return dict(cell=cell, family=cell.split('-')[0], n=64, answers=answers, strict=strict,
                hops=cfg['hops'], people=cfg['people'], mean_calls=float(cfg['hops']),
                mean_output_tokens=float(cfg['hops'] + 1), over_cap=0, no_end=0,
                marked=bool(TR.FAMILY_MARK[cell.split('-')[0]] is not None
                            and answers >= TR.FAMILY_MARK[cell.split('-')[0]]
                            and strict >= TR.FAMILY_MARK[cell.split('-')[0]]))


def score_file(folder, arch, seed, phase, arm, *, good, tag='x'):
    """`good=True` writes marks that satisfy every registered rule for that run."""
    cells = {}
    for cell in N.DEV_CELL_ORDER:
        if not good:
            cells[cell] = cell_row(cell, 10, 10)
        elif arm == 'R' and phase == 'offline':
            cells[cell] = cell_row(cell, 64, 40) if cell.startswith('N-') \
                else cell_row(cell, 64, 64)
        else:
            cells[cell] = cell_row(cell, 64, 64)
    payload = dict(kind='novelty19-score', arch=arch, seed=int(seed), phase=phase, arm=arm,
                   updates_done=6000 if phase == 'awake' else 2000,
                   total_updates=6000 if phase == 'awake' else 2000,
                   checkpoint=f'/nowhere/{arch}-{seed}-{phase}-{arm}.pt',
                   checkpoint_sha256=H64, final_weight_fingerprint=H64,
                   panels=str(PANELS.resolve()),
                   panel_manifest_sha256=TR.sha(PANELS / 'manifest.json'),
                   panel_guard=dict(is_confirmation=False), n_per_cell=64,
                   cell_order=list(N.DEV_CELL_ORDER), cells_scored=len(cells), cells=cells)
    folder.mkdir(parents=True, exist_ok=True)
    name = f'{phase}-{arch}-s{seed}' + (f'-{arm}' if arm else '') + f'-{tag}.json'
    (folder / name).write_text(json.dumps(payload))


def build(exp, seeds, *, good=True, drop=()):
    shutil.rmtree(exp, ignore_errors=True)
    scores = exp / 'scores'
    for seed in seeds:
        for arch in TR.ARCHES:
            if ('awake', arch, seed) not in drop:
                score_file(scores, arch, seed, 'awake', None, good=good)
            for arm in TR.ARMS:
                if (arm, arch, seed) in drop:
                    continue
                score_file(scores, arch, seed, 'offline', arm, good=good)
        # builder A's generation-gate audit, faked as a pass
        buf = exp / f'buffers-{seed}'
        buf.mkdir(parents=True, exist_ok=True)
        structures = {k: dict(distinct_questions=16, distinct_worlds=16, awake_instances=0,
                              required=16, passed=True)
                      for k in ('LINK LINK LINK 8', 'LINK LINK LINK 9',
                                'LINK LINK LINK LINK 8', 'LINK LINK LINK LINK 9')}
        audit = dict(seed=int(seed), arms=list(TR.ARMS),
                     generation_gate=dict(passed=True, structures=structures),
                     identical_world_bytes=dict(identical=True),
                     composite_r10_exposure=dict(zero_exposure=True),
                     per_arm={a: dict(fallbacks=0, accepted=4096, sha256=H64,
                                      length_histogram={'c=1,r=8': 4096})
                              for a in TR.ARMS})
        (buf / 'audit.json').write_text(json.dumps(audit))
        (buf / 'manifest.json').write_text(json.dumps(
            dict(seed=int(seed), arms=list(TR.ARMS), audit_sha256=TR.sha(buf / 'audit.json'),
                 files={f'buffer-{a}.pt': H64 for a in TR.ARMS})))
    return exp


def run(*argv):
    proc = subprocess.run([PY, '-B', TRAIN, *argv], capture_output=True, text=True)
    return proc.returncode, proc.stdout[-4000:], proc.stderr[-1200:]


# ---- attack 1: fully forged evidence for the three REGISTERED seeds -----------------
exp = build(FAKE / 'a1', TR.REGISTERED_SEEDS)
code, so, se = run('report', '--exp', str(exp))
out['attack1_forged_registered_seeds'] = dict(
    returncode=code, dev_passed_written=(exp / 'DEV-PASSED.json').exists(),
    dev_passed=json.loads((exp / 'DEV-PASSED.json').read_text())
    if (exp / 'DEV-PASSED.json').exists() else None,
    development_rule_line=[l for l in so.splitlines() if 'development rule' in l],
    stderr=se)

# ---- attack 2: ONE non-registered seed, --seeds 9991 --------------------------------
exp = build(FAKE / 'a2', (9991,))
code, so, se = run('report', '--exp', str(exp), '--seeds', '9991')
flag = exp / 'DEV-PASSED.json'
out['attack2_single_unregistered_seed'] = dict(
    returncode=code, dev_passed_written=flag.exists(),
    seeds_in_flag=json.loads(flag.read_text())['seeds'] if flag.exists() else None,
    checkpoint_keys=sorted(json.loads(flag.read_text())['awake_checkpoints'])
    if flag.exists() else None,
    expected_keys=list(N.AWAKE_CHECKPOINT_KEYS),
    development_rule_line=[l for l in so.splitlines() if 'development rule' in l], stderr=se)

# ---- attack 3: one run missing ------------------------------------------------------
exp = build(FAKE / 'a3', TR.REGISTERED_SEEDS, drop=(('G', 'D', 1902),))
code, so, se = run('report', '--exp', str(exp))
out['attack3_missing_run'] = dict(
    returncode=code, dev_passed_written=(exp / 'DEV-PASSED.json').exists(),
    development_rule_line=[l for l in so.splitlines() if 'development rule' in l],
    missing_lines=[l for l in so.splitlines() if '(missing)' in l][:4])

# ---- attack 4: conflicting duplicate score files ------------------------------------
exp = build(FAKE / 'a4', TR.REGISTERED_SEEDS)
score_file(exp / 'scores', 'D', 1900, 'offline', 'G', good=False, tag='dup')
code, so, se = run('report', '--exp', str(exp))
out['attack4_conflicting_scores'] = dict(
    returncode=code, dev_passed_written=(exp / 'DEV-PASSED.json').exists(),
    conflict_lines=[l for l in so.splitlines() if 'CONFLICT' in l][:3],
    development_rule_line=[l for l in so.splitlines() if 'development rule' in l])

# ---- attack 5: an empty / malformed DEV-PASSED.json unlocks confirmation? -----------
lock = FAKE / 'lock'
shutil.rmtree(lock, ignore_errors=True)
lock.mkdir(parents=True)
(lock / 'DEV-PASSED.json').write_text('{}')
conf = S / 'confirm-fake'
shutil.rmtree(conf, ignore_errors=True)
conf.mkdir(parents=True)
(conf / 'manifest.json').write_text(json.dumps(
    dict(kind='confirmation', namespace=N.NS_CONFIRM, n=64, cell_order=['F-c1-r8'],
         cells={'F-c1-r8': dict(n=64)}, files={})))
code, so, se = run('score', '--arch', 'T', '--ckpt',
                   str(S / 'runs/awake-T-whole/ckpt-000008.pt'), '--panels', str(conf),
                   '--out', str(FAKE / 'conf-score.json'), '--confirmation',
                   '--experiment', str(lock))
out['attack5_empty_dev_passed_unlocks_confirmation'] = dict(
    returncode=code, stderr=se.strip().splitlines()[-1] if se.strip() else '',
    guard_rejected_on_flag_contents=bool('DEV-PASSED' in se and 'refusing' in se),
    note='the guard only tests Path.exists(); the failure below is the panel loader, '
         'not the lockout')

# no flag at all -> must be refused by the guard
shutil.rmtree(lock, ignore_errors=True)
lock.mkdir(parents=True)
code, so, se = run('score', '--arch', 'T', '--ckpt',
                   str(S / 'runs/awake-T-whole/ckpt-000008.pt'), '--panels', str(conf),
                   '--out', str(FAKE / 'conf-score2.json'), '--confirmation',
                   '--experiment', str(lock))
out['attack6_no_dev_passed_refused'] = dict(returncode=code,
                                            stderr=se.strip().splitlines()[-1] if se else '')

# ---- attack 7: partial cells --------------------------------------------------------
part = S / 'dev-partial'
shutil.rmtree(part, ignore_errors=True)
shutil.copytree(PANELS, part)
data = json.loads((part / 'F-c1-r8.json').read_text())
data['units'] = data['units'][:32]
(part / 'F-c1-r8.json').write_text(json.dumps(data))
code, so, se = run('score', '--arch', 'T', '--ckpt',
                   str(S / 'runs/awake-T-whole/ckpt-000008.pt'), '--panels', str(part),
                   '--out', str(FAKE / 'part.json'), '--cells', 'F-c2-r8')
out['attack7_partial_cell'] = dict(returncode=code,
                                   stderr=se.strip().splitlines()[-1] if se else '',
                                   refused=code != 0)
shutil.rmtree(part, ignore_errors=True)

# ---- attack 8: forgetting screen, forced trigger and forced UNDETERMINED ------------
def forged_forgetting(awake_counts, offline_counts, gate_ok=True, seeds=TR.REGISTERED_SEEDS):
    runs = {}
    for seed in seeds:
        acells, ocells = {}, {}
        for cell in N.DEV_CELL_ORDER:
            a = awake_counts.get((seed, cell), 64 if gate_ok else 10)
            o = offline_counts.get((seed, cell), a)
            acells[cell] = cell_row(cell, a, a)
            ocells[cell] = cell_row(cell, o, o)
        runs[TR.run_key('D', seed, 'awake', None)] = dict(cells=acells)
        for arm in TR.ARMS:
            runs[TR.run_key('D', seed, 'offline', arm)] = dict(cells=ocells)
    return dict(runs=runs, missing=[], incomplete={}, conflicts=[], files=[], expected=[])


# one cell, one metric, two seeds, exactly -7
coll = forged_forgetting({}, {(1900, 'F-c2-r8'): 57, (1901, 'F-c2-r8'): 57})
screen = TR.forgetting_screen(coll, 'D')
# spread the drops over different cells -> must NOT trigger
coll2 = forged_forgetting({}, {(1900, 'F-c2-r8'): 57, (1901, 'F-c3-r8'): 57})
screen2 = TR.forgetting_screen(coll2, 'D')
# H cell below the eligibility mark
coll3 = forged_forgetting({(s, 'H-c2-p6'): 57 for s in TR.REGISTERED_SEEDS},
                          {(s, 'H-c2-p6'): 40 for s in TR.REGISTERED_SEEDS})
screen3 = TR.forgetting_screen(coll3, 'D')
# a seed that fails the awake-fit gate
coll4 = forged_forgetting({(1902, c): 10 for c in TR.FIT_CELLS},
                          {(1900, 'F-c2-r8'): 57, (1901, 'F-c2-r8'): 57})
screen4 = TR.forgetting_screen(coll4, 'D')
out['attack8_forgetting_screen'] = dict(
    same_cell_two_seeds=dict(outcome=screen['outcome'], triggered=screen['triggered'][:4]),
    different_cells=dict(outcome=screen2['outcome'], triggered=screen2['triggered'],
                         n_undetermined=len(screen2['undetermined'])),
    h_cell_below_eligibility=dict(
        outcome=screen3['outcome'],
        triggered_on_H=[t for t in screen3['triggered'] if '|H-' in t],
        statuses=sorted({v['status'] for c, combo in screen3['combos'].items()
                         if '|H-c2-p6|' in c for v in combo['per_seed'].values()})),
    one_seed_gate_failed=dict(outcome=screen4['outcome'],
                              triggered=screen4['triggered'],
                              gate=screen4['awake_fit_gate']))

# ---- attack 9: awake-fit gate with one FAIL and one MISSING -------------------------
entry = dict(cells={c: cell_row(c, 64, 64) for c in TR.FIT_CELLS})
entry['cells']['F-c1-r8'] = cell_row('F-c1-r8', 10, 10)
del entry['cells']['F-c2-r8']
out['attack9_gate_fail_plus_missing'] = dict(
    passed=TR.awake_fit_gate(entry)['passed'],
    expected='False would be safest; None is reported',
    all_present_fail=TR.awake_fit_gate(
        dict(cells={**{c: cell_row(c, 64, 64) for c in TR.FIT_CELLS},
                    'F-c1-r8': cell_row('F-c1-r8', 10, 10)}))['passed'],
    missing_entry=TR.awake_fit_gate(None)['passed'])

print(json.dumps(out, indent=1, default=str))
(HERE / 'report-attacks.json').write_text(json.dumps(out, indent=1, default=str))
