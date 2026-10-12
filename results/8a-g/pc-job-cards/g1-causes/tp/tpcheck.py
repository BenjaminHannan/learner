# CPU check for install_tp.ps1, run from the new src-tp folder: python tpcheck.py PATH_TO_G1_LEDGER.py (src-8ag\custom_io\models\ledger.py).
# No EmbeddingGemma weights and no GPU: eg_embed models are built on torch's meta device (shapes only); behaviour is tested with eg_embed False.
#  (i)   self_prog=0 is G1: same state_dict at the same seed, and loss, every aux value and every grad bit-identical to G1's own ledger.py
#  (ii)  G1's 3M B2 cfg + self_prog 8 = the same 3,544,913 trained params as G1's, the band check passes, b2-extra reaches the train.py --cfg
#  (iii) the hit picker (pure function) on hand-made programs
#  (iv)  loss() with self_prog 8: runs, finite, backward, aux keys; with the sampler replaced by known programs the written targets are right
#        and a teacher-forced run() reproduces the gold value at the hit's result slot; a candidate with no hit gets NOOP weight 0
#  (v)   queue 8aTP parses (2 entries), the g8a line's --b2-extra is {"eg_embed": true, "self_prog": 8}
import sys, os, json, importlib.util
import torch
sys.path.insert(0, '.')
torch.set_num_threads(min(torch.get_num_threads(), 2))
from custom_io.local_runner import parse_queue
from custom_io.g8a import caps as CP, configs as C
from custom_io.data import Dataset, collate
from custom_io.models import progparse as pp

ORIG = sys.argv[1]
caps = json.load(open('custom_io/g8a/caps_g.json'))
CP.apply(caps)                      # patches custom_io.models.ledger (the new file) and progparse, like train.py --caps
from custom_io.models import ledger as NEW
assert NEW.pick_hits and NEW.Ledger.__init__.__code__.co_varnames.count('self_prog') == 1, 'custom_io.models.ledger is not the T-P file'
spec = importlib.util.spec_from_file_location('ledger_g1_orig', ORIG)
OLD = importlib.util.module_from_spec(spec)
spec.loader.exec_module(OLD)
for k, v in dict(N_NUM=pp.N_NUM, N_RES=pp.N_RES, W_MAX=pp.W_MAX, R0=pp.R0, M=pp.M).items():     # the same patch caps.apply gives custom_io.models.ledger
    setattr(OLD, k, v)
OLD.N_REG, OLD.GEN_MAX = caps['n_reg'], caps['n_reg'] - 1
assert not hasattr(OLD, 'pick_hits') and 'self_prog' not in OLD.Ledger.__init__.__code__.co_varnames, f'{ORIG} is not G1\'s ledger.py'
assert (NEW.N_NUM, NEW.N_RES, NEW.M, NEW.R0, NEW.N_REG, NEW.GEN_MAX) == (OLD.N_NUM, OLD.N_RES, OLD.M, OLD.R0, OLD.N_REG, OLD.GEN_MAX) == (91, 11, 106, 95, 36, 35)
N_LOOPS = CP.n_loops_needed(caps)
assert N_LOOPS == 12
V = C.vocab()
G1 = dict(d=256, n_heads=4, reader_layers=2, blocks=2, n_loops=N_LOOPS, mlp=4.8, copy=True)      # G1's 3M B2 without the Gemma front


def row(i, prompt, answer, steps=(), fam='t'):
    return dict(id=f'tp_{i}', prompt=prompt, answer=answer, accepted=[answer], family=fam, level=1, steps=list(steps))


ROWS = [
    row(0, 'Tom has 12 apples and buys 5 more. How many apples does he have?', '17', ['12 + 5 = 17'], 'arith'),          # program, NUM
    row(1, 'Ann has 30 coins and spends 8. How many are left?', '22', ['30 - 8 = 22'], 'arith'),                          # program, NUM
    row(2, 'Which is larger, 41 or 87? Answer with the number.', '87', [], 'pick'),                                         # no program, answer is a prompt number: NUM
    row(3, 'The capital of France is ____.', 'Paris', [], 'cloze'),                                                         # cloze-like GEN
    row(4, 'The river runs through the ____ of the old town.', 'centre', [], 'cloze'),                                      # cloze-like GEN
    row(5, 'What is 17 plus 25?', '42', [], 'table_lookup'),                                                                 # integer GEN, no steps (candidate)
    row(6, 'What is 3 plus 4 plus 5?', '12', [], 'seq_next'),                                                                # candidate
    row(7, 'Name the number after 7, 14, 21, 28.', '35', [], 'seq_next'),                                                    # candidate
    row(8, 'Copy the word apple: apple', 'apple', [], 'copy'),                                                               # WORD
]


def batch_of(rows):
    ds = Dataset(rows, V, strict=False)
    return collate([ds[i] for i in range(len(rows))])


def seeded(mod, seed=11, **cfg):
    torch.manual_seed(seed)
    return mod.Ledger(V, **cfg)


# ---- (i) identity at self_prog = 0
old, new = seeded(OLD, **G1), seeded(NEW, self_prog=0, **G1)
sa, sb = old.state_dict(), new.state_dict()
assert list(sa) == list(sb) and all(torch.equal(sa[k], sb[k]) for k in sa), 'state_dict differs at the same seed'
assert old.n_params() == new.n_params()
b = batch_of(ROWS)
lo, ao = old.loss(b)
ln, an = new.loss(b)
lo.backward(); ln.backward()
assert torch.equal(lo, ln) and list(ao) == list(an) and all(torch.equal(ao[k], an[k]) for k in ao), (lo, ln, ao, an)
bad = [n for (n, p), q in zip(old.named_parameters(), new.parameters()) if not ((p.grad is None and q.grad is None) or torch.equal(p.grad, q.grad))]
assert not bad, f'grads differ: {bad[:5]}'
for les in (None, 'noexec', 'opswap'):          # free-run outputs too
    with torch.no_grad():
        assert old.generate(b, lesion=les) == new.generate(b, lesion=les), les
print('(i) identity: %d params, state_dict equal at one seed; loss %.6f and %d aux values and %d grads bit-identical with self_prog=0' % (new.n_params(), ln.item(), len(an), sum(1 for _ in new.parameters())))
assert 'sp_cand' not in an

# ---- (ii) size, bands, b2-extra -> cfg, on the meta device (EmbeddingGemma is never loaded: FrozenEG is lazy)
extra = dict(eg_embed=True, self_prog=8, n_loops=N_LOOPS)
with torch.device('meta'):
    cfgs, counts = C.sizes('3M', extra)
    cfg0 = dict(cfgs['B2']); cfg0.pop('self_prog')
    g1 = OLD.Ledger(V, **cfg0).n_params()
    keys_old = {k: tuple(t.shape) for k, t in OLD.Ledger(V, **cfg0).state_dict().items()}
    keys_new = {k: tuple(t.shape) for k, t in NEW.Ledger(V, **cfgs['B2']).state_dict().items()}
C.check_bands('3M', cfgs, counts, exact_3m=False)
assert counts['B2'] == g1 == 3_544_913 and keys_old == keys_new, (counts, g1)
assert cfgs['B2'] == dict(d=256, n_heads=4, reader_layers=2, blocks=2, n_loops=12, mlp=4.8, copy=True, eg_embed=True, self_prog=8), cfgs['B2']
targs = C.train_args('3M', 'B2', 400, 24000, 'POOL', b2_extra=extra, caps='caps.json')
assert json.loads(targs[targs.index('--cfg') + 1]) == cfgs['B2']
print('(ii) 3M B2 + self_prog 8: %s trained (G1 %s), same state_dict keys and shapes, band ok, in train.py --cfg: %s' % ('{:,}'.format(counts['B2']), '{:,}'.format(g1), targs[targs.index('--cfg') + 1]))

# ---- (iii) the hit picker
R0, L, M_, K = NEW.R0, NEW.N_RES, NEW.M, 4


def mk(progs, n=1):
    """progs: n lists of K samples; a sample = list of (op, result value, valid) per step. -> ops [n*K, L], vals [n*K, M], valid [n*K, M]"""
    ops, vals, valid = torch.zeros(n * K, L, dtype=torch.long), torch.zeros(n * K, M_, dtype=torch.long), torch.zeros(n * K, M_, dtype=torch.bool)
    for i, row_samples in enumerate(progs):
        for j, sm in enumerate(row_samples):
            for s, (op, v, ok) in enumerate(sm):
                ops[i * K + j, s], vals[i * K + j, R0 + s], valid[i * K + j, R0 + s] = op, v, ok
    return ops, vals, valid


def pick(progs, gold):
    n = len(gold)
    return [x.tolist() for x in NEW.pick_hits(*mk(progs, n), torch.tensor(gold), K)]


ADD, MUL = 1, 3
hit1, hit2, junk = [(ADD, 42, True)], [(ADD, 7, True), (MUL, 42, True)], [(ADD, 5, True)]
assert pick([[junk, hit2, hit1, junk]], [42]) == [[True], [1], [2]], 'shortest wins'
assert pick([[hit2, hit1, hit1, junk]], [42]) == [[True], [1], [1]], 'tie: lowest sample index'
assert pick([[hit2, junk, hit2, junk]], [42]) == [[True], [2], [0]], 'tie at length 2: sample 0'
assert pick([[junk, junk, junk, junk]], [42]) == [[False], [0], [0]], 'no sample hits'
assert pick([[[(0, 42, True)], [(ADD, 7, True), (0, 42, True)], junk, junk]], [42]) == [[False], [0], [0]], 'a NOOP step is not a hit'
assert pick([[[(ADD, 7, True), (0, 7, True), (ADD, 42, True)], junk, junk, junk]], [42]) == [[False], [0], [0]], 'NOOP mid-program breaks the run: later value is not a hit'
assert pick([[[(ADD, 42, False)], [(ADD, 7, False), (MUL, 42, True)], junk, junk]], [42]) == [[False], [0], [0]], 'an invalid step is not a hit, nor is anything after it'
assert pick([[[(ADD, 41, True)], [(ADD, 43, True), (ADD, 44, True)], junk, junk]], [42]) == [[False], [0], [0]], 'wrong value is not a hit'
assert pick([[[(ADD, 7, True), (MUL, 42, True)], junk, junk, junk]], [42]) == [[True], [2], [0]], 'value at step 2 after a valid step 1 is a hit of length 2'
assert pick([[[(ADD, 42, True), (ADD, 9, True)], junk, junk, junk]], [42]) == [[True], [1], [0]], 'a later wrong step does not undo the hit'
assert pick([[[(ADD, 7, True), (ADD, 8, True), (MUL, 42, True)], junk, junk, junk]], [42]) == [[True], [3], [0]], 'length 3'
assert pick([[junk, junk, hit1, junk], [hit2, junk, junk, junk], [junk, junk, junk, junk]], [42, 42, 42]) == [[True, True, False], [1, 2, 0], [2, 0, 0]], 'rows are independent'
assert pick([[junk, junk, hit1, junk], [junk, hit1, junk, junk]], [5, 42]) == [[True, True], [1, 1], [0, 1]], 'each row has its own gold value (junk is 5 for row 0)'
print('(iii) pick_hits: 12 cases ok')

# ---- (iv) loss with self_prog = 8
sp = seeded(NEW, self_prog=8, **G1)
assert all(torch.equal(sp.state_dict()[k], sa[k]) for k in sa), 'self_prog changed the init'
# the real sampler on the mixed batch: every hit it finds is reproduced by teacher forcing; runs, finite, backward
nreal = 0
for seed in range(12):
    torch.manual_seed(seed)
    gx, nh_, sx = sp.self_programs(b, sp.gold(b['rows'], 'cpu'))
    with torch.no_grad():
        ox = sp.run(b, gold=gx)
    for i in (5, 6, 7):
        if bool(gx['has'][i]):
            nreal += 1
            sl = int((gx['op'][i] > 0).sum())
            assert gx['mode'][i].item() == 0 and int(ox['vals'][i, R0 + sl - 1]) == int(b['rows'][i]['answer']) and bool(ox['valid'][i, R0 + sl - 1]), (seed, i)
assert nreal > 0, 'the real sampler found no hit in 12 tries (the reproduction check had nothing to test)'
torch.manual_seed(0)
loss, aux = sp.loss(b)
loss.backward()
assert torch.isfinite(loss) and all(torch.isfinite(v) for v in aux.values()), (loss, aux)
assert all(torch.isfinite(p.grad).all() for p in sp.parameters() if p.grad is not None)
assert abs(aux['sp_cand'].item() - 3 / len(ROWS)) < 1e-6, aux['sp_cand']          # rows 5, 6, 7
assert {'sp_cand', 'sp_hit', 'sp_len'} <= set(aux) and set(aux) - {'sp_cand', 'sp_hit', 'sp_len'} == set(an)
print('(iv-a) real sampler, 9 mixed rows: %d hits in 12 draws all reproduced by teacher forcing; loss %.4f finite, backward ok, sp_cand %.4f sp_hit %.4f sp_len %.4f' % (nreal, loss.item(), aux['sp_cand'], aux['sp_hit'], aux['sp_len']))
# rep > 1 with argmax is the same program per sample as rep = 1
with torch.no_grad():
    sub = batch_of(ROWS[5:8])
    o1, o3 = sp.run(sub), sp.run(sub, rep=3)
    assert o3['vals'].shape[0] == 9 and torch.equal(o3['vals'], o1['vals'].repeat_interleave(3, 0)) and all(torch.equal(x.repeat_interleave(3, 0), y) for x, y in zip(o1['prog'], o3['prog']))
    os_ = sp.run(sub, rep=5, sample_t=1.0)
    assert os_['vals'].shape[0] == 15 and os_['prog'][0].shape == (15, L)
    assert (os_['prog'][1] < M_).all() and bool(os_['valid'].gather(1, os_['prog'][1][:, :1]).all()), 'sampled operands must be valid slots'
print('(iv-b) run(rep=3) = run() repeated; run(rep=5, sample_t=1) shapes and valid operands ok')

# the sampler replaced by known programs (a row's list of samples; every other sample is an idle NOOP program)
def prog_of(steps):
    """[(op, a, b)] -> teacher-forcing tensors for a one-row run"""
    op = torch.zeros(1, L, dtype=torch.long)
    A, B_ = torch.zeros(1, L, M_, dtype=torch.bool), torch.zeros(1, L, M_, dtype=torch.bool)
    for s in range(L):
        o, a, bb = steps[s] if s < len(steps) else (0, 0, 0)
        op[0, s], A[0, s, a], B_[0, s, bb] = o, True, True
    return dict(op=op, a=A, b=B_)


C0 = pp.N_NUM        # prompt numbers are slots 0..N_NUM-1; the constants 1 2 10 100 follow (C0 holds 1)
KNOWN = {      # prompt -> {sample index: program}
    'What is 17 plus 25?': {1: [(ADD, 0, 1), (MUL, R0, C0)], 3: [(ADD, 0, 1)], 6: [(ADD, 0, 1)]},        # 2-step hit, then two 1-step hits: sample 3 wins
    'What is 3 plus 4 plus 5?': {2: [(ADD, 0, 1), (ADD, R0, 2)], 5: [(ADD, 0, 1), (ADD, 1, 2)]},                                                   # 2-step hit at sample 2; sample 5 is a miss
    'Name the number after 7, 14, 21, 28.': {4: [(ADD, 0, 1)]},                                                                                     # no hit (7 + 14 = 21)
}
real_run = NEW.Ledger.run
calls = []


def fake_run(self, batch, *a, rep=1, sample_t=None, **k):
    if rep == 1:
        return real_run(self, batch, *a, **k)
    calls.append((len(batch['rows']), rep, sample_t))
    outs = []
    for r in batch['rows']:
        for j in range(rep):
            st = KNOWN[r['prompt']].get(j, [])
            one = {k_: (batch[k_][[batch['rows'].index(r)]] if torch.is_tensor(batch[k_]) else [r]) for k_ in batch}
            with torch.no_grad():
                o = real_run(self, one, gold=prog_of(st))
            outs.append(o)
    cat = lambda f: torch.cat([f(o) for o in outs], 0)
    return dict(prog=tuple(cat(lambda o, i=i: o['prog'][i]) for i in range(3)), vals=cat(lambda o: o['vals']), valid=cat(lambda o: o['valid']))


NEW.Ledger.run = fake_run
try:
    sp = seeded(NEW, self_prog=8, **G1)
    g0 = sp.gold(b['rows'], 'cpu')
    g0 = {k_: v.clone() for k_, v in g0.items()}
    g, cand_nh, spd = sp.self_programs(b, {k_: v.clone() for k_, v in g0.items()})
    assert calls == [(3, 8, 1.0)], calls                      # one sampler call on the 3 candidates, K = 8, temperature 1
    # untouched rows: every target equal to gold()'s
    for i in (0, 1, 2, 3, 4, 8):
        assert all(torch.equal(g[k_][i], g0[k_][i]) for k_ in g0), i
    assert cand_nh.tolist() == [False] * 7 + [True, False], cand_nh.tolist()
    # row 5: hit of length 1 at sample 3 (the 2-step sample 1 and the tied sample 6 lose)
    for i, s, prog, gold in ((5, 1, [(ADD, 0, 1)], 42), (6, 2, [(ADD, 0, 1), (ADD, R0, 2)], 12)):
        assert g['op'][i].tolist() == [o for o, _, _ in prog] + [0] * (L - len(prog)), (i, g['op'][i])
        for j in range(L):
            if j < s:
                assert g['a'][i, j].nonzero()[:, 0].tolist() == [prog[j][1]] and g['b'][i, j].nonzero()[:, 0].tolist() == [prog[j][2]], (i, j)
            else:
                assert g['a'][i, j].nonzero()[:, 0].tolist() == [0] and g['b'][i, j].nonzero()[:, 0].tolist() == [0], (i, j)     # what gold() leaves for padding
        assert g['mode'][i].item() == 0 and g['ans'][i].nonzero()[:, 0].tolist() == [R0 + s - 1] and (g['gen'][i] == -100).all() and bool(g['has'][i])
        assert g0['mode'][i].item() == 2 and not bool(g0['has'][i])                                 # it was a GEN row without a program
        assert torch.equal(g['word'][i], g0['word'][i])
    # row 7 (candidate without a hit) keeps its GEN target and the no-hit flag; row 3's cloze answer is no candidate
    assert g['mode'][7].item() == 2 and torch.equal(g['gen'][7], g0['gen'][7]) and not bool(g['has'][7])
    assert abs(spd['sp_cand'].item() - 3 / 9) < 1e-6 and abs(spd['sp_hit'].item() - 2 / 3) < 1e-6 and abs(spd['sp_len'].item() - 1.5) < 1e-6, spd
    # teacher-forced run() reproduces the gold value at the written result slot
    with torch.no_grad():
        o = real_run(sp, b, gold=g)
    for i, s, gold in ((5, 1, 42), (6, 2, 12)):
        assert int(o['vals'][i, R0 + s - 1]) == gold and bool(o['valid'][i, R0 + s - 1]) and int(o['vals'][i, R0 + s - 1]) == int(b['rows'][i]['answer']), (i, o['vals'][i, R0:R0 + 3])
    # the full loss: finite, backward, weights (the no-hit candidate's NOOP steps weigh 0; the hit rows' weigh 1)
    loss, aux = sp.loss(b)
    loss.backward()
    assert torch.isfinite(loss) and all(torch.isfinite(p.grad).all() for p in sp.parameters() if p.grad is not None)
    assert abs(aux['sp_hit'].item() - 2 / 3) < 1e-6
    only = batch_of([ROWS[7]])                  # a lone no-hit candidate: NOOP weight 0, so its program loss is exactly 0
    l_sp, a_sp = sp.loss(only)
    l_g1, a_g1 = seeded(NEW, self_prog=0, **G1).loss(only)
    assert a_sp['prog'].item() == 0.0 and a_g1['prog'].item() > 0.0, (a_sp['prog'], a_g1['prog'])
    assert torch.equal(a_sp['gen'], a_g1['gen']) and torch.equal(a_sp['mode'], a_g1['mode']), 'a no-hit row keeps its GEN and mode targets'
    hit_only = batch_of([ROWS[5]])              # a lone hit row is trained like a parsed program (op weight 1) in NUM mode
    l_h, a_h = sp.loss(hit_only)
    assert a_h['prog'].item() > 0 and abs(a_h['sp_hit'].item() - 1) < 1e-9 and a_h['gen'].item() == 0.0 and a_h['sp_len'].item() == 1.0, a_h
finally:
    NEW.Ledger.run = real_run
print('(iv-c) known programs: targets for the length-1 and length-2 hits, the no-hit candidate, untouched rows, teacher-forced vals[R0+s-1]==gold, weights: ok')

# ---- (v) the queue
r = parse_queue('custom_io/queue_local/8aTP-pc.txt', work='W')
assert len(r) == 2 and r[0][0] == '8a-data' and r[1][0] == '8aTP-3M-s400' and r[1][1] == 'g8a', [x[:2] for x in r]
args = r[1][2]
assert args[args.index('--b2-extra') + 1] and json.loads(args[args.index('--b2-extra') + 1]) == {'eg_embed': True, 'self_prog': 8}, args
assert args[args.index('--rung') + 1] == '3M' and args[args.index('--seed') + 1] == '400' and args[args.index('--arms') + 1:args.index('--arms') + 2] == ['B2']
assert C.RUNGS['3M']['own_rung'] == 10 and C.RUNGS['3M']['web'] == 'rung30'            # the pool key p10-rung30-s400-a64 (G1's, reused)
from custom_io.g8a import job as J
assert J.parse_accum(args[args.index('--accum') + 1], None, '3M') == {'B2': 4}
assert r[1][3] == 9000, r[1][3]
print('(v) queue 8aTP: %s' % ' | '.join('%s mem %d' % (x[0], x[3]) for x in r))
print('TP CPU CHECK OK')
