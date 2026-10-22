"""python3 -m pytest creative/tests/test_make_c2c.py   (CPU, about 20 s; no model)
Bid C draft, creative/make_c2c.py. Every generation here uses a test seed (never 93801) and a temp dir; creative/data/c2c is never written."""
import hashlib, json, os, tempfile
import pytest
from creative import make_c2c as M, rules_real as R
from creative.c2b import load_test

SMALL = dict(affine=6, square=6, sq_plus=5, last_digit=5, double_add=5)


def test_seed_rule():
    assert (M.SEED, M.FALLBACK_SEED) == (93801, 93802)
    assert M.resolve_seed(93801, {0}) == 93801
    assert M.resolve_seed(93801, {0, 93801}) == 93802
    for used in ({93801, 93802}, {7}):
        with pytest.raises(SystemExit, match='REFUSED'):
            M.resolve_seed(93801 if 93801 in used else 7, used)
    assert M.manifest_seeds({'a': {'seed': 5}, 'b': [{'split_seed': 6}, {'seeds': [7, 8]}], 'n': 9}) == {5, 6, 7, 8}
    man = json.load(open('creative/data/c2/MANIFEST.json'))
    assert M.manifest_seeds(man) == set() and M.resolve_seed(93801, M.manifest_seeds(man) | set(M.SEEDS_USED_BY_C2)) == 93801      # C2's manifest records no seed


def test_c2_is_seed_0_of_this_generator():
    """Why SEEDS_USED_BY_C2 = (0,): redrawing C2 with rules_real.make_questions at seed 0 (usable instances from the manifest) reproduces every split's sha256."""
    man, c2 = M.load_c2()
    use = M.usable_params(man)
    use.update({k: [p for p in R.PARAMS[k]] for k in R.PRACTISED})
    avoid, got = set(), {}
    got['warm'] = R.make_questions(R.PRACTISED, use, R.SPLITS['warm'], 0, 'warm', avoid)
    for name in ('dev', 'pool', 'test', 'labelled'):
        got[name] = R.make_questions(R.HELD_OUT, use, R.SPLITS[name], 0, name, avoid)
    for name, rows in got.items():
        assert rows == c2[name], name


def test_usable_params_match_the_manifest():
    man, _ = M.load_c2()
    use = M.usable_params(man)
    assert {k: len(v) for k, v in use.items()} == {'affine': 49, 'square': 1, 'sq_plus': 7, 'last_digit': 1, 'double_add': 7}


def test_small_draw_properties():
    with tempfile.TemporaryDirectory() as d:
        out = M.make(os.path.join(d, 'c2c'), seed=4242, counts=SMALL)
        path = os.path.join(d, 'c2c', 'test.jsonl')
        rows = [json.loads(l) for l in open(path)]
        assert out['test']['n'] == len(rows) == 27 and out['test']['kinds'] == dict(sorted(SMALL.items())) and out['_spec']['seed'] == 4242
        assert [r['kind'] for r in rows[:6]] == ['affine', 'square', 'sq_plus', 'last_digit', 'double_add', 'affine'] and rows[0]['id'] == 'c2c:test:00000'
        assert out['_spec']['disjoint_from_c2']['prompt_overlap'] == out['_spec']['disjoint_from_c2']['key_overlap'] == 0
        assert out['_spec']['length_check']['answers_over_8_chars'] == out['_spec']['length_check']['prompts_over_208_chars'] == 0
        assert out['_spec']['per_kind_counts_from'] == 'override' and out['_spec']['c2_seeds_checked'] == [0]
        man = json.load(open(os.path.join(d, 'c2c', 'MANIFEST.json')))
        assert man == json.loads(json.dumps(out)) and set(man['_spec']['c2_split_sha256']) == set(R.SPLITS)
        for r in rows:                                                        # the same row form and the same answer key as C2
            f = R.fn(r['kind'], tuple(r['params']))
            assert r['family'] == 'fewshot_number_rule' and r['real'] and r['answer'] == str(f(int(r['prompt'].rsplit('Now ', 1)[1].split(' ')[0])))
        c2_prompts = {r['prompt'] for name in R.SPLITS for r in R.load_split('creative/data/c2', name)}
        assert not c2_prompts & {r['prompt'] for r in rows}
        r2, info = load_test(path)                                            # creative.c2b --test reads it, sha256 checked against the MANIFEST
        assert len(r2) == 27 and info['n'] == 27
        assert M.check(os.path.join(d, 'c2c'))['sha256'] == out['test']['sha256']
        with tempfile.TemporaryDirectory() as d2:                             # deterministic per seed, different across seeds
            again = M.make(os.path.join(d2, 'a'), seed=4242, counts=SMALL)
            other = M.make(os.path.join(d2, 'b'), seed=4243, counts=SMALL)
            assert again['test']['sha256'] == out['test']['sha256'] and other['test']['sha256'] != out['test']['sha256']


def test_refuses_to_overwrite():
    with tempfile.TemporaryDirectory() as d:
        M.make(d, seed=4242, counts=SMALL)
        before = open(os.path.join(d, 'test.jsonl'), 'rb').read()
        with pytest.raises(SystemExit, match='REFUSED'):
            M.make(d, seed=4244, counts=SMALL)
        assert open(os.path.join(d, 'test.jsonl'), 'rb').read() == before
        os.remove(os.path.join(d, 'test.jsonl'))                              # only the manifest is left: still refused
        with pytest.raises(SystemExit, match='REFUSED'):
            M.make(d, seed=4244, counts=SMALL)
        assert not os.path.exists(os.path.join(d, 'test.jsonl'))


def test_prompt_collision_is_dropped_and_redrawn():
    man, c2 = M.load_c2()
    use = M.usable_params(man)
    rows, dropped = M.draw(use, SMALL, 4242, c2)
    assert dropped == 0 and len(rows) == 27
    twin = dict(rows[0], kind='zzz', params=[99])                             # same prompt, a different (kind, params) key
    rows2, dropped2 = M.draw(use, SMALL, 4242, dict(c2, extra=[twin]))
    assert dropped2 >= 1 and len(rows2) == 27 and rows[0]['prompt'] not in {r['prompt'] for r in rows2}
    assert {k: sum(r['kind'] == k for r in rows2) for k in SMALL} == SMALL and len({r['prompt'] for r in rows2}) == 27


def test_length_and_overlap_reports():
    rows = [dict(prompt='p' * 208, answer='1' * 8), dict(prompt='p' * 209, answer='1' * 9), dict(prompt='q', answer='12')]
    rep = M.length_report(rows)
    assert rep == dict(rows=3, max_answer_chars=9, answers_over_8_chars=1, max_prompt_chars=209, prompts_over_208_chars=1)
    c2 = {'dev': R.load_split('creative/data/c2', 'dev')}
    planted = [dict(c2['dev'][0]), dict(c2['dev'][0], id='x')]
    assert M.overlap_report(planted, c2) == dict(c2_rows=256, prompt_overlap=2, key_overlap=2, duplicate_prompts_within=1)


def test_full_size_matches_the_c2_test_counts():
    with tempfile.TemporaryDirectory() as d:
        M.main(['--out', os.path.join(d, 'c2c'), '--seed', '4242'])
        man = json.load(open(os.path.join(d, 'c2c', 'MANIFEST.json')))
        c2 = json.load(open('creative/data/c2/MANIFEST.json'))
        assert man['test']['n'] == 512 and man['test']['kinds'] == c2['test']['kinds'] == dict(affine=103, double_add=102, last_digit=102, sq_plus=102, square=103)
        assert man['_spec']['disjoint_from_c2']['prompt_overlap'] == 0 and man['_spec']['length_check']['answers_over_8_chars'] == 0
        assert M.check(os.path.join(d, 'c2c'))['n'] == 512
    assert not os.path.exists('creative/data/c2c')


def test_check_exits_nonzero_on_overlap_or_long_rows(capsys):
    """N9: --check is a gate, not a printout: any overlap with C2 or any row over the old caps -> exit 1."""
    with tempfile.TemporaryDirectory() as d:
        M.make(d, seed=4242, counts=SMALL)
        assert M.main(['--check', d]) is None and M.check(d)['problems'] == []
        rows = [json.loads(l) for l in open(os.path.join(d, 'test.jsonl'))]
        c2 = R.load_split('creative/data/c2', 'dev')[0]
        def rewrite(new_rows):
            with open(os.path.join(d, 'test.jsonl'), 'w') as f:
                f.write(''.join(json.dumps(r, sort_keys=True) + '\n' for r in new_rows))
            man = json.load(open(os.path.join(d, 'MANIFEST.json')))
            man['test']['sha256'] = hashlib.sha256(open(os.path.join(d, 'test.jsonl'), 'rb').read()).hexdigest()
            json.dump(man, open(os.path.join(d, 'MANIFEST.json'), 'w'))
        rewrite(rows[:-1] + [dict(c2, id='c2c:test:99999')])                           # a C2 question smuggled in
        with pytest.raises(SystemExit) as e:
            M.main(['--check', d])
        assert e.value.code == 1 and any(x.startswith('prompt_overlap') for x in M.check(d)['problems']) and 'key_overlap' in capsys.readouterr().err
        rewrite(rows[:-1] + [dict(rows[-1], answer='1' * 9)])
        with pytest.raises(SystemExit) as e:
            M.main(['--check', d])
        assert e.value.code == 1 and M.check(d)['problems'] == ['answers_over_8_chars = 1']
        rewrite(rows[:-1] + [dict(rows[-1], prompt='Examples: ' + '; '.join(['1 -> 1'] * 40) + '. Now 5 -> ?')])
        assert M.check(d)['problems'] == ['prompts_over_208_chars = 1']


def test_make_refuses_with_explicit_raises_not_asserts(monkeypatch):
    """N9: the correctness guards in make() must survive python -O: SystemExit, nothing written."""
    monkeypatch.setattr(M, 'overlap_report', lambda rows, c2: dict(c2_rows=0, prompt_overlap=1, key_overlap=0, duplicate_prompts_within=0))
    with tempfile.TemporaryDirectory() as d:
        with pytest.raises(SystemExit, match='REFUSED.*overlaps'):
            M.make(os.path.join(d, 'c2c'), seed=4242, counts=SMALL)
        assert not os.path.exists(os.path.join(d, 'c2c'))
    man, c2 = M.load_c2()
    use = M.usable_params(man)
    with pytest.raises(SystemExit, match='cannot fill'):
        M.draw(use, dict(square=10), 4242, c2, max_rounds=0)
    bad = json.loads(json.dumps(man))
    bad['_spec']['usable_counts']['affine'] += 1
    with pytest.raises(SystemExit, match='usable parameter sets'):
        M.usable_params(bad)
    bad = json.loads(json.dumps(man))
    bad['_spec']['kind_seal'] = 'x'
    with pytest.raises(SystemExit, match='kind rules changed'):
        M.usable_params(bad)
