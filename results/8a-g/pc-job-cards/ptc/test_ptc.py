"""python3 -m custom_io.tests.test_ptc   (CPU, about two minutes; no data files, no Gemma: eg_embed is only counted, never run)
PTC (addendum AG): the plain step model (PTS: all_steps) trained with the calculator. calc_train leaves the characters the calculator writes (the result after each
step `expr =`) out of the loss, and the intact model decodes with the calculator on; lesion `nocalc` = off.
  1  calc_full: the whole integer expression, precedence, brackets, negatives, exact division only; garbage never raises.
  2  mask = generate: a model that writes the gold text (a poison character where the calculator writes) gets exactly the masked positions forced, and the text comes
     out equal to the gold; a gold step with another result stays in the loss and is counted (calc_mismatch).
  3  calc_train off = the base code (commit 74d6e92c75): same weights at the same seed, loss, target ids, a trained model's decodes (intact and `calc`), LESIONS, cap
     counters, the old arms' sizes and train_args. The base tree is a git archive (or the tree named by PTC_ORIG_TREE, which the PC check uses).
  4  PTC: count = PTS at 3M and 10M (and at 30M with the no-plug front of 74d6e92c75), cfg = PTS cfg + calc_train, LESIONS ['nocalc'], train_args builds, job.py caps handling = PTS's.
  5  masked loss: the loss ignores the calculator characters (no gradient there, targets -100) and the width W is that of calc_train off.
caps.apply mutates module globals, so everything that applies caps runs in a subprocess."""
import json, os, random, subprocess, sys, tempfile, types
import torch
from custom_io import capcount
from custom_io.data import CharVocab, EOS, PAD
from custom_io.g8a import configs as C
from custom_io.models import build
from custom_io.models import plain_tf_steps as M
from custom_io.models.plain_tf_steps import calc_full, calc_mask, calc_fill, target_text_all

BASE = '74d6e92c75'
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
G8A = os.path.join(ROOT, 'custom_io', 'g8a')
V = CharVocab.build([])

STEP_ROWS = [      # real step formats (tests/test_progtext.py ROWS); the answer is the last result
    dict(family='story_addsub', prompt='Tom has 12 apples and buys 5 more. How many now?', steps=['12 + 5 = 17'], answer='17'),
    dict(family='chain_ops', prompt='3 + 4 * 5', steps=['3 + 4 * 5 = 23'], answer='23'),
    dict(family='chain_ops', prompt='(3 + 4) * 5 - 2', steps=['(3 + 4) * 5 - 2 = 33'], answer='33'),
    dict(family='var_chain', prompt='Let x = 6 * 7 and y = x + 10. What is y?', steps=['x = 6 * 7 = 42', 'y = 42 + 10 = 52'], answer='52'),
    dict(family='arith_bare', prompt='20 / ? = 4', steps=['20 / 5 = 4'], answer='5'),
    dict(family='arith_bare', prompt='? - 5 = 12', steps=['17 - 5 = 12'], answer='17'),
    dict(family='backward_solve', prompt='A number plus 5 equals 12.', steps=['7 + 5 = 12', 'x = 12 - 5 = 7'], answer='7'),
    dict(family='state_update', prompt='Start at 12. Then +5, -3.', steps=['+5 -> 17', '-3 -> 14'], answer='14'),
    dict(family='chain_ops', prompt='3 - 8 + 2', steps=['3 - 8 + 2 = -3'], answer='-3'),
    dict(family='list_stats', prompt='Count evens in [4, 7, 10], then times 10.', steps=['count_even of [4, 7, 10]', '2 * 10 = 20'], answer='20'),
    dict(family='compare_numbers', prompt='Which is bigger, 9 or 4?', steps=['compare 9 4'], answer='9'),
    dict(family='verify_claim', prompt='Claim: 42', steps=['6 * 7 = 42'], answer='yes'),
    dict(family='percent_rate', prompt='x', steps=['a = 7 * 6 = 42', 'b = 42 / 6 = 7', 'c = 7 x 3 = 21'], answer='21'),
    dict(family='sum_list', prompt='Add 3, 4, 5.', steps=['sum [3,4,5]'], answer='12'),
    dict(family='copy_word', prompt='Echo: sune', answer='sune'),
    dict(family='arith_bare', prompt='7 # 2 =', steps=['7 # 2 = 5 # odd'], answer='5'),
]


def make_batch(rs, vocab=V):
    enc = [vocab.encode(r['prompt']) for r in rs]
    T = max(map(len, enc))
    ids = torch.full((len(rs), T), PAD, dtype=torch.long)
    mask = torch.zeros((len(rs), T), dtype=torch.bool)
    for i, e in enumerate(enc):
        ids[i, :len(e)] = torch.tensor(e)
        mask[i, :len(e)] = True
    return {'rows': rs, 'prompt_ids': ids, 'prompt_mask': mask}


def small(**kw):
    torch.manual_seed(0)
    return build('plain_tf_steps_g', V, d_model=32, n_layers=1, n_heads=4, **kw)


# 1
def test_calc_full():
    cases = {'12 + 5 =': ' 17', '3 + 4 * 5 =': ' 23', '(3 + 4) * 5 - 2 =': ' 33', 'x = 6 * 7 =': ' 42', 'a; 3 - 8 + 2 =': ' -3', '7 / 2 =': None, '20 / 5 =': ' 4',
             '6 x 7 =': ' 42', '12 + 5': None, 'compare 9 4': None, '12+5=': '17', '5 =': None, '': None, '=': None, '7 / 0 =': None, '-3 * -2 =': ' 6',
             'z = 21 * 2 = 42; m = 42 * 7 =': ' 294', 'm = z * 7 =': None, '(3 + 4 =': None, '3 + 4) =': None, '9 4 =': None, '12 + 5 = 17; 8 - 3 =': ' 5',
             '7 # 2 = 5 # 9 - 2 =': ' 7', '2 * (3 + 4) / 7 =': ' 2', '10 / 5 / 2 =': ' 1', '10 / (2 + 3) * 4 =': ' 8', 'total: 3 + 4 =': None, '3 + =': None,
             '12 + 5 = 17 =': None, '0 - 5 =': ' -5', '3 +4 =': ' 7'}
    for t, want in cases.items():
        assert calc_full(t) == want, (t, calc_full(t), want)
    # the old calc_fill and calc_full agree on what calc_fill knows (single operations)
    for t in ('12 + 5 =', '8 - 3 =', '6 * 7 =', '20 / 5 =', '12+5=', '9 x 3 =', '7 / 2 ='):
        assert calc_fill(t) == calc_full(t), t
    rng = random.Random(1)
    alpha = '0123456789 +-*/x()=;#abc.,%\n\t~é'
    for _ in range(4000):
        t = ''.join(rng.choice(alpha) for _ in range(rng.randint(0, 40)))
        r = calc_full(t)
        assert r is None or (isinstance(r, str) and r.strip().lstrip('-').isdigit()), (t, r)
        r2 = calc_full(t + '=')
        assert r2 is None or isinstance(r2, str), t
    for t in ('(' * 5000 + '1 + 1' + ')' * 5000 + ' =', '9' * 600 + ' * 3 =', '1' + ' * 9' * 150 + ' =', None, 5):
        try:
            calc_full(t)
        except Exception as e:
            raise SystemExit('calc_full raised on %r: %r' % (str(t)[:20], e))
    print('ok calc_full: %d fixed cases, calc_fill agreement, 8000 random strings, deep brackets and huge numbers: never raises' % len(cases))


# 2
def fake_generate(m, texts, poison_masked):
    """Run m.generate (calculator on, lesion None, or 'nocalc') with a model that 'writes' the gold text: logits are one-hot on the gold character at each step (a
    poison character where the calculator would write). Returns (decoded full texts, [(prefix, forced string)] the calculator was consulted with and answered)."""
    gold = []
    for t in texts:
        cm, _ = calc_mask(t)
        gold.append([V.stoi['~'] if (c and poison_masked) else V.stoi[ch] for ch, c in zip(t, cm)] + [EOS])
    state = {'t': 0}

    def logits(h):
        t, state['t'] = state['t'], state['t'] + 1
        out = torch.zeros(h.shape[0], len(V))
        for b, g in enumerate(gold):
            out[b, g[t] if t < len(g) else EOS] = 1
        return out

    seen, real_full, real_final, real_logits = [], M.calc_full, M.final_answer, m.logits

    def spy(text):
        f = real_full(text)
        if f:
            seen.append((text, f))
        return f
    M.calc_full, M.final_answer, m.logits = spy, (lambda s: s), logits
    try:
        return m.generate(make_batch([dict(prompt='Q') for _ in texts]), lesion='nocalc' if not poison_masked else None), seen
    finally:
        M.calc_full, M.final_answer = real_full, real_final
        del m.logits


def test_mask_equals_generate():
    texts = [target_text_all(r) for r in STEP_ROWS]
    assert max(map(len, texts)) + 1 < M.MAX_NEW, max(map(len, texts))
    m = small(all_steps=True, calc_train=True).eval()
    n_masked = 0
    got, seen = fake_generate(m, texts, True)       # calculator on: every masked position is forced
    for t, g in zip(texts, got):
        cm, bad = calc_mask(t)
        assert bad == 0, (t, bad)
        forced = set()
        for pre, f in seen:
            if t.startswith(pre) and t[len(pre):len(pre) + len(f)] == f:
                forced |= set(range(len(pre), len(pre) + len(f)))
            assert not t.startswith(pre) or t[len(pre):].startswith(f), (t, pre, f)      # whenever it was consulted on this row's prefix, the gold continues with its answer
        assert forced == {i for i, c in enumerate(cm) if c}, (t, sorted(forced), [i for i, c in enumerate(cm) if c])
        assert g == t, (g, t)                                                              # poison never survives; the text equals the gold
        n_masked += sum(cm)
    assert n_masked > 40, n_masked
    got0, seen0 = fake_generate(m, texts, False)    # lesion nocalc: nothing forced; the model writes the gold text itself (poison_masked False here)
    assert not seen0 and got0 == texts, 'nocalc must force nothing'
    # the intact model with a calc-trained cfg vs the old calc lesion refused
    for bad_lesion in ('calc',):
        try:
            m.generate(make_batch([dict(prompt='Q')]), lesion=bad_lesion)
            raise SystemExit('PTC accepted lesion calc')
        except ValueError:
            pass
    # a gold step whose result differs stays in the loss and is counted
    for t, mism, nm in (('12 + 5 = 18', 1, 0), ('12 + 5 = 170', 1, 0), ('12 + 5 =17', 1, 0), ('12 + 5 = 17', 0, 3), ('x = 6 * 7 = 42; y = 42 + 1 = 44 # 44', 1, 3),
                        ('7 / 2 = 3', 0, 0)):
        cm, bad = calc_mask(t)
        assert (bad, sum(cm)) == (mism, nm), (t, bad, sum(cm))
    assert calc_mask('12 + 5 = 18')[0] == [False] * 11 and calc_mask('12 + 5 = 17')[0] == [False] * 8 + [True] * 3
    capcount.reset()
    small(all_steps=True, calc_train=True).loss(make_batch([dict(STEP_ROWS[0], steps=['12 + 5 = 18'], answer='18'), STEP_ROWS[0]]))
    assert capcount.HITS['calc_mismatch'] == 1 and capcount.HITS['calc_rows'] == 2 and capcount.HITS['calc_forced'] == 3, dict(capcount.HITS)
    assert capcount.snapshot()['total'] == 0 and capcount.snapshot()['calc_mismatch'] == 1       # reported beside the counters, not part of their total
    capcount.reset()
    print('ok mask = generate: %d rows, %d result characters, forced positions == masked positions, text == gold, nocalc forces nothing, a mismatching step stays in the '
          'loss and is counted' % (len(texts), n_masked))


# 3
PARITY = r'''
import json, sys, torch
from custom_io import capcount
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
for tag, name, kw in (('pt', 'plain_tf_steps', {}), ('ptg', 'plain_tf_steps_g', {}), ('pts', 'plain_tf_steps_g', dict(all_steps=True)), ('lm', 'plain_lm', {})):
    torch.manual_seed(0)
    m = build(name, V, d_model=48, n_layers=2, n_heads=4, **kw)
    out[tag + '_sd0'] = {k: v.clone() for k, v in m.state_dict().items()}
    out[tag + '_loss0'] = m.loss(batch).item()
    out[tag + '_lesions'] = list(m.LESIONS)
    if tag != 'lm':
        out[tag + '_targets'] = [t.clone() for t in m._targets(batch)]
        opt = torch.optim.AdamW(m.parameters(), lr=3e-3)
        for _ in range(40):
            opt.zero_grad(); l = m.loss(batch); l.backward(); opt.step()
        out[tag + '_loss'] = l.item()
        out[tag + '_sd'] = {k: v.clone() for k, v in m.state_dict().items()}
        m.eval()
        out[tag + '_gen'] = [m.generate(batch), m.generate(batch, lesion='calc'), m.generate(batch, lesion='loops:0') if hasattr(m, 'n_loops') else None]
out['hits'] = dict(capcount.snapshot())
cfgs, counts = C.sizes('3M')
out['sizes'] = json.dumps([cfgs, counts, list(C.ARMS)], sort_keys=True)
out['train_args'] = json.dumps([C.train_args('3M', arm, 1, 10, '/x') for arm in C.ARMS])
out['arms'] = json.dumps([list(C.ALL_ARMS), C.MODEL_OF])
torch.save(out, sys.argv[1])
'''


def pypath(tree):
    """The tree first, then whatever PYTHONPATH the caller has (the PC's torch / eg site-packages)."""
    return os.pathsep.join([tree] + ([os.environ['PYTHONPATH']] if os.environ.get('PYTHONPATH') else []))


def run_parity(tree, rows_json, dst):
    subprocess.check_call([sys.executable, '-c', PARITY, dst, rows_json], cwd=tree, env=dict(os.environ, PYTHONPATH=pypath(tree), OMP_NUM_THREADS='1'))
    return torch.load(dst)


def test_off_is_base():
    rs = STEP_ROWS
    with tempfile.TemporaryDirectory(prefix='ptcbase-', dir=os.environ.get('PTS_TEST_TMP')) as d:
        rows_json = os.path.join(d, 'rows.json')
        json.dump(rs, open(rows_json, 'w'))
        ref = os.environ.get('PTC_ORIG_TREE')
        if not ref:
            ref = os.path.join(d, 'ref')
            os.makedirs(ref)
            arc = subprocess.Popen(['git', 'archive', BASE, 'custom_io'], cwd=ROOT, stdout=subprocess.PIPE)
            subprocess.check_call(['tar', '-x', '-C', ref], stdin=arc.stdout)
            assert arc.wait() == 0
        a, b = run_parity(ref, rows_json, os.path.join(d, 'ref.pt')), run_parity(ROOT, rows_json, os.path.join(d, 'new.pt'))
    a_arms, b_arms = json.loads(a.pop('arms')), json.loads(b.pop('arms'))
    assert a_arms[0] + ['PTC'] == b_arms[0] and {k: v for k, v in b_arms[1].items() if k != 'PTC'} == a_arms[1], (a_arms, b_arms)
    assert a.keys() == b.keys()
    for k in a:
        if k.endswith('_sd') or k.endswith('_sd0'):
            assert a[k].keys() == b[k].keys() and all(torch.equal(a[k][n], b[k][n]) for n in a[k]), k
        elif k.endswith('_targets'):
            assert all(torch.equal(x, y) for x, y in zip(a[k], b[k])), k
        else:
            assert a[k] == b[k], (k, a[k], b[k])
    assert a['pt_lesions'] == ['calc'] and b['pts_lesions'] == ['calc'] and b['lm_lesions'] == ['calc'], b['pts_lesions']
    print('ok calc_train off = base %s: every weight at the seed, loss before and after 40 updates, target ids, intact / calc / loops:0 decodes (PT, PT_g, PTS), LESIONS '
          "['calc'], cap counters, old arms' sizes and train_args are equal" % BASE)


# 4
def count_rows():
    """Run in a subprocess: PT, PTS and PTC at 3M and 10M under caps_b3s with eg_embed (as the job builds them)."""
    from custom_io.g8a import caps as CP
    caps = json.load(open(os.path.join(G8A, 'caps_b3s.json')))
    CP.apply(caps)
    loops = CP.n_loops_needed(caps)
    b2x = dict(n_loops=loops, eg_embed=True) if loops > 8 else dict(eg_embed=True)
    res = {}
    for rung in ('3M', '10M'):
        cfgs, counts = C.sizes(rung, b2x)
        C.add_pts(rung, cfgs, counts, b2x)
        C.add_ptc(rung, cfgs, counts, b2x)
        C.check_bands(rung, cfgs, counts, exact_3m=False)
        a = C.train_args(rung, 'PTC', 400, 10, '/x', b2_extra=b2x, caps='/x/caps.json')
        guards = []
        for kw in (dict(b2_extra=b2x), dict(b2_extra={k: v for k, v in b2x.items() if k != 'eg_embed'}, caps='/x/caps.json')):
            try:
                C.train_args(rung, 'PTC', 400, 10, '/x', **kw)
                guards.append('')
            except AssertionError as e:
                guards.append(str(e))
        res[rung] = dict(counts=counts, PTS_cfg=cfgs['PTS'], PTC_cfg=cfgs['PTC'], args=a, guards=guards)
    # the no-plug front of 74d6e92c75 (30M / 100M only, width 512, eg_pre): PTC takes it as PTS does (job.py's front asserts, check_bands' no-plug branch)
    npx = {C.NOPLUG: True}
    cfgs, counts = C.sizes('30M', npx)
    C.add_pts('30M', cfgs, counts, npx)
    C.add_ptc('30M', cfgs, counts, npx)
    C.check_bands('30M', cfgs, counts, exact_3m=False)
    try:
        C.check_bands('30M', cfgs, dict(counts, PTC=int(counts['PTC'] * 1.05)), exact_3m=False)
        off_band = ''
    except AssertionError as e:
        off_band = str(e)
    res['30M-noplug'] = dict(counts=counts, PTS_cfg=cfgs['PTS'], PTC_cfg=cfgs['PTC'], off_band=off_band)
    return res


def sub(*flags):
    out = subprocess.run([sys.executable, '-m', 'custom_io.tests.test_ptc', *flags], cwd=ROOT, env=dict(os.environ, PYTHONPATH=pypath(ROOT), OMP_NUM_THREADS='1'), capture_output=True, text=True)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-4000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_ptc_arm():
    r = sub('--count')
    npl = r.pop('30M-noplug')
    for rung, x in r.items():
        c = x['counts']
        assert c['PTC'] == c['PTS'] == c['PT'], (rung, c)
        assert x['PTC_cfg'] == dict(x['PTS_cfg'], calc_train=True) and 'calc_train' not in x['PTS_cfg'] and x['PTC_cfg']['all_steps'] and x['PTC_cfg']['eg_embed'], x
        a = x['args']
        assert a[a.index('--model') + 1] == 'plain_tf_steps_g' and json.loads(a[a.index('--cfg') + 1]) == x['PTC_cfg'] and '--caps' in a and '--final-eval' in a, a
        assert 'needs --caps' in x['guards'][0] and 'not within' in x['guards'][1], x['guards']
    c = npl['counts']
    assert c['PTC'] == c['PTS'] == c['PT'] and npl['PTC_cfg'] == dict(npl['PTS_cfg'], calc_train=True) and npl['PTC_cfg']['eg_pre'] and npl['PTC_cfg']['d_model'] == 512, npl
    assert 'PTC' in npl['off_band'] and 'not within' in npl['off_band'], npl['off_band']          # the no-plug band check covers PTC
    m = build('plain_tf_steps_g', V, d_model=32, n_layers=1, n_heads=4, all_steps=True, calc_train=True)
    assert m.LESIONS == ['nocalc'] and build('plain_tf_steps_g', V, d_model=32, n_layers=1, n_heads=4, all_steps=True).LESIONS == ['calc']
    from custom_io.train import lesion_names
    assert lesion_names(m)[0] == 'nocalc' and 'calc' not in lesion_names(m), lesion_names(m)
    assert M.PlainTFSteps.LESIONS == ['calc'], 'the class list is untouched (the instance carries the PTC one)'
    try:
        build('plain_tf_steps_g', V, d_model=32, n_layers=1, n_heads=4).generate(make_batch([dict(prompt='Q')]), lesion='nocalc')
        raise SystemExit('PTS accepted nocalc')
    except ValueError:
        pass
    try:
        build('plain_lm', V, d_model=32, n_layers=1, n_heads=4, calc_train=True)
        raise SystemExit('plain_lm accepted calc_train')
    except AssertionError:
        pass
    print('ok PTC: count %s (3M), %s (10M), %s (30M no plug) = PTS = PT; cfg = PTS cfg + calc_train; LESIONS [nocalc] (PTS keeps [calc]); train_args builds, refused without --caps / eg_embed' %
          (f"{r['3M']['counts']['PTC']:,}", f"{r['10M']['counts']['PTC']:,}", f"{npl['counts']['PTC']:,}"))


def rowline(**kw):
    return json.dumps(dict(dict(id='x', family='cloze_steps', prompt='Add them.', answer='9', steps=['4 + 5 = 9']), **kw)) + '\n'


def test_job_caps():
    from custom_io.g8a import job
    pin = json.load(open(os.path.join(G8A, 'caps_b3s.json')))
    too_long = ['%d + %d = %d' % (i, i + 1, 2 * i + 1) for i in range(1, 11)] + ['11 + 12 = 23']
    ns = lambda arms, **kw: types.SimpleNamespace(**dict(dict(arms=arms, scale=1.0, caps_file=None, big_data=None, own72=None, data8a=None, web30=None, recompute_caps=False,
                                                              cloze_long=None, work='/nonexistent'), **kw))

    def pool(d, train=(), dev=()):
        os.makedirs(os.path.join(d, 'dev'))
        open(os.path.join(d, 'train.jsonl'), 'w').writelines(train)
        open(os.path.join(d, 'dev', 'in_dist.jsonl'), 'w').writelines(dev)
        return d

    with tempfile.TemporaryDirectory(prefix='ptcpool-', dir=os.environ.get('PTS_TEST_TMP')) as t:
        d = pool(os.path.join(t, 'ok'), train=[rowline()], dev=[rowline(prompt='Dev.')])
        assert job.caps_dir(ns(['PTC']), d) == job.caps_dir(ns(['PTS']), d) != d                  # the same sibling dir as PTS
        assert job.get_caps(ns(['PTC']), d) == pin
        assert not os.path.exists(os.path.join(d, 'caps.json'))
        rep = json.load(open(os.path.join(job.caps_dir(ns(['PTC']), d), 'caps_report.json')))
        assert rep['all_steps'] is True and not any(rep['rows_over_caps'].values())
        assert job.get_caps(ns(['PTS']), d) == pin                                                  # PTS reads what PTC measured (cached and valid)
        open(os.path.join(d, 'train.jsonl'), 'a').write(rowline(steps=too_long, answer='23'))
        try:
            job.get_caps(ns(['PTC']), d)
            raise SystemExit('PTC accepted a cached pool with a too-long row')
        except SystemExit as e:
            assert 'plain_target' in str(e), e
        for bad in (ns(['PTC', 'B3G2']), ns(['PTC'], caps_file=os.path.join(G8A, 'caps_b3.json'))):
            try:
                job.get_caps(bad, pool(os.path.join(t, 'bad%d' % id(bad)), train=[rowline()], dev=[rowline()]))
                raise SystemExit('PTC accepted a different caps pin')
            except AssertionError:
                pass
    print('ok job caps: PTC shares PTS\'s caps dir and pin (caps_b3s.json), refuses a row over plain_target %d, refuses B3G2 beside it and another caps file' % pin['plain_target'])


# 5
def test_masked_loss():
    texts = [target_text_all(r) for r in STEP_ROWS]
    batch = make_batch(STEP_ROWS)
    cap = {}
    real_ce = torch.nn.functional.cross_entropy

    def ce(lg, tgt, **kw):
        lg.retain_grad()
        cap['lg'], cap['tgt'] = lg, tgt.clone()
        return real_ce(lg, tgt, **kw)
    out = {}
    torch.nn.functional.cross_entropy = ce
    try:
        for tag, kw in (('off', {}), ('on', dict(calc_train=True))):
            m = small(all_steps=True, **kw)
            l = m.loss(batch)
            l.backward()
            out[tag] = dict(loss=l.item(), lg=cap['lg'].detach().clone(), grad=cap['lg'].grad.clone(), tgt=cap['tgt'].clone())
    finally:
        torch.nn.functional.cross_entropy = real_ce
    off, on = out['off'], out['on']
    assert off['lg'].shape == on['lg'].shape, (off['lg'].shape, on['lg'].shape)            # the width W is the same
    assert torch.equal(off['lg'], on['lg']), 'same weights and inputs: same logits'
    B = len(STEP_ROWS)
    W = off['lg'].shape[0] // B
    lens = batch['prompt_mask'].sum(1)
    want = off['tgt'].clone().view(B, W)
    nmask = 0
    for i, t in enumerate(texts):
        cm, _ = calc_mask(t)
        for j, c in enumerate(cm):
            if c:
                assert want[i, 1 + lens[i] + j] == V.stoi[t[j]], (i, j)
                want[i, 1 + lens[i] + j] = -100
                nmask += 1
    assert torch.equal(on['tgt'].view(B, W), want), 'targets: -100 exactly at the calculator characters'
    assert (off['tgt'] != -100).sum() - (on['tgt'] != -100).sum() == nmask > 40
    keep = on['tgt'] != -100
    ref = real_ce(on['lg'][keep], on['tgt'][keep])
    assert abs(ref.item() - on['loss']) < 1e-6 and abs(on['loss'] - off['loss']) > 1e-4, (ref.item(), on['loss'], off['loss'])
    assert float(on['grad'][~keep].abs().sum()) == 0.0 and float(on['grad'][keep].abs().sum()) > 0, 'no gradient at the calculator characters'
    # long targets are not cut: the longest target's last real position is inside W
    long_row = dict(STEP_ROWS[12], steps=['%d + %d = %d' % (i, i + 1, 2 * i + 1) for i in range(1, 15)], answer='9')
    lt = target_text_all(long_row)
    assert len(lt) > 100
    mm = small(all_steps=True, calc_train=True)
    ids, am = mm._targets(make_batch([long_row]))
    assert int(am.sum()) == len(lt) + 1
    cap2 = {}
    torch.nn.functional.cross_entropy = lambda lg, tgt, **kw: (cap2.update(n=int((tgt != -100).sum()), W=lg.shape[0]), real_ce(lg, tgt, **kw))[1]
    try:
        mm.loss(make_batch([long_row]))
    finally:
        torch.nn.functional.cross_entropy = real_ce
    assert cap2['W'] == 2 + len(long_row['prompt']) + len(lt) + 1, cap2        # W = 2 + prompt + the whole target + EOS: the mask never shortens it
    assert cap2['n'] == len(lt) + 1 - sum(calc_mask(lt)[0]), cap2
    print('ok masked loss: %d result characters get target -100 and no gradient, the rest equal calc_train off; W unchanged (%d); a %d-char target keeps its tail (%d trained)' %
          (nmask, W, len(lt), cap2['n']))


if __name__ == '__main__':
    if '--count' in sys.argv:
        print(json.dumps(count_rows()))
        sys.exit(0)
    for f in (test_calc_full, test_mask_equals_generate, test_masked_loss, test_ptc_arm, test_job_caps, test_off_is_base):
        f()
    print('all test_ptc checks passed')
