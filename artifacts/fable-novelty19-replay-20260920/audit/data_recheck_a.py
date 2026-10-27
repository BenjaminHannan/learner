#!/usr/bin/env python3
"""Data re-check, part A: protected-API behaviour, the `audit` roster, manifest stability."""
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'scripts'))

import independent_checks as IC                        # noqa: E402  (my own parser, task 1)
import fable_novelty19_data as N                       # noqa: E402

PY = sys.executable
DATA = str(ROOT / 'scripts' / 'fable_novelty19_data.py')
S = HERE / 'scratch2'
OLD = json.loads((HERE / 'independent-checks-9991.json').read_text())
out = {}


def run(*argv, cwd=None):
    p = subprocess.run([PY, '-B', DATA, *argv], capture_output=True, text=True,
                       cwd=str(cwd or S))
    return p.returncode, p.stdout, p.stderr


# ---- 1. protected API: rebuild the exact task-1 fixture and re-census it ------------
for name in ('awakeB', 'memB', 'bufB'):
    shutil.rmtree(S / name, ignore_errors=True)
rc1, so1, se1 = run('awake-stream', '--seed', '9991', '--updates', '100', '--chunk', '100',
                    '--out', 'awakeB', '--dev-panels', 'dev', '--quiet')
rc2, so2, se2 = run('memory', '--seed', '9991', '--stream', 'awakeB', '--out', 'memB')
rc3, so3, se3 = run('buffers', '--seed', '9991', '--memory', 'memB', '--out', 'bufB',
                    '--dev-panels', 'dev')
new_awake = IC.check_awake(S / 'awakeB')
new_mem = IC.check_memory(S / 'memB', new_awake)
old_awake, old_mem = OLD['awake'], OLD['memory']
out['protected_api'] = dict(
    rebuild_returncodes=[rc1, rc2, rc3],
    awake_census_identical=new_awake['census'] == old_awake['census'],
    awake_census_new=new_awake['census'], awake_census_old=old_awake['census'],
    memory_census_identical=new_mem['census'] == old_mem['census'],
    memory_counts_match_recount=new_mem['counts_match_my_recount'],
    memory_distinct_worlds=new_mem['distinct_world_signatures'],
    old_distinct_worlds=old_mem['distinct_world_signatures'],
    transition_probs_new={k: v for k, v in IC.NOTES.items()} if hasattr(IC, 'NOTES') else None,
    note='the stream/memory content produced by the PROTECTED API is compared through my '
         'own parser, not through file hashes: the block schema gained world_signature, so '
         'the .pt bytes are expected to differ')

# the chunk file hash is expected to move because the schema changed
index_new = json.loads((S / 'awakeB' / 'index.json').read_text())
out['protected_api']['chunk_sha_old'] = \
    json.loads((HERE / 'scratch/awake9991/index.json').read_text())['chunks'][0]['sha256']
out['protected_api']['chunk_sha_new'] = index_new['chunks'][0]['sha256']
out['protected_api']['index_has_wall_clock'] = \
    sorted(k for k in index_new if k in ('created_unix', 'seconds'))
out['protected_api']['index_meta_sidecar'] = N.read_meta(S / 'awakeB' / 'index.json')

# ---- 2. the audit roster ------------------------------------------------------------
rc, so, se = run('audit', '--seed', '9991', '--stream', 'awakeB', '--memory', 'memB',
                 '--buffers', 'bufB', '--dev-panels', 'dev', '--operator-history', 'ophist')
verdict = None
for blob in json.JSONDecoder().raw_decode, :
    pass
_pos, _dec = 0, json.JSONDecoder()
while _pos < len(so):
    try:
        _obj, _pos = _dec.raw_decode(so, _pos)
    except json.JSONDecodeError:
        _pos += 1
        continue
    if isinstance(_obj, dict) and 'checks' in _obj:
        verdict = _obj
    while _pos < len(so) and so[_pos] in ' \n\r\t':
        _pos += 1
out['audit_roster'] = dict(
    returncode=rc,
    expected_checks=len(N.EXPECTED_AUDIT_CHECKS),
    checks_run=None if verdict is None else verdict.get('checks_run'),
    checks_expected=None if verdict is None else verdict.get('checks_expected'),
    checks_absent=None if verdict is None else verdict.get('checks_absent'),
    passed=None if verdict is None else verdict.get('passed'),
    failures=None if verdict is None else verdict.get('failures'),
    stderr=se[-300:])

# every source is a required CLI flag?
required = {}
for cmd, flags in (('audit', ['--stream', '--memory', '--buffers', '--dev-panels',
                              '--operator-history']),
                   ('awake-stream', ['--dev-panels']),
                   ('buffers', ['--dev-panels'])):
    rc2_, so2_, se2_ = run(cmd, '--help')
    required[cmd] = {f: ('[%s' % f) not in so2_ for f in flags}   # not bracketed => required
out['audit_roster']['flags_required'] = required

# ---- 3. a missing check is itself a failure ----------------------------------------
saved = N.EXPECTED_AUDIT_CHECKS
try:
    N.EXPECTED_AUDIT_CHECKS = saved + ('a_check_that_never_runs',)
    v = N.audit_everything(9991, stream=S / 'awakeB', memory=S / 'memB', buffers=S / 'bufB',
                           dev_panels=S / 'dev', operator_history=S / 'ophist')
    out['missing_check_fails'] = dict(passed=v['passed'], failures=v['failures'],
                                      checks_absent=v['checks_absent'],
                                      checks_run=v['checks_run'],
                                      checks_expected=v['checks_expected'])
finally:
    N.EXPECTED_AUDIT_CHECKS = saved

# ---- 4. manifest reproducibility -----------------------------------------------------
shutil.rmtree(S / 'dev-rep', ignore_errors=True)
rc, so, se = run('dev-panels', '--out', 'dev-rep', '--operator-history', 'ophist',
                 '--cells', 'F-c1-r8,N-c4-p6,L-c6-prac', '--quiet')
first = {p.name: N.sha(p) for p in sorted((S / 'dev-rep').glob('*.json'))
         if not p.name.endswith('.meta.json')}
shutil.rmtree(S / 'dev-rep', ignore_errors=True)
rc, so, se = run('dev-panels', '--out', 'dev-rep', '--operator-history', 'ophist',
                 '--cells', 'F-c1-r8,N-c4-p6,L-c6-prac', '--quiet')
second = {p.name: N.sha(p) for p in sorted((S / 'dev-rep').glob('*.json'))
          if not p.name.endswith('.meta.json')}
# and to a DIFFERENT folder, to see which documents carry absolute paths
shutil.rmtree(S / 'dev-rep2', ignore_errors=True)
rc, so, se = run('dev-panels', '--out', 'dev-rep2', '--operator-history', 'ophist',
                 '--cells', 'F-c1-r8,N-c4-p6,L-c6-prac', '--quiet')
third = {p.name: N.sha(p) for p in sorted((S / 'dev-rep2').glob('*.json'))
         if not p.name.endswith('.meta.json')}
out['manifest_reproducible'] = dict(
    same_path_twice_identical=first == second,
    differing=[k for k in first if first[k] != second.get(k)],
    other_path_identical=[k for k in first if first[k] == third.get(k)],
    other_path_differing=[k for k in first if first[k] != third.get(k)],
    meta_sidecars=sorted(p.name for p in (S / 'dev-rep').glob('*.meta.json'))[:4],
    wall_clock_keys_in_manifest=[k for k in
                                 json.loads((S / 'dev-rep' / 'manifest.json').read_text())
                                 if k in ('created_unix', 'seconds')])
shutil.rmtree(S / 'dev-rep', ignore_errors=True)
shutil.rmtree(S / 'dev-rep2', ignore_errors=True)

# ---- 5. execution profile pinned ----------------------------------------------------
prof = json.loads((S / 'dev' / 'manifest.json').read_text())['execution_profile']
out['execution_profile'] = dict(
    keys=sorted(prof), python=prof['python'], torch=prof['torch'],
    implementation=prof['implementation'], machine=prof['machine'],
    script_sha256=prof['script_sha256'],
    runtime_local_json_pinned='runtime' in json.dumps(prof).lower(),
    present_in=[f for f in ('awakeB/index.json', 'memB/manifest.json', 'bufB/manifest.json',
                            'dev/manifest.json', 'ophist/manifest.json')
                if 'execution_profile' in json.loads((S / f).read_text())])

print(json.dumps(out, indent=1, default=str))
(HERE / 'data-recheck-a.json').write_text(json.dumps(out, indent=1, default=str))
