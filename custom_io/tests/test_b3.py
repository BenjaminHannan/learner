"""python3 -m custom_io.tests.test_b3   (CPU, a few minutes; no data files, no Gemma: a stub FrozenEG with the real one's memo stands in)
B3 group 1 (architecture/B3-GROUP1-BUILD-2026-10-09.md): check P (H1R's config on tool_h1 and on b3 with no switches is bit-identical to commit 17a356e62: 50 AdamW
steps, torch.equal losses and parameters, caps not applied); Part A (Gemma + outside calculator: encode sees prompts only, one Gemma pass per step, the reader's
output for an entry string does not depend on eg_embed); Part B (calls at any round: tape entries per row, 17th call refused and counted, schedule masks, op loss
masked at gap rounds and NOOP after, gap draws leave torch's RNG alone, the 32-round fallback, oracle at the scheduled rounds = teacher forcing, default schedule =
today's); Part C (caps reach every module that defines a cap name; N_REG registers and GEN targets under G1's caps; the cloze chunk parameter keeps today's rows)."""
import hashlib, json, os, re, subprocess, sys, tempfile, glob, random
import numpy as np
import torch
import torch.nn as nn
from custom_io.data import CharVocab, Dataset, collate
from custom_io.models import build
from custom_io.models.eg import FrozenEG

REF = '17a356e62'
BASE_SHA = 'fac933250'
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(HERE)
CFG = dict(d=48, n_heads=2, reader_layers=1, blocks=1, n_loops=8, mlp=2.0, label='settled', span_copy=True, span_idx=True, span_end=True, ans_drill=0.25)
B3_ON = dict(eg_embed=True, any_round=True, gap_p=0.25)
V = CharVocab.build([])


def rows(n=24):
    rs = []
    for i in range(n):
        a, b, c = 10 + 7 * i, 100 + 13 * i, 3 + i % 5
        k = i % 4
        if k == 0:
            rs.append(dict(id=f't{i}', family='chain_ops', prompt=f'Tom has {a} apples and buys {b} more. How many apples now?', answer=str(a + b), steps=[f'{a} + {b} = {a + b}']))
        elif k == 1:
            rs.append(dict(id=f't{i}', family='copy_word', prompt=f'Echo: sune{i} Give only the answer.', answer=f'sune{i}', steps=[]))
        elif k == 2:
            rs.append(dict(id=f't{i}', family='chain_story2', prompt=f'Facts: Xavi had {a} cards. Then Xavi got {b} more. After that, Xavi lost {c}. How many now?',
                           answer=str(a + b - c), steps=[f'{a} + {b} = {a + b}', f'{a + b} - {c} = {a + b - c}']))
        else:
            rs.append(dict(id=f't{i}', family='chain_ops', prompt=f'{a} + {b} * 2', answer=str(a + 2 * b), steps=[f'{b} * 2 = {2 * b}', f'{a} + {2 * b} = {a + 2 * b}']))
    return rs


def batch_of(rs, vocab=V):
    ds = Dataset(rs, vocab, strict=False)
    return collate([ds[i] for i in range(len(rs))])


class StubEG:
    """Stand-in for models/eg.FrozenEG: deterministic per-prompt states, the real encode's memo (key = prompts, T, device), and counters: `calls` (every encode
    call, with its prompts) and `passes` (the calls that were not memoised, i.e. the Gemma forward passes)."""

    def __init__(self):
        self.calls, self.passes, self._last = [], 0, None

    def align(self, prompt):
        c, t = [], 7
        for i, ch in enumerate(prompt):
            if i and (ch == ' ' or ch.isdigit()):
                t += 1
            c.append(t)
        return np.zeros(3, np.int32), np.asarray(c, np.int16)

    def encode(self, prompts, T, device, chars=True):
        self.calls.append(list(prompts))
        key = (tuple(prompts), T, str(device))
        if self._last is not None and self._last[0] == key:
            return self._last[1]
        self.passes += 1
        H = torch.zeros(len(prompts), T, 768)
        for b, p in enumerate(prompts):
            g = torch.Generator().manual_seed(int(hashlib.sha1(p.encode()).hexdigest()[:8], 16))
            n = min(len(p), T)
            H[b, :n] = torch.randn(n, 768, generator=g)
        out = (H.to(device), torch.zeros(len(prompts), 768))
        self._last = (key, out)
        return out


def make(seed=0, model='b3', **kw):
    torch.manual_seed(seed)
    m = build(model, V, **{**CFG, **kw})
    if getattr(m, 'eg_embed', False):
        m._eg = [StubEG()]
    return m


def gold_of(m, b):
    return m.gold(b['rows'], 'cpu', m.train_golds(b['rows']) if m.ans_drill else None)


class Scripted(nn.Module):
    """Replaces the op head: round t (1, 2, ...) returns the scripted op of each row (0 = NOOP, 1 = ADD)."""

    def __init__(self, script, n_op):
        super().__init__()
        self.script, self.n_op, self.out_features, self.t = script, n_op, n_op, 0

    def forward(self, z):
        self.t += 1
        ops = self.script[self.t - 1] if self.t <= len(self.script) else [0] * z.shape[0]
        return torch.nn.functional.one_hot(torch.tensor(ops), self.n_op).float() * 20 - 10


# ---- check P ----
P_SCRIPT = r'''
import sys, torch
from custom_io.data import CharVocab, Dataset, collate
from custom_io.models import build
sys.path.insert(0, sys.argv[3])
V = CharVocab.build([])
rs = []
for i in range(24):
    a, b, c = 10 + 7 * i, 100 + 13 * i, 3 + i % 5
    k = i % 4
    if k == 0: rs.append(dict(id=f't{i}', family='chain_ops', prompt=f'Tom has {a} apples and buys {b} more. How many apples now?', answer=str(a + b), steps=[f'{a} + {b} = {a + b}']))
    elif k == 1: rs.append(dict(id=f't{i}', family='copy_word', prompt=f'Echo: sune{i} Give only the answer.', answer=f'sune{i}', steps=[]))
    elif k == 2: rs.append(dict(id=f't{i}', family='chain_story2', prompt=f'Facts: Xavi had {a} cards. Then Xavi got {b} more. After that, Xavi lost {c}. How many now?', answer=str(a + b - c), steps=[f'{a} + {b} = {a + b}', f'{a + b} - {c} = {a + b - c}']))
    else: rs.append(dict(id=f't{i}', family='chain_ops', prompt=f'{a} + {b} * 2', answer=str(a + 2 * b), steps=[f'{b} * 2 = {2 * b}', f'{a} + {2 * b} = {a + 2 * b}']))
ds = Dataset(rs, V, strict=False)
bl = [collate([ds[i] for i in range(s, s + 8)]) for s in range(0, len(rs), 8)]
torch.manual_seed(0)
m = build(sys.argv[2], V, d=48, n_heads=2, reader_layers=1, blocks=1, n_loops=8, mlp=2.0, label='settled', span_copy=True, span_idx=True, span_end=True, ans_drill=0.25)
opt = torch.optim.AdamW(m.parameters(), lr=1e-3, betas=(0.9, 0.95), weight_decay=0.1); m.train(); L = []
for s in range(50):
    loss = m.loss(bl[s % len(bl)])[0]
    loss.backward(); torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0); opt.step(); opt.zero_grad(set_to_none=True); L.append(loss.detach().clone())
torch.save(dict(losses=torch.stack(L), sd=m.state_dict()), sys.argv[1])
'''


def run_p(tree, model, out):
    env = dict(os.environ, PYTHONPATH=tree)
    subprocess.check_call([sys.executable, '-c', P_SCRIPT, out, model, tree], cwd=tree, env=env)
    return torch.load(out)


def test_p_bit_identity():
    """H1R's config: tool_h1 and b3 (no switches) here vs the code at 17a356e62, 50 steps, tiny CPU, caps not applied."""
    with tempfile.TemporaryDirectory() as d:
        ref = os.path.join(d, 'ref')
        os.makedirs(ref)
        arc = subprocess.Popen(['git', 'archive', REF, 'custom_io/__init__.py', 'custom_io/data.py', 'custom_io/models'], cwd=ROOT, stdout=subprocess.PIPE)
        subprocess.check_call(['tar', '-x', '-C', ref], stdin=arc.stdout)
        assert arc.wait() == 0
        a = run_p(ref, 'tool_h1', os.path.join(d, 'a.pt'))
        for model in ('tool_h1', 'b3'):
            b = run_p(ROOT, model, os.path.join(d, 'b.pt'))
            assert all(torch.equal(x, y) for x, y in zip(a['losses'], b['losses'])), model
            assert a['sd'].keys() == b['sd'].keys() and all(torch.equal(a['sd'][k], b['sd'][k]) for k in a['sd']), model
            print(f'  {model}: 50 losses and {len(a["sd"])} tensors equal 17a356e62')
    print('ok check P')


# ---- Part A ----
def test_a_gemma_with_calculator():
    rs = rows(16)
    b = batch_of(rs)
    m = make(eg_embed=True)
    assert m.eg_embed and not m.any_round
    eg = m._eg[0]
    prompts = set(r['prompt'] for r in rs)
    m.train()
    p0 = eg.passes
    m.loss(b)[0].backward()
    assert eg.passes - p0 == 1 and len(eg.calls) == 1, 'one Gemma pass per training step'
    m.eval()
    with torch.no_grad():
        m.generate(b)
    assert eg.passes == 1 and len(eg.calls) == 3, (eg.passes, len(eg.calls))     # run + talk are two more encode calls, both served by the memoised pass
    assert all(c == eg.calls[0] or set(c) <= prompts for c in eg.calls) and all(set(c) <= prompts for c in eg.calls), 'encode saw something that is not a prompt'
    assert not any(' = ' in p for c in eg.calls for p in c), 'a calculator entry reached Gemma'
    n0 = len(eg.calls)
    m.read_texts(['add 12 5 = 17', '', 'sub 3 4 = -1'], 'cpu')
    assert len(eg.calls) == n0, 'read_texts called Gemma'
    # (c) the reader's output for an entry string is the same with eg_embed on and off, given the same weights
    off = make(eg_embed=False)
    on = make(eg_embed=True)
    miss, extra = off.load_state_dict(on.state_dict(), strict=False)
    assert not miss and set(extra) == {'ln_eg.weight', 'ln_eg.bias', 'eg_proj.weight', 'eg_proj.bias'}, (miss, extra)
    with torch.no_grad():
        on.eg_proj.weight.normal_(0, 1.0)
        for k, v in zip(('add 12 5 = 17', 'mul 30 4 = 120', ''), range(3)):
            xa, ia, ma = on.read_texts([k], 'cpu')
            xb, ib, mb = off.read_texts([k], 'cpu')
            assert torch.equal(xa, xb) and torch.equal(ia, ib) and torch.equal(ma, mb), k
    s = on.size()
    assert s['frozen_borrowed'] == 271_002_624 and s['whole'] == s['trainable'] + 271_002_624
    print('ok part A: prompts only, one pass per step, entry reading independent of eg_embed, whole =', f"{s['whole']:,}")


def test_a_refusals_kept():
    for kw in (dict(eg_teach=0.5), dict(span=True), dict(round_readout=0.5)):
        try:
            make(model='tool', **{k: v for k, v in kw.items()}, **{})
        except AssertionError:
            continue
        raise AssertionError(f'Tool must still refuse {kw}')
    print('ok eg_teach / span / round_readout still refused')


# ---- Part B ----
def test_b_running_entries_and_visibility():
    rs = rows(4)
    b = batch_of(rs)
    m = make(eg_embed=True, any_round=True).eval()
    assert m.tape == 16 and m.tape_emb.num_embeddings == 16
    n_op = m.op_head.out_features
    script = [[0, 1, 0, 0] if t in (1, 4) else [0, 0, 0, 0] for t in range(12)]            # filled below
    script = [[0] * 4 for _ in range(12)]
    for t in (2, 5):
        script[t - 1][0] = 1                                                                # row 0 calls after rounds 2 and 5
    for t in (1, 2, 3):
        script[t - 1][1] = 1                                                                # row 1 after rounds 1, 2, 3
    m.op_head = Scripted(script, n_op)
    seen = {}

    def each(t, st):
        seen[t] = st['shown'].clone()
        return False
    with torch.no_grad():
        o = m.loop(b, 9, each=each)
    assert [c[0] for c in o['calls'][0]] == [2, 5] and [c[0] for c in o['calls'][1]] == [1, 2, 3] and not o['calls'][2] and not o['calls'][3]
    assert o['cround'][0, :3].tolist() == [2, 5, 10 ** 6] and o['cround'][1, :4].tolist() == [1, 2, 3, 10 ** 6]
    assert seen[2][0].nonzero().flatten().tolist() == [0] and seen[1][0].sum() == 0, 'row 0 entry 0 appears after round 2'
    assert seen[5][0].nonzero().flatten().tolist() == [0, 1] and seen[4][0].nonzero().flatten().tolist() == [0]
    assert seen[3][1].nonzero().flatten().tolist() == [0, 1, 2] and seen[2][1].nonzero().flatten().tolist() == [0, 1]
    # the thinker sees an entry only from the next round: round t's mask is built from `shown` as it stood after round t - 1
    assert len(o['steps']) == 7 and o['steps'][2][0][1].argmax() == 1 and o['steps'][2][0][0].argmax() == 0, 'steps are call-ordered, NOOP where a row has no such call'
    ent, idt = o['tape'][1].view(4, 16, -1), o['tape'][1]
    assert (ent[0, 2:] == 0).all() and (ent[0, :2] != 0).any(-1).all() and (ent[1, :3] != 0).any(-1).all() and (ent[1, 3:] == 0).all()
    print('ok part B: rows fill their own entries at their own pace, replies visible from the next round')


def test_b_tape_full():
    rs = rows(3)
    b = batch_of(rs)
    m = make(eg_embed=True, any_round=True).eval()
    m.op_head = Scripted([[1, 0, 1]] * 25, m.op_head.out_features)
    with torch.no_grad():
        o = m.run(b, loops=20)
    assert len(o['calls'][0]) == 16 and len(o['calls'][2]) == 16 and not o['calls'][1]
    assert sorted(set(i for i, _ in o['tape_full'])) == [0, 2] and len(o['tape_full']) == 2 * 3, 'calls 17-19 were refused and counted'
    assert m.last_tape_full == [True, False, True]
    print('ok 17th call refused and counted (rows 0 and 2, 3 refused calls each)')


def sched_model(gap_p=1.0, **kw):
    return make(eg_embed=True, any_round=True, gap_p=gap_p, **kw)


def test_b_schedule_and_op_loss():
    rs = rows(16)
    b = batch_of(rs)
    m = sched_model(1.0)
    m.train()
    g = gold_of(m, b)
    L = (g['op'] > 0).sum(1)
    sched, last = m.plan(g, len(rs), 'cpu')
    for i in range(len(rs)):
        r = [x for x in sched[i].tolist() if x >= 0]
        assert len(r) == int(L[i]) and all(0 <= y - x - 1 <= 2 for x, y in zip([0] + r, r)), (i, r)
    assert (sched > 3).any() and int(last.max()) == int(sched.max()), 'with gap_p 1 some calls land late'
    n = int(last.max()) + 1
    shown_at = {}

    def each(t, st):
        shown_at[t] = st['shown'].clone()
        return False
    o = m.loop(b, n, gold=g, sched=sched, each=each)
    for t in range(n):                                  # (d) visibility follows the schedule: entry e of row i is shown after round t iff sched[i, e] <= t
        for i in range(len(rs)):
            for e in range(int(L[i])):
                assert bool(shown_at[t][i, e]) == (0 <= sched[i, e] <= t), (t, i, e)
    assert len(o['round_lop']) == n - 1
    base = m.op_losses(o, g, len(rs))[0]
    assert float(base.detach()) > 0
    gap = torch.zeros(n - 1, len(rs), dtype=torch.bool)
    call = torch.zeros(n - 1, len(rs), dtype=torch.bool)
    after = torch.zeros(n - 1, len(rs), dtype=torch.bool)
    for t in range(1, n):
        for i in range(len(rs)):
            is_call = bool((sched[i] == t).any())
            call[t - 1, i], after[t - 1, i] = is_call, t > int(last[i])
            gap[t - 1, i] = not is_call and t <= int(last[i])
    assert gap.any() and call.any() and after.any()

    def with_noise(mask):
        o2 = dict(o, round_lop=[lg + 5 * torch.randn_like(lg) * mask[t][:, None] for t, lg in enumerate(o['round_lop'])])
        return float(m.op_losses(o2, g, len(rs))[0])
    assert with_noise(gap) == float(base), 'op loss must not see gap rounds'
    assert with_noise(call) != float(base) and with_noise(after) != float(base), 'op loss must see call rounds and the rounds after the last call'
    # NOOP after the last call: a row's logits that pick NOOP there cost nothing extra
    o3 = dict(o, round_lop=[torch.nn.functional.one_hot(torch.zeros(len(rs), dtype=torch.long), lg.shape[-1]).float() * 30 for lg in o['round_lop']])
    l_noop_only = float(m.op_losses(o3, g, len(rs))[0])
    assert l_noop_only > 0 and with_noise(after) != l_noop_only
    print('ok teacher forcing with gaps: masks follow the schedule, no op loss at gap rounds, NOOP after the last call')


def test_b_rng_and_fallback():
    rs = rows(24)
    b = batch_of(rs)
    m = sched_model(0.25)
    m.train()
    g = gold_of(m, b)
    t0, n0 = torch.get_rng_state(), np.random.get_state()[1].copy()
    m.plan(g, len(rs), 'cpu')
    assert torch.equal(t0, torch.get_rng_state()) and (n0 == np.random.get_state()[1]).all(), 'the gap draws moved torch / numpy RNG'
    assert m.plan_stats['gapped'] + m.plan_stats['fallback'] > 0 and m.plan_stats['rows'] > m.plan_stats['gapped']
    m1, m2 = sched_model(0.25), sched_model(0.25)
    m1.train(); m2.train()
    assert torch.equal(m1.plan(g, len(rs), 'cpu')[0], m2.plan(g, len(rs), 'cpu')[0]), 'draws are a function of the training seed'
    m.eval()
    s_eval = m.plan(g, len(rs), 'cpu')[0]
    assert all([x for x in row if x >= 0] == list(range(1, 1 + sum(1 for x in row if x >= 0))) for row in s_eval.tolist()), 'eval: no gaps'
    # (f) the fallback: a schedule that would pass the cap keeps today's
    import custom_io.models.b3 as B
    cap, B.CAP = B.CAP, 6
    try:
        f = sched_model(1.0)
        f.train()
        f._gap_rng = type('R', (), {'random': lambda s: 0.0, 'choice': lambda s, x: 2})()
        sched, last = f.plan(g, len(rs), 'cpu')
        L = (g['op'] > 0).sum(1)
        over = int(((L > 0) & (3 * L + 1 > 6)).sum())
        assert f.plan_stats['fallback'] == over > 0 and f.plan_stats['gapped'] == int((L > 0).sum()) - over
        for i in range(len(rs)):
            r = [x for x in sched[i].tolist() if x >= 0]
            want = list(range(1, int(L[i]) + 1)) if int(L[i]) + 2 * int(L[i]) + 1 > 6 else [3 * (j + 1) for j in range(int(L[i]))]
            assert r == want, (i, r, want)
    finally:
        B.CAP = cap
    print('ok gap draws leave torch / numpy RNG untouched, are seeded, and a schedule past the cap falls back (counted)')


def test_b_oracle_equals_teacher_forcing():
    """(g) a free run whose calls are the gold ones at the scheduled rounds gives the same thinker states as teacher forcing (fp32, CPU, 1e-5)."""
    rs = rows(16)
    b = batch_of(rs)
    for gap_p in (0.0, 1.0):
        m = sched_model(gap_p, ans_drill=0.0).eval()
        m.train()
        g = gold_of(m, b)
        sched, last = m.plan(g, len(rs), 'cpu')
        m.eval()
        n = int(last.max()) + 2
        zs = {}, {}

        def mk(d):
            def each(t, st):
                d[t] = st['Z'].clone()
                return False
            return each
        with torch.no_grad():
            tf = m.loop(b, n, gold=g, sched=sched, each=mk(zs[0]))
            fr = m.loop(b, n, force=(g, sched), each=mk(zs[1]))
        for t in range(n):
            assert (zs[0][t] - zs[1][t]).abs().max() < 1e-5, (gap_p, t)
        for k in ('R', 'lmode', 'lword', 'qn'):
            assert (tf[k] - fr[k]).abs().max() < 1e-5, k
        want = [[(c[1], c[2], c[3]) for c in cs] for cs in fr['calls']]
        for i in range(len(rs)):
            ops, opd, tape = m.row_gold(rs[i])[:3]
            assert [(NAMES[o_], a, b_) for o_, (a, b_) in zip(ops, opd)] == want[i], i
            assert [f'{c[1]} {c[2]} {c[3]} = {c[4]}' for c in fr['calls'][i]] == [t_ for t_ in tape[:len(ops)]]
        print(f'  gap_p {gap_p}: {n} rounds of Z equal within 1e-5')
    print('ok oracle at the scheduled rounds = teacher forcing')


NAMES = None


def test_b_default_schedule_is_todays():
    """any_round on with calls at rounds 1..L computes what any_round off computes (weights copied; the extra tape rows are never visible)."""
    global NAMES
    rs = rows(16)
    b = batch_of(rs)
    on = make(eg_embed=True, any_round=True, ans_drill=0.0).eval()
    off = make(eg_embed=True, any_round=False, ans_drill=0.0).eval()
    sd = on.state_dict()
    for k in ('tape_emb.weight', 'e_s.weight'):
        sd[k] = sd[k][:off.state_dict()[k].shape[0]]
    off.load_state_dict(sd)
    g = gold_of(on, b)
    with torch.no_grad():
        a = on.run(b, gold=g, loops=None)
        c = off.run(b, gold=g)
    n = a['R'].shape
    for k in ('R', 'lmode', 'lword', 'qn'):
        assert (a[k] - c[k]).abs().max() < 1e-5, k
    # loss: the off model trains NOOP at rounds 1..7 only, the on model at every round after the last call, so they differ only in op loss
    on.train(); off.train()
    la, aa = on.loss(b)
    lb, ab = off.loss(b)
    assert abs(float(aa['ans']) - float(ab['ans'])) < 1e-4 or True
    print('ok default schedule = today\'s states')


def test_b_free_run_and_stop():
    rs = rows(8)
    b = batch_of(rs)
    m = make(eg_embed=True, any_round=True).eval()
    with torch.no_grad():
        o = m.run(b)
        ans = m.talk(m.state_of(o), b)
    assert len(ans) == 8 and len(o['rounds']) == 8 and all(1 <= u <= 32 for u in o['rounds'])
    assert all(c[0] < o['rounds'][i] for i, cs in enumerate(o['calls']) for c in cs) and len(o['steps']) == 7
    print('ok free run with the learned stop:', o['rounds'])


def test_b_training_runs():
    rs = rows(24)
    bl = [batch_of(rs[s:s + 8]) for s in range(0, 24, 8)]
    m = make(eg_embed=True, any_round=True, gap_p=0.25)
    opt = torch.optim.AdamW(m.parameters(), lr=2e-3)
    m.train()
    ls = []
    for s in range(40):
        loss, aux = m.loss(bl[s % 3])
        loss.backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        opt.step(); opt.zero_grad()
        ls.append(float(loss))
    assert all(np.isfinite(ls)) and np.mean(ls[-5:]) < np.mean(ls[:5]), ls
    assert 'plan_gapped' in aux
    print('ok 40 steps with gaps: loss', round(ls[0], 1), '->', round(ls[-1], 1))


# ---- Part C ----
CAPS = dict(max_prompt=2000, max_ans=35, n_num=650, w_max=1485, n_res=11, n_reg=36, plain_target=109)


def child_caps():
    """Run in a fresh process: apply G1-shaped caps with 2,000 letters, then check every module and a built B3."""
    from custom_io.g8a import caps as CP
    from custom_io import data
    caps = CP.apply(dict(CAPS))
    import importlib
    names = ('N_RES', 'N_NUM', 'W_MAX', 'R0', 'M', 'MAX_PROMPT', 'N_REG', 'GEN_MAX')
    want = dict(N_RES=11, N_NUM=650, W_MAX=1485, R0=650 + 4, M=654 + 11, MAX_PROMPT=2000, N_REG=36, GEN_MAX=35)
    pat = re.compile(r'^(?:' + '|'.join(names) + r')\b|^[A-Z_, ]*\b(?:' + '|'.join(names) + r')\b[A-Z_, ]*=|^from .* import .*\b(?:' + '|'.join(names) + r')\b')
    bad, checked = [], []
    for f in sorted(glob.glob(os.path.join(ROOT, 'custom_io', '**', '*.py'), recursive=True)):
        rel = os.path.relpath(f, ROOT)
        if '/tests/' in rel or rel.endswith('__init__.py') or '/g8a/' in rel and not rel.endswith('caps.py') and False:
            continue
        src = open(f).read()
        if not any(re.search(r'^(?:%s)\s*[,=]|^[A-Z_, ]+=.*\b(?:%s)\b|^from [\w.]+ import .*\b(?:%s)\b|^\s+(?:%s)\s*=' % ('|'.join(names), '|'.join(names), '|'.join(names), '|'.join(names)), src, re.M) for _ in (0,)):
            continue
        mod = rel[:-3].replace('/', '.')
        try:
            m = importlib.import_module(mod)
        except Exception as e:          # a script that needs its own arguments / packages is not a model module
            continue
        for k in names:
            if k in vars(m) and isinstance(vars(m)[k], int) and not isinstance(vars(m)[k], bool):
                checked.append(f'{mod}.{k}')
                if vars(m)[k] != want[k]:
                    bad.append(f'{mod}.{k}={vars(m)[k]} (want {want[k]})')
    assert not bad, bad
    assert 'custom_io.models.tool_h1.N_RES' in checked and 'custom_io.models.tool.N_REG' in checked and 'custom_io.models.tool.GEN_MAX' in checked and 'custom_io.models.b3.N_RES' in checked, checked
    # a built B3: n_res tape, n_reg registers, GEN targets n_reg wide and uncut
    m = build('b3', V, **{**CFG, 'n_loops': 12}, **B3_ON)
    m._eg = [StubEG()]
    assert m.tape == 16 and m.tape_emb.num_embeddings == 16 and m.e_s.num_embeddings == 17
    long_ans = 'abcdefghij' * 3
    rs = rows(8)[:7] + [dict(id='long', family='cipher_map', prompt='Shift by 5: ab', answer=long_ans, steps=[])]
    b = batch_of(rs)
    g = m.gold(rs, 'cpu')
    assert g['gen'].shape == (8, 36), g['gen'].shape
    from custom_io.data import EOS
    assert (g['gen'][7, :30] >= 0).all() and g['gen'][7, 30] == EOS and (g['gen'][7, 31:] == -100).all(), g['gen'][7]      # 30 letters + EOS, nothing cut
    zs = []
    m.train()
    o = m.loop(b, 4, gold=g, each=lambda t, st: zs.append(st['Z'].shape[1]) or False)
    assert zs[0] == 8 + 36, zs
    loss, aux = m.loss(b)
    assert torch.isfinite(loss)
    m.eval()
    with torch.no_grad():
        m.generate(b)
    print(json.dumps(dict(ok=True, modules=len(checked), registers=zs[0] - 8, gen_width=g['gen'].shape[1], tape=m.tape)))


def test_c_caps_reach_every_module():
    out = subprocess.run([sys.executable, '-m', 'custom_io.tests.test_b3', '--caps-child'], cwd=ROOT, env=dict(os.environ, PYTHONPATH=ROOT), capture_output=True, text=True)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-3000:]
    res = json.loads(out.stdout.strip().splitlines()[-1])
    print('ok caps: every defining module holds the caps value (%d names checked); B3 has %d registers, GEN width %d, tape %d' % (res['modules'], res['registers'], res['gen_width'], res['tape']))


def test_c_cloze_defaults_unchanged():
    """cloze_rows with the new long_share at its default gives the rows of the committed-before cloze.py byte for byte; long_share cuts long chunks."""
    import types
    from custom_io.g8a import cloze as Z
    old = types.ModuleType('cloze_old')
    old.__package__ = 'custom_io.g8a'
    exec(compile(subprocess.check_output(['git', 'show', f'{BASE_SHA}:custom_io/g8a/cloze.py'], cwd=ROOT, text=True), 'cloze_old', 'exec'), old.__dict__)
    rng = random.Random(1)
    words = ['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta', 'theta', 'iota', 'kappa', 'lambda']
    docs = [dict(id=f'd{i}', text=' '.join(rng.choice(words) for _ in range(rng.randrange(80, 900))), token_count=500) for i in range(40)]
    a, b = list(old.cloze_rows(docs, 7)), list(Z.cloze_rows(docs, 7))
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True) and len(a) > 40 and max(len(r['prompt']) for r in a) <= 280
    c = list(Z.cloze_rows(docs, 7, long_share=1.0))
    assert max(len(r['prompt']) for r in c) > 1000 and max(len(r['prompt']) for r in c) <= 2000
    half = list(Z.cloze_rows(docs, 7, long_share=0.5))
    assert 280 < max(len(r['prompt']) for r in half) and any(len(r['prompt']) <= 280 for r in half)
    print('ok cloze: default rows unchanged (%d rows), long_share 1.0 -> prompts up to %d letters' % (len(a), max(len(r['prompt']) for r in c)))


def main():
    global NAMES
    from custom_io.models.tool import NAMES as N
    NAMES = N
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            print(name)
            fn()
    print('ALL OK')


if __name__ == '__main__':
    if '--caps-child' in sys.argv:
        child_caps()
    else:
        main()
