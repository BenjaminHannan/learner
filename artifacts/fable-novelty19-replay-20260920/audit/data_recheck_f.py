#!/usr/bin/env python3
"""Re-check 3, part 2: the confirmation consumer -- the original R2-7 attack site."""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'scripts'))

import independent_checks as IC                        # noqa: E402
import fable_confirmation_panels as CP                 # noqa: E402
import fable_novelty19_data as N                       # noqa: E402

S = HERE / 'scratch3'
SEEDS = (9991,)
out = {}
H = 'cd' * 32

exp = S / 'exp9991'
shutil.rmtree(exp, ignore_errors=True)
exp.mkdir(parents=True)
for key, src in (('stream', S / 'awakeB'), ('memory', S / 'memB'), ('buffers', S / 'bufB')):
    (exp / N.EXPERIMENT_LAYOUT[key].format(seed=9991)).symlink_to(src.resolve())
(exp / N.EXPERIMENT_LAYOUT['dev_panels']).symlink_to((S / 'dev').resolve())
(exp / N.EXPERIMENT_LAYOUT['operator_history']).symlink_to((S / 'ophist').resolve())
good = dict(schema=N.DEV_PASSED_SCHEMA, seeds=[9991], report_sha256=H,
            dev_panels=dict(path=str((S / 'dev').resolve()),
                            manifest_sha256=N.sha(S / 'dev' / 'manifest.json')),
            awake_checkpoints={k: H for k in N.checkpoint_keys('awake', SEEDS)},
            offline_checkpoints={k: H for k in N.checkpoint_keys('offline', SEEDS)})
(exp / 'DEV-PASSED.json').write_text(json.dumps(good))

CELLS = ['N-c4-p6', 'L-c6-prac']


def build(dest, n=32):
    shutil.rmtree(dest, ignore_errors=True)
    return N.build_dev_panels(dest, n=n, namespace=N.NS_CONFIRM,
                              cells={c: N.DEV_CELLS[c] for c in CELLS}, cell_order=CELLS,
                              confirmation=True, experiment=exp, seeds=SEEDS, progress=False)


# ---- 1. clean build: provenance and world exclusion ------------------------------------
build(S / 'confirm')
man = json.loads((S / 'confirm' / 'manifest.json').read_text())
te = man['training_exclusion']
sources = [{k: v for k, v in s.items()
            if k in ('name', 'questions', 'worlds', 'questions_sha256', 'worlds_sha256',
                     'verified', 'manifest')} for s in te['sources']]


def sigs(folder, cells):
    got = set()
    for cell in cells:
        for unit in json.loads((Path(folder) / f'{cell}.json').read_text())['units']:
            for side in ['a'] + (['b'] if unit['kind'] == 'pair' else []):
                u = unit[side]
                got.add(CP.world_signature(CP.fact_tuples(
                    [r for i, r in enumerate(u['memory']) if r and i < u['where']])))
    return got


train = set()
for folder in (S / 'awakeB', S / 'memB', S / 'bufB'):
    for path in sorted(Path(folder).glob('*.pt')):
        _meta, blocks = IC.load_blocks(path)
        for block in blocks:
            stories = IC.my_stories(block)
            for owner in set(block['owner'].tolist()):
                train.add(CP.world_signature(CP.fact_tuples(
                    [r for r in stories[owner] if r])))
conf = sigs(S / 'confirm', CELLS)
dev = sigs(S / 'dev', N.DEV_CELL_ORDER)
out['confirmation_clean'] = dict(
    confirmation_worlds=len(conf), training_worlds=len(train), dev_worlds=len(dev),
    overlap_with_training=len(conf & train), overlap_with_development=len(conf & dev),
    union_applied=dict(questions=te['questions'], worlds=te['worlds']),
    sources=sources,
    every_source_carries_a_verified_sha=all(
        s.get('verified') is True and (s.get('worlds_sha256') or s.get('questions_sha256'))
        for s in sources),
    consumed_exclusions_present='consumed_exclusions' in man,
    operator_history=man['operator_history']['world_union_sha256'],
    dev_passed=man.get('dev_passed', {}).get('sha256'))

# ---- 2. the same five attacks, against the CONFIRMATION consumer ------------------------
HEXA = 'a' * 64
cases = {}
for target in ('awakeB/forbidden-worlds.json', 'bufB/forbidden-worlds.json',
               'ophist/forbidden-worlds.json', 'dev/forbidden-semantics.json'):
    path = S / target
    original = path.read_bytes()
    doc = json.loads(original)
    n = len(doc)
    variants = [('truncated', sorted(doc[:5])),
                ('same-count-tampered', sorted(set(doc[:-1] + [HEXA]))),
                ('duplicate-padded', sorted(doc[:5]) + [doc[5]] * (n - 5)),
                ('unsorted', list(reversed(sorted(doc)))),
                ('emptied', [])]
    per = {}
    for label, value in variants:
        path.write_bytes(json.dumps(value).encode())
        try:
            build(S / 'confirm-atk', n=8)
            per[label] = 'ACCEPTED'
        except BaseException as exc:                                # noqa: BLE001
            per[label] = f'{type(exc).__name__}: {str(exc)[-110:]}'
        finally:
            shutil.rmtree(S / 'confirm-atk', ignore_errors=True)
    path.write_bytes(original)
    cases[target] = per
out['confirmation_attacks'] = dict(
    cases=cases,
    total=sum(len(v) for v in cases.values()),
    all_refused=all(v != 'ACCEPTED' for per in cases.values() for v in per.values()),
    accepted=[(t, k) for t, per in cases.items() for k, v in per.items()
              if v == 'ACCEPTED'])

# control: the clean build still works after restoring every file
try:
    build(S / 'confirm-control', n=8)
    out['confirmation_attacks']['control_after_restore'] = 'builds'
except BaseException as exc:                                        # noqa: BLE001
    out['confirmation_attacks']['control_after_restore'] = f'{type(exc).__name__}: {exc}'[:150]
shutil.rmtree(S / 'confirm-control', ignore_errors=True)

print(json.dumps(out, indent=1, default=str)[:6000])
(HERE / 'data-recheck-f.json').write_text(json.dumps(out, indent=1, default=str))
