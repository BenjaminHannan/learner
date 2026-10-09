"""python3 -m custom_io.tests.test_pts   (CPU, about a minute; no data files, no Gemma: eg_embed is only counted, never run)
B3 steps-for-all (PTS): the plain step arm trains on '; '.join(steps) + ' # ' + answer for EVERY row that has steps (no family gate, no cut at CAP + 12).
  a  all_steps off = the code at HEAD 20b72089d9 bit for bit: every parameter, a loss, the target ids, a decode, and the 3M sizes / train_args of the old arms
     (plain_tf_steps, plain_tf_steps_g, plain_lm). The base tree is a git archive extracted to a temp dir (PTS_TEST_TMP picks the parent) and removed afterwards.
  b  a '#' inside a step scores right: the answer is read after the LAST '#', also through a trained model's generate.
  c  a long all-steps target is not truncated: plain_tf_steps AND plain_tf_steps_g keep it whole, loss() runs on it, and it is decoded past the default MAX_NEW.
  d  PTS 3M trained params == 4,022,440 with caps_b3.json applied (= PT = G2C3); under its own pin caps_b3s.json PTS == PT and sits exactly 6 x d_model above G2C3.
  e  the job's caps report refuses any row longer than caps plain_target (also from a cached caps.json), and PTS never runs beside the B3 arms.
caps.apply mutates module globals, so everything that applies caps runs in a subprocess."""
import json, os, shutil, subprocess, sys, tempfile, types
import torch
from custom_io.data import CharVocab, EOS, PAD, N_SPECIAL
from custom_io.g8a.configs import PLAIN_BAND
from custom_io.models import build
from custom_io.models import plain_tf_steps as pts
from custom_io.models.plain_tf_steps import final_answer, target_text_all

BASE = '20b72089d9223d38198295e55140e3ec964ead2c'      # the last commit that touched custom_io before the PTS edits (HEAD's custom_io is identical to it); the default-off path must equal it
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
G8A = os.path.join(ROOT, 'custom_io', 'g8a')
V = CharVocab.build([])
G2C3 = 4_022_440                                        # the plain 3M control at caps_b3 (configs.G2C3)


def rows():
    long_steps = ['%d + %d = %d' % (i, i + 1, 2 * i + 1) for i in range(12)]          # about 140 chars, over CAP (64)
    return [
        dict(family='story_addsub', prompt='Ann has 3 apples and buys 4 more. How many now?', steps=['3 + 4 = 7'], answer='7'),
        dict(family='cloze_steps', prompt='Which is bigger, 5 or 9?', steps=['9 > 5'], answer='9'),       # not a STEP_FAMILIES family
        dict(family='story_addsub', prompt='Long chain of sums.', steps=long_steps, answer='42'),          # over CAP: the old path falls back to the answer
        dict(family='plain', prompt='Say the word.', answer='q' * 90),                                      # no steps; answer over CAP + 12: the old path cuts it
        dict(family='arith_bare', prompt='7 # 2 =', steps=['7 # 2 = 5 # odd'], answer='5'),                 # a '#' inside a step
    ]


def make_batch(rs):
    enc = [V.encode(r['prompt']) for r in rs]
    T = max(map(len, enc))
    ids = torch.full((len(rs), T), PAD, dtype=torch.long)
    mask = torch.zeros((len(rs), T), dtype=torch.bool)
    for i, e in enumerate(enc):
        ids[i, :len(e)] = torch.tensor(e)
        mask[i, :len(e)] = True
    return {'rows': rs, 'prompt_ids': ids, 'prompt_mask': mask}


# (a) run in a tree (the base archive or the working tree) with the default config: every parameter, a loss, the target ids and a decode of the three plain
# models, and the 3M sizes / train_args of the old arms
PARITY = r'''
import json, sys, torch
from custom_io.data import CharVocab, PAD
from custom_io.models import build
from custom_io.g8a import configs as C
rows = json.load(open(sys.argv[2]))
V = CharVocab.build([])
enc = [V.encode(r['prompt']) for r in rows]
T = max(map(len, enc))
ids = torch.full((len(rows), T), PAD, dtype=torch.long)
mask = torch.zeros((len(rows), T), dtype=torch.bool)
for i, e in enumerate(enc):
    ids[i, :len(e)] = torch.tensor(e)
    mask[i, :len(e)] = True
batch = {'rows': rows, 'prompt_ids': ids, 'prompt_mask': mask}
out = {}
for name in ('plain_tf_steps', 'plain_tf_steps_g', 'plain_lm'):
    torch.manual_seed(0)
    m = build(name, V, d_model=64, n_layers=2, n_heads=4)
    out[name + '_loss'] = m.loss(batch).item()
    out[name + '_sd'] = {k: v.clone() for k, v in m.state_dict().items()}
    if name != 'plain_lm':
        out[name + '_targets'] = [t.clone() for t in m._targets(batch)]
        out[name + '_gen'] = m.eval().generate(batch)
cfgs, counts = C.sizes('3M')
out['sizes'] = json.dumps([cfgs, counts, list(C.ARMS)], sort_keys=True)
out['train_args'] = json.dumps([C.train_args('3M', arm, 1, 10, '/x') for arm in C.ARMS])
torch.save(out, sys.argv[1])
'''


def test_off_is_head():
    rs = rows()
    with tempfile.TemporaryDirectory(prefix='ptsbase-', dir=os.environ.get('PTS_TEST_TMP')) as d:        # removed on exit, also when an assertion fails
        ref = os.path.join(d, 'ref')
        os.makedirs(ref)
        rows_json = os.path.join(d, 'rows.json')
        json.dump(rs, open(rows_json, 'w'))
        arc = subprocess.Popen(['git', 'archive', BASE, 'custom_io'], cwd=ROOT, stdout=subprocess.PIPE)
        subprocess.check_call(['tar', '-x', '-C', ref], stdin=arc.stdout)
        assert arc.wait() == 0
        res = {}
        for tag, tree in (('ref', ref), ('new', ROOT)):
            subprocess.check_call([sys.executable, '-c', PARITY, os.path.join(d, tag + '.pt'), rows_json], cwd=tree,
                                  env=dict(os.environ, PYTHONPATH=tree, OMP_NUM_THREADS='1'))
            res[tag] = torch.load(os.path.join(d, tag + '.pt'))
        a, b = res['ref'], res['new']
        assert a.keys() == b.keys()
        for k in a:
            if k.endswith('_sd'):
                assert a[k].keys() == b[k].keys() and all(torch.equal(a[k][n], b[k][n]) for n in a[k]), k
            elif k.endswith('_targets'):
                assert all(torch.equal(x, y) for x, y in zip(a[k], b[k])), k
            else:
                assert a[k] == b[k], (k, a[k], b[k])
    assert not os.path.exists(d)
    # the switch on changes the loss on this batch, and not the weights (same seed, no RNG draw)
    batch = make_batch(rs)
    torch.manual_seed(0)
    m_off = build('plain_tf_steps_g', V, d_model=64, n_layers=2, n_heads=4)
    torch.manual_seed(0)
    m_on = build('plain_tf_steps_g', V, d_model=64, n_layers=2, n_heads=4, all_steps=True)
    assert all(torch.equal(x, y) for x, y in zip(m_off.state_dict().values(), m_on.state_dict().values()))
    lo, lon = m_off.loss(batch).item(), m_on.loss(batch).item()
    assert abs(lo - lon) > 1e-6, (lo, lon)
    try:
        build('plain_lm', V, d_model=64, n_layers=2, n_heads=4, all_steps=True)
        raise SystemExit('plain_lm accepted all_steps')
    except AssertionError:
        pass
    print('ok all_steps off = HEAD %s: every parameter, loss, target ids, decode (plain_tf_steps, plain_tf_steps_g, plain_lm) and the 3M sizes / train_args '
          'of B2, PT, LLM are equal; on: loss %.4f vs off %.4f, same weights; plain_lm refuses the switch' % (BASE[:10], lon, lo))


# (b)
def test_scoring():
    from custom_io.g8a import caps as CP
    for r in rows():
        assert final_answer(target_text_all(r)) == r['answer'], (r, target_text_all(r))
        assert CP.measure(r, progs=False, all_steps=True)['plain_target'] == len(target_text_all(r)), r        # the caps report measures the string that is trained
    t = target_text_all(rows()[4])
    assert t.count('#') == 3 and final_answer(t) == '5', t
    assert final_answer('1 # 2 # 3 # 9') == '9' and final_answer('no hash 4') == 'no hash 4'
    print('ok scoring: the answer is read after the LAST #, with a # inside a step; caps.measure(all_steps) = len(target_text_all) on every row')


# (c)
def test_no_truncation():
    steps = ['%d + %d = %d' % (i, i + 1, 2 * i + 1) for i in range(22)]              # about 290 chars: over CAP + 12
    row = dict(family='story_addsub', prompt='Long.', steps=steps, answer='42')
    t = target_text_all(row)
    assert len(t) > pts.CAP + 12 + 100, len(t)
    for name in ('plain_tf_steps', 'plain_tf_steps_g'):                                 # PlainTFSteps and the PTS class PlainStepsG
        m_on = build(name, V, d_model=64, n_layers=1, n_heads=4, all_steps=True)
        ids, am = m_on._targets(make_batch([row]))
        got = ''.join(V.itos[x] for x in ids[0].tolist() if x >= N_SPECIAL)
        assert got == t, (name, got[:60], t[:60])
        assert int(am[0].sum()) == len(t) + 1 and ids[0, len(t)].item() == EOS, (name, int(am[0].sum()))
        m_off = build(name, V, d_model=64, n_layers=1, n_heads=4)
        long_ans = dict(family='plain', prompt='Long.', answer='q' * 120)             # no steps: the default path cuts the answer at CAP + 12
        assert m_off._targets(make_batch([long_ans]))[0].shape[1] == pts.CAP + 12 + 1
        mid = dict(family='cloze_steps', prompt='Mid.', steps=steps[:11], answer='9')       # about 150 chars: over CAP + 12 and it fits the position table
        tm = target_text_all(mid)
        assert pts.CAP + 12 < len(tm) < 200 and 2 + 4 + len(tm) + 1 < pts.MAX_POS, len(tm)
        ids, am = m_on._targets(make_batch([mid]))
        assert int(am[0].sum()) == len(tm) + 1, (name, int(am[0].sum()))
        assert torch.isfinite(m_on.loss(make_batch([mid]))), name                      # loss() sees the whole target (the old path would have fallen back to '9')
    print('ok no truncation: a %d-char all-steps target is kept whole (+EOS) by plain_tf_steps and plain_tf_steps_g, loss() runs on a %d-char one; the default path still '
          'cuts at CAP + 12' % (len(t), len(tm)))


def gen_rows():
    """Run in a subprocess: caps_b3s applied; a tiny PTS model memorises three rows (a '#' inside a step, a target past the default decode limit, no steps)
    and writes them back with generate()."""
    from custom_io.g8a import caps as CP
    default_new = pts.MAX_NEW
    caps = json.load(open(os.path.join(G8A, 'caps_b3s.json')))
    CP.apply(caps)
    long_steps = ['%d + %d = %d' % (i, i + 1, 2 * i + 1) for i in range(1, 10)]
    rs = [dict(family='arith_bare', prompt='Odd or even?', steps=['7 # 2 = 5 # odd'], answer='5'),
          dict(family='cloze_steps', prompt='Add the run.', steps=long_steps, answer='42'),
          dict(family='copy_word', prompt='Which colour?', answer='blue')]
    longest = max(len(target_text_all(r)) for r in rs)
    assert default_new < longest + 1 <= caps['plain_target'] + 1, (default_new, longest, caps['plain_target'])
    torch.manual_seed(0)
    m = build('plain_tf_steps_g', V, d_model=64, n_layers=2, n_heads=4, all_steps=True)
    opt = torch.optim.AdamW(m.parameters(), lr=3e-3)
    batch = make_batch(rs)
    first = last = None
    for step in range(400):
        opt.zero_grad()
        loss = m.loss(batch)
        loss.backward()
        opt.step()
        first = loss.item() if first is None else first
        last = loss.item()
    got = m.eval().generate(batch)
    return dict(got=got, want=[r['answer'] for r in rs], first=first, last=last, default_new=default_new, max_new=pts.MAX_NEW, longest=longest)


def test_generate():
    r = sub('--gen')
    assert r['got'] == r['want'], r
    assert r['max_new'] > r['longest'] > r['default_new'], r
    print('ok generate: a trained PTS model (loss %.3f -> %.4f) writes %s back, with a # inside a step and a %d-char target past the default decode limit %d (MAX_NEW %d under '
          'caps_b3s)' % (r['first'], r['last'], r['want'], r['longest'], r['default_new'], r['max_new']))


# (d)
def count_rows(caps_name):
    """Run in a subprocess: the 3M PT and PTS configs under the caps file with eg_embed (the G2C3 control's settings)."""
    from custom_io.g8a import caps as CP, configs as C
    caps = json.load(open(os.path.join(G8A, caps_name)))
    CP.apply(caps)
    loops = CP.n_loops_needed(caps)
    b2x = dict(n_loops=loops, eg_embed=True) if loops > 8 else dict(eg_embed=True)           # as job.py builds it
    cfgs, counts = C.sizes('3M', b2x)
    C.add_pts('3M', cfgs, counts, b2x)
    C.check_bands('3M', cfgs, counts, exact_3m=False)
    a = C.train_args('3M', 'PTS', 1, 10, '/x', b2_extra=b2x, caps='/x/caps.json')
    guards = []
    for kw in (dict(b2_extra=b2x), dict(b2_extra={k: v for k, v in b2x.items() if k != 'eg_embed'}, caps='/x/caps.json')):    # no caps / no eg_embed: refused
        try:
            C.train_args('3M', 'PTS', 1, 10, '/x', **kw)
            guards.append('')
        except AssertionError as e:
            guards.append(str(e))
    from custom_io.models import plain_tf_steps as P
    return dict(counts=counts, PT_cfg=cfgs[C.PT_ARM], PTS_cfg=cfgs[C.PTS_ARM], max_pos=P.MAX_POS, loops=loops, args=a, guards=guards)


def sub(*flags):
    out = subprocess.run([sys.executable, '-m', 'custom_io.tests.test_pts', *flags], cwd=ROOT, env=dict(os.environ, PYTHONPATH=ROOT, OMP_NUM_THREADS='1'),
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-4000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_counts():
    r = sub('--count', 'caps_b3.json')
    c = r['counts']
    assert r['loops'] == 12, r['loops']
    assert c['PT'] == G2C3 and c['PTS'] == G2C3, c
    assert r['PTS_cfg'].get('all_steps') is True and 'all_steps' not in r['PT_cfg'], r['PTS_cfg']
    assert r['PTS_cfg'].get('eg_embed') is True, r['PTS_cfg']
    assert {k: v for k, v in r['PTS_cfg'].items() if k != 'all_steps'} == r['PT_cfg'], (r['PTS_cfg'], r['PT_cfg'])
    assert 'needs --caps' in r['guards'][0] and 'not within' in r['guards'][1], r['guards']
    s = sub('--count', 'caps_b3s.json')        # what the arm runs: its own pin (plain_target 115)
    cs = s['counts']
    assert cs['PT'] == cs['PTS'], cs
    gap = (s['max_pos'] - r['max_pos']) * r['PT_cfg']['d_model']      # the only difference between the two caps files that is a weight: the position table
    assert cs['PTS'] - G2C3 == gap > 0, (cs, gap)
    a = s['args']
    assert a[a.index('--model') + 1] == 'plain_tf_steps_g' and json.loads(a[a.index('--cfg') + 1]) == s['PTS_cfg'] and '--caps' in a, a
    assert abs(cs['PTS'] / cs['B2'] - 1) <= PLAIN_BAND, cs
    print('ok count: PT %s and PTS %s at 3M under caps_b3 (eg_embed, n_loops %d); PTS cfg = PT cfg + all_steps; PTS refused without --caps or without eg_embed' %
          (f"{c['PT']:,}", f"{c['PTS']:,}", r['loops']))
    print('ok count under the pin caps_b3s: PT = PTS = %s, %s above G2C3 (plain_target 115 vs 109: MAX_POS %d vs %d, x d_model %d)' %
          (f"{cs['PTS']:,}", f"{gap:,}", s['max_pos'], r['max_pos'], r['PT_cfg']['d_model']))


# (e)
def rowline(**kw):
    return json.dumps(dict(dict(id='x', family='cloze_steps', prompt='Add them.', answer='9', steps=['4 + 5 = 9']), **kw)) + '\n'


def test_caps_report_refuses():
    from custom_io.g8a import caps as CP, job
    pin = json.load(open(os.path.join(G8A, 'caps_b3s.json')))
    too_long = ['%d + %d = %d' % (i, i + 1, 2 * i + 1) for i in range(1, 11)] + ['11 + 12 = 23']          # joined > the pin's plain_target
    long_row = rowline_row(steps=too_long, answer='23')
    assert CP.measure(long_row, progs=False)['plain_target'] < pin['plain_target'] < CP.measure(long_row, progs=False, all_steps=True)['plain_target']     # cloze_steps: outside the family gate
    ns = lambda arms, **kw: types.SimpleNamespace(**dict(dict(arms=arms, scale=1.0, caps_file=None, big_data=None, own72=None, data8a=None, web30=None, recompute_caps=False,
                                                              cloze_long=None, work='/nonexistent'), **kw))

    def pool(d, train=(), dev=()):
        os.makedirs(os.path.join(d, 'dev'))
        open(os.path.join(d, 'train.jsonl'), 'w').writelines(train)
        open(os.path.join(d, 'dev', 'in_dist.jsonl'), 'w').writelines(dev)
        return d

    with tempfile.TemporaryDirectory(prefix='ptspool-', dir=os.environ.get('PTS_TEST_TMP')) as t:
        d = pool(os.path.join(t, 'ok'), train=[rowline()], dev=[rowline(prompt='Dev.')])
        assert job.get_caps(ns(['PTS']), d) == pin
        rep = json.load(open(os.path.join(d, 'caps_report.json')))
        assert rep['all_steps'] is True and rep['train_bytes'] == os.path.getsize(os.path.join(d, 'train.jsonl')) and not any(rep['rows_over_caps'].values()), rep
        # cached: used as is, without a new measurement ...
        real = CP.report
        CP.report = lambda *a, **k: (_ for _ in ()).throw(AssertionError('measured again'))
        try:
            assert job.get_caps(ns(['PTS']), d) == pin
        finally:
            CP.report = real
        # ... until train.jsonl changes: a too-long row in the cached pool is refused (and the cache removed), also in a family outside STEP_FAMILIES
        open(os.path.join(d, 'train.jsonl'), 'a').write(rowline(steps=too_long, answer='23'))
        try:
            job.get_caps(ns(['PTS']), d)
            raise SystemExit('a cached pool with a too-long row was accepted')
        except SystemExit as e:
            assert 'plain_target' in str(e), e
        assert not os.path.exists(os.path.join(d, 'caps.json'))
        # a too-long dev row is refused too; a row in a family the group-1 rule skips is measured whole
        d2 = pool(os.path.join(t, 'dev'), train=[rowline()], dev=[rowline(steps=too_long, answer='23')])
        try:
            job.get_caps(ns(['PTS']), d2)
            raise SystemExit('a too-long dev row was accepted')
        except SystemExit as e:
            assert 'plain_target' in str(e), e
        d3 = pool(os.path.join(t, 'old'), train=[rowline(steps=too_long, answer='23')], dev=[rowline()])
        assert job.get_caps(ns(['PT'], caps_file=os.path.join(G8A, 'caps_b3s.json')), d3) == pin        # the old arms measure with the family gate: unchanged
        # PTS pins its caps for the whole job: not beside the B3 arms, not with another caps file
        for bad in (ns(['PTS', 'B3G2']), ns(['PTS'], caps_file=os.path.join(G8A, 'caps_b3.json'))):
            try:
                job.get_caps(bad, pool(os.path.join(t, 'bad%d' % id(bad)), train=[rowline()], dev=[rowline()]))
                raise SystemExit('PTS accepted a different caps pin')
            except AssertionError:
                pass
    print('ok job caps report: PTS refuses a row over plain_target %d in train, dev and a cached pool; PTS pins caps_b3s.json and does not run beside B3 / B3G2' % pin['plain_target'])


def rowline_row(**kw):
    return json.loads(rowline(**kw))


if __name__ == '__main__':
    if '--count' in sys.argv:
        print(json.dumps(count_rows(sys.argv[sys.argv.index('--count') + 1])))
        sys.exit(0)
    if '--gen' in sys.argv:
        print(json.dumps(gen_rows()))
        sys.exit(0)
    for f in (test_off_is_head, test_scoring, test_no_truncation, test_generate, test_counts, test_caps_report_refuses):
        f()
    print('all test_pts checks passed')
