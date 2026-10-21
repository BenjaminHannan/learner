"""python3 -m custom_io.tests.test_ledger_copy   (CPU, about 3 minutes; the real-data checks need the skills data at data.DEFAULT_DATA / $CUSTOM_IO_DATA)
B2 = design B + `copy=True` (models/ledger.py, design/design-B2.md): (1) copy=False is exactly B; (2) copy=True: size, shared init, loss / backward, lesions,
donor swap, extra eval; (3) the mechanism: a pointer-generator GEN talker emits first letters it never saw as answers, the B talker cannot."""
import contextlib, hashlib, json, os, random, string, tempfile, time
import torch
from custom_io.data import DEFAULT_DATA, MAX_ANS, CharVocab, Dataset, collate, load_rows
from custom_io.evalx import donor_eval, evaluate
from custom_io.models import progparse as pp
from custom_io.models.ledger import Ledger
from custom_io.tests.test_ledger import S_CFG, SMALL, batch_of, train_rows, vocab
from custom_io.train import lesion_names

NEW = ('ln_wc', 'k_wc', 'q_cp', 'k_cp', 'g_cp')
B_LESIONS = ['shuffle_state', 'zero_state', 'noexec', 'opswap']
B_PARAMS, B2_PARAMS, PLAIN_TF_S = 3252368, 3302481, 3244544        # vocab 108, S cfg; B2 = B + 50,113
# fingerprints of the UNMODIFIED design-B code (torch.manual_seed(0); Ledger(vocab, **cfg); loss on train_rows(48, 4)), taken before copy existed
GOLD = {'SMALL': dict(params=86152, keys=65, keyhash='e7abfda7bb5e83bcfbc569b97f32104cb8d40046', wabs=1847.9286408642, wsq=473.5623363775, loss=10.72521496,
                      aux=dict(prog=6.41172981, op_acc=0.0, mode=1.10034311, ans=0.60510999, word=0.86066204, gen=1.74737012)),
        'S': dict(params=3252368, keys=91, keyhash='fe07990926a3deee86b35b7dccbe777844881871', wabs=41793.4268707199, wsq=4438.8753759934, loss=11.03054047,
                  aux=dict(prog=6.62084103, op_acc=0.0, mode=1.16103232, ans=0.62023848, word=0.85977197, gen=1.76865673))}
GOLD_TRAIN_BYTES = 111878160            # size of the train.jsonl the loss fingerprints were taken on (skips only the loss check if the data differ)


def seeded(copy, cfg, seed=0, v=None):
    torch.manual_seed(seed)
    return Ledger(v or vocab(), copy=copy, **cfg)


def test_copy_false_is_B():
    """copy=False: same modules, state_dict keys, param count, seeded init, loss, aux and outputs as the unmodified B (fingerprints above)."""
    v, rows = vocab(), train_rows(48, 4)
    data_ok = os.path.exists(os.path.join(DEFAULT_DATA, 'train.jsonl')) and os.path.getsize(os.path.join(DEFAULT_DATA, 'train.jsonl')) == GOLD_TRAIN_BYTES
    for name, cfg in (('SMALL', SMALL), ('S', S_CFG)):
        gd, m = GOLD[name], seeded(False, cfg, v=v)
        sd = m.state_dict()
        assert m.n_params() == gd['params'] and len(sd) == gd['keys'], (name, m.n_params(), len(sd))
        assert hashlib.sha1(repr([(k, tuple(t.shape)) for k, t in sd.items()]).encode()).hexdigest() == gd['keyhash'], name
        assert abs(sum(float(t.double().abs().sum()) for t in sd.values()) / gd['wabs'] - 1) < 1e-8, name
        assert abs(sum(float((t.double() ** 2).sum()) for t in sd.values()) / gd['wsq'] - 1) < 1e-8, name
        assert not any(k.split('.')[0] in NEW for k in sd) and m.LESIONS == B_LESIONS and not m.copy
        b = batch_of(rows, v)
        assert set(m.run(b)) == {'R', 'vals', 'valid', 'lmode', 'steps', 'wvalid', 'lans', 'lword', 'prog'}      # no extra keys in B
        for les in ('nocopy', 'nowordc'):
            try:
                m.generate(b, lesion=les)
                raise AssertionError(f'copy=False accepted lesion {les}')
            except ValueError:
                pass
        if data_ok:
            loss, aux = m.loss(b)
            assert abs(loss.item() - gd['loss']) < 1e-4, (name, loss.item(), gd['loss'])
            assert all(abs(float(aux[k]) - x) < 1e-4 for k, x in gd['aux'].items()) and set(aux) == set(gd['aux']), (name, aux)
        print(f'  {name}: {m.n_params():,} params, {len(sd)} keys, init + loss {"match" if data_ok else "match (loss not checked: train.jsonl differs from the fingerprint data)"} the unmodified B')
    print('ok copy_false_is_B')


def test_copy_true_size_and_init():
    """New modules last; every B weight starts identical at the same seed; exact size, within 3% of plain_tf S."""
    v = vocab()
    assert len(v) == 108
    mb, m = seeded(False, S_CFG, 5, v), seeded(True, S_CFG, 5, v)
    sb, sc = mb.state_dict(), m.state_dict()
    assert list(sc)[:len(sb)] == list(sb), 'new keys must come last'
    assert all(torch.equal(sb[k], sc[k]) for k in sb), 'a shared weight differs from B at the same seed'
    new = list(sc)[len(sb):]
    assert {k.split('.')[0] for k in new} == set(NEW) and len(new) == 10, new
    assert (sc['ln_wc.weight'] == 1).all() and (sc['ln_wc.bias'] == 0).all()
    for mod in ('k_wc', 'q_cp', 'k_cp', 'g_cp'):                       # Linear weights normal(0, 0.02), biases zero
        w = getattr(m, mod)
        assert abs(w.weight.std().item() - 0.02) < 0.004 and (w.bias == 0).all(), mod
    n = m.n_params()
    print(f'  copy=False {mb.n_params():,}  copy=True {n:,} (+{n - mb.n_params():,}, {100 * (n / PLAIN_TF_S - 1):+.2f}% vs plain_tf S {PLAIN_TF_S:,})')
    assert mb.n_params() == B_PARAMS and n == B2_PARAMS and abs(n / PLAIN_TF_S - 1) <= 0.03 and n <= 3341880
    assert m.LESIONS == B_LESIONS + ['nocopy', 'nowordc'] and mb.LESIONS == B_LESIONS
    assert lesion_names(m) == B_LESIONS + ['nocopy', 'nowordc', 'loops:0', 'loops:1', 'loops:2', 'loops:16']
    for les in m.LESIONS:
        assert m.check_lesion(les)[0] == les
    print('ok copy_true_size_and_init')


def test_copy_true_runs():
    v, rows = vocab(), train_rows(48, 4)
    m = seeded(True, SMALL, v=v)
    b = batch_of(rows, v)
    loss, aux = m.loss(b)
    assert torch.isfinite(loss) and all(torch.isfinite(x) for x in aux.values()) and 'copy_share' in aux
    loss.backward()
    for mod in NEW:
        gs = [p.grad.abs().sum().item() for n, p in getattr(m, mod).named_parameters() if n == 'weight']
        assert gs and all(x > 0 for x in gs), (mod, gs)
        print(f'  grad |weight| {mod}: {gs[0]:.4g}')
    m.eval()
    assert m.supports_donor()
    out = m.generate(b)
    assert len(out) == 48 and all(isinstance(x, str) for x in out)
    for les in [None] + m.LESIONS + [f'loops:{k}' for k in (0, 1, 2, 8)]:
        r = evaluate(m, rows, 32, 'cpu', les)
        assert r['n'] == 48, les
        assert all(isinstance(x, str) for x in m.generate(b, lesion=les)), les
    d = donor_eval(m, rows, 32, 'cpu')
    assert 'exact' in d and 'donor_match' in d
    # no leak: states and answers do not depend on answers / steps (copy keys come from the prompt only)
    b2 = batch_of(rows, v)
    b2['rows'] = [{k: x for k, x in r.items() if k not in ('answer', 'steps', 'accepted')} for r in rows]
    b2['ans_ids'], b2['ans_mask'] = torch.zeros_like(b2['ans_ids']), torch.zeros_like(b2['ans_mask'])
    with torch.no_grad():
        for kw in (dict(), dict(loops=1), dict(lesion='noexec'), dict(lesion='nowordc')):
            assert all(torch.equal(x, y) for x, y in zip(m.state(b, **kw), m.state(b2, **kw))), kw
        for les in (None, 'nocopy'):
            assert m.talk(m.state(b), b, les) == m.talk(m.state(b2), b2, les)
    print('ok copy_true_runs')


def test_lesion_semantics():
    """nocopy = vocabulary only; gate 0 = copy only (outputs are prompt chars, taken from the CURRENT batch even under a donor state);
    nowordc = the WORD keys without the content term; the content term is zero for empty words."""
    v, rows = vocab(), train_rows(64, 9)
    m = seeded(True, SMALL, 1, v).eval()
    b, cur, don = batch_of(rows, v), batch_of(rows[:32], v), batch_of(rows[32:], v)
    with torch.no_grad():
        o = m.run(b)
        p, g = m.gen_copy(o['R'], o['X'], o['xm'], b['prompt_ids'])
        assert torch.allclose(p.sum(-1), torch.ones(p.shape[:2]), atol=1e-4)                       # a distribution
        p0, g0 = m.gen_copy(o['R'], o['X'], o['xm'], b['prompt_ids'], nocopy=True)
        assert (g0 == 1).all() and torch.allclose(p0, m.readout(o['R']).float().softmax(-1), atol=1e-6)
        force = lambda lm: tuple(lm if i == 3 else x for i, x in enumerate(m.state(b)))
        gen_mode = torch.tensor([0., 0, 5]).expand(len(rows), -1)                                   # force every row to GEN
        st = force(gen_mode)
        ref = [m.vocab.decode(r)[::-1] for r in m.readout(st[0]).argmax(-1).tolist()]
        assert m.talk(st, b, 'nocopy') == ref                                                       # lesion nocopy = the B readout
        m.g_cp.bias.fill_(-50.0)                                                                    # gate 0: copy only
        outs = m.talk(st, b)
        assert all(set(x) <= set(r['prompt']) for x, r in zip(outs, rows)), 'copy-only output must be prompt characters'
        assert any(outs) and outs != ref
        st_don = tuple(x[32:] for x in st)                                                           # donor state (rows 32..63), recipient batch rows 0..31
        outs = m.talk(st_don, cur)
        assert all(set(x) <= set(r['prompt']) for x, r in zip(outs, rows[:32])), 'the copy source is the CURRENT batch'
        m.g_cp.bias.zero_()
        # nowordc
        l_int, l_no = m.run(b)['lword'], m.run(b, lesion='nowordc')['lword']
        assert not torch.equal(l_int, l_no)
        k0 = m.k_wc.weight.clone()
        m.k_wc.weight.zero_()
        assert torch.equal(m.run(b)['lword'], l_no)                                                  # no content term == k_wc zeroed
        m.k_wc.weight.copy_(k0)
        ns, ne, nv, ws, we = m.tokenize(b)
        wc = m.word_content(o['X'], ws, we)
        assert (wc[we == ws] == 0).all() and (wc[we > ws].abs().sum(-1) > 0).all()
    print('ok lesion_semantics')


def test_extra_copy_gate():
    v = vocab()
    m = seeded(True, SMALL, 2, v).eval()
    tmp = tempfile.mkdtemp()
    os.makedirs(tmp + '/dev')
    dev = load_rows(os.path.join(DEFAULT_DATA, 'dev', 'in_dist.jsonl'))
    sample = random.Random(1).sample(dev, 300)
    with open(tmp + '/dev/in_dist.jsonl', 'w') as f:
        for r in sample:
            f.write(json.dumps(r) + '\n')
    ctx = dict(data=tmp, big=None, device=torch.device('cpu'), batch_size=64, amp=contextlib.nullcontext)
    gen = [r for r in sample if pp.row_targets(r)['mode'] == 2]
    want = {}
    for r in gen:
        want[r['family']] = want.get(r['family'], 0) + len(r['answer'][:MAX_ANS])                   # registers that hold a target char (EOS excluded)
    for bias, expect in ((-50.0, 1.0), (50.0, 0.0)):                                                 # gate 0: every target register copies; gate 1: none
        with torch.no_grad():
            m.g_cp.bias.fill_(bias)
        cg = m.copy_gate_eval(sample, ctx)
        assert cg['n_regs'] == want and cg['n_rows'] == len(gen), (cg['n_regs'], want)
        assert all(abs(x - expect) < 1e-6 for x in cg['by_family'].values()) and abs(cg['overall'] - expect) < 1e-6, cg
    with torch.no_grad():
        m.g_cp.bias.zero_()
    ex = m.extra_evals(ctx)                                                                          # the full extra eval: B's keys plus copy_gate
    json.dumps(ex)
    assert {'coverage', 'op_acc', 'noexec', 'opswap', 'copy_gate'} <= set(ex), set(ex)
    assert set(ex['copy_gate']) == {'by_family', 'n_regs', 'overall', 'n_rows'} and 0 <= ex['copy_gate']['overall'] <= 1
    print(f"  copy_gate over {len(gen)} GEN rows of {len(sample)}: {json.dumps({f: round(x, 3) for f, x in ex['copy_gate']['by_family'].items()})}")
    assert 'copy_gate' not in seeded(False, SMALL, 2, v).eval().extra_evals(dict(ctx, data=tmp))     # copy=False: extra evals as before
    print('ok extra_copy_gate')


# ---- the mechanism: copy a letter that was never an answer in training ---------------------------------------------------
MECH_CFG = dict(d=64, n_heads=2, reader_layers=1, blocks=1, n_loops=4, mlp=2.0)
MECH_STEPS, MECH_CAP_S = 700, 110


def first_letter_rows(n, letters, tag, seed):
    """'What is the first letter of zijovonu?' -> 'z'. The answer is one letter, never a whole prompt word, so progparse gives GEN mode."""
    rng, out = random.Random(seed), []
    for i in range(n):
        w = rng.choice(letters) + ''.join(rng.choice(string.ascii_lowercase) for _ in range(rng.randint(4, 7)))
        out.append(dict(id=f'syn_first_{tag}_{i}', prompt=f'What is the first letter of {w}?', answer=w[0], accepted=[w[0]], family='first_letter', level=1, steps=[]))
    assert all(pp.row_targets(r)['mode'] == 2 for r in out)
    return out


def train_first_letter(copy, rows, v, seed=0, bs=64, lr=2e-3):
    torch.manual_seed(seed)
    m = Ledger(v, copy=copy, **MECH_CFG)
    opt = torch.optim.AdamW(m.parameters(), lr=lr, weight_decay=0.0)
    ds, rng, t0 = Dataset(rows, v), random.Random(seed), time.time()
    for step in range(MECH_STEPS):
        loss, aux = m.loss(collate([ds[i] for i in rng.sample(range(len(rows)), bs)]))
        loss.backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        opt.step(); opt.zero_grad()
        if time.time() - t0 > MECH_CAP_S:
            break
    print(f'  copy={copy}: {step + 1} steps, final loss {loss.item():.4f}, {time.time() - t0:.0f}s')
    return m.eval()


def test_mechanism_first_letter():
    """Train words start with a-m (a-m answers), test words start with n-z (answers never seen in training). copy=True gets the test rows,
    copy=False cannot (it can only say what it said in training); nocopy removes the gain; a donor state still copies the recipient's letter."""
    torch.set_num_threads(min(torch.get_num_threads(), 2))
    v = CharVocab.build([])
    assert len(v) == 108
    tr = first_letter_rows(4000, string.ascii_lowercase[:13], 'train', 0)
    dev = first_letter_rows(200, string.ascii_lowercase[:13], 'dev', 2)        # unseen words, trained letters
    te = first_letter_rows(200, string.ascii_lowercase[13:], 'test', 1)        # untrained answer letters
    res = {}
    for copy in (False, True):
        m = train_first_letter(copy, tr, v)
        r = res[copy] = dict(dev=evaluate(m, dev, 100, 'cpu')['exact'], test=evaluate(m, te, 100, 'cpu')['exact'])
        r['donor_dev'], r['donor_test'] = donor_eval(m, dev, 100, 'cpu'), donor_eval(m, te, 100, 'cpu')
        if copy:
            r['nocopy_test'], r['nocopy_dev'] = evaluate(m, te, 100, 'cpu', 'nocopy')['exact'], evaluate(m, dev, 100, 'cpu', 'nocopy')['exact']
            r['shuffle_test'] = evaluate(m, te, 100, 'cpu', 'shuffle_state')['exact']
        print(f"  copy={copy}: trained letters a-m {r['dev']:.1f}%, new letters n-z {r['test']:.1f}%; donor swap on n-z: exact {r['donor_test']['exact']:.1f}%, "
              f"donor_match {r['donor_test']['donor_match']:.1f}%" + (f"; nocopy: a-m {r['nocopy_dev']:.1f}% n-z {r['nocopy_test']:.1f}%" if copy else ''))
    f, t = res[False], res[True]
    assert f['dev'] >= 70, f"copy=False did not learn the task on the trained letters ({f['dev']}%, chance 8%): the comparison would mean nothing"
    assert f['test'] <= 10, f"copy=False emitted untrained letters: {f['test']}%"
    assert t['dev'] >= 90 and t['test'] >= 90, (t['dev'], t['test'])
    assert t['test'] - f['test'] >= 80
    assert t['nocopy_test'] <= 10, f"the gain must come from the copy path: nocopy n-z {t['nocopy_test']}%"
    assert t['donor_test']['exact'] >= 90 and t['donor_test']['donor_match'] <= 10        # the state says where to copy, the prompt says what
    assert f['donor_dev']['donor_match'] >= 90                                              # B's GEN registers carry the letter in the state itself
    print('ok mechanism_first_letter')


if __name__ == '__main__':
    torch.set_num_threads(min(torch.get_num_threads(), 2))
    t0 = time.time()
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            t = time.time()
            fn()
            print(f'  [{name} {time.time() - t:.0f}s]')
    print(f'all ok ({time.time() - t0:.0f}s)')
