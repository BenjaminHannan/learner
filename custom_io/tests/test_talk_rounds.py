"""python3 -m custom_io.tests.test_talk_rounds   (CPU, about a minute; no data files, no Gemma: test_b3's stub FrozenEG; run with OMP_NUM_THREADS=2)
Every-round reading (G2f build spec section 4; B3G2 cfg talk_rounds, off by default). Ben's rule 2: the talker "should read the thoughts of the thinker, maybe at every step, but at least the last".
'last' (the default) is bit-identical to the model without the switch: the same parameters, loss, aux, gradients, free run and answers on the same seed, whether the key is left out or
passed. 'all' adds no parameters; it runs end to end (the loss backpropagates, every parameter that trains under 'last' still gets a gradient, free run, talk, the lesions, ST1's
sample_traces / trace_loss); the writer sees exactly (t + 1) * n_z vectors after round t (n_z = 17 = the control and register vectors of one round), for calls and answers, teacher forced
and free; a row that stopped keeps the memory of its stop round (the learned stop runs quiet_last and a row cannot stop on a round where it wrote a call); a forced run's settle pass is one more memory block
for the rows that got it only; run(each=...) with loops=None returns a mem_mask; zero_state / shuffle_state act on everything the writer reads (the memory and its mask)."""
import torch
from custom_io.models.b3g2 import B3G2
from custom_io.tests.test_b3 import batch_of, rows
from custom_io.tests.test_b3g2 import V, Script, make


def seen(m, fn):
    """Runs fn() and returns the list of (Z.shape[1], visible vectors per row [B]) of every writer call (teacher forced forward and free greedy)."""
    log = []
    hook = m.writer.register_forward_pre_hook(lambda mod, a: log.append((a[0].shape[1], a[1].sum(1).tolist())))
    real = m.writer.greedy

    def spy(Z, zmask, *a, **k):
        log.append((Z.shape[1], zmask.sum(1).tolist()))
        return real(Z, zmask, *a, **k)
    m.writer.greedy = spy
    try:
        fn()
    finally:
        hook.remove()
        m.writer.greedy = real
    return log


def test_last_is_bit_identical():
    b = batch_of(rows(8), V)
    outs = []
    for kw in ({}, dict(talk_rounds='last')):
        m = make(3, **kw)
        torch.manual_seed(11)
        loss, aux = m.loss(b)
        loss.backward()
        grads = {n: p.grad.clone() for n, p in m.named_parameters() if p.grad is not None}
        m.eval()
        with torch.no_grad():
            o = m.run(b)
            st = m.state_of(o)
            ans = m.talk(st, b)
            les = [m.generate(b, lesion=x) for x in (None, 'zero_state', 'shuffle_state', 'loops:3')]
        assert len(st) == 4 and 'mem' not in o and m.talk_rounds == 'last'
        outs.append((loss.detach(), aux, grads, o['records'], o['rounds'], ans, les, {k: v.clone() for k, v in m.state_dict().items()}, st[0].clone()))
    a, c = outs
    assert torch.equal(a[0], c[0]) and all(torch.equal(torch.as_tensor(a[1][k]), torch.as_tensor(c[1][k])) for k in a[1]), 'loss / aux'
    assert a[2].keys() == c[2].keys() and all(torch.equal(a[2][k], c[2][k]) for k in a[2]), 'gradients'
    assert a[3] == c[3] and a[4] == c[4] and a[5] == c[5] and a[6] == c[6] and torch.equal(a[8], c[8]), 'free run / answers / lessons'
    assert all(torch.equal(a[7][k], c[7][k]) for k in a[7])
    # and the writer reads exactly the last round's n_z vectors, all visible
    m = make(3)
    m.eval()
    with torch.no_grad():
        log = seen(m, lambda: m.talk(m.state(b, 3), b))
    assert log and all(n == m.ctrl.weight.shape[0] + 9 and set(v) == {n} for n, v in log), log
    print('ok talk_rounds last (default and explicit): loss, aux, gradients, free run, answers, lessons and the weights bit-identical; the writer reads the last round only')


def test_all_adds_no_parameters():
    ma, ml = make(4, talk_rounds='all'), make(4)
    assert ma.talk_rounds == 'all'
    sa, sl = ma.state_dict(), ml.state_dict()
    assert sa.keys() == sl.keys() and all(torch.equal(sa[k], sl[k]) for k in sa), 'same parameters, same init'
    try:
        make(4, talk_rounds='sometimes')
        raise SystemExit('talk_rounds must be last or all')
    except AssertionError:
        pass
    print('ok talk_rounds all: no new parameters (the state dict is the same keys and values as last)')


def test_all_end_to_end():
    m = make(5, talk_rounds='all')
    nz = m.ctrl.weight.shape[0] + 9
    assert nz == 17
    b = batch_of(rows(8), V)
    # teacher forced: the loss backpropagates, every parameter gets a gradient, and after round t the writer sees (t + 1) * n_z vectors
    log = seen(m, lambda: m.loss(b)[0].backward())
    assert log and all(n % nz == 0 and set(v) == {n} for n, v in log), log
    ts = {n // nz for n, _ in log}
    assert min(ts) >= 1 and ts == set(range(min(ts), max(ts) + 1)), ts      # t + 1 rounds of vectors after round t: answers from round 0 (rows with no call), calls from round 1
    ml = make(5)
    ml.loss(b)[0].backward()
    assert all(p.grad is not None for p in m.parameters() if p.requires_grad) and all(torch.isfinite(p.grad).all() for p in m.parameters() if p.grad is not None)
    assert {n for n, p in m.named_parameters() if p.grad is None} == {n for n, p in ml.named_parameters() if p.grad is None}
    ga = sum(float(p.grad.abs().sum()) for n, p in m.named_parameters() if n.startswith('step_emb'))
    assert ga > 0, 'step_emb is read by the writer now'
    # a forced run of K rounds: the memory is K rounds of vectors, all visible; the free run's writer sees (t + 1) * n_z at round t
    m.eval()
    with torch.no_grad():
        for K in (0, 1, 3):
            st = m.state(b, K)
            assert len(st) == 6 and st[4].shape[1] == max(K, 1) * nz and bool(st[5].all()) and st[5].shape == st[4].shape[:2]
            assert len(m.talk(st, b)) == 8
        log = seen(m, lambda: m.run(b, loops=4))
        assert [n for n, _ in log] == [r * nz for r in (2, 3, 4)], [n for n, _ in log]           # the call asked after rounds 1, 2, 3 (t = 1..3): (t + 1) * n_z
        # the learned stop with a different stop round per row: row i stops after round i % 3, and keeps the memory of rounds 0..i % 3
        calls = [0]

        def p_stop(zf):
            t, calls[0] = calls[0], calls[0] + 1
            return torch.tensor([1.0 if t >= i % 3 else 0.0 for i in range(zf.shape[0])])
        m.p_stop = p_stop
        o = m.run(b)
        assert o['rounds'] == [i % 3 + 1 for i in range(8)], o['rounds']
        st = m.state_of(o)
        assert st[4].shape[1] >= 3 * nz and st[5].sum(1).tolist() == [(i % 3 + 1) * nz for i in range(8)], st[5].sum(1).tolist()
        log = seen(m, lambda: m.talk(st, b))
        assert log == [(st[4].shape[1], [(i % 3 + 1) * nz for i in range(8)])] * len(log) and log, log
        del m.p_stop
        # a row's answer does not depend on the rounds after its stop (its memory is masked there): scribble over them
        st2 = (st[0], st[1], st[2], st[3], st[4] + 7.0 * (~st[5]).unsqueeze(-1).to(st[4].dtype), st[5])
        assert m.talk(st, b) == m.talk(st2, b)
        # the lesions act on everything the writer reads
        z = m.lesioned(st, 'zero_state')
        assert not z[0].any() and not z[4].any() and torch.equal(z[5], st[5]) and z[1] is st[1]
        s = m.lesioned(st, 'shuffle_state')
        assert torch.equal(s[4], st[4].roll(1, 0)) and torch.equal(s[5], st[5].roll(1, 0)) and torch.equal(s[0], st[0].roll(1, 0)) and torch.equal(s[3], st[3])
        for les in (None, 'zero_state', 'shuffle_state', 'noexec', 'opswap', 'nocopy', 'loops:0', 'loops:2'):
            out = m.generate(b, lesion=les)
            assert len(out) == 8 and all(isinstance(x, str) for x in out), (les, out)
        zero_ans = m.talk((torch.zeros_like(st[0]),) + st[1:4] + (torch.zeros_like(st[4]), st[5]), b)
        assert m.generate(b, lesion='zero_state') != [] and isinstance(zero_ans, list)
        # donor: the writer follows the donor's memory (and its mask), not the current prompt
        other = batch_of(rows(8)[::-1], V)
        assert m.talk(m.state(other), b) == m.talk(m.state(other), other)
    # ST1
    gen = torch.Generator().manual_seed(0)
    tr = m.sample_traces(b, 1.0, gen)
    assert len(tr) == 8 and all(set(t) == {'calls', 'answer'} for t in tr)
    m.train()
    loss, aux = m.trace_loss(b, tr)
    loss.backward()
    assert torch.isfinite(loss)
    # an answer asked after the last round of a long run: the memory grows with the run (checkpointed rounds t >= 8 included)
    m.train()
    m.zero_grad()
    log = seen(m, lambda: m.loss(batch_of(rows(8), V))[0].backward())
    assert all(n % nz == 0 for n, _ in log)
    print('ok talk_rounds all: end to end (loss + backward, free run, forced loops 0/1/3, learned stop per row, talk, lessons, donor, sample_traces / trace_loss); the writer sees (t + 1) * %d vectors after round t' % nz)


def test_settle_block_is_per_row_memory():
    """'all' + a forced run's settle pass: the row that wrote a call at the last round gets that pass's Z (plus step_emb[min(n, n_loops - 1)]) as one more memory block, visible in its
    mem_mask; the row without it does not see the block (scribbling over it changes nothing for that row) and its memory is exactly rounds 0..n-1."""
    m = make(5, talk_rounds='all').eval()
    nz, n = 17, 3
    b = batch_of(rows(8)[:2], V)
    Script(m, [['', 'add 7 5'], []])                  # row 0 writes a call at round 2 = the last round of loops=3; row 1 never calls
    with torch.no_grad():
        o = m.run(b, loops=n)
    m.writer.greedy = m.writer.greedy.real
    assert o['calls'][0] and o['calls'][0][0][0] == 2 and not o['calls'][1]
    M, mm = o['mem'], o['mem_mask']
    assert M.shape == (2, (n + 1) * nz, m.d) and mm.shape == M.shape[:2]
    assert mm[0].all() and mm[1, :n * nz].all() and not mm[1, n * nz:].any(), mm.sum(1).tolist()
    assert torch.equal(M[0, n * nz:], o['Z'][0] + m.step_emb.weight[min(n, m.n_loops - 1)]), 'the settle block = the settle pass Z + its step_emb'
    with torch.no_grad():
        Ms = M.clone()
        Ms[1, n * nz:] += 5.0                        # row 1's masked block: must not matter
        st, st2 = m.state_of(o), m.state_of(dict(o, mem=Ms))
        assert m.talk(st, b) == m.talk(st2, b)
        # row 1 alone (no call, no settle): the same memory without the extra block
        Script(m, [[]])
        o1 = m.run(batch_of(rows(8)[1:2], V), loops=n)
        m.writer.greedy = m.writer.greedy.real
    assert o1['mem'].shape[1] == n * nz and (o1['mem'][0] - M[1, :n * nz]).abs().max().item() <= 1e-5 and bool(o1['mem_mask'].all()), 'a row without the settle pass keeps rounds 0..n-1 exactly'
    print('ok talk_rounds all: the settle pass is one more memory block, visible to the row that got it only')


def test_each_without_loops_has_mem_mask():
    """run(each=...) with loops=None used to return no mem_mask (state_of -> KeyError under 'all'): every return path sets it."""
    m = make(5, talk_rounds='all').eval()
    nz = 17
    b = batch_of(rows(8), V)
    with torch.no_grad():
        o = m.run(b, each=lambda t, st: False)
        assert o['mem_mask'].shape == o['mem'].shape[:2] and bool(o['mem_mask'].all()) and o['mem'].shape[1] == m.n_loops * nz
        assert len(m.state_of(o)) == 6 and len(m.talk(m.state_of(o), b)) == 8
        o = m.run(b, each=lambda t, st: t >= 1)       # stopped by each after round 1: two rounds of memory
        assert o['mem'].shape[1] == 2 * nz and bool(o['mem_mask'].all()) and len(m.talk(m.state_of(o), b)) == 8
        o = m.run(b, loops=0)
        assert o['mem_mask'].shape == o['mem'].shape[:2] and len(m.talk(m.state_of(o), b)) == 8
    print("ok talk_rounds all: run(each=...) (loops=None) and loops=0 return a mem_mask; state_of / talk work")


def test_learned_stop_memory_covers_each_rows_rounds():
    """'all' + the learned stop with quiet_last and the 'wrote' rule: a row that wrote a call at round t cannot stop there; mem_mask covers rounds 0..stop round of each row; no call is asked at the last round."""
    m = make(5, talk_rounds='all').eval()
    nz = 17
    b = batch_of(rows(8)[:2], V)
    asked = []

    def call_greedy(Z, temperature=0.0, generator=None, zm=None):
        asked.append(Z.shape[0])
        outs = [m.vocab.encode('add 7 5') if (len(asked) == 1 and j == 0) else [] for j in range(Z.shape[0])]       # row 0 writes a call at round 1 only
        return outs, torch.ones(Z.shape[0], dtype=torch.bool)
    real_cg, m.call_greedy = m.call_greedy, call_greedy
    ticks = [0]

    def p_stop(z):
        ticks[0] += 1
        return torch.full((z.shape[0],), 1.0 if ticks[0] >= 2 else 0.0)        # never at round 0; from round 1 on every row wants to stop
    m.p_stop = p_stop
    with torch.no_grad():
        o = m.run(b)
    assert o['rounds'] == [3, 2], o['rounds']           # row 1 stops after round 1 (rounds=2); row 0 wrote a call at round 1, so it stops only after round 2 (rounds=3)
    assert o['calls'][0] and o['calls'][0][0][0] == 1 and not o['calls'][1]
    assert o['mem_mask'].sum(1).tolist() == [3 * nz, 2 * nz] and bool(o['mem_mask'][:, :2 * nz].all())
    assert len(m.talk(m.state_of(o), b)) == 2
    m.p_stop = lambda z: torch.zeros(z.shape[0])      # nobody stops by the head: they run to the cap; no call is asked at the last round
    asked.clear()
    with torch.no_grad():
        o = m.run(b)
    assert o['rounds'] == [m.cap, m.cap] and len(asked) == m.cap - 2, (o['rounds'], len(asked), m.cap)
    assert bool(o['mem_mask'].all()) and o['mem'].shape[1] == m.cap * nz
    del m.p_stop
    m.call_greedy = real_cg
    print('ok talk_rounds all: learned stop with quiet_last and the wrote rule; mem_mask covers rounds 0..stop round for each row')


def test_memory_is_rounds_plus_step_emb():
    m = make(6, talk_rounds='all')
    hist = [torch.randn(2, 17, m.d) for _ in range(4)]
    M = m.memory(hist, 2)
    assert M.shape == (2, 3 * 17, m.d)
    for r in range(3):
        assert torch.equal(M[:, r * 17:(r + 1) * 17], hist[r] + m.step_emb.weight[min(r, m.n_loops - 1)])
    big = [torch.randn(1, 17, m.d) for _ in range(m.n_loops + 3)]
    M = m.memory(big, len(big) - 1)
    assert torch.equal(M[:, -17:], big[-1] + m.step_emb.weight[m.n_loops - 1]), 'rounds past n_loops share the last step embedding'
    print('ok memory: rounds 0..t, each round plus step_emb[min(r, n_loops - 1)]')


if __name__ == '__main__':
    torch.set_num_threads(1)
    for f in (test_last_is_bit_identical, test_all_adds_no_parameters, test_all_end_to_end, test_settle_block_is_per_row_memory, test_each_without_loops_has_mem_mask, test_learned_stop_memory_covers_each_rows_rounds, test_memory_is_rounds_plus_step_emb):
        f()
    print('ALL OK')
