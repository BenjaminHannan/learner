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
        assert capcount.snapshot()['turn_cap'] == (0 if want is None else 8) and capcount.snapshot()['total'] == 0, capcount.snapshot()
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
        assert len(spy.think) == 32 + 5 * 16 and capcount.snapshot()['turn_rounds_capped'] == 1 and capcount.snapshot()['total'] == 0, (len(spy.think), capcount.snapshot())
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
        assert capcount.snapshot()['turn_rounds_capped'] == 0 and aux['stop_w'] == 0.0 and aux['stop_pairs'] == 0.0 and torch.isfinite(loss) and aux['rounds'] == 4 * 3.5
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
    orig = M.B3AT.carry_draw
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
        M.B3AT.carry_draw = orig
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
    assert len(tr) == 8 and all(set(t) == {'calls', 'answer'} and isinstance(t['answer'], str) and isinstance(t['calls'], list) for t in tr)
    assert m.sample_traces(b, 1.0, torch.Generator().manual_seed(0)) == tr                     # drawn only from the generator
    # well-formed with a scripted talker: every tool line is a (line, reply) pair, notes included, the answer is the final line
    sc = LineScript(m, [['add 3 4', 'sub 7 2', 'five'], ['x'], ['note hi', 'mul 2 3', '6'], [''], ['add 1', 'q'], ['div 7 0', 'r'], ['max 3 9', 'nine'], ['cmp 2 2', 'ok']])
    tr = m.sample_traces(b, 1.0, torch.Generator().manual_seed(0))
    sc.off()
    assert tr[0] == dict(calls=[('add 3 4', '7'), ('sub 7 2', '5')], answer='five') and tr[1] == dict(calls=[], answer='x') and tr[2] == dict(calls=[('note hi', ''), ('mul 2 3', '6')], answer='6')
    assert tr[3] == dict(calls=[], answer='') and tr[4]['calls'] == [('add 1', '?')] and tr[6] == dict(calls=[('max 3 9', '9')], answer='nine')
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
    assert all(snap[k] == 0 for k in FAULTS) and snap['total'] == 0 and snap['turn_cap'] == 0 and snap['turn_rounds_capped'] == 0, snap
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


if __name__ == '__main__':
    torch.set_num_threads(2)
    for f in (test_paths_and_lesions, test_scripted_free_run, test_replies_only_through_read_texts, test_talker_sees_only_thoughts, test_teacher_forcing_caps_and_keep,
              test_teacher_forced_thinker_equals_free_run, test_carry_draw, test_grads, test_st1_hooks, test_counters, test_call_evals_and_names):
        f()
    print('ALL OK')
