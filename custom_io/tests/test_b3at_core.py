"""python3 -m custom_io.tests.test_b3at_core   (CPU, a few minutes; no data files, no Gemma: test_b3's stub FrozenEG; run with OMP_NUM_THREADS=2)
The core of the agent-turn model (architecture/AT-BUILD-SPEC-2026-10-11.md secs. 1-4, talker/B3AT-BUILD-NOTES-2026-10-11.md; models/b3at.py), the sealed AT-0 checks that need only the model
class: (i) a tool's reply enters the model ONLY through read_texts (its calls and outputs are recorded; replacing one reply string changes the thinker's inputs only at that entry's tape
positions, and not at all before the turn after it was written; the source of b3at.py never turns reply text into an embedding itself); (ii) the talker sees only thoughts (Z held fixed:
changing the prompt, the tape and the replies leaves every line's probabilities bit-identical, teacher forced, talk and a multi-turn free run; every writer call has the empty, masked
context); (v) the ST1 hooks (sample_traces well-formed and generator-pure, trace_loss backpropagates, st1.self_teach runs); (vii) the counters (a forced 17th line, an over-long reply, an
over-long line, rounds per turn over 32, each increments its own; normal toy rows leave every counter at 0). Plus: the free run with a SCRIPTED talker (dispatch by first word, replies
visible from the next turn, the learned stop per turn, forced loops, the caps), the teacher-forced loop (per-row TOTAL_CAP cut, keep-Z logic, stop pairs only at R_i = TCAP), teacher-forced
thinker states equal the free run's on the same lines, the loss backpropagates to every parameter that should learn, run / generate with each lesion, talk_rounds 'all', the per-turn
evals (call_evals)."""
import re
import torch
from custom_io import capcount
from custom_io.data import EOS, ByteVocab
from custom_io.models import NAMES, build, get_class
from custom_io.models import b3at as M
from custom_io.models.b3g2 import B3G2
from custom_io.models.tool import LE
from custom_io.tests.test_b3 import CFG, StubEG, batch_of, rows

G2 = dict(CFG, eg_embed=True, any_round=True, gap_p=0.0, no_slots=True, no_place=True, bytes=True)
V = ByteVocab()
FAULTS = ('turns_over', 'tape_entry_over', 'writer_over', 'unended', 'turn_rounds_over', 'steps_unparsed', 'no_trace', 'steps_over')
LESIONS = [None, 'noexec', 'opswap', 'nocopy', 'zero_state', 'shuffle_state', 'loops:0', 'loops:4', 'loops:32', 'ctl27']


def make(seed=0, vocab=V, **kw):
    torch.manual_seed(seed)
    m = build('b3at', vocab, **{**G2, **kw})
    m._eg = [StubEG()]
    m.eval()
    return m


class LineScript:
    """Replaces model.write_lines: the t-th time row i is asked (turn t of row i, in lockstep) it writes lines[i][t] (a row past its list writes ''; a (row, turn) in `unended` does not end).
    Records every call as (rows, Z.shape). The writer is not run."""

    def __init__(self, m, lines, unended=()):
        self.m, self.lines, self.unended, self.real, self.log = m, lines, set(unended), m.write_lines, []
        self.turn = [0] * len(lines)
        m.write_lines = self

    def __call__(self, Z, zm=None, rows=None, temperature=0.0, generator=None):
        self.log.append((list(rows), tuple(Z.shape), None if zm is None else tuple(zm.shape)))
        outs, ended = [], []
        for i in rows:
            k, self.turn[i] = self.turn[i], self.turn[i] + 1
            t = self.lines[i][k] if k < len(self.lines[i]) else ''
            outs.append(self.m.vocab.encode(t)); ended.append((i, k) not in self.unended)
        return outs, torch.tensor(ended)

    def off(self):
        self.m.write_lines = self.real


class Spy:
    """Records every thinker round's inputs (Z in, kvs, kvx, mask, the global round index) and every read_texts call (texts, X, ids, mask)."""

    def __init__(self, m):
        self.m, self.think, self.read = m, [], []
        self.real_think, self.real_read = m.think, m.read_texts
        m.think, m.read_texts = self.on_think, self.on_read

    def on_think(self, Z, kvs, kvx, mask, t):
        self.think.append((Z.clone(), [k.clone() for k in kvs], [k.clone() for k in kvx], mask.clone(), t))
        return self.real_think(Z, kvs, kvx, mask, t)

    def on_read(self, texts, dev, le=LE):
        X, ids, mask = self.real_read(texts, dev, le)
        self.read.append((list(texts), X.clone(), ids.clone(), mask.clone()))
        return X, ids, mask

    def off(self):
        self.m.think, self.m.read_texts = self.real_think, self.real_read


def tape_counts(spy, K=16, le=LE):
    """-> per thinker call, the visible tape positions of each row (the mask's tape part, no_slots)."""
    return [sp[3][:, :K * le].sum(1).tolist() for sp in spy.think]


# ---- the model, its registry entry and every path ----
def test_paths_and_lesions():
    assert 'b3at' in NAMES and get_class('b3at') is M.B3AT and issubclass(M.B3AT, B3G2) and M.TCAP == 32 and M.KS_T == (4, 8, 16, 32) and M.TOTAL_CAP == 96
    m = make()
    assert m.TURNS == 17 and m.tape == 16 and m.WCAP == 69 and not m.writer.copy
    b = batch_of(rows(8), V)
    m.train()
    loss, aux = m.loss(b)              # a deleted attribute touched anywhere on a path raises AttributeError
    loss.backward()
    assert torch.isfinite(loss) and aux['copy_share'] == 0.0 and aux['R'] in M.KS_T and aux['turns'] == 2.25, aux
    m.eval()
    with torch.no_grad():
        for les in LESIONS:
            out = m.generate(b, lesion=les)
            assert len(out) == 8 and all(isinstance(x, str) for x in out), (les, out)
        o = m.run(b)
        st = m.state_of(o)
        assert len(st) == 4 and st[0].shape[0] == 8 and len(o['answers']) == 8 and len(o['rounds']) == 8 and m.last_rounds == o['rounds'] and m.last_turns == o['turns']
        assert all(1 <= r <= 32 * 17 for r in o['rounds']) and all(1 <= t <= 17 for t in o['turns'])
        assert m.generate(b) == o['answers']                               # generate() is the free run's answers
        assert [x for x in m.talk(st, b)] == [x for x in m.talk(st, b)] and len(m.talk(st, b)) == 8
        d = batch_of(rows(8)[::-1], V)                                   # a donor swap: the donor's state, the current batch
        assert len(m.talk(m.state(d), b)) == 8 and m.supports_donor()
        a = m.run(b, loops=3)
        assert a['rounds'] == [3 * t for t in a['turns']] and m.last_rounds == a['rounds']
    try:
        m.generate(b, lesion='nowordc')
        raise SystemExit('nowordc should be refused')
    except ValueError:
        pass
    # talk_rounds 'all': every path runs, the state carries the memory, the lesions act on it
    ma = make(1, talk_rounds='all')
    ma.train()
    loss, _ = ma.loss(b)
    loss.backward()
    ma.eval()
    with torch.no_grad():
        for les in LESIONS:
            out = ma.generate(b, lesion=les)
            assert len(out) == 8 and all(isinstance(x, str) for x in out), (les, out)
        o = ma.run(b, loops=3)
        st = ma.state_of(o)
        assert len(st) == 6 and st[4].shape[0] == 8 and st[4].shape[1] % 17 == 0 and st[5].shape == st[4].shape[:2] and st[5].any(1).all()
        assert len(ma.talk(st, b)) == 8 and len(ma.sample_traces(b, 1.0, torch.Generator().manual_seed(0))) == 8
        z = ma.lesioned(st, 'zero_state')
        assert z[4].abs().sum() == 0 and torch.equal(z[5], st[5]) and torch.equal(ma.lesioned(st, 'shuffle_state')[5], st[5].roll(1, 0))
    print('ok b3at registered (subclass of B3G2, TCAP 32, KS_T %s, TOTAL_CAP %d, %d turns); loss / run / generate run under every lesion %s; talk_rounds all runs with memory (state %d long)'
          % (M.KS_T, M.TOTAL_CAP, m.TURNS, [str(x) for x in LESIONS], len(st)))


# ---- the free run with a scripted talker ----
def test_scripted_free_run():
    m = make(5)
    b = batch_of(rows(4), V)
    lines = [['add 7 5', 'sub 12 3', 'ans9'], ['foo bar'], ['add 1', 'note hello there', 'mul 3 4', '12'], ['add 1 1'] * 19]
    spy = Spy(m)
    sc = LineScript(m, lines)
    with torch.no_grad():
        o = m.run(b, loops=2)
    c = o['calls']
    assert c[0] == [(0, 'add', '7', '5', '12'), (1, 'sub', '12', '3', '9')], c[0]
    assert o['answers'][0] == 'ans9' and o['answers'][1] == 'foo bar' and c[1] == [], (o['answers'], c[1])        # a line whose first word names no tool IS the final answer
    assert c[2] == [(0, 'add', '1', '', '?'), (1, 'note', 'hello there', '', ''), (2, 'mul', '3', '4', '12')] and o['answers'][2] == '12', c[2]
    assert len(c[3]) == 16 and o['tape_full'] == [(3, 16)] and o['answers'][3] == '' and m.last_tape_full == [False, False, False, True]
    assert o['turns'] == [3, 1, 4, 17] == m.last_turns and o['rounds'] == [6, 2, 8, 34] == m.last_rounds and o['turn_rounds'][0] == [2, 2, 2]
    assert o['records'][0] == [(0, 'add 7 5', '12'), (1, 'sub 12 3', '9')]
    assert [r for r, _, _ in sc.log[0:1]] == [[0, 1, 2, 3]] and sc.log[1][0] == [0, 2, 3] and sc.log[3][0] == [2, 3] and sc.log[4][0] == [3]       # only the live rows write
    Xt, idt, vis = o['tape']
    ent = lambda i, k: V.decode(idt[i, k * LE:(k + 1) * LE][vis[i, k * LE:(k + 1) * LE]].tolist())
    assert [ent(0, k) for k in range(3)] == ['add 7 5 = 12', 'sub 12 3 = 9', ''] and ent(1, 0) == '' and [ent(2, k) for k in range(3)] == ['add 1 = ?', 'note hello there', 'mul 3 4 = 12']
    # a reply is on the tape and visible from the NEXT turn (2 rounds per turn: thinker call 2 * turn is the turn's first round)
    cnt = tape_counts(spy)
    assert [cnt[2 * t][0] for t in range(3)] == [0, 12, 24] and [cnt[2 * t][2] for t in range(4)] == [0, 9, 25, 37] and [cnt[2 * t][3] for t in range(4)] == [0, 11, 22, 33], cnt[::2][:5]
    assert cnt[0] == [0, 0, 0, 0] and cnt[1] == [0, 0, 0, 0] and cnt[2][1] == 0 and len(spy.think) == 2 * 17
    assert o['Z'].shape[0] == 4 and o['rounds'][1] == 2
    # the learned stop decides per turn: one round each (p = 1) or the cap (p = 0: 32 rounds, counted turn_cap, reported)
    spy.off()
    sc.off()
    for bias, want in ((50.0, None), (-50.0, 32)):
        m.stop.weight.data.zero_(); m.stop.bias.data.fill_(bias)
        sc = LineScript(m, lines[:3])
        capcount.reset()
        with torch.no_grad():
            o = m.run(batch_of(rows(3), V))
        assert o['turn_rounds'] == [[want or 1] * 3, [want or 1], [want or 1] * 4], o['turn_rounds']
        assert o['rounds'] == [(want or 1) * x for x in (3, 1, 4)]
        assert capcount.snapshot()['reported']['turn_cap'] == (0 if want is None else 8) and capcount.snapshot()['total'] == 0, capcount.snapshot()
        sc.off()
    # noexec / opswap act inside the dispatch, the oracle replaces the calculator's reply for a two-token call (called as oracle(i, turn, call))
    seen = []
    for les, want in ((None, ['12', '9']), ('noexec', ['?', '?']), ('opswap', ['2', '15'])):
        sc = LineScript(m, lines[:3])
        with torch.no_grad():
            o = m.run(batch_of(rows(3), V), loops=1, lesion=les)
        assert [x[4] for x in o['calls'][0]] == want, (les, o['calls'][0])
        assert [x[4] for x in o['calls'][2]] == {None: ['?', '', '12'], 'noexec': ['?', '', '?'], 'opswap': ['?', '', '12']}[les], o['calls'][2]       # a note replies nothing; mul is not swapped
        sc.off()
    sc = LineScript(m, lines[:3])
    with torch.no_grad():
        o = m.run(batch_of(rows(3), V), loops=1, oracle=lambda i, t, call: (seen.append((i, t, call)), '99')[1])
    assert [x[4] for x in o['calls'][0]] == ['99', '99'] and [x[4] for x in o['calls'][2]] == ['?', '', '99'] and o['calls'][1] == [], o['calls']
    assert seen == [(0, 0, ('add', '7', '5')), (0, 1, ('sub', '12', '3')), (2, 2, ('mul', '3', '4'))], seen
    sc.off()
    # a line with no EOS within WCAP is not written: the row answers '' and ends (counted unended)
    capcount.reset()
    sc = LineScript(m, [['add 1 1', 'x'], ['y']], unended={(0, 1), (1, 0)})
    with torch.no_grad():
        o = m.run(batch_of(rows(2), V), loops=1)
    assert o['answers'] == ['', ''] and o['turns'] == [2, 1] and len(o['calls'][0]) == 1 and capcount.snapshot()['unended'] == 2 and m.free_stats['unended'] >= 2
    sc.off()
    capcount.reset()
    print('ok scripted talker: dispatch by first word (unknown / empty = the answer), notes and bad arity, replies visible from the next turn, 17th line ends the row, learned stop per turn / TCAP, lesions, oracle, unended')


# ---- (i) replies enter only through read_texts ----
def test_replies_only_through_read_texts():
    m = make(11)
    b = batch_of(rows(4), V)
    lines = [['add 7 5', 'sub 12 3', 'done'], ['mul 3 4', 'done'], ['add 1 1', 'done'], ['done']]
    out = {}
    for tag, repl in (('base', None), ('same_len', '99'), ('longer', '9999')):
        spy = Spy(m)
        sc = LineScript(m, lines)
        with torch.no_grad():
            o = m.run(b, loops=2, oracle=None if repl is None else (lambda i, t, c, r=repl: r if (i, t) == (0, 0) else m.calculator(c[0], f'{c[1]} {c[2]}')))
        out[tag] = (o, spy)
        spy.off(); sc.off()
    base_o, base = out['base']
    n = len(base.think)
    assert n == 2 * 3 and all(len(out[t][1].think) == n for t in out)
    # every tape string the model holds was read by read_texts (Gemma + letter window) and by nothing else: the strings of the final tape are among the strings read_texts was given, and
    # what the tape holds IS read_texts' output (+ tape_emb[k])
    Xt, idt, vis = base_o['tape']
    given = [t for texts, *_ in base.read for t in texts]
    for i in range(4):
        for k in range(16):
            s = V.decode(idt[i, k * LE:(k + 1) * LE][vis[i, k * LE:(k + 1) * LE]].tolist())
            assert s == '' or s in given, (i, k, s)
    recorded = {t for texts, *_ in base.read for t in texts}
    assert {'add 7 5 = 12', 'sub 12 3 = 9', 'mul 3 4 = 12', 'add 1 1 = 2'} <= recorded
    # per-turn thinker inputs: replace row 0's turn-0 reply ('12' -> '99'): before turn 1 nothing differs; from turn 1 only row 0's kvs at the slot-0 positions differ (and Z follows)
    for tag, same_mask in (('same_len', True), ('longer', False)):
        o2, alt = out[tag]
        assert o2['calls'][0][0][4] == ('99' if tag == 'same_len' else '9999') and base_o['calls'][0][0][4] == '12'
        for c, (a, bb) in enumerate(zip(base.think, alt.think)):
            turn = c // 2
            Za, kva, kxa, ma, ta = a
            Zb, kvb, kxb, mb, tb = bb
            assert ta == tb == c and all(torch.equal(x, y) for x, y in zip(kxa, kxb)), 'the question side never depends on a reply'
            for kx, ky in zip(kva, kvb):
                d = (kx != ky).any(0).any(1).any(-1)                    # [B, tape positions]: where the tape's keys / values differ
                assert not d[1:].any(), f'{tag} call {c}: another row\'s inputs changed'
                pos = d[0].nonzero()[:, 0].tolist()
                if turn == 0:
                    assert not pos, (tag, c)
                else:
                    assert pos and max(pos) < LE, (tag, c, pos)         # only slot 0 (the reply's own entry) differs
            dm = (ma != mb)
            assert not dm[1:].any()
            if same_mask:
                assert not dm.any()
            elif turn >= 1:
                pos = dm[0].nonzero()[:, 0].tolist()
                assert pos and max(pos) < LE and len(pos) == 2, (tag, c, pos)       # '99' -> '9999': two more visible positions, inside slot 0
            else:
                assert not dm.any()
            assert not (Za[1:] != Zb[1:]).any(), 'rows that did not change see the same Z'
            if c <= 2:
                assert torch.equal(Za, Zb), f'{tag} call {c}: Z must agree up to the first round that can see the reply'
        assert (base.think[3][0][0] != alt.think[3][0][0]).any(), 'the reply changed what row 0 thinks'
        # read_texts: the same calls in the same order; the one string that differs is that entry, and only its output rows differ
        assert len(base.read) == len(alt.read)
        diffs = 0
        for (ta, Xa, ia, ma_), (tb, Xb, ib, mb_) in zip(base.read, alt.read):
            assert len(ta) == len(tb)
            for q, (sa, sb) in enumerate(zip(ta, tb)):
                if sa == sb:
                    assert torch.equal(Xa[q], Xb[q]) and torch.equal(ia[q], ib[q])
                else:
                    diffs += 1
                    assert sa == 'add 7 5 = 12' and sb == 'add 7 5 = ' + ('99' if tag == 'same_len' else '9999') and (Xa[q] != Xb[q]).any()
        assert diffs == 1, diffs
    # the model's source never turns reply text into a vector by itself: only read_texts (through tape_of / the turn's entry) does
    src = open(M.__file__).read()
    body = re.sub(r'""".*?"""', '', src, flags=re.S)                    # the docstrings quote the rules
    for bad in ('tok.weight', 'reader.tok', 'nn.Embedding', 'F.embedding', 'ord(', 'int(rep', 'float(rep', 'isdigit', 'eg()'):
        assert bad not in body, bad
    assert body.count('read_texts(') == 1 and body.count('tape_of(') == 2 and 'self.vocab.encode(' not in body
    print('ok replies enter only through read_texts: %d read calls recorded, every tape string among them; replacing one reply changes the thinker only at slot 0 of that row from the next turn '
          '(same-length: keys / values only; longer: and the mask at 2 positions); nothing else differs' % len(base.read))


# ---- (ii) the talker sees only thoughts ----
class AnyTool(dict):
    """A tool table in which every first word names a tool and replies `reply` (so the free run goes on for all 17 turns whatever the talker writes)."""

    def __init__(self, reply):
        super().__init__()
        self.reply = reply

    def __contains__(self, k):
        return True

    def get(self, k, d=None):
        return lambda rest: self.reply


def test_talker_sees_only_thoughts():
    m = make(21)
    B, d = 8, m.d
    zfix = torch.randn(B, 17, d, generator=torch.Generator().manual_seed(3))
    m.think = lambda Z, kvs, kvx, mask, t: zfix.clone()                    # Z is held fixed: whatever the thinker would have read, the talker gets this
    log = []
    real_head = m.writer.head

    def head(R, Xc, cmask, cids, nocopy, ckeys):
        p, gate, a = real_head(R, Xc, cmask, cids, nocopy, ckeys)
        log.append((Xc.clone(), cmask.clone(), cids.clone(), nocopy, ckeys, gate.clone(), p.clone()))
        return p, gate, a
    m.writer.head = head

    def context_is_empty():
        assert log and all(not x.any() and not cm.any() and not ci.any() and not nc and ck is None and bool((g == 1).all()) for x, cm, ci, nc, ck, g, _ in log), 'a line saw a context'
    rA, rB = rows(8), rows(8)[::-1]
    bA, bB = batch_of(rA, V), batch_of(rB, V)
    assert [r['prompt'] for r in rA] != [r['prompt'] for r in rB]
    # teacher forced: the same lines (the golds' texts and answers), other prompts, other tape entries / replies -> bit-identical probabilities at every round of every turn
    gA = m.plain_golds(rA)
    gB = [dict(g, tape=[f'{t} = {1000 + 7 * i + k}' if ' ' in t and not t.startswith('note') else t + ' (other)' for k, t in enumerate(g['texts'])]) for i, g in enumerate(gA)]
    assert any(a['tape'] != c['tape'] for a, c in zip(gA, gB))
    with torch.no_grad():
        log.clear(); m._turns(bA, gA, 4, count=False); pa = [x[-1] for x in log]; context_is_empty()
        log.clear(); m._turns(bB, gB, 4, count=False); pb = [x[-1] for x in log]; context_is_empty()
    assert len(pa) == len(pb) > 0 and all(torch.equal(x, y) for x, y in zip(pa, pb)), 'teacher forced: a line changed with the prompt / tape / replies'
    # talk (greedy): the same Z with another prompt and another tape -> the same probabilities and the same text
    st = (zfix, torch.randn(B, 16 * LE, d), torch.randint(1, 50, (B, 16 * LE)), torch.rand(B, 16 * LE) > 0.5)
    st2 = (zfix, torch.randn(B, 16 * LE, d), torch.randint(1, 50, (B, 16 * LE)), torch.rand(B, 16 * LE) > 0.5)
    with torch.no_grad():
        log.clear(); ta = m.talk(st, bA); pa = [x[-1] for x in log]; context_is_empty()
        log.clear(); tb = m.talk(st2, bB); pb = [x[-1] for x in log]; context_is_empty()
        tc = m.talk((zfix.flip(0),) + st2[1:], bB)
    assert ta == tb and len(pa) == len(pb) > 0 and all(torch.equal(x, y) for x, y in zip(pa, pb)), 'talk: a line changed with the prompt / tape'
    m.writer.bias.data[EOS] = 50.0                                         # now every line is '' (EOS first), so the free run below writes 17 turns of the same thing
    # free run, greedy, all 17 turns: another prompt, other replies ('r1' / 'r2') -> bit-identical probabilities at every line
    plog = []
    for b_, rep in ((bA, 'r1'), (bB, 'r2')):
        m.tools = AnyTool(rep)
        m.is_call = lambda line: True                                   # every line (even '') is a call here, so the run goes on for all 17 turns whatever the talker writes
        log.clear()
        with torch.no_grad():
            o = m.run(b_, loops=1)
        context_is_empty()
        plog.append([x[-1] for x in log])
        assert o['turns'] == [17] * B and all(len(c) == 16 for c in o['calls']) and o['calls'][0][0][4] == rep and m.last_tape_full == [True] * B
    assert len(plog[0]) == 17 and all(torch.equal(x, y) for x, y in zip(*plog)), 'free run: a line changed with the prompt / replies'
    # the writer has no other way in: ans_pass takes Z, the line's own bytes and nothing from the prompt or the tape
    import inspect
    assert list(inspect.signature(m.ans_pass).parameters) == ['Z', 'inp', 'tgt', 'fb', 'zm'] and list(inspect.signature(m.write_lines).parameters) == ['Z', 'zm', 'rows', 'temperature', 'generator']
    m.writer.head = real_head
    print('ok the talker sees only thoughts: Z fixed, other prompt / tape / replies -> bit-identical line probabilities (teacher forced %d passes, talk %d, a 17-turn free run %d lines); every writer call has the empty masked context, gate 1, no ckeys'
          % (len(pa), len(pa), len(plog[0])))


# ---- teacher forcing ----
def test_teacher_forcing_caps_and_keep():
    import custom_io.models.b3at as MM
    MM.KS_T = (32,)
    try:
        m = make(2)
        m.train()
        rs = rows(2)
        texts = ['add 1 1'] * 5
        gl = [m.make_gold(texts, [f'{t} = 2' for t in texts], '2'), m.make_gold([], [], 'sune')]
        spy = Spy(m)
        capcount.reset()
        loss, aux = m._loss(batch_of(rs, V), gl)
        spy.off()
        # R = 32; row 0 has L = 5: R_0 = min(32, 96 // 6) = 16 rounds in each of its 6 turns; row 1 (L = 0) runs 32 rounds in turn 0 and keeps its Z afterwards
        assert len(spy.think) == 32 + 5 * 16 and capcount.snapshot()['reported']['turn_rounds_capped'] == 1 and capcount.snapshot()['total'] == 0, (len(spy.think), capcount.snapshot())
        assert aux['R'] == 32.0 and aux['rounds'] == (16 * 6 + 32) / 2 and aux['turns'] == 3.5 and aux['stop_pairs'] == 32.0 and aux['stop_w'] == 1.0, aux
        zin = [sp[0] for sp in spy.think]
        assert all(torch.equal(zin[r][0], zin[16][0]) for r in range(16, 32)), 'row 0 past its R_i keeps its Z'
        assert not torch.equal(zin[16][1], zin[17][1]) and not torch.equal(zin[15][0], zin[16][0])
        assert all(torch.equal(zin[32 + 16 * t][1], zin[32][1]) for t in range(1, 5)), 'row 1 past its last turn keeps its Z'
        assert [sp[4] for sp in spy.think] == list(range(112)), 'the global round index counts every batched round'
        loss.backward()
        assert torch.isfinite(loss) and float(aux['ans']) > 0 and float(aux['call']) > 0
        # R = 4: no row is cut, the stop loss is off (no pair ran the whole turn)
        MM.KS_T = (4,)
        capcount.reset()
        m.zero_grad()
        loss, aux = m._loss(batch_of(rs, V), gl)
        assert capcount.snapshot()['reported']['turn_rounds_capped'] == 0 and aux['stop_w'] == 0.0 and aux['stop_pairs'] == 0.0 and torch.isfinite(loss) and aux['rounds'] == 4 * 3.5
        # a line that cannot be written in WCAP steps has no target and is counted (never cut): the row's loss only counts its other lines
        capcount.reset()
        long = m.make_gold(['add 1 1'], ['add 1 1 = 2'], 'x' * 90)
        assert capcount.snapshot()['writer_over'] == 1
        loss, aux = m._loss(batch_of(rs, V), [long, gl[1]])
        assert torch.isfinite(loss) and aux['line_acc_ans'] <= 1.0
        capcount.reset()
    finally:
        MM.KS_T = (4, 8, 16, 32)
    print('ok teacher forcing: R=32 with L=5 is cut to 16 rounds per turn (counted turn_rounds_capped), a row past its R_i / last turn keeps its Z, global round index 0..111, stop loss only on R_i = TCAP pairs (32), R=4 turns the stop off, an over-long line gets no target')


def test_teacher_forced_thinker_equals_free_run():
    """The thinker's state after the last turn is the same computation teacher forced and free (same lines, same tape, same rounds per turn)."""
    for mode in ('last', 'all'):
        m = make(8, talk_rounds=mode)
        rs = rows(6)
        b = batch_of(rs, V)
        golds = m.plain_golds(rs)
        with torch.no_grad():
            _, _, info = m._turns(b, golds, 3, count=False)
            sc = LineScript(m, [g['texts'] + [g['ans']] for g in golds])
            o = m.run(b, loops=3)
            sc.off()
        assert o['turns'] == [len(g['texts']) + 1 for g in golds] and o['answers'] == [g['ans'] for g in golds], (o['turns'], o['answers'])
        assert [[x[1] for x in r] for r in o['records']] == [g['texts'] for g in golds]
        assert torch.allclose(info['Z'], o['Z'], atol=1e-4, rtol=1e-4), float((info['Z'] - o['Z']).abs().max())
    print('ok teacher-forced thinker state == free-run state on the same lines (3 rounds per turn, max |diff| %.2g), talk_rounds last and all' % float((info['Z'] - o['Z']).abs().max()))


def test_carry_draw():
    """_turns carry='last' (the default; evals) is the old path; carry='draw' (_loss) starts the next turn from the Z after a drawn round c_ij in 1..R_i. Tested with c forced through carry_draw."""
    m = make(9)
    m.eval()
    rs = rows(6)
    b = batch_of(rs, V)
    golds = m.plain_golds(rs)
    orig, orig_coin = M.B3AT.carry_draw, M.B3AT.carry_coin
    M.B3AT.carry_coin = staticmethod(lambda B, dev: torch.ones(B))                          # coin forced to 'uniform' (coin >= CARRY_STOP): the c_ij path alone
    try:
        t0, a0, _ = m._turns(b, golds, 3, count=False)                                  # carry='last'
        M.B3AT.carry_draw = staticmethod(lambda Rt, dev: Rt.clone())                       # c_ij = R_i: the drawn path must equal 'last' bit for bit
        t1, a1, _ = m._turns(b, golds, 3, count=False, carry='draw')
        assert torch.equal(t0, t1) and all(torch.equal(torch.as_tensor(a0[k]), torch.as_tensor(a1[k])) for k in a0), (float(t0), float(t1))
        M.B3AT.carry_draw = staticmethod(lambda Rt, dev: torch.ones_like(Rt))              # c_ij = 1
        log, th = [], m.think
        m.think = lambda Z, *a, **k: (log.append((Z.detach().clone(), None)), log.__setitem__(-1, (log[-1][0], th(Z, *a, **k).detach().clone())), th(Z, *a, **k))[-1]
        m._turns(b, golds, 3, count=False, carry='draw')
        m.think = th
    finally:
        M.B3AT.carry_draw, M.B3AT.carry_coin = staticmethod(orig), staticmethod(orig_coin)
    assert len(log) == 3 * (max(len(g['texts']) for g in golds) + 1), len(log)
    rows1 = [i for i, g in enumerate(golds) if len(g['texts']) >= 1]
    assert rows1
    step0 = m.step_emb.weight[0]
    for j in range(1, 3):                                                                   # turn j starts (log index 3 j) from the first turn's Z after round 1 (index 3 (j - 1)), for the rows that ran turn j
        for i in [i for i, g in enumerate(golds) if len(g['texts']) >= j]:
            assert torch.allclose(log[3 * j][0][i] - step0, log[3 * (j - 1)][1][i], atol=1e-6), (j, i)
    assert not torch.allclose(log[3][0][rows1[0]] - step0, log[2][1][rows1[0]], atol=1e-4)      # and not the Z after round 3 ('last')
    assert torch.equal(M.B3AT.carry_draw(torch.tensor([1, 5, 32]), 'cpu')[:1], torch.ones(1, dtype=torch.long))
    for _ in range(20):
        c = M.B3AT.carry_draw(torch.tensor([1, 5, 32]), 'cpu')
        assert c[0] == 1 and 1 <= c[1] <= 5 and 1 <= c[2] <= 32
    print("ok carry: 'last' == 'draw' with c = R_i (loss %.6f and every aux key bit-identical); with c = 1 turn j starts from the previous turn's Z after round 1 (%d rows checked); carry_draw stays in 1..R_i" % (float(t0.detach()), len(rows1)))


def test_carry_stop():
    """carry='draw' with the coin on 'stop' carries the Z after the stop round s_ij; the choice adds no gradient path to the stop head."""
    m = make(9)
    m.eval()
    rs = rows(6)
    b = batch_of(rs, V)
    golds = m.plain_golds(rs)
    B = len(rs)
    orig_draw, orig_coin = M.B3AT.carry_draw, M.B3AT.carry_coin
    try:
        # (2) coin forced 'stop', the stop fires at round 2 for every row: turn j starts from the previous turn's Z after round 2
        M.B3AT.carry_coin = staticmethod(lambda B_, dev: torch.zeros(B_))
        m.stop_fires = lambda zd, r: torch.full((zd.shape[0],), r == 1, dtype=torch.bool)
        log, th = [], m.think
        m.think = lambda Z, *a, **k: (log.append((Z.detach().clone(), None)), log.__setitem__(-1, (log[-1][0], th(Z, *a, **k).detach().clone())), th(Z, *a, **k))[-1]
        try:
            _, aux, _ = m._turns(b, golds, 3, count=False, carry='draw')
        finally:
            m.think = th
        step0 = m.step_emb.weight[0]
        n = 0
        for j in range(1, 3):
            for i in [i for i, g in enumerate(golds) if len(g['texts']) >= j]:
                assert torch.allclose(log[3 * j][0][i] - step0, log[3 * (j - 1) + 1][1][i], atol=1e-6), (j, i)
                n += 1
        assert n and abs(float(aux['carry_stop_round']) - 2.0) < 1e-6, (n, aux['carry_stop_round'])
        print('ok carry stop: coin on stop, stop fires at round 2 -> turn j starts from the previous turn\'s Z after round 2 (%d (row, turn) pairs), carry_stop_round = %.1f' % (n, float(aux['carry_stop_round'])))
        # a stop that never fires carries round R_i (= 'last'); the coin on 'uniform' with c = R_i is the same graph
        del m.stop_fires
        m.stop_fires = lambda zd, r: torch.zeros(zd.shape[0], dtype=torch.bool)
        grads = []
        for coin in (0.0, 1.0):
            M.B3AT.carry_coin = staticmethod(lambda B_, dev, coin=coin: torch.full((B_,), coin))
            M.B3AT.carry_draw = staticmethod(lambda Rt, dev: Rt.clone())
            m.zero_grad()
            t, _, _ = m._turns(b, golds, 3, count=False, carry='draw')
            gs = torch.autograd.grad(t, list(m.stop.parameters()), allow_unused=True)
            grads.append(gs)
        assert all(torch.equal(x, y) for x, y in zip(*grads) if x is not None)
        # (3) the stop decision itself carries no graph, even from an input that requires grad
        del m.stop_fires
        zd = torch.randn(B, m.stop.in_features if hasattr(m.stop, 'in_features') else 1, requires_grad=True)
        try:
            assert not m.stop_fires(zd, 0).requires_grad
        except Exception as e:
            if isinstance(e, AssertionError):
                raise
    finally:
        M.B3AT.carry_draw, M.B3AT.carry_coin = staticmethod(orig_draw), staticmethod(orig_coin)
        m.__dict__.pop('stop_fires', None)
    print('ok carry stop: stop-head gradients are identical with the coin on stop and on uniform (stop never firing, c = R_i); the stop decision has requires_grad False')


def test_grads():
    import custom_io.models.b3at as MM
    MM.KS_T = (32,)
    try:
        for mode in ('last', 'all'):
            m = make(2, talk_rounds=mode)
            m.train()
            b = batch_of(rows(8), V)            # 0, 1 and 2 calls per row: R_i = 32 everywhere (96 // 3), so the stop loss counts
            loss, aux = m.loss(b)
            assert float(aux['stop_w']) == 1.0 and aux['R'] == 32.0 and aux['rounds'] == 32 * 2.25
            loss.backward()
            bad, zero = [], []
            for n, p in m.named_parameters():
                if p.grad is None or not torch.isfinite(p.grad).all():
                    bad.append(n)
                elif not p.grad.abs().sum() > 0 and not n.startswith(('tape_emb', 'step_emb', 'reader.pos', 'reader.place', 'ctrl', 'src', 'ln_eg')):
                    zero.append(n)
            assert not bad, bad
            assert not zero, f'no gradient reached: {zero}'
            assert torch.isfinite(loss) and float(aux['call']) > 0 and float(aux['ans']) > 0
            assert m.tape_emb.weight.grad[:2].abs().sum() > 0 and m.step_emb.weight.grad.abs().sum() > 0, 'the tape and the rounds embeddings learn'
            # the gradient reaches the thinker through the talker, across turns: the first turn's thoughts carry the later calls' information (a tape row read only from turn 1 on)
            assert m.stop.weight.grad.abs().sum() > 0 and m.ln_z.weight.grad.abs().sum() > 0
    finally:
        MM.KS_T = (4, 8, 16, 32)
    print('ok teacher-forced loss finite; every trainable parameter (%d tensors) gets a gradient (the stop head too), talk_rounds last and all' % sum(1 for _ in m.parameters()))


# ---- (v) ST1 ----
def test_st1_hooks():
    from custom_io import st1
    m = make(7)
    rs = rows(8)
    b = batch_of(rs, V)
    gen = torch.Generator().manual_seed(0)
    tr = m.sample_traces(b, 1.0, gen)
    assert len(tr) == 8 and all(set(t) == {'calls', 'answer', 'no_answer'} and isinstance(t['answer'], str) and isinstance(t['calls'], list) for t in tr)
    assert m.sample_traces(b, 1.0, torch.Generator().manual_seed(0)) == tr                     # drawn only from the generator
    # well-formed with a scripted talker: every tool line is a (line, reply) pair, notes included, the answer is the final line
    sc = LineScript(m, [['add 3 4', 'sub 7 2', 'five'], ['x'], ['note hi', 'mul 2 3', '6'], [''], ['add 1', 'q'], ['div 7 0', 'r'], ['max 3 9', 'nine'], ['cmp 2 2', 'ok']])
    tr = m.sample_traces(b, 1.0, torch.Generator().manual_seed(0))
    sc.off()
    assert tr[0] == dict(calls=[('add 3 4', '7'), ('sub 7 2', '5')], answer='five', no_answer=False) and tr[1] == dict(calls=[], answer='x', no_answer=False) and tr[2] == dict(calls=[('note hi', ''), ('mul 2 3', '6')], answer='6', no_answer=False)
    assert tr[3] == dict(calls=[], answer='', no_answer=False) and tr[4]['calls'] == [('add 1', '?')] and tr[6] == dict(calls=[('max 3 9', '9')], answer='nine', no_answer=False)
    tr = [dict(calls=[('add 3 4', '7'), ('sub 7 2', '5')], answer='5')] * 4 + [dict(calls=[], answer='x')] * 4
    m.train()
    loss, aux = m.trace_loss(b, tr)
    loss.backward()
    assert torch.isfinite(loss) and sum(1 for p in m.parameters() if p.grad is not None and p.grad.abs().sum() > 0) > 20
    gold = m.trace_gold(tr[0])
    assert gold['texts'] == ['add 3 4', 'sub 7 2'] and gold['tape'] == ['add 3 4 = 7', 'sub 7 2 = 5'] and gold['ans'] == '5'
    try:
        m.trace_loss(b, tr[:3])
        raise SystemExit('trace_loss must refuse a wrong number of traces')
    except AssertionError:
        pass
    opt = torch.optim.AdamW(m.parameters(), lr=1e-4)
    qa = [dict(r, steps=[], accepted=[r['answer']]) for r in rs]
    res = st1.self_teach(m, qa, rs, lambda rs_: batch_of(rs_, V), opt, rounds=1, k=2, temperature=1.0, updates=2, batch_size=4, seed=0, log=lambda *a: None)
    assert len(res['rounds']) == 1
    print('ok ST1 hooks: sample_traces is generator-pure and well-formed (calls = (line, reply) pairs, notes included, answer = the final line), trace_loss backpropagates, self_teach runs')


# ---- (vii) counters ----
def test_counters():
    m = make(31)
    b = batch_of(rows(4), V)
    # a forced 17th line (a tool line on a full tape): the row ends with answer '', counted turns_over
    capcount.reset()
    sc = LineScript(m, [['add 1 1'] * 20, ['done'], ['add 1 1', 'done'], ['done']])
    with torch.no_grad():
        o = m.run(b, loops=1)
    snap = capcount.snapshot()
    assert o['turns'][0] == 17 and o['answers'][0] == '' and len(o['calls'][0]) == 16 and snap['turns_over'] == 1 and o['tape_full'] == [(0, 16)] and m.last_tape_full[0], (snap, o['turns'])
    assert snap['total'] == 1, snap
    sc.off()
    # a row that answers on its 17th line is fine: no counter
    capcount.reset()
    sc = LineScript(m, [['add 1 1'] * 16 + ['done'], ['done'], ['done'], ['done']])
    with torch.no_grad():
        o = m.run(b, loops=1)
    assert o['answers'][0] == 'done' and o['turns'][0] == 17 and capcount.snapshot()['total'] == 0
    sc.off()
    # an over-long reply (longer than LE): counted tape_entry_over, held to LE (never silently cut: the count says so)
    capcount.reset()
    sc = LineScript(m, [['add 1 1', 'done'], ['done'], ['done'], ['done']])
    with torch.no_grad():
        o = m.run(b, loops=1, oracle=lambda i, t, c: '9' * 80)
    assert capcount.snapshot()['tape_entry_over'] == 1 and capcount.snapshot()['total'] == 1
    sc.off()
    # an over-long line: a gold the writer cannot write in WCAP steps is counted writer_over and gets no target; a free-run line with no EOS within WCAP is counted unended
    capcount.reset()
    m.trace_of(dict(id='long', family='copy_word', prompt='Echo: ' + 'x' * 90, answer='x' * 90, steps=[]))
    assert capcount.snapshot()['writer_over'] == 1
    capcount.reset()
    sc = LineScript(m, [['done'], ['done'], ['add 1 1'], ['done']], unended={(2, 0)})
    with torch.no_grad():
        o = m.run(b, loops=1)
    assert capcount.snapshot()['unended'] == 1 and o['answers'][2] == '' and capcount.snapshot()['total'] == 1
    sc.off()
    # more than 32 rounds in a turn: only a forced loops:K with K > 32 (counted per live row and turn)
    capcount.reset()
    sc = LineScript(m, [['done'], ['add 1 1', 'done'], ['done'], ['done']])
    with torch.no_grad():
        m.run(b, loops=32)
        assert capcount.snapshot()['turn_rounds_over'] == 0
        sc.off()
        sc = LineScript(m, [['done'], ['add 1 1', 'done'], ['done'], ['done']])
        m.run(b, loops=33)
    assert capcount.snapshot()['turn_rounds_over'] == 4 + 1, capcount.snapshot()
    sc.off()
    # normal toy rows leave every counter at 0: a teacher-forced loss over rows with 0-2 calls (R = 4 .. 32), and free runs of a scripted talker that writes each row's gold lines
    capcount.reset()
    m.train()
    for _ in range(6):
        m.loss(batch_of(rows(8), V))
    m.eval()
    m.stop.weight.data.zero_(); m.stop.bias.data.fill_(50.0)
    rs = rows(8)
    golds = m.plain_golds(rs)
    script = [g['texts'] + [g['ans']] for g in golds]
    with torch.no_grad():
        for kw in (dict(), dict(loops=4)):
            sc = LineScript(m, script)
            o = m.run(batch_of(rs, V), **kw)
            sc.off()
            assert o['answers'] == [g['ans'] for g in golds]
        sc = LineScript(m, script)
        m.sample_traces(batch_of(rs, V), 1.0, torch.Generator().manual_seed(1))
        sc.off()
        sc = LineScript(m, script)
        m.generate(batch_of(rs, V), 'loops:32')
        sc.off()
    snap = capcount.snapshot()
    assert all(snap[k] == 0 for k in FAULTS) and snap['total'] == 0 and capcount.snapshot()['reported']['turn_cap'] == 0 and capcount.snapshot()['reported']['turn_rounds_capped'] == 0, snap
    capcount.reset()
    print('ok counters: a forced 17th tool line -> turns_over, a reply over LE -> tape_entry_over, an over-long gold -> writer_over, a line with no EOS -> unended, loops:33 -> turn_rounds_over; normal toy rows leave %s at 0 (turn_cap, turn_rounds_capped reported)' % (list(FAULTS),))


# ---- call_evals (per-turn) ----
def test_call_evals_and_names():
    m = make(4)
    rs = [dict(r, accepted=[r['answer']]) for r in rows(8)]
    b = batch_of(rs, V)
    golds = m.plain_golds(rs)
    with torch.no_grad():
        total, aux, info = m._turns(b, golds, 3, count=False, names=True)
    lr = info['last_right']
    assert len(lr) == sum(len(g['texts']) + 1 for g in golds) and {k for _, _, k, _, _ in lr} == {'call', 'ans'} and all(isinstance(x, bool) for *_, x in lr)
    out = {}
    batches = lambda sl: (batch_of(sl[s:s + 4], V) for s in range(0, len(sl), 4))
    from contextlib import nullcontext
    with torch.no_grad():
        m.call_evals(out, rs, batches, dict(device=torch.device('cpu'), amp=nullcontext))
    assert set(out['op_acc']) == {'teacher_forced', 'free_run', 'n'} and set(out['op_acc']['free_run']) == {'op', 'call', 'program', 'answer'} and out['op_acc']['n'] == 8
    assert out['call_text']['n_stop_rounds'] == 8 and set(out['at_lines']['by_turn']) == {'0', '1', '2'} and out['at_lines']['by_turn']['0']['n'] == 8
    # a scripted perfect free run scores 100% program accuracy: the same lines the golds hold
    sc = LineScript(m, [g['texts'] + [g['ans']] for g in golds])
    out2 = {}
    with torch.no_grad():
        m.call_evals(out2, rs, lambda sl: iter([batch_of(sl, V)]), dict(device=torch.device('cpu'), amp=nullcontext))
    sc.off()
    assert out2['op_acc']['free_run']['program'] == 100.0 and out2['op_acc']['free_run']['call'] == 100.0 and out2['op_acc']['free_run']['op'] == 100.0, out2['op_acc']
    print('ok call_evals per turn: teacher-forced line accuracy by turn (%s), free-run program accuracy (a scripted run of the gold lines scores 100)' % out['at_lines']['by_turn'])


def scripted_writer(m, per_call):
    """Replaces model.write_lines by a script on the CALL COUNT: the n-th call writes per_call[n][k] for the k-th Z row (a (text, ended) pair; a short list repeats its last entry). Returns the call log."""
    log = []

    def wl(Z, zm=None, rows=None, temperature=0.0, generator=None):
        spec = per_call[min(len(log), len(per_call) - 1)]
        log.append(Z.shape[0])
        pick = [spec[min(k, len(spec) - 1)] for k in range(Z.shape[0])]
        return [m.vocab.encode(t) for t, _ in pick], torch.tensor([e for _, e in pick])
    m.write_lines = wl
    return log


def test_call_rule_and_answer_gold():
    """A1: ONE rule, is_call: first word a tool name AND another token; a bare tool name is the final answer, in run, talk, generate, sample_traces, and the gold side."""
    m = make(11)
    for line, want in (('max', False), ('add', False), ('note', False), ('', False), ('add ', False), ('foo bar', False), ('max 3', True), ('note hi', True), ('add 1 2', True), ('add 1', True), (' add 1 2', False), ('maxx 3', False)):
        assert m.is_call(line) == want, (line, want)
    b = batch_of(rows(4), V)
    lines = [['add 7 5', 'max'], ['max'], ['note'], ['cmp 3 4', 'add']]
    sc = LineScript(m, lines)
    with torch.no_grad():
        o = m.run(b, loops=1)
    assert o['answers'] == ['max', 'max', 'note', 'add'] and [len(c) for c in o['calls']] == [1, 0, 0, 1] and o['turns'] == [2, 1, 1, 2] and o['no_answer'] == [False] * 4, (o['answers'], o['calls'])
    sc.off()
    # generate (zero_state: talk on the final Z) and talk apply the same rule
    scripted_writer(m, [[('max', True)]])
    with torch.no_grad():
        assert m.generate(b, lesion='zero_state')[0] == 'max'
        st = m.state_of(m.run(b, loops=1))
    scripted_writer(m, [[('max 3', True)]])
    with torch.no_grad():
        assert m.talk(st, b) == [''] * 4
    # gold side: a gold answer that would run as a call has no target and is counted answer_is_call; a bare tool name keeps its target
    capcount.reset()
    g1 = m.make_gold(['add 1 2'], ['add 1 2 = 3'], 'max')
    assert g1['ans_ids'] is not None and capcount.snapshot().get('answer_is_call', 0) == 0
    g2 = m.make_gold(['add 1 2'], ['add 1 2 = 3'], 'max 3')
    assert g2['ans_ids'] is None and capcount.HITS['answer_is_call'] == 1 and m.trace_stats['answer_is_call'] == 1
    m.train()
    rs = rows(2)
    golds = [g2, m.make_gold([], [], 'add 4 4')]
    total, aux, info = m._turns(batch_of(rs, V), golds, 2, count=False)
    assert torch.isfinite(total) and {(i, j) for i, j, *_ in info['last_right']} == {(0, 0)}, info['last_right']      # only row 0's call has a target; no answer target for either row
    assert capcount.HITS['answer_is_call'] == 2
    capcount.reset()
    print('ok call rule: a bare tool name / empty is the answer in run, talk, generate; a tool name + a token is a call; a gold answer that would be a call gets no target and counts answer_is_call')


def test_no_answer_traces():
    """A2: a trace whose run ended by unended / turns_over has no answer target (not a blank EOS) and is counted."""
    m = make(12)
    b = batch_of(rows(3), V)
    LineScript(m, [['add 1 1', 'x'], ['y'], ['add 2 2'] * 20], unended={(0, 1), (1, 0)})
    gen = torch.Generator().manual_seed(0)
    tr = m.sample_traces(b, 0.0, gen)
    assert [t['no_answer'] for t in tr] == [True, True, True] and [t['answer'] for t in tr] == ['', '', ''], tr
    assert len(tr[2]['calls']) == 16
    m.trace_stats['no_answer'] = 0
    gl = [m.trace_gold(t) for t in tr]
    assert all(g['ans_ids'] is None for g in gl) and m.trace_stats['no_answer'] == 3
    m.train()
    total, aux = m.trace_loss(b, tr)
    assert torch.isfinite(total) and aux['line_acc_ans'] == 0.0 and aux['ans'] == 0.0      # no answer pair was trained
    total.backward()
    # a normal trace keeps its answer target
    LineScript(m, [['add 1 1', '2']] * 3)
    ok = m.sample_traces(b, 0.0, gen)
    assert [t['no_answer'] for t in ok] == [False] * 3 and all(m.trace_gold(t)['ans_ids'] == V.encode('2') for t in ok)
    print('ok ST1 traces ended by unended / turns_over: no_answer flag, gold answer target None (no EOS target), counted in trace_stats[no_answer] (%d), loss backpropagates' % m.trace_stats['no_answer'])


def test_answer_unended_and_tape():
    """A5 talk counts answer_unended; A6 tape must be 16."""
    m = make(13)
    b = batch_of(rows(3), V)
    scripted_writer(m, [[('add 1 1', True)]])
    st = m.state_of(m.run(b, loops=1))
    scripted_writer(m, [[('7', True), ('x', False), ('add 1 2', True)]])
    before = m.free_stats['answer_unended']
    with torch.no_grad():
        out = m.talk(st, b)
    assert out == ['7', '', ''] and m.free_stats['answer_unended'] == before + 1, (out, m.free_stats)
    assert make(14).tape == 16
    orig = B3G2.__init__

    def bad(self, *a, **k):
        orig(self, *a, **k)
        self.tape = 8
    B3G2.__init__ = bad
    try:
        make(14)
        raise SystemExit('a tape of 8 must be refused')
    except AssertionError as e:
        assert 'at most 16 tool turns' in str(e)
    finally:
        B3G2.__init__ = orig
    print('ok talk counts answer_unended (as B3G2.talk); the answer rule gives \'\' for a call or an unended line; B3AT asserts tape == 16')


def dev_dir(rs, tag='d'):
    import json, os, tempfile
    from custom_io.data import DEV_SPLITS
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, 'dev'))
    for sp in list(DEV_SPLITS) + ['in_dist']:
        with open(os.path.join(d, 'dev', f'{sp}.jsonl'), 'w') as f:
            for r in rs:
                f.write(json.dumps(dict(r, id=r['id'] + sp, accepted=[r['answer']], level=2, variant='v', stage=9)) + '\n')
    return d


def test_per_turn_h1_and_past_trained():
    """A4: the H1 block is per (row, turn) against TCAP, plus a whole-question block; A8: turn_rounds_past_trained; A7: call_evals reports each row's real R_i."""
    from contextlib import nullcontext
    m = make(15)
    rs = [r for r in rows(8) if r['family'] != 'copy_word'][:6]
    ctx = dict(data=dev_dir(rs), big=None, device=torch.device('cpu'), batch_size=4, amp=nullcontext)
    saved = (M.TCAP, M.TOTAL_CAP)
    M.TCAP, M.TOTAL_CAP = 3, 4
    try:
        m.stop.weight.data.zero_(); m.stop.bias.data.fill_(-50.0)               # the stop never fires: every turn runs TCAP = 3 rounds
        calls = [0]
        real_q = m.question

        def q(batch):
            calls[0] = 0
            return real_q(batch)
        m.question = q

        def wl(Z, zm=None, rows=None, temperature=0.0, generator=None):
            t, calls[0] = ('add 1 2' if calls[0] == 0 else '3'), calls[0] + 1
            return [m.vocab.encode(t)] * Z.shape[0], torch.ones(Z.shape[0], dtype=torch.bool)
        m.write_lines = wl
        h1 = m.h1_evals(ctx)
        assert h1['per'] == 'turn' and h1['cap'] == 3 and h1['pooled5']['mean'] == 3 and h1['pooled5']['at_cap'] == 100.0, h1['pooled5']
        n_rows = h1['pooled5']['n'] // 2                                        # two turns per row
        q_ = h1['whole_question']
        assert q_['pooled5']['mean'] == 6 and q_['pooled5']['n'] == n_rows and 'at_cap' not in q_['pooled5'] and q_['by_family'], q_['pooled5']
        assert all(v == [3, 3] for v in h1['rows']['big_in_dist'].values())
        at = m.at_evals(ctx)
        pt = at['turn_rounds_past_trained']
        assert pt['pairs'] == pt['of'] == 2 * at['n'] and pt['share'] == 100.0, pt            # 2 lines -> budget min(3, 4 // 2) = 2 < 3 rounds
        M.TOTAL_CAP = 96
        pt = m.at_evals(ctx)['turn_rounds_past_trained']
        assert pt['pairs'] == 0 and pt['of'] == 2 * at['n'], pt
    finally:
        M.TCAP, M.TOTAL_CAP = saved
    assert B3AT_past([[30, 5, 24, 25], [32]]) == (2, 5)
    # A7: the rows' real R_i, not TCAP
    m2 = make(16)
    rs8 = [dict(r, accepted=[r['answer']]) for r in rows(8)]
    real = m2.plain_golds
    m2.plain_golds = lambda rr: [m2.make_gold(['add 1 2'] * 5, ['add 1 2 = 3'] * 5, '3') if k % 2 else g for k, g in enumerate(real(rr))]
    out = {}
    with torch.no_grad():
        m2.call_evals(out, rs8, lambda sl: iter([batch_of(sl, V)]), dict(device=torch.device('cpu'), amp=nullcontext))
    assert out['at_lines']['rounds'] == {'16': 4, '32': 4} and out['at_lines']['tcap'] == 32, out['at_lines']
    print('ok per-turn H1 block (3 rounds per turn = 100%% at the toy cap; whole question 6 per row, no cap), turn_rounds_past_trained scripted (%s), call_evals reports real R_i %s' % (pt, out['at_lines']['rounds']))


def test_by_gold_calls():
    """at_evals' by_gold_calls: rows split by their gold call count (0 / 1-2 / 3+), n sums to the rows, accuracy equals an independent count of the same free run."""
    import json
    from contextlib import nullcontext
    from custom_io.data import DEV_SPLITS, collate, Dataset, to_device
    from custom_io.evalx import _dev_rows, is_hit
    m = make(21)
    z = lambda i: dict(id=f'g{i}', family='copy_word', prompt=f'Echo: sune{i} Give only the answer.', answer=f'sune{i}', steps=[])
    one = lambda i, a: dict(id=f'g{i}', family='chain_ops', prompt=f'Tom has {a} apples and buys 20 more. How many apples now?', answer=str(a + 20), steps=[f'{a} + 20 = {a + 20}'])
    three = lambda i, a: dict(id=f'g{i}', family='chain_ops', prompt=f'Tom has {a} apples and buys 20 more. Then he buys 5 more. Then he loses 3. How many?', answer=str(a + 22),
                              steps=[f'{a} + 20 = {a + 20}', f'{a + 20} + 5 = {a + 25}', f'{a + 25} - 3 = {a + 22}'])
    rs = [z(0), one(1, 10), three(2, 10), z(3), one(4, 11), three(5, 12)]
    assert [m.gold_calls(r) for r in rs] == [0, 1, 3, 0, 1, 3]
    ctx = dict(data=dev_dir(rs), big=None, device=torch.device('cpu'), batch_size=4, amp=nullcontext)
    at = m.at_evals(ctx)
    g = at['by_gold_calls']
    assert set(g) == {'0', '1-2', '3+'} and sum(v['n'] for v in g.values()) == at['n'] == 6 * len(DEV_SPLITS) and all(v['n'] > 0 for v in g.values()), g
    seen, dev = set(), []
    for sp in DEV_SPLITS:
        for r in _dev_rows(ctx['data'], sp, None):
            if r['id'] not in seen:
                seen.add(r['id']); dev.append(r)
    hit = {'0': 0, '1-2': 0, '3+': 0}
    for s0 in range(0, len(dev), 4):
        ch = dev[s0:s0 + 4]
        with torch.no_grad():
            o = m.run(to_device(collate([Dataset(ch, m.vocab, strict=False)[i] for i in range(len(ch))]), ctx['device']))
        for r, a in zip(ch, o['answers']):
            n = m.gold_calls(r)
            hit['0' if n == 0 else '1-2' if n <= 2 else '3+'] += is_hit(a, r)
    for k, v in g.items():
        assert abs(v['accuracy'] - 100 * hit[k] / v['n']) < 1e-9, (k, v, hit)
    print('ok by_gold_calls: ' + json.dumps(g))


def B3AT_past(tr):
    return M.B3AT.past_trained(tr)


if __name__ == '__main__':
    torch.set_num_threads(2)
    for f in (test_paths_and_lesions, test_scripted_free_run, test_replies_only_through_read_texts, test_talker_sees_only_thoughts, test_teacher_forcing_caps_and_keep,
              test_teacher_forced_thinker_equals_free_run, test_carry_draw, test_carry_stop, test_grads, test_st1_hooks, test_counters, test_call_evals_and_names, test_call_rule_and_answer_gold, test_no_answer_traces, test_answer_unended_and_tape, test_per_turn_h1_and_past_trained, test_by_gold_calls):
        f()
    print('ALL OK')
