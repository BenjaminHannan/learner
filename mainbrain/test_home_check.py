"""Tests for home_sample, home_check (fingerprint and reuse helpers) and home_compare.

  python -m mainbrain.test_home_check
"""
import json
import os
import random
import tempfile

import torch

from mainbrain import home_check, home_compare, home_sample

torch.set_num_threads(1)


def write_jsonl(path, rows):
    with open(path, 'w') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')


def test_sample():
    d = tempfile.mkdtemp()
    data = os.path.join(d, 'data')
    os.makedirs(os.path.join(data, 'dev'))
    train = []
    for fam in ('a', 'b', 'c'):
        for i in range(10):
            train.append(dict(id=f'{fam}{i}', family=fam, prompt=f'q {fam} {i}'))
    train.append(dict(id='dup', family='a', prompt='q a 0'))
    train.append(dict(id='bad', family='a', prompt='q a é'))
    train.append(dict(id='long', family='a', prompt='x' * 300))
    write_jsonl(os.path.join(data, 'train.jsonl'), train)
    write_jsonl(os.path.join(data, 'dev', 'in_dist.jsonl'), [dict(id='d', family='a', prompt='q a 9')])
    chars = sorted({c for r in train[:30] for c in r['prompt']})
    parents = []
    for i in range(2):
        p = os.path.join(d, f'p{i}.pt')
        torch.save(dict(chars=''.join(chars) + ('Z' if i else '')), p)
        parents.append(p)
    runs = []
    for seed, scanned in ((200, 6), (201, 9)):
        r = os.path.join(d, f'sheet-s{seed}-x')
        os.makedirs(r)
        with open(os.path.join(r, 'log.jsonl'), 'w') as f:
            f.write(json.dumps(dict(event='start', seed=seed, constants=dict(replay_fresh=False))) + '\n')
            f.write(json.dumps(dict(event='diary', scanned=scanned)) + '\n')
        runs.append(r)
    out = os.path.join(d, 'out')
    home_sample.main(['--data', data, '--parents', ','.join(parents), '--runs', ','.join(runs), '--out-dir', out, '--per-family', '4', '--seed', 's'])
    vch = set(chars)
    pool = list(dict.fromkeys(r['prompt'] for r in train if len(r['prompt']) <= 208 and set(r['prompt']) <= vch))
    assert len(pool) == 30
    excl = {'q a 9'}
    for seed, scanned in ((200, 6), (201, 9)):
        p = list(pool)
        random.Random(f'{seed}-diary').shuffle(p)
        excl |= set(p[:scanned])
    h1 = [json.loads(l) for l in open(os.path.join(out, 'home-H1.jsonl'))]
    h2 = [json.loads(l) for l in open(os.path.join(out, 'home-H2.jsonl'))]
    h12 = [json.loads(l) for l in open(os.path.join(out, 'home-H12.jsonl'))]
    assert h12 == h1 + h2
    assert all(r['half'] == 'H1' for r in h1) and all(r['half'] == 'H2' for r in h2)
    got = [r['prompt'] for r in h12]
    assert len(set(got)) == len(got) and not set(got) & excl
    assert not {'q a é', 'x' * 300} & set(got)
    for fam in 'abc':
        n1 = sum(r['family'] == fam for r in h1)
        n2 = sum(r['family'] == fam for r in h2)
        avail = sum(1 for p in pool if p.split()[1] == fam and p not in excl)
        assert n1 + n2 == min(4, avail) and n1 == (n1 + n2) // 2, (fam, n1, n2, avail)
    man = json.load(open(os.path.join(out, 'home-manifest.json')))
    assert man['scanned_per_seed'] == {'200': 6, '201': 9}
    assert man['files']['home-H12.jsonl']['sha256'] == home_sample.sha256_file(os.path.join(out, 'home-H12.jsonl'))
    with open(os.path.join(runs[0], 'log.jsonl'), 'w') as f:
        f.write(json.dumps(dict(event='start', seed=200, constants=dict(replay_fresh=True))) + '\n')
        f.write(json.dumps(dict(event='diary', scanned=6)) + '\n')
    try:
        home_sample.main(['--data', data, '--parents', parents[0], '--runs', runs[0], '--out-dir', out])
        raise AssertionError('replay_fresh should stop')
    except SystemExit as e:
        assert 'replay_fresh' in str(e)
    assert home_sample.run_info(runs[1])[0] == 201
    print('sample ok')


def test_fingerprint():
    w = {'a': torch.arange(6, dtype=torch.float32).reshape(2, 3), 'b': torch.ones(3, dtype=torch.bfloat16), 's': torch.tensor(2.0)}
    ck1 = dict(model=w, name='x', step=1)
    ck2 = dict(model={k: v.clone() for k, v in w.items()}, name='x', step=99)
    assert home_check.fingerprint(ck1) == home_check.fingerprint(ck2)
    w3 = {k: v.clone() for k, v in w.items()}
    w3['a'][0, 0] += 1
    assert home_check.fingerprint(dict(model=w3)) != home_check.fingerprint(ck1)
    d = tempfile.mkdtemp()
    torch.save(ck1, os.path.join(d, 'c.pt'))
    assert home_check.file_fingerprint(os.path.join(d, 'c.pt')) == home_check.fingerprint(ck1)
    known = [('parent', 'p'), (1, 'f1'), (2, 'f2')]
    assert home_check.find_reuse('p', known) == 'parent'
    assert home_check.find_reuse('f2', known) == 2
    assert home_check.find_reuse('zz', known) is None
    assert home_check.hit_string([1, 0, True]) == '101'
    print('fingerprint ok')


def hits(rows, zero_family=None, zero_n=0, flip_all=0):
    h = [1] * len(rows)
    seen = 0
    for i, r in enumerate(rows):
        if r['family'] == zero_family and seen < zero_n:
            h[i] = 0
            seen += 1
    return ''.join(map(str, h))


def test_compare():
    rows = []
    for half in ('H1', 'H2'):
        for fam in ('f', 'g'):
            for i in range(40):
                rows.append(dict(id=f'{half}{fam}{i}', family=fam, half=half, prompt=f'{half}{fam}{i}'))
    ph = '1' * len(rows)
    ix_f_h1 = [i for i, r in enumerate(rows) if r['half'] == 'H1' and r['family'] == 'f']
    bad = list(ph)
    for i in ix_f_h1[:10]:
        bad[i] = '0'
    bad = ''.join(bad)
    v = home_compare.home_verdicts(ph, bad, rows)
    assert v['H1']['fired'] == ['f'] and v['H1']['bad'] and abs(v['H1']['top']['f']['drop'] - 25.0) < 1e-9
    assert v['H2']['fired'] == [] and not v['H2']['bad'] and v['H2']['drop'] == 0
    assert v['H12']['fired'] == ['f'] and abs(v['H12']['top']['f']['drop'] - 12.5) < 1e-9
    assert v['H12']['bad'] and abs(v['H12']['drop'] - 100 * 10 / 160) < 1e-9
    spread = list(ph)
    for fam_i, (f, n) in enumerate((('f', 1), ('g', 1))):
        for i in [j for j, r in enumerate(rows) if r['family'] == f and r['half'] == 'H1'][:n]:
            spread[i] = '0'
    sp = home_compare.home_verdicts(ph, ''.join(spread), rows)
    assert sp['H1']['fired'] == [] and abs(sp['H1']['drop'] - 2.5) < 1e-9 and sp['H1']['bad'] and not sp['H2']['bad']
    one = list(ph)
    one[ix_f_h1[0]] = '0'
    ov = home_compare.home_verdicts(ph, ''.join(one), rows)
    assert not ov['H1']['bad'] and ov['H1']['drop'] == 1.25

    d = tempfile.mkdtemp()
    rp = os.path.join(d, 'rows.jsonl')
    write_jsonl(rp, rows)
    ids = [r['id'] for r in rows]

    def home(nights):
        return dict(ids=ids, parent=dict(hits=ph), nights=nights)

    def hn(h, reused=None):
        return dict(hits=h, reused_from=reused)

    def dev(drops):
        return dict(nights={str(k): dict(in_dist_drop=dr, fired=fi) for k, (dr, fi) in drops.items()})

    spec = []
    # run A: DEV fails at night 2 (family fires); home sees it at night 3 (caught, within +1); night 4 repeats night 3 (reused)
    a_dev = dev({1: (0.0, []), 2: (6.0, ['f']), 3: (7.0, ['f']), 4: (7.0, ['f'])})
    a_home = home({'1': hn(ph), '2': hn(ph), '3': hn(bad), '4': hn(bad, 3)})
    # run B: DEV good at nights 1,2; home fires at night 2 (false alarm)
    b_dev = dev({1: (0.0, []), 2: (0.5, [])})
    b_home = home({'1': hn(ph), '2': hn(bad)})
    # run C: DEV fails at night 1, home never (missed)
    c_dev = dev({1: (3.0, [])})
    c_home = home({'1': hn(ph)})
    for name, dv, hm in (('A', a_dev, a_home), ('B', b_dev, b_home), ('C', c_dev, c_home)):
        for kind, obj in (('dev', dv), ('home', hm)):
            json.dump(obj, open(os.path.join(d, f'{name}-{kind}.json'), 'w'))
        spec.append(dict(name=name, dev_summary=[os.path.join(d, f'{name}-dev.json')], home=os.path.join(d, f'{name}-home.json'), rows=rp))
    json.dump([dict(nights={'1': dict(in_dist_drop=9.0, fired=['f'])})], open(os.path.join(d, 'x.json'), 'w'))
    assert home_compare.load_dev([os.path.join(d, 'A-dev.json'), os.path.join(d, 'B-dev.json')])['1']['in_dist_drop'] == 0.0
    sp_path, out = os.path.join(d, 'spec.json'), os.path.join(d, 'out.json')
    json.dump(spec, open(sp_path, 'w'))
    home_compare.main(['--spec', sp_path, '--out', out])
    res = json.load(open(out))
    A, B, C = res['runs']['A'], res['runs']['B'], res['runs']['C']
    assert A['dev_first_bad'] == 2 and A['H1_first_bad'] == 3 and A['H2_first_bad'] is None and A['H12_first_bad'] == 3
    assert A['dev_fired'] == ['f'] and A['H1_fired'] == ['f'] and A['H2_fired'] == []
    assert B['dev_first_bad'] is None and B['H12_first_bad'] == 2 and C['dev_first_bad'] == 1 and C['H12_first_bad'] is None
    o = res['overall']
    assert o['H1']['dev_failing_runs'] == 2 and o['H1']['caught'] == 1 and o['H2']['caught'] == 0 and o['H12']['caught'] == 1
    assert o['H1']['pairs'] == 1 and o['H1']['pairs_matched'] == 1 and o['H2']['pair_match_rate'] == 0.0
    assert o['H1']['dev_good_nights'] == 3 and o['H1']['false_alarms'] == 1
    assert o['H1']['unique_nights'] == 6
    assert abs(home_compare.pearson([1, 2, 3], [2, 4, 6]) - 1) < 1e-9 and home_compare.pearson([1, 1], [1, 2]) is None
    assert o['H1_vs_H2']['unique_nights'] == 6
    print('compare ok')


if __name__ == '__main__':
    test_sample()
    test_fingerprint()
    test_compare()
    print('all ok')
