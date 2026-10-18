"""Acceptance tests for `learn_probe train --diary-data` (DRAFT): the folder whose train.jsonl is the diary prompt pool.

  python3 -m pytest domain/far/test_learn_probe_diary_data.py -v     (CPU only)

Until now build_parent_diary(data=DIARY_DATA) always read one hard-coded scratch path, because train() never passed `data`.
Reuses the stand-in world of test_learn_probe_c8 (tiny random Tool parent, F4-two rows, the guard source exported from git).
"""
import inspect
import json
import os
import sys

import pytest

from domain import mode
from domain.far import learn_probe as LP
from domain.far.test_learn_probe_c8 import world, guard_world, run   # noqa: F401  (module-scoped fixtures, reused as they are)


@pytest.fixture
def clean_guard_imports():
    """load_guard / train import `mainbrain.*` from the guard source folder and cache it; drop what this test added, or a later
    test with its own guard source (test_learn_probe_c8) trips the 'klreplay comes from guard_src' check."""
    mods, path = set(sys.modules), list(sys.path)
    yield
    for k in set(sys.modules) - mods:
        if k == 'mainbrain' or k.startswith('mainbrain.'):   # only those: dropping lazily imported torch modules breaks a re-import
            del sys.modules[k]
    sys.path[:] = path


def argv(world, out, *extra):
    return ['train', '--arm', 'LB', '--out', out, '--updates', '3', '--steps', '3', '--threads', '1', '--cells', 'l1',
            '--parent', world['parent'], '--rows', world['train'], '--probe', world['probe'], '--diary-compare', 'none', *extra]


def test_default_is_the_original_path_in_flag_and_in_train():
    seen = []
    real = LP.train
    LP.train = lambda *a, **kw: seen.append(kw)
    try:
        LP.main(['train', '--arm', 'LB', '--out', 'x', '--updates', '5'])
        LP.main(['train', '--arm', 'LB', '--out', 'x', '--updates', '5', '--diary-data', '/somewhere/else'])
    finally:
        LP.train = real
    assert seen[0]['diary_data'] == LP.DIARY_DATA, 'default flag value = DIARY_DATA (byte-identical default behaviour)'
    assert seen[1]['diary_data'] == '/somewhere/else'
    assert inspect.signature(LP.train).parameters['diary_data'].default == LP.DIARY_DATA
    assert inspect.signature(LP.build_parent_diary).parameters['data'].default == LP.DIARY_DATA


def test_diary_data_flag_makes_build_parent_diary_read_that_folder(world, guard_world, clean_guard_imports, tmp_path, monkeypatch):   # noqa: F811
    pool = tmp_path / 'diary-pool'   # not named dev / panel: mode.guard refuses those
    pool.mkdir()
    prompts = [r['prompt'] for r in world['rows'][48:]]   # valid prompts: chars inside the stand-in parent's vocabulary
    (pool / 'train.jsonl').write_text(''.join(json.dumps(dict(prompt=p)) + '\n' for p in prompts))
    opened, calls = [], []
    real_guard, real_build = mode.guard, LP.build_parent_diary

    def spy_guard(path):   # mode.guard is called on the path build_parent_diary is about to open; record it, change nothing
        opened.append(os.path.realpath(str(path)))
        return real_guard(path)

    def spy_build(*a, **kw):
        calls.append(kw.get('data'))
        return real_build(*a, **kw)
    monkeypatch.setattr(mode, 'guard', spy_guard)
    monkeypatch.setattr(LP, 'build_parent_diary', spy_build)
    monkeypatch.setattr(LP, 'FIT_N', 4)   # test only, as in the C8 test: the real 420 needs 420 joined rows
    out = str(tmp_path / 'run')
    # No --diary-cache: a cache would short-circuit the read. The random stand-in parent may answer nothing usable, so build_diary
    # can return 0 rows (the C8 test found exactly that; here the 16-prompt pool is also smaller than the check set) and the run can stop there: assert the READ PATH, not the row count.
    try:
        LP.main(argv(world, out, '--guard', 'kfsoft', '--guard-src', guard_world['src'], '--guard-every', '8',
                     '--kl-replay-rows', '4', '--kl-weight', '10', '--guard-soft', '10', '--diary-data', str(pool)))
    except ValueError as e:   # max() of an empty diary in the guard setup, downstream of the read; not what this test is about
        print('run stopped after the diary read:', e)
    assert calls == [str(pool)], calls   # train() passed the flag through as data=
    assert opened == [os.path.realpath(pool / 'train.jsonl')], opened   # and build_parent_diary opened <folder>/train.jsonl, nothing else
    assert LP.DIARY_DATA not in opened
    assert os.path.exists(os.path.join(out, 'diary-compare.json')), 'build_parent_diary got as far as writing its comparison'


def test_recorded_config_carries_the_diary_folder(world, guard_world, clean_guard_imports):   # noqa: F811
    # Here the run must get through, so the stand-in diary cache is used (as in the C8 guard test); the cache short-circuits the
    # read, but the recorded folder is still the one given. Default run: the recorded folder is DIARY_DATA.
    kw = dict(guard='kfsoft', guard_src=guard_world['src'], guard_every=8, kl_replay_rows=4, kl_weight=10, guard_soft=10,
              diary_cache=guard_world['cache'], diary_compare='none')
    rec = lambda out: json.loads(open(os.path.join(out, 'scores.jsonl')).readline())
    assert rec(run(world, 'dd_default', False, updates=5, every=5, **kw)['out'])['guard_diary_data'] == LP.DIARY_DATA
    assert rec(run(world, 'dd_given', False, updates=5, every=5, diary_data='/given/folder', **kw)['out'])['guard_diary_data'] == '/given/folder'
