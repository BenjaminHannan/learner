#!/usr/bin/env python3
"""M-1 re-run.  The first attempt was inconclusive: guard_confirmation validates the
unlock against the module global REGISTERED_SEEDS, so a disposable-seed fixture is
refused on the SEED check before the binding check is ever reached.  The only
substitution made here is that global (9991 instead of 1900-1902), so the seed gate
passes and the binding logic under test -- comparing the presented file's sha256 with
the confirmation manifest's recorded dev_passed.sha256 -- runs for real.
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

import fable_novelty19_data as N                          # noqa: E402
import fable_novelty19_train as TR                        # noqa: E402

S = HERE / 'scratch4'
SEEDS = (9991,)
TR.REGISTERED_SEEDS = SEEDS                               # the ONLY substitution

exp = S / 'exp9991'
conf = S / 'confirm'
man_path = conf / 'manifest.json'
manifest = json.loads(man_path.read_text())
bound = manifest.get('dev_passed', {}).get('sha256')


def unlock(report_sha):
    h = 'cd' * 32
    return dict(schema=N.DEV_PASSED_SCHEMA, seeds=[9991], report_sha256=report_sha,
                dev_panels=dict(path=str((S / 'dev').resolve()),
                                manifest_sha256=N.sha(S / 'dev' / 'manifest.json')),
                awake_checkpoints={k: h for k in N.checkpoint_keys('awake', SEEDS)},
                offline_checkpoints={k: h for k in N.checkpoint_keys('offline', SEEDS)})


first = unlock('cd' * 32)
(exp / 'DEV-PASSED.json').write_text(json.dumps(first))
first_sha = N.sha(exp / 'DEV-PASSED.json')


def guard(label):
    try:
        got = TR.guard_confirmation(conf, True, exp)
        return dict(case=label, accepted=True, bound=got.get('dev_passed_bound_to_suite'),
                    sha=got.get('dev_passed_sha256'))
    except BaseException as exc:                                        # noqa: BLE001
        return dict(case=label, accepted=False, message=str(exc)[-210:])


cases = [guard('the original unlock (control)')]

second = unlock('ab' * 32)
(exp / 'DEV-PASSED.json').write_text(json.dumps(second))
second_sha = N.sha(exp / 'DEV-PASSED.json')
cases.append(guard('a second, independently valid unlock'))
(exp / 'DEV-PASSED.json').write_text(json.dumps(first))

for label, mutate in (('manifest dev_passed.sha256 removed',
                       lambda m: m['dev_passed'].pop('sha256', None)),
                      ('manifest dev_passed.sha256 blank',
                       lambda m: m['dev_passed'].update(sha256='')),
                      ('manifest dev_passed block removed',
                       lambda m: m.pop('dev_passed', None))):
    doc = json.loads(man_path.read_text())
    mutate(doc)
    man_path.write_text(json.dumps(doc, indent=1))
    cases.append(guard(label))
    man_path.write_text(json.dumps(manifest, indent=1))

cases.append(guard('the original unlock again (control after restore)'))

# a development suite must still be scorable without any of this
dev_guard = TR.guard_confirmation(S / 'dev', False, None)

out = dict(
    suite_records_dev_passed_sha256=bound,
    first_unlock_sha=first_sha, second_unlock_sha=second_sha,
    suite_is_bound_to_the_first=bool(bound == first_sha),
    two_unlocks_both_valid_and_different=bool(first_sha != second_sha),
    cases=cases,
    legitimate_unlock_passes=bool(cases[0]['accepted'] and cases[-1]['accepted']),
    every_attack_refused=all(not c['accepted'] for c in cases[1:-1]),
    development_suite_unaffected=dev_guard,
    closed=bool(cases[0]['accepted'] and cases[-1]['accepted']
                and all(not c['accepted'] for c in cases[1:-1])))
print(json.dumps(out, indent=1, default=str))
(HERE / 'train-recheck3-m1.json').write_text(json.dumps(out, indent=1, default=str))
