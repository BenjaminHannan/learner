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
    print('ok R2 (d): run + talk on a batch with calls embed the question once; replies take their own passes outside the memo')


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


def main():
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            print(name)
            fn()
    print('ALL OK')


if __name__ == '__main__':
    main()
