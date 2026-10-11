"""python3 -m custom_io.tests.test_reader_rule   (CPU, about two minutes; no data files, no Gemma: test_b3's stub FrozenEG; run with OMP_NUM_THREADS=1)
Ben's two rules for B3 group 2 (model 'b3g2').
RULE 1 (4:06 PM ET): "also for the calculator, it should be read by the reader. It is a fully external tool, just like minecraft. I really feel like you ignored me on that one".
  A tape string (calculator reply entry, note, drill string, '?') is read by exactly the function that reads the question, as its own prompt: the letter window plus the
  Gemma term (Ledger.eg_term), through FrozenEG.encode_texts, which leaves the question's memo alone.
RULE 2 (4:08 PM ET): "the talker shouldn't get a pointer from the thinker, it just transcribes the thoughts of the thinker. So it should read the thoughts of the thinker, maybe at every
  step, but at least the last, and answer in english from that. It literally is a math to language translator."
  The answer (writer mode 1) is written from Z alone: no prompt, no tape, no copy keys, no selective-read feedback."""
import torch
from custom_io.data import BOS, EOS
from custom_io.models.writer import ByteWriter
from custom_io.tests.test_b3 import batch_of, rows
from custom_io.tests.test_b3g2 import G2, V, Script, make

S = 'add 12 5 = 17'


def lone(s):
    """A one-row batch whose prompt is s."""
    return batch_of([dict(id='x', family='copy_word', prompt=s, answer='x', steps=[])], V)


def loud(m):
    """eg_proj is zero at init (the Gemma term is 0): give it a real weight so the term shows."""
    with torch.no_grad():
        m.eg_proj.weight.normal_(0, 0.5)
        m.eg_proj.bias.normal_(0, 0.5)
    return m


# ---- RULE 1 ----
def test_r1_tape_string_is_read_like_the_question():
    for kw in (dict(), dict(eg_adapter='mlp')):
        m = loud(make(**kw)).eval()
        if m.eg_adapter == 'mlp':
            with torch.no_grad():
                m.eg_hid.weight.normal_(0, 0.5)
        for s in (S, 'note hello there', 'sub 3 4 = -1', 'x = ?'):
            b = lone(s)
            T = b['prompt_ids'].shape[1]
            with torch.no_grad():
                Xq, mq = m.read(b, talker=True)
                Xr, ir, mr = m.read_texts([s], 'cpu', T)
            assert Xr.shape == Xq.shape and torch.equal(Xr, Xq) and torch.equal(mr, mq) and torch.equal(ir, b['prompt_ids']), (kw, s)
    # eg_thinker mirrors the question's talker flag: no Gemma term on either
    mt = loud(make(eg_thinker=True)).eval()
    b = lone(S)
    with torch.no_grad():
        assert torch.equal(mt.read_texts([S], 'cpu', b['prompt_ids'].shape[1])[0], mt.read(b, talker=True)[0])
        assert not torch.equal(mt.read(b)[0], mt.read(b, talker=True)[0])
    assert not mt._eg[0].text_calls
    print('ok R1 (a): read_texts([s]) == the question reader on a one-row batch, bit for bit (linear and mlp adapters; eg_thinker mirrors the talker flag)')


def test_r1_gemma_really_reaches_the_reply():
    m = loud(make()).eval()
    eg = m._eg[0]
    with torch.no_grad():
        a = m.read_texts([S, 'mul 2 3 = 6'], 'cpu', 20)[0]
        eg.offset[S] = 3.0
        b = m.read_texts([S, 'mul 2 3 = 6'], 'cpu', 20)[0]
    assert not torch.equal(a[0], b[0]) and torch.equal(a[1], b[1]), 'only the string whose Gemma state changed moved'
    assert eg.text_calls and all(S in c or 'mul 2 3 = 6' in c for c in eg.text_calls)
    print('ok R1 (b): changing Gemma\'s output for a reply changes the reader\'s output for it')


def test_r1_eg_off_is_the_old_letter_path():
    m = make(eg_embed=False).eval()
    texts = [S, '', 'note hi', 'x']
    with torch.no_grad():
        X, ids, mask = m.read_texts(texts, 'cpu', 20)
        rs_ = [dict(prompt=m.vocab.clip(t, 20)) for t in texts if t]
        full = [i for i, t in enumerate(texts) if t]
        Xo, _ = m.reader({'prompt_ids': ids[full], 'prompt_mask': mask[full], 'rows': rs_})        # the old code: the letter reader alone
    assert torch.equal(X[full], Xo) and not X[1].any()
    # eg_embed on with eg_proj still zero (init): the same letters-only numbers
    on = make().eval()
    with torch.no_grad():
        assert torch.equal(on.read_texts(texts, 'cpu', 20)[0], make(eg_embed=False).eval().read_texts(texts, 'cpu', 20)[0])
    print('ok R1 (c): eg_embed off is bit-identical to the letter-only path (and eg_embed on at init)')


def test_r1_question_memo_not_evicted():
    b = batch_of(rows(8), V)
    m = loud(make()).eval()
    eg = m._eg[0]
    texts = [['add 7 5', 'sub 12 3', ''], ['mul 2 2'], ['note hi'], [], ['add 1 1'], [], ['add 4 4', 'add 1 2'], ['sub 9 1']]
    Script(m, texts)
    with torch.no_grad():
        o = m.run(b, loops=4)
        ans = m.talk(m.state_of(o), b)
    assert sum(len(c) for c in o['calls']) > 0 and eg.passes == 1, ('the question is embedded once for run + talk', eg.passes, len(eg.calls))
    assert eg.text_pass_n >= 1 and not any(' = ' in p for c in eg.calls for p in c), 'tape strings never go through the memoised encode'
    m2 = loud(make()).train()
    m2.loss(b)[0].backward()
    e = m2._eg[0]
    assert e.passes == 1 and len(e.calls) == 1 and e.text_pass_n >= 1, (e.passes, len(e.calls), e.text_pass_n)
    print('ok R1 (d): run + talk on a batch with calls embed the question once; replies take their own passes outside the memo')


def test_r1_gradient_reaches_the_adapter_from_replies():
    m = loud(make()).train()
    X, ids, mask = m.read_texts([S, 'note hi', ''], 'cpu', 20)
    (X * mask[..., None]).pow(2).sum().backward()
    for n in ('eg_proj.weight', 'eg_proj.bias', 'ln_eg.weight'):
        g = dict(m.named_parameters())[n].grad
        assert g is not None and g.abs().sum() > 0, n
    m2 = loud(make(eg_adapter='mlp')).train()
    with torch.no_grad():
        m2.eg_hid.weight.normal_(0, 0.5)
    X, ids, mask = m2.read_texts([S], 'cpu', 20)
    X.pow(2).sum().backward()
    assert m2.eg_hid.weight.grad.abs().sum() > 0 and m2.eg_proj.weight.grad.abs().sum() > 0
    print('ok R1 (e): the gradient from reply positions reaches ln_eg / eg_proj (and eg_hid)')


def test_r1_question_path_bit_identical_and_sizes():
    rs = [r for r in rows(8) if not r['steps']] or [dict(id=f'c{i}', family='copy_word', prompt=f'Echo: sune{i} Give only the answer.', answer=f'sune{i}', steps=[]) for i in range(4)]
    b = batch_of(rs, V)

    def old_read(self, batch, talker=False):           # the code before the factoring, op for op
        if not self.eg_embed or (talker and self.eg_thinker):
            return self.reader(batch)
        ids = batch['prompt_ids']
        H, _ = self.eg().encode([r['prompt'] for r in batch['rows']], ids.shape[1], ids.device)
        h = self.ln_eg(H.float())
        if self.eg_adapter == 'none':
            return self.reader(batch, extra=h)
        if self.eg_adapter == 'mlp':
            h = torch.nn.functional.gelu(self.eg_hid(h))
        return self.reader(batch, extra=self.eg_proj(h))
    for kw in (dict(), dict(eg_adapter='mlp')):
        a, c = loud(make(**kw)), loud(make(**kw))
        c.read = old_read.__get__(c)
        la, lc = [], []
        for m, out in ((a, la), (c, lc)):
            m.train()
            torch.manual_seed(5)
            loss, aux = m.loss(b)
            out.append(loss.detach())
        assert torch.equal(la[0], lc[0]), kw
        assert torch.equal(a.read(b, talker=True)[0], old_read(a, b, talker=True)[0])
    # R4: no new parameters
    off, on = make(eg_embed=False), make()
    assert on.size()['trainable'] - off.size()['trainable'] == sum(p.numel() for n, p in on.named_parameters() if n.startswith(('ln_eg', 'eg_proj')))
    assert set(on.state_dict()) - set(off.state_dict()) == {'ln_eg.weight', 'ln_eg.bias', 'eg_proj.weight', 'eg_proj.bias'}
    print('ok R3/R4 (f): the question path (read and the loss of a no-call batch) is bit-identical to the old ops; no new parameters')


# ---- RULE 2 ----
def a_state(m, b, texts=None):
    """A run's state (Z, Xt, idt, vis) with calls scripted, so the tape has content."""
    texts = texts or [['add 7 5', 'sub 12 3'], ['mul 2 2'], ['note hi'], [], ['add 1 1'], [], ['add 4 4', 'add 1 2'], ['sub 9 1']]
    Script(m, texts)
    with torch.no_grad():
        o = m.run(b, loops=4)
    m.writer.greedy = m.writer.greedy.real
    return m.state_of(o)


def noisy_writer(m):
    with torch.no_grad():                       # an untrained writer is near-uniform: give it some structure so strings differ with Z
        for p in m.writer.parameters():
            p.add_(torch.randn_like(p) * 0.3)
    return m


def test_r2_answer_reads_z_only():
    m = noisy_writer(loud(make())).eval()
    b1 = batch_of(rows(8), V)
    other = [dict(r, prompt=r['prompt'][::-1] + ' zzz qqq', id=r['id'] + 'x') for r in rows(8)]
    b2 = batch_of(other, V)
    st = a_state(m, b1)
    Z, Xt, idt, vis = st
    assert vis.any() and Xt.abs().sum() > 0
    # a different tape: other letters, other ids, other visibility
    g = torch.Generator().manual_seed(3)
    st2 = (Z, torch.randn(Xt.shape, generator=g), idt.flip(1), ~vis)
    answers = [r['answer'] for r in rows(8)]
    with torch.no_grad():
        a0 = m.talk(st, b1)
        outs = [m.talk(st, b2), m.talk(st2, b1), m.talk(st2, b2), m.talk(st, None), m.talk(st, b1, lesion='nocopy')]
        assert all(o == a0 for o in outs), (a0, outs)
        f0 = m.forced_answer(st, b1, answers)
        for f in (m.forced_answer(st, b2, answers), m.forced_answer(st2, b1, answers), m.forced_answer(st2, b2, answers), m.forced_answer(st, b1, answers, nocopy=True)):
            assert all(torch.equal(x, y) for x, y in zip(f0, f))
        assert (f0[2] == 0).all(), 'answer copy mass reports 0'
    print('ok R2 T1 (a): with Z fixed, the prompt, the tape and nocopy leave talk() and the teacher-forced answer bit-identical; copy mass 0')


def test_r2_changing_z_changes_the_answer():
    m = noisy_writer(loud(make())).eval()
    b = batch_of(rows(8), V)
    st = a_state(m, b)
    answers = [r['answer'] for r in rows(8)]
    Z2 = st[0] + torch.randn(st[0].shape, generator=torch.Generator().manual_seed(1)) * 2.0
    with torch.no_grad():
        f0, f1 = m.forced_answer(st, b, answers), m.forced_answer((Z2,) + tuple(st[1:]), b, answers)
        assert not torch.equal(f0[0], f1[0]), 'the teacher-forced nll follows Z'
        rolled = m.talk((st[0].roll(1, 0),) + tuple(st[1:]), b)
        assert m.talk(st, b) != m.talk((Z2,) + tuple(st[1:]), b) or m.talk(st, b) != rolled
    print('ok R2 T1 (b): changing Z changes the answer log-probs and the written answer')


def test_r2_zero_length_context_and_empty_context_shapes():
    m = noisy_writer(make()).eval()
    w = m.writer
    B, d = 3, m.d
    Z = torch.randn(B, 17, d)
    zm = torch.ones(B, 17, dtype=torch.bool)
    mode = torch.ones(B, dtype=torch.long)
    inp = torch.tensor([[1, 20, 21]] * B)
    with torch.no_grad():
        # (1) the shape used everywhere: one fully masked position
        Xc, cm, ci = m.answer_context(Z)
        assert Xc.shape == (B, 1, d) and not cm.any()
        te = ByteWriter.teacher([[20, 21], [], [22]], ci, cm, 69, 1, 2)
        assert not te['fb'].any()
        p1, g1, a1 = w.run(Z, zm, Xc, cm, ci, mode, inp, te['fb'][:, :3], False, None)
        assert (g1 == 1).all() and (a1 == 0).all()
        # (2) a truly empty context also works through head / run / greedy
        X0, c0, i0 = torch.zeros(B, 0, d), torch.zeros(B, 0, dtype=torch.bool), torch.zeros(B, 0, dtype=torch.long)
        p0, g0, a0 = w.run(Z, zm, X0, c0, i0, mode, inp, torch.zeros(B, 3, 0), False, None)
        assert (g0 == 1).all() and torch.equal(p0, p1), 'empty and masked-dummy contexts give the same distribution'
        o0, _ = w.greedy(Z, zm, X0, c0, i0, mode)
        o1, _ = w.greedy(Z, zm, Xc, cm, ci, mode)
        assert o0 == o1
    print('ok R2 T1: ByteWriter.head / run / greedy work with a zero-length context and with one fully masked position (same result: gate 1, copy 0)')


def test_r2_call_mode_still_copies():
    m = noisy_writer(make()).eval()
    b = batch_of(rows(8), V)
    texts = [['add 7 5'], [], [], [], [], [], [], []]
    st = a_state(m, b, texts)
    # call mode (mode 0) keeps its copy context [prompt; visible tape] and ckeys: its gate is not forced to 1 and the context reaches its output
    X, xm = m.read(b, talker=True)
    Xc, cm, ci = torch.cat([X, st[1].to(X.dtype)], 1), torch.cat([xm, st[3]], 1), torch.cat([b['prompt_ids'], st[2]], 1)
    ck = m.ckeys(Xc.shape[1], X.shape[1], st[1].shape[1] // m.tape, cm)
    zm = torch.ones(8, st[0].shape[1], dtype=torch.bool)
    inp = torch.full((8, 3), 5)
    with torch.no_grad():
        p, g, a = m.writer.run(st[0], zm, Xc, cm, ci, torch.zeros(8, dtype=torch.long), inp, torch.zeros(8, 3, Xc.shape[1]), False, ck)
        assert (g < 1).all() and a.sum() > 0
        Xc2 = Xc + torch.randn(Xc.shape) * 3
        p2, _, _ = m.writer.run(st[0], zm, Xc2, cm, ci, torch.zeros(8, dtype=torch.long), inp, torch.zeros(8, 3, Xc.shape[1]), False, ck)
        assert not torch.equal(p, p2)
    print('ok R2 T2: call mode keeps its copy context (gate < 1, attention over [prompt; tape], context-sensitive)')


def test_r2_call_and_stop_inputs_do_not_depend_on_the_answer_path():
    """The call loss and the call/EOS hits come from the call writer alone: replacing the answer pass by a constant leaves them bit-identical (no hard-coded floats)."""
    b = batch_of(rows(8), V)
    outs = []
    for stub in (False, True):
        m = loud((torch.manual_seed(0), make())[1]).train()
        if stub:
            m.ans_pass = lambda Z, inp, tgt, fb: (Z.sum((1, 2)) * 0.0, torch.zeros(Z.shape[0], dtype=torch.bool), torch.zeros(Z.shape[0]), torch.ones(Z.shape[0]))
        torch.manual_seed(7)
        loss, aux = m.loss(b)
        outs.append((float(aux['call']).hex(), float(aux['call_acc']).hex(), float(aux['eos_acc']).hex()))
        assert torch.isfinite(loss) and float(aux['copy_share']) == 0.0
    assert outs[0] == outs[1], outs
    print('ok R2 T2 (d): the call loss and the call/EOS hits are bit-identical whatever the answer pass does')


def calling_golds(m, flip):
    rs = [r for r in rows(8) if r['steps']]
    b = batch_of(rs, V)
    golds = m.train_golds(rs)
    for gd in golds:
        assert gd['texts']
        if flip:
            t = gd['tape'][-1]
            gd['tape'][-1] = t[:-1] + ('7' if t[-1] != '7' else '3')               # same length, other reply digit
    return b, golds


def test_r2_answer_rounds_come_after_the_last_reply():
    """Every round at which the answer is asked has a Z that has read the row's last calculator reply: changing only the last reply's text changes Z there."""
    seen = []
    for flip in (False, True):
        m = loud((torch.manual_seed(1), make())[1]).train()
        m.gap_p = 0.0
        zs = []
        real = m.ans_pass
        m.ans_pass = lambda Z, inp, tgt, fb, real=real, zs=zs: (zs.append(Z.detach().clone()), real(Z, inp, tgt, fb))[1]
        b, golds = calling_golds(m, flip)
        torch.manual_seed(5)
        m._loss(b, golds)
        seen.append(zs)
    assert len(seen[0]) == len(seen[1]) and len(seen[0]) > 0
    for z0, z1 in zip(*seen):
        assert (z0 - z1).abs().flatten(1).max(1).values.gt(0).all(), 'an answer round whose Z has not read the last reply'
    print('ok R2 (f): in training, every answer round of a calling row sees the last reply (max|dZ| > 0 for every row at every answer round)')


def test_r2_free_runs_read_the_last_reply():
    """A forced run (loops=2, one call at round 1) and the learned stop both return a Z that has read the last reply; the answer follows the reply."""
    m = noisy_writer(loud(make())).eval()
    b = batch_of([dict(id='x', family='copy_word', prompt='Echo: abc', answer='x', steps=[])], V)
    zs = []
    for rep in ('12', '99999'):
        Script(m, [['add 7 5']])
        with torch.no_grad():
            o = m.run(b, loops=2, oracle=lambda i, t, call, rep=rep: rep)
        m.writer.greedy = m.writer.greedy.real
        assert o['calls'][0] and o['calls'][0][0][4] == rep, o['calls']
        zs.append(o['Z'])
    assert not torch.equal(zs[0], zs[1]), 'loops:2 with a call at round 1: Z must have read the reply'
    # learned stop: a row never stops in the round it called (its Z could not have read the reply)
    m2 = make().eval()
    m2.p_stop = lambda z: torch.ones(z.shape[0])
    Script(m2, [['add 7 5']])
    with torch.no_grad():
        o = m2.run(b)
    m2.writer.greedy = m2.writer.greedy.real
    assert all(c[0] < o['rounds'][0] - 0 for c in o['calls'][0]) and (not o['calls'][0] or o['rounds'][0] >= o['calls'][0][-1][0] + 2), (o['rounds'], o['calls'])
    print('ok R2 (g): forced runs settle one more pass after a final call; the learned stop never stops in a round that wrote a call')


def test_r2_lessons_still_run():
    from custom_io.evalx import donor_eval
    rs = [dict(r, accepted=[r['answer']]) for r in rows(8)]
    m = noisy_writer(make()).eval()
    b = batch_of(rs, V)
    with torch.no_grad():
        for les in (None, 'shuffle_state', 'zero_state', 'nocopy', 'noexec', 'opswap', 'loops:2'):
            out = m.generate(b, lesion=les)
            assert len(out) == 8 and all(isinstance(x, str) for x in out), les
        res = donor_eval(m, rs, batch_size=4, device=torch.device('cpu'), return_preds=True)
    assert res['n'] == 8, res
    byid = {r['id']: r for r in rs}
    for rid, (did, pred) in res['preds'].items():       # the answer is the donor's thoughts (its own answer when run alone), whatever the current prompt
        with torch.no_grad():
            assert pred == m.generate(batch_of([byid[did]], V))[0], (rid, did)
    m.train()
    loss, aux = m.loss(b)
    loss.backward()
    assert torch.isfinite(loss)
    print('ok R2 (e): shuffle_state / zero_state / nocopy / donor swap still run; a donor-swapped row says what the donor alone says')


def main():
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            print(name)
            fn()
    print('ALL OK')


if __name__ == '__main__':
    main()
