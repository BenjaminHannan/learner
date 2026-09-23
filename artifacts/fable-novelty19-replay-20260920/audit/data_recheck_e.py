#!/usr/bin/env python3
"""Re-check 3: the R2-7 tamper matrix against EVERY consumer, consumed_exclusions
provenance, the 37-check audit roster, and content equality with Re-check 2."""
import json
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'scripts'))

import independent_checks as IC                        # noqa: E402
import fable_confirmation_panels as CP                 # noqa: E402
import fable_novelty19_data as N                       # noqa: E402

PY = sys.executable
DATA = str(ROOT / 'scripts' / 'fable_novelty19_data.py')
S = HERE / 'scratch3'
out = {}


def run(*argv):
    p = subprocess.run([PY, '-B', DATA, *argv], capture_output=True, text=True, cwd=str(S))
    tail = [ln for ln in (p.stderr or '').strip().splitlines() if ln.strip()]
    return p.returncode, p.stdout, (tail[-1][:150] if tail else '')


# ===================================================================== 1. tamper matrix
HEXA = 'a' * 64


def attacks(path):
    """The four edits the coordinator asked for, as (label, new bytes)."""
    doc = json.loads(Path(path).read_text())
    n = len(doc)
    same_count = sorted(set(doc[:-1] + [HEXA]))
    if len(same_count) != n:                      # keep the count EXACTLY equal
        same_count = sorted(set(doc[:-2] + [HEXA, 'b' * 64]))[:n]
    padded = sorted(doc[:5]) + [doc[5]] * (n - 5)  # right count, duplicate-padded
    return [('truncated', json.dumps(sorted(doc[:5]))),
            ('same-count-tampered', json.dumps(same_count)),
            ('duplicate-padded', json.dumps(padded)),
            ('unsorted', json.dumps(list(reversed(sorted(doc))))),
            ('emptied', json.dumps([]))]


CONSUMERS = {
    'awake-stream (reads dev panels)':
        lambda: run('awake-stream', '--seed', '9992', '--updates', '4', '--chunk', '4',
                    '--out', 'atk-awake', '--dev-panels', 'dev', '--quiet'),
    'buffers (reads dev panels)':
        lambda: run('buffers', '--seed', '9991', '--memory', 'memB', '--out', 'atk-buf',
                    '--dev-panels', 'dev'),
    'dev-panels (reads operator history)':
        lambda: run('dev-panels', '--out', 'atk-dev', '--operator-history', 'ophist',
                    '--cells', 'F-c1-r8', '--quiet'),
    'audit (reads every artifact)':
        lambda: run('audit', '--seed', '9991', '--stream', 'awakeB', '--memory', 'memB',
                    '--buffers', 'bufB', '--dev-panels', 'dev',
                    '--operator-history', 'ophist'),
}

TARGETS = {
    'dev/forbidden-semantics.json': ['awake-stream (reads dev panels)',
                                     'buffers (reads dev panels)',
                                     'audit (reads every artifact)'],
    'dev/forbidden-worlds-primary.json': ['awake-stream (reads dev panels)',
                                          'buffers (reads dev panels)',
                                          'audit (reads every artifact)'],
    'ophist/forbidden-worlds.json': ['dev-panels (reads operator history)',
                                     'audit (reads every artifact)'],
    'bufB/forbidden-worlds.json': ['audit (reads every artifact)'],
}

matrix, baseline = {}, {}
for name, fn in CONSUMERS.items():
    for junk in ('atk-awake', 'atk-buf', 'atk-dev'):
        shutil.rmtree(S / junk, ignore_errors=True)
    code, _so, err = fn()
    baseline[name] = dict(returncode=code, ok=code == 0, stderr=err)
for junk in ('atk-awake', 'atk-buf', 'atk-dev'):
    shutil.rmtree(S / junk, ignore_errors=True)

for target, consumers in TARGETS.items():
    path = S / target
    if not path.exists():
        matrix[target] = dict(error='file absent')
        continue
    original = path.read_bytes()
    per_attack = {}
    for label, body in attacks(path):
        path.write_bytes(body.encode())
        results = {}
        for name in consumers:
            for junk in ('atk-awake', 'atk-buf', 'atk-dev'):
                shutil.rmtree(S / junk, ignore_errors=True)
            code, so, err = CONSUMERS[name]()
            refused = code != 0
            if name.startswith('audit') and not refused:
                doc = None
                dec, pos = json.JSONDecoder(), 0
                while pos < len(so):
                    try:
                        obj, pos = dec.raw_decode(so, pos)
                    except json.JSONDecodeError:
                        pos += 1
                        continue
                    if isinstance(obj, dict) and 'checks' in obj:
                        doc = obj
                    while pos < len(so) and so[pos] in ' \n\r\t':
                        pos += 1
                refused = bool(doc is not None and doc.get('passed') is False)
                err = f'audit passed={None if doc is None else doc.get("passed")} ' \
                      f'failures={None if doc is None else doc.get("failures")}'[:150]
            results[name] = dict(refused=refused, returncode=code, message=err)
        per_attack[label] = results
    path.write_bytes(original)
    matrix[target] = per_attack

# ---- a missing / stripped producing manifest --------------------------------------------
manifest_attacks = {}
for label, mutate in (('manifest deleted', 'delete'),
                      ('published_exclusions stripped', 'strip'),
                      ('published_exclusions sha blanked', 'blank')):
    man = S / 'dev' / 'manifest.json'
    original = man.read_bytes()
    if mutate == 'delete':
        man.unlink()
    else:
        doc = json.loads(original)
        if mutate == 'strip':
            doc.pop('published_exclusions', None)
        else:
            doc['published_exclusions']['questions_sha256'] = ''
        man.write_text(json.dumps(doc, sort_keys=True, indent=1))
    results = {}
    for name in ('awake-stream (reads dev panels)', 'buffers (reads dev panels)'):
        for junk in ('atk-awake', 'atk-buf'):
            shutil.rmtree(S / junk, ignore_errors=True)
        code, _so, err = CONSUMERS[name]()
        results[name] = dict(refused=code != 0, message=err)
    man.write_bytes(original)
    manifest_attacks[label] = results
for junk in ('atk-awake', 'atk-buf', 'atk-dev'):
    shutil.rmtree(S / junk, ignore_errors=True)

flat = [(t, a, c, r['refused'])
        for t, per in matrix.items() if isinstance(per, dict) and 'error' not in per
        for a, res in per.items() for c, r in res.items()]
out['tamper_matrix'] = dict(
    baseline_all_consumers_pass=all(v['ok'] for v in baseline.values()),
    baseline=baseline,
    total_cases=len(flat),
    all_refused=all(r for *_x, r in flat),
    accepted=[dict(target=t, attack=a, consumer=c) for t, a, c, r in flat if not r],
    manifest_attacks=manifest_attacks,
    manifest_all_refused=all(r['refused'] for v in manifest_attacks.values()
                             for r in v.values()),
    matrix=matrix)

# ===================================================================== 2. load_operator_history
oh = {}
path = S / 'ophist' / N.FORBIDDEN_WORLDS
original = path.read_bytes()
for label, body in attacks(path):
    path.write_bytes(body.encode())
    try:
        N.load_operator_history(S / 'ophist', require_full=True)
        oh[label] = 'ACCEPTED'
    except BaseException as exc:                                    # noqa: BLE001
        oh[label] = f'{type(exc).__name__}: {str(exc)[:110]}'
path.write_bytes(original)
try:
    N.load_operator_history(S / 'ophist', require_full=True)
    oh['restored'] = 'accepted (control)'
except BaseException as exc:                                        # noqa: BLE001
    oh['restored'] = f'{type(exc).__name__}: {exc}'[:110]
out['operator_history_loader'] = dict(cases=oh,
                                      all_tampered_refused=all(
                                          v != 'ACCEPTED' for k, v in oh.items()
                                          if k != 'restored'))

# ===================================================================== 3. consumed_exclusions
prov = {}
for label, folder, key in (('dev panels', S / 'dev', 'manifest.json'),
                           ('awake stream', S / 'awakeB', 'index.json'),
                           ('buffers', S / 'bufB', 'manifest.json')):
    doc = json.loads((folder / key).read_text())
    rec = doc.get('consumed_exclusions')
    prov[label] = dict(present=rec is not None, value=rec)
out['consumed_exclusions'] = dict(
    per_artifact=prov,
    every_consumer_records_it=all(v['present'] for v in prov.values()))

# ===================================================================== 4. audit roster
code, so, err = run('audit', '--seed', '9991', '--stream', 'awakeB', '--memory', 'memB',
                    '--buffers', 'bufB', '--dev-panels', 'dev',
                    '--operator-history', 'ophist')
doc, dec, pos = None, json.JSONDecoder(), 0
while pos < len(so):
    try:
        obj, pos = dec.raw_decode(so, pos)
    except json.JSONDecodeError:
        pos += 1
        continue
    if isinstance(obj, dict) and 'checks' in obj:
        doc = obj
    while pos < len(so) and so[pos] in ' \n\r\t':
        pos += 1
out['audit_roster'] = dict(returncode=code, expected=len(N.EXPECTED_AUDIT_CHECKS),
                           checks_run=doc and doc.get('checks_run'),
                           checks_absent=doc and doc.get('checks_absent'),
                           passed=doc and doc.get('passed'),
                           failures=doc and doc.get('failures'),
                           new_since_recheck2=[c for c in N.EXPECTED_AUDIT_CHECKS
                                               if 'exclusion' in c or 'consumed' in c
                                               or 'verif' in c])

# ===================================================================== 5. content equality
old_c = json.loads((HERE / 'data-recheck-c.json').read_text())['shortcut_permutation_scan']
old_b = json.loads((HERE / 'data-recheck-b.json').read_text())
now_purity, now_r6 = {}, {}
for cell in N.DEV_CELL_ORDER:
    units = json.loads((S / f'dev/{cell}.json').read_text())['units']
    ans = [u['a']['answer'] for u in units]
    feats = dict(
        ending=[int(u['a']['question'][-2]) for u in units],
        start_entity=[int(u['a']['question'][1]) for u in units],
        row_count=[len([r for r in u['a']['memory'] if r]) for u in units],
        where=[u['a']['where'] for u in units],
        people_visited=[len({s[0] for s in u['a']['chain']}) for u in units],
        calls=[len(u['a']['question']) - 3 for u in units],
        distinct_people=[len({r[0] for i, r in enumerate(u['a']['memory'])
                              if r and i < u['a']['where']}) for u in units],
        index_mod_2=[u['index'] % 2 for u in units],
        question_length=[len(u['a']['question']) for u in units],
        answer_position_hint=[u['a']['memory'][u['a']['where'] - 1][0]
                              if u['a']['where'] else -1 for u in units])
    cell_out = {}
    for name, f in feats.items():
        if len(set(f)) < 2:
            cell_out[name] = None
            continue
        groups = defaultdict(list)
        for x, a in zip(f, ans):
            groups[x].append(a)
        cell_out[name] = round(sum(Counter(g).most_common(1)[0][1]
                                   for g in groups.values()) / len(ans), 3)
    now_purity[cell] = cell_out
    now_r6[cell] = dict(
        endings=sorted(set(feats['ending'])),
        answer_counts=sorted(Counter(ans).values()),
        target_ok=all(u['a']['answer'] == N.target_answer(u['index']) for u in units))
mismatch = []
for cell, row in now_purity.items():
    for name, value in row.items():
        before = old_c['per_cell'][cell][name]['purity']
        if value != before:
            mismatch.append(dict(cell=cell, feature=name, before=before, now=value))
r6_mismatch = [c for c in now_r6
               if now_r6[c]['endings'] != old_b['ruling6_stratification']['per_cell'][c]['endings']
               or now_r6[c]['answer_counts']
               != old_b['ruling6_stratification']['per_cell'][c]['answer_counts']
               or not now_r6[c]['target_ok']]
awake = IC.check_awake(S / 'awakeB')
memory = IC.check_memory(S / 'memB', awake)
old_i = json.loads((HERE / 'independent-checks-9991.json').read_text())
chunk_meta, _blocks = N.load_chunk(S / 'awakeB' / 'awake-000000-000100.pt')
out['content_equality'] = dict(
    awake_census_identical=awake['census'] == old_i['awake']['census'],
    memory_census_identical=memory['census'] == old_i['memory']['census'],
    memory_distinct_worlds=memory['distinct_world_signatures'],
    dev_panel_purity_tables_identical=not mismatch, purity_mismatches=mismatch[:8],
    dev_panel_ruling6_identical=not r6_mismatch, ruling6_mismatches=r6_mismatch,
    chunk_sha_now=N.sha(S / 'awakeB' / 'awake-000000-000100.pt'),
    chunk_sha_recheck2=json.loads((HERE / 'data-recheck-a.json').read_text())
    ['protected_api']['chunk_sha_new'],
    chunk_embeds_execution_profile='execution_profile' in chunk_meta,
    chunk_script_sha=chunk_meta['execution_profile']['script_sha256'],
    note='the .pt chunk metadata embeds execution_profile.script_sha256, so its sha256 '
         'MUST move when the script changes; content equality is therefore established '
         'through decoded content, not file hashes')

print(json.dumps({k: v for k, v in out.items()
                  if k not in ('tamper_matrix',)}, indent=1, default=str)[:4000])
print(json.dumps({k: v for k, v in out['tamper_matrix'].items() if k != 'matrix'},
                 indent=1, default=str)[:3000])
(HERE / 'data-recheck-e.json').write_text(json.dumps(out, indent=1, default=str))
