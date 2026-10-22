"""python3 -m custom_io.tests.test_reader_rule   (CPU, about two minutes; no data files, no Gemma: test_b3's stub FrozenEG; run with OMP_NUM_THREADS=1)
Ben's two rules for B3 group 2 (model 'b3g2').
RULE 1 (4:06 PM ET): "also for the calculator, it should be read by the reader. It is a fully external tool, just like minecraft. I really feel like you ignored me on that one".
  A tape string (calculator reply entry, note, drill string, '?') is read by exactly the function that reads the question, as its own prompt: the letter window plus the
  Gemma term (Ledger.eg_term), through FrozenEG.encode_texts, which leaves the question's memo alone.
RULE 2 (4:08 PM ET): "the talker shouldn't get a pointer from the thinker, it just transcribes the thoughts of the thinker. So it should read the thoughts of the thinker, maybe at every
  step, but at least the last, and answer in english from that. It literally is a math to language translator."
  The answer (writer mode 1) is written from Z alone: no prompt, no tape, no copy keys, no selective-read feedback. Since G2f (fix 2b) the CALL (mode 0) is too: nothing in B3G2 copies."""
import ast, inspect
import torch
from custom_io.data import BOS, EOS
from custom_io.models.b3 import B3
from custom_io.models.writer import ByteWriter
from custom_io.tests.test_b3 import StubEG, batch_of, rows
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
    # eg_thinker mirrors the question's talker flag: no Gemma term on either. B3G2 refuses eg_thinker (under rule 1 its thinker must read the question and every reply through
    # Gemma), so this half runs on group 1 (B3), the same class with the same switches, where Tool.read_texts still honours the flag.
    try:
        make(eg_thinker=True)
        raise SystemExit('b3g2 must refuse eg_thinker')
    except AssertionError:
        pass
    class B3Bytes(B3):                      # B3 with B3G2's input switches (no_slots, no_place, bytes): no operand cells, as in B3G2
        OPERAND_CELLS = False
    torch.manual_seed(0)
    mt = B3Bytes(V, **G2, eg_thinker=True)
    mt._eg = [StubEG()]
    mt = loud(mt).eval()
    b = lone(S)
    with torch.no_grad():
        assert torch.equal(mt.read_texts([S], 'cpu', b['prompt_ids'].shape[1])[0], mt.read(b, talker=True)[0])
        assert not torch.equal(mt.read(b)[0], mt.read(b, talker=True)[0])
    assert not mt._eg[0].text_calls
    print('ok R1 (a): read_texts([s]) == the question reader on a one-row batch, bit for bit (linear and mlp adapters); B3G2 refuses eg_thinker, and on B3 eg_thinker mirrors the talker flag')


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
        Xc, cm, ci = m.line_context(Z)
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


class Spy:
    """Records what the call writer is given: every call_pass log-prob, every call_greedy result, and every context the writer's head receives."""

    def __init__(self, m):
        self.logp, self.greedy, self.heads = [], [], []
        cp, cg, hd = type(m).call_pass.__get__(m), type(m).call_greedy.__get__(m), ByteWriter.head.__get__(m.writer)       # the originals: a new Spy replaces the last one

        def call_pass(Z, inp, tgt):
            out = cp(Z, inp, tgt)
            self.logp.append(out[0].detach().clone())
            return out

        def call_greedy(Z, temperature=0.0, generator=None):
            out = cg(Z, temperature, generator)
            self.greedy.append((out[0], out[1].tolist()))
            return out

        def head(R, Xc, cmask, cids, nocopy, ckeys):
            self.heads.append((bool(cmask.any()), bool(nocopy), ckeys is None, bool(Xc.abs().sum() > 0), bool(cids.any())))
            return hd(R, Xc, cmask, cids, nocopy, ckeys)
        m.call_pass, m.call_greedy, m.writer.head = call_pass, call_greedy, head


def fixed_z(m):
    """The thinker replaced by a function of Z alone (the prompt, the tape and the replies are not read): with it, Z is the same whatever the batch."""
    m.think = lambda Z, kvs, kvx, mask, t: Z * 0.9 + 0.01 * (t + 1)
    return m


def test_r2_calls_read_z_only():
    """Rule 2 now covers calls: with Z fixed, changing the prompt, the tape and the replies leaves the call's teacher-forced log-probs bit-identical and the greedy call text identical."""
    m = fixed_z(noisy_writer(loud(make()))).eval()
    b1 = batch_of(rows(8), V)
    b2 = batch_of([dict(r, prompt=r['prompt'][::-1] + ' zzz qqq', id=r['id'] + 'x') for r in rows(8)], V)

    def tf(b, tape):
        golds = m.plain_golds(b1['rows'])                                            # the same gold calls (they are read off the rows' own prompts); only the batch the model sees changes
        Ls = [len(x['texts']) for x in golds]
        sched, last = m.plan(Ls, len(Ls), b['prompt_ids'].device)
        g = dict(L=Ls, ids=[x['ids'] for x in golds], tape=[tape(x) for x in golds], has=torch.tensor([bool(L) for L in Ls]))
        spy = Spy(m)
        with torch.no_grad():
            o = m.loop(b, max(Ls) + 2, g=g, sched=sched)
        return spy, o

    s0, o0 = tf(b1, lambda x: x['tape'])
    s1, o1 = tf(b2, lambda x: ['mul 9 9 = 81'] * len(x['tape']))               # another prompt, another tape, other replies
    s2, o2 = tf(b1, lambda x: [t + ' = ?' for t in x['texts']])
    assert s0.logp and len(s0.logp) == len(s1.logp) == len(s2.logp)
    assert all(torch.equal(a, c) and torch.equal(a, d) for a, c, d in zip(s0.logp, s1.logp, s2.logp)), 'teacher-forced call log-probs follow Z only'
    assert torch.equal(o0['Z'], o1['Z']) and float(o0['lcall']) == float(o1['lcall']) == float(o2['lcall'])
    spy, ref = Spy(m), None
    for b, les in ((b1, None), (b2, None), (b1, 'noexec'), (b2, 'opswap'), (b1, 'nocopy')):       # free run: another prompt, replies changed by the lesion, the tape follows
        n0 = len(spy.greedy)
        with torch.no_grad():
            m.run(b, loops=5, lesion=les)
        got = spy.greedy[n0:]
        ref = ref or got
        assert got and got == ref, (les, 'the greedy call text follows Z only')
    assert spy.heads and all(not has and not nc and ck and not xc and not ci for has, nc, ck, xc, ci in spy.heads), 'the call writer\'s head never receives a visible context, keys or the lesion'
    print('ok R2 T2: with Z fixed, changing the prompt, the tape and the replies leaves the call log-probs bit-identical and the greedy call text identical; the head never sees a context')


def test_r2_no_prompt_or_tape_reaches_any_writer_call():
    """Source check: in b3g2.py no writer call is given a prompt / tape tensor; the context it gets is line_context(Z)'s, and the copy-key machinery is gone."""
    import custom_io.models.b3g2 as M
    tree = ast.parse(inspect.getsource(M))
    forbid = {'X', 'xm', 'Xt', 'idt', 'mt', 'vis', 'pids', 'batch', 'ckeys', 'ck', 'shown'}
    n_calls = 0
    for fn in [x for x in ast.walk(tree) if isinstance(x, ast.FunctionDef)]:
        ctx_from_z = {t.id for a in ast.walk(fn) if isinstance(a, ast.Assign) and isinstance(a.value, ast.Call) and getattr(a.value.func, 'attr', '') == 'line_context'
                      for tg in a.targets for t in ast.walk(tg) if isinstance(t, ast.Name)}
        for c in [x for x in ast.walk(fn) if isinstance(x, ast.Call)]:
            f = ast.unparse(c.func)
            if not (f == 'self.writer' or f.startswith('self.writer.') and f.split('.')[-1] in ('greedy', 'run', 'forward', 'head')):
                continue
            n_calls += 1
            names = {x.id for a in c.args + [k.value for k in c.keywords] for x in ast.walk(a) if isinstance(x, ast.Name)}
            attrs = {x.attr for a in c.args + [k.value for k in c.keywords] for x in ast.walk(a) if isinstance(x, ast.Attribute)}
            assert not names & forbid and not attrs & {'prompt_ids', 'ckeys'}, (fn.name, f, names, attrs)
            assert not {'Xc', 'cmask', 'cids'} & names or {'Xc', 'cmask', 'cids'} <= ctx_from_z, (fn.name, 'the writer context is not line_context(Z)')
    assert n_calls >= 3, n_calls
    names = {x.attr for x in ast.walk(tree) if isinstance(x, ast.Attribute)} | {x.name for x in ast.walk(tree) if isinstance(x, ast.FunctionDef)}
    assert not names & {'ckeys', 'layout_terms', 'span_keys', 'e_s', 'e_e'}, names & {'ckeys', 'layout_terms', 'span_keys', 'e_s', 'e_e'}
    assert M.B3G2.answer_context is M.B3G2.line_context
    print('ok R2 T2: b3g2.py passes no prompt / tape tensor into any writer call (%d call sites), the context is line_context(Z), no copy-key code' % n_calls)


GOLD = dict(call='0x1.03e5640000000p+7', call_acc='0x0.0p+0', eos_acc='0x0.0p+0', stop_in='0x1.f334380000000p-15', stop_abs='0x1.2905bcd29db68p+13')       # re-taken at G2f (calls from Z only): the copy-free writer draws fewer init numbers, so loud()'s eg_proj draw (global RNG, after make) moves; before G2f: call 0x1.2ee1860000000p+7, stop_in 0x1.8874b80000000p-15, stop_abs 0x1.28eccd1bf5ea8p+13


def test_r2_call_and_stop_inputs_unchanged_by_the_answer_rule():
    m = loud((torch.manual_seed(0), make())[1]).train()
    cap = {}
    m.stop.register_forward_hook(lambda mod, inp, out: cap.update(z=inp[0].detach()))
    b = batch_of(rows(8), V)
    torch.manual_seed(7)
    loss, aux = m.loss(b)
    z = cap['z'].double()
    got = dict(call=float(aux['call']).hex(), call_acc=float(aux['call_acc']).hex(), eos_acc=float(aux['eos_acc']).hex(), stop_in=float(z.sum()).hex(), stop_abs=float(z.abs().sum()).hex())
    assert got == GOLD, (got, GOLD)
    assert torch.isfinite(loss) and float(aux['copy_share']) == 0.0
    print('ok R2 T2 (d): the call loss, the call/EOS hits and the stop head\'s inputs are bit-identical to the G2f pin (taken at G2f; the answer term and the stop LABELS, which are built from the answers, change)')


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


def test_r2_settle_pass_is_per_row():
    """A forced run's extra "settle" think pass (after a call written at the last round) is per row: loops=2 on a 2-row batch where only row 0 calls at round 1 -> row 1's Z and
    its talk() output equal row 1 run alone (it has no reply to read, so it gets no extra pass whatever its batch mate does); row 0 still reads its last reply."""
    m = noisy_writer(loud(make())).eval()
    P0 = 'Echo: abc'
    for P1 in ('Echo: xyz', 'Echo: a rather longer second prompt'):        # same length, and a different one (padding must not matter)
        b2 = batch_of([dict(id='a', family='copy_word', prompt=P0, answer='x', steps=[]), dict(id='b', family='copy_word', prompt=P1, answer='x', steps=[])], V)
        b1 = batch_of([dict(id='b', family='copy_word', prompt=P1, answer='x', steps=[])], V)
        a0 = batch_of([dict(id='a', family='copy_word', prompt=P0, answer='x', steps=[])], V)
        zs = {}
        for rep in ('12', '99999'):
            Script(m, [['add 7 5'], []])
            with torch.no_grad():
                o = m.run(b2, loops=2, oracle=lambda i, t, call, rep=rep: rep)
                st = m.state_of(o)
                ans = m.talk(st, b2)
            m.writer.greedy = m.writer.greedy.real
            assert o['calls'][0] and o['calls'][0][0][0] == 1 and o['calls'][0][0][4] == rep and not o['calls'][1], o['calls']
            assert (o['cround'][0] == 1).any() and not (o['cround'][1] == 1).any()
            Script(m, [[]])
            with torch.no_grad():
                o1 = m.run(b1, loops=2)
                ans1 = m.talk(m.state_of(o1), b1)
            m.writer.greedy = m.writer.greedy.real
            assert not o1['calls'][0]
            d1 = (o['Z'][1] - o1['Z'][0]).abs().max().item()
            assert d1 <= 1e-6, ('row 1 changed by its batch mate', P1, rep, d1)
            assert ans[1] == ans1[0], (ans[1], ans1[0])
            Script(m, [['add 7 5']])
            with torch.no_grad():
                oa = m.run(a0, loops=2, oracle=lambda i, t, call, rep=rep: rep)
            m.writer.greedy = m.writer.greedy.real
            assert (o['Z'][0] - oa['Z'][0]).abs().max().item() <= 1e-5, 'row 0 alone and in the batch agree'
            zs[rep] = o['Z'][0]
        assert (zs['12'] - zs['99999']).abs().max() > 0, 'row 0 still reads its last reply (its Z follows the reply text)'
    print('ok R2 (h): the settle pass after a forced run is per row: a row that wrote no call at the last round keeps its Z (and its talk()) as if run alone; the row that did still reads its reply')


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
