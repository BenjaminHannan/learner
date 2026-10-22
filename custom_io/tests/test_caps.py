"""python3 -m pytest custom_io/tests/test_caps.py   (CPU, about 1 minute; synthetic rows, no skills data needed)
Bid C draft: custom_io/caps.py (the ported 8a-G overlay), custom_io/caps/*.json and train.py --caps. (1) the caps files hold today's values except max_ans 35 / n_reg 36;
(2) apply() sets the globals and records what it applied; (3) B2 is 3,302,481 params by default and 3,307,857 under caps-bidc (only reader.place grows); a checkpoint made
under one cannot load under the other; (4) GEN targets follow GEN_MAX; (5) train.py without --caps is exactly the old train.py (fingerprints taken on the unmodified branch),
with --caps it applies first and writes the caps path, sha256 and values to RESULT.json."""
import hashlib, io, json, os, subprocess, sys, tempfile, contextlib, random
import pytest
import torch
from custom_io import caps, data, train
from custom_io.data import CharVocab, Dataset, collate
from custom_io.models import build, ledger, progparse as pp, reader

CAPS_DIR = os.path.join(os.path.dirname(caps.__file__), 'caps')
BIDC, OLD = os.path.join(CAPS_DIR, 'caps-bidc.json'), os.path.join(CAPS_DIR, 'caps-old-defaults.json')
SMALL = dict(d=48, n_heads=2, reader_layers=1, blocks=1, n_loops=8, mlp=2.0, copy=True)
# fingerprints of the UNMODIFIED branch (456c26288): torch.manual_seed(0); Ledger(vocab108, copy=True, ...); and a 3-step train.py run on the synthetic rows below
GOLD = {'b2': dict(params=3302481, keys=101, keyhash='87faa8145762799f5341adf0778570c67baf5cf9', wabs=42836.94923092964),
        'small': dict(params=95705, keys=75, keyhash='637008fe524aa00f27f705b5509eb1ad1dcc1f40', wabs=2043.77598129692)}
GOLD_RESULT_KEYS = ['config', 'final_eval', 'final_train_loss', 'lesions', 'n_params', 'status', 'steps', 'steps_per_s', 'train_s', 'wall_s']
GOLD_CKPT_KEYS = ['cfg', 'chars', 'model', 'name', 'step']
GOLD_LOSS = 15.901201248168945


@pytest.fixture(autouse=True)
def fresh_globals():
    """apply() patches module globals: put today's back after every test."""
    caps.APPLIED = None
    yield
    caps.apply(caps.TODAY)
    caps.APPLIED = None


def fp(m):
    sd = m.state_dict()
    return dict(params=m.n_params(), keys=len(sd), keyhash=hashlib.sha1(repr([(k, tuple(t.shape)) for k, t in sd.items()]).encode()).hexdigest(),
                wabs=sum(float(t.double().abs().sum()) for t in sd.values()))


def b2(**cfg):
    torch.manual_seed(0)
    return ledger.Ledger(CharVocab.build([]), copy=True, **cfg)


def rows(n, seed, long_answers=0):
    rng, out = random.Random(seed), []
    for i in range(n):
        a, b = rng.randrange(2, 90), rng.randrange(2, 90)
        out.append(dict(id=f'syn:{seed}:{i}', prompt=f'What is {a} plus {b}?', answer=str(a + b), accepted=[str(a + b)], family='arith_bare', level=1, stage=1, variant='',
                        steps=[f'{a} + {b} = {a + b}']))
    for r in out[:long_answers]:                     # answers over the old cap of 8 chars
        r['answer'] = 'x' * 20
        r['accepted'] = [r['answer']]
    return out


def data_dir(train_rows, dev_rows):
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, 'dev'))
    for name, rs in (('train.jsonl', train_rows), (os.path.join('dev', 'in_dist.jsonl'), dev_rows)):
        with open(os.path.join(d, name), 'w') as f:
            f.write(''.join(json.dumps(r) + '\n' for r in rs))
    return d


def run_train(argv):
    with contextlib.redirect_stdout(io.StringIO()):
        train.main(argv)


def test_caps_module_is_importable_beside_the_caps_dir():
    assert os.path.isdir(CAPS_DIR) and hasattr(caps, 'apply') and caps.__file__.endswith('caps.py')
    assert len(caps.UPSTREAM_SHA256) == 64 and caps.UPSTREAM_SHA256.startswith('3da2dfbb')


def test_caps_files_are_today_except_max_ans_and_n_reg():
    old, bidc = (json.load(open(p)) for p in (OLD, BIDC))
    cut = lambda d: {k: d[k] for k in caps.TODAY}
    assert cut(old) == caps.TODAY
    assert cut(bidc) == dict(caps.TODAY, max_ans=35, n_reg=36)
    assert bidc['n_reg'] == bidc['max_ans'] + 1


def test_today_is_what_the_modules_say():
    """caps.TODAY against the unpatched module globals, read in a fresh interpreter (this process may have patched them)."""
    code = ('import json; from custom_io import data; from custom_io.models import progparse as pp, reader, ledger, plain_tf_steps as s;'
            'print(json.dumps(dict(max_prompt=data.MAX_PROMPT, max_ans=data.MAX_ANS, n_num=pp.N_NUM, w_max=pp.W_MAX, n_res=pp.N_RES, n_reg=ledger.N_REG,'
            ' plain_target=s.CAP, gen_max=ledger.GEN_MAX, n_place=reader.N_PLACE)))')
    live = json.loads(subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True).stdout)
    assert {k: live[k] for k in caps.TODAY} == caps.TODAY and live['gen_max'] == caps.TODAY['n_reg'] - 1 and live['n_place'] == 16


def test_apply_records_path_sha_and_values():
    assert caps.APPLIED is None
    got = caps.apply_file(BIDC)
    rec = caps.APPLIED
    assert rec['path'] == os.path.abspath(BIDC) and rec['values'] == got
    assert rec['sha256'] == hashlib.sha256(open(BIDC, 'rb').read()).hexdigest() and len(rec['sha256']) == 64
    assert got['max_ans'] == 35 and got['n_reg'] == 36
    assert (data.MAX_ANS, ledger.N_REG, ledger.GEN_MAX, reader.N_PLACE, reader.PLACE_NONE) == (35, 36, 35, 37, 36)
    assert caps.check_applied(BIDC) is rec
    json.dumps(rec)                                                 # goes into RESULT.json


def test_check_applied_refuses():
    with pytest.raises(AssertionError, match='has not run'):
        caps.check_applied(BIDC)
    caps.apply_file(OLD)
    with pytest.raises(AssertionError, match='not'):                # applied the old defaults, asked for bidc
        caps.check_applied(BIDC)
    caps.apply(json.load(open(BIDC)))                               # same values but no file: no sha to compare
    assert caps.APPLIED['sha256'] is None and caps.APPLIED['path'] is None
    with pytest.raises(AssertionError):
        caps.check_applied(BIDC)
    twin = os.path.join(tempfile.mkdtemp(), 'twin.json')           # same values, different bytes: a different file
    with open(twin, 'w') as f:
        f.write(open(BIDC).read() + '\n')
    caps.apply_file(BIDC)
    with pytest.raises(AssertionError):
        caps.check_applied(twin)


def test_apply_never_goes_below_today():
    got = caps.apply({'max_ans': 3, 'n_reg': 2, 'max_prompt': 10})
    assert got == caps.TODAY and caps.is_today(got)
    assert not caps.is_today(caps.apply_file(BIDC))


def test_default_b2_is_unchanged():
    """No caps, and caps equal to today's values: the same modules, state_dict keys and shapes, seeded init as the unmodified branch."""
    for tag, cfg in (('b2', {}), ('small', SMALL)):
        m = b2(**{k: v for k, v in cfg.items() if k != 'copy'})
        g, f = GOLD[tag], fp(m)
        assert (f['params'], f['keys'], f['keyhash']) == (g['params'], g['keys'], g['keyhash']), tag
        assert abs(f['wabs'] / g['wabs'] - 1) < 1e-8, tag
        caps.apply_file(OLD)                                        # today's caps written out: also identical
        f2 = fp(b2(**{k: v for k, v in cfg.items() if k != 'copy'}))
        assert f2 == f, tag


def test_bidc_b2_size_and_shapes():
    base = b2()
    sd0 = base.state_dict()
    caps.apply_file(BIDC)
    m = b2()
    sd1 = m.state_dict()
    assert base.n_params() == 3302481 and m.n_params() == 3307857                       # card sec. 1: +21 place rows x 256
    assert list(sd0) == list(sd1)
    diff = {k for k in sd0 if sd0[k].shape != sd1[k].shape}
    assert diff == {'reader.place.weight'} and sd0['reader.place.weight'].shape == (16, 256) and sd1['reader.place.weight'].shape == (37, 256)
    nonemb = lambda mod: mod.n_params() - sum(p.numel() for x in mod.modules() if isinstance(x, torch.nn.Embedding) for p in x.parameters())
    assert nonemb(m) == nonemb(base)                                                    # the 2.21x width multiple is untouched


def test_checkpoint_does_not_cross_the_caps():
    """Load gate checks 1 and 2 at the state-dict level: old-default caps load an old checkpoint, the Bid C caps raise a shape error."""
    sd = b2().state_dict()
    caps.apply_file(OLD)
    b2().load_state_dict(sd)
    caps.apply_file(BIDC)
    with pytest.raises(RuntimeError, match='size mismatch'):
        b2().load_state_dict(sd)
    sd_bidc = b2().state_dict()
    b2().load_state_dict(sd_bidc)                                                       # a Bid C checkpoint loads under Bid C
    caps.apply_file(OLD)
    with pytest.raises(RuntimeError, match='size mismatch'):
        b2().load_state_dict(sd_bidc)


def test_gen_targets_follow_the_caps():
    """The Ledger cut GEN register targets at data.MAX_ANS imported by value, so max_ans 35 was not enough: now it follows GEN_MAX."""
    v = CharVocab.build([])
    long_rows = rows(4, 7, long_answers=2)
    pp._CACHE.clear()
    with pytest.raises(AssertionError, match='answer too long'):
        Dataset(long_rows, v)                                                           # default caps: 20-char answers are refused
    ds = Dataset(long_rows, v, strict=False)
    g = b2(**{k: x for k, x in SMALL.items() if k != 'copy'}).gold(collate([ds[i] for i in range(4)])['rows'], 'cpu')['gen']
    assert g.shape == (4, 9) and int((g[0] >= 0).sum()) == 9                            # 8 letters, no EOS: cut at the old cap
    caps.apply_file(BIDC)
    pp._CACHE.clear()
    ds = Dataset(long_rows, v)
    m = b2(**{k: x for k, x in SMALL.items() if k != 'copy'})
    g = m.gold(collate([ds[i] for i in range(4)])['rows'], 'cpu')['gen']
    assert g.shape == (4, 36) and int((g[0] >= 0).sum()) == 21 and int((g[1] >= 0).sum()) == 21   # 20 letters + EOS
    assert int(g[0, 20]) == 2                                                           # EOS id
    loss, _ = m.loss(collate([ds[i] for i in range(4)]))
    assert torch.isfinite(loss)


def test_train_without_caps_is_unchanged():
    """Same RESULT keys, config keys (plus the one new optional 'caps' = None), checkpoint keys, params and loss as the unmodified train.py."""
    d = data_dir(rows(64, 1), rows(16, 2))
    out = os.path.join(d, 'out')
    run_train(['--model', 'ledger', '--cfg', json.dumps(SMALL), '--data', d, '--steps', '3', '--batch', '8', '--warmup', '1', '--log-every', '1', '--device', 'cpu', '--out', out])
    r = json.load(open(os.path.join(out, 'RESULT.json')))
    assert sorted(r) == GOLD_RESULT_KEYS and r['n_params'] == 95705
    assert r['config']['caps'] is None and 'caps' not in r
    assert abs(r['final_train_loss'] - GOLD_LOSS) < 1e-5
    assert sorted(torch.load(os.path.join(out, 'checkpoint.pt'))) == GOLD_CKPT_KEYS
    assert caps.APPLIED is None and data.MAX_ANS == 8 and reader.N_PLACE == 16


def test_train_with_caps_applies_first_and_records():
    train_rows = rows(64, 1, long_answers=6)                                            # 20-char answers: refused unless the caps ran before the data was built
    d = data_dir(train_rows, rows(16, 2))
    out = os.path.join(d, 'out')
    base = ['--model', 'ledger', '--cfg', json.dumps(SMALL), '--data', d, '--steps', '3', '--batch', '8', '--warmup', '1', '--log-every', '1', '--device', 'cpu']
    with pytest.raises(AssertionError, match='answer too long'):
        run_train(base)
    caps.apply(caps.TODAY)
    run_train(base + ['--caps', BIDC, '--out', out])
    r = json.load(open(os.path.join(out, 'RESULT.json')))
    sha = hashlib.sha256(open(BIDC, 'rb').read()).hexdigest()
    assert r['caps'] == dict(path=os.path.abspath(BIDC), sha256=sha, values=dict(caps.TODAY, max_ans=35, n_reg=36))
    assert r['config']['caps'] == BIDC and sorted(k for k in r if k != 'caps') == GOLD_RESULT_KEYS
    assert r['n_params'] == 95705 + 21 * 48                                             # place table 16 -> 37 rows at d 48
    ck = torch.load(os.path.join(out, 'checkpoint.pt'))
    assert ck['caps']['sha256'] == sha and ck['model']['reader.place.weight'].shape == (37, 48) and sorted(k for k in ck if k != 'caps') == GOLD_CKPT_KEYS
    assert caps.check_applied(BIDC)['sha256'] == sha


def test_train_refuses_a_model_that_does_not_follow_the_caps():
    d = data_dir(rows(16, 1), rows(8, 2))
    with pytest.raises(SystemExit, match='reads them by value'):
        run_train(['--model', 'plain_tf', '--data', d, '--steps', '1', '--device', 'cpu', '--caps', BIDC])
