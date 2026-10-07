"""T1 (roadmap 2c; marks /mnt/project-files/architecture/MARKS-D0-T1-2026-10-07.md, PASS-MARKS.md addendum 17): B2 with the calculator
OUTSIDE the model. The one change: the thinker no longer gets exact value codes or executor result slots. At each round t = 1..7 the talker
writes a calculator call as text, `<op> <a> <b>` (e.g. `add 12 5`); a plain Python function (calc(), no learned part) parses that text and
returns a string (`17`, or `?` for a call it cannot run); the entry `add 12 5 = 17` is appended to the context, read by the same reader as
ordinary characters, and seen by the thinker from round t + 1 on. After the last round the talker writes the answer text.

What stays exactly as in B2 (Ledger copy=True, same S config, same init order, so every shared weight starts as in B2 at the same seed): the
reader (char table, positions, place-from-the-right code, two conv blocks), the 8 + 9 token controller, its blocks and loop count, the WORD talker,
the GEN pointer-generator (ln_t, readout tied to the char table, q_cp / k_cp / g_cp), the op head, the mode head and the word pointer.
Removed (B2 parts that only fed or read the executor): vcode, res_from_z, op_emb, the four slot pointers q_a / q_b / q_ans / k_slot and ln_k,
and the 4 constant and 7 result slots. Kept and disclosed: 16 workspace slots for the PROMPT numbers only, each = mean of the reader output
over the number's digits + ordinal + slot type (B2's slot without the value code; the regex only says where a number is).
New: W_a, W_b (d -> d) and tape_emb (7 x d, the entry's place in the transcript).

Call writer (part of the talker): op = op head on control token 0 (B2's head; NOOP = no call). Operand k in {a, b} is written in 11 cells,
units first (as B2's GEN registers are): cell j's state is W_k(ln_z(control 0)) + place row j of the reader's place table, and it goes through
B2's own pointer-generator (vocabulary readout or copy attention over the context chars: prompt + every entry written so far); decode =
argmax per cell up to the first EOS, reversed. So every digit of a call is written by a learned writer, never by str() of a value.
Answer: B2's NUM mode (str(value of a slot)) is gone; those rows are GEN rows and the 9 registers write the answer with the same
pointer-generator, copying from the prompt and the entries. WORD is unchanged.
Tape: entry k is read by the reader as its own string (positions from 0, at most LE = 40 chars), + tape_emb[k]; the thinker cross-attends to
[prompt-number slots; entries written so far; prompt]. Teacher forcing (training): the entries are the gold calls with their results (the same
text calc() returns for them, tested), revealed one round at a time, and the call writer is trained by -log p of the gold operand strings
(either order for ADD MUL MIN MAX, as B2's pointer loss).
Lesions: noexec (calc returns `?` for every call: tool off), opswap (calc swaps add and sub), nocopy, nowordc, shuffle / zero state, loops:K,
donor; ctl27 (test only). extra_evals: call accuracy, tool-off on the noexec program set, chain-5 lesions, opswap swap_match by replaying the
model's own calls, write_copy (D0 writing: every calc result replaced by a random 1-9 digit string; exact copy into the next call / the answer).
Size (vocab 108, S cfg): 3,277,393 (B2 3,302,481; -0.76%).

span_copy=True (T1S; MARKS-D0-T1-2026-10-07.md Amendment 3, PASS-MARKS.md addendum 22; default False = exactly T1): the one link fix after the T1
screen (write_copy failed at 4+ digits: each cell copied by its place row, and rows 4+ were almost never trained). Each writer can now also copy a
whole number already in the context (a prompt number or any number in an entry written so far) as a span:
- a pointer (q_s, k_s; fp32, B2's ptr) picks one char of the context: the number's units digit (T1's writers write units first, so the span
  starts at the units digit and the copy runs toward the number's front, the writers' own order);
- the copy then advances by itself one char at a time (to the next char on the left, in the same string) and a learned stop head ends it
  (stop_s on the char about to be copied, read from the char table (detached, parameter-free layer norm), one logit for prompt text and
  one for entries: in the prompt a '-' never belongs to a number (the prompt-number regex is unsigned), in an entry the calculator writes
  signs). No code gives a length; the only bounds are the end of the string (there is nothing to copy there) and a ceiling of SPAN_MAX = LE
  chars;
- operand k: gate g_s(W_k(z)) chooses span (>= 0.5) or T1's 11 cells (kept for numbers the writer composes itself, e.g. a constant that is
  not in the text); the answer: mode 0 (B2's NUM slot, unused by T1) = copy the span the answer pointer q_s(ln_z(control 1)) picks, over the
  CURRENT prompt and the state's tape, as GEN does. A span answer has no 8-char register limit.
Training (additive: T1's losses are unchanged, so cells and GEN still learn every target): gate BCE (span iff the gold string is a number token
of the visible context), pointer -log sum p over every visible occurrence's units digit (either order for ADD MUL MIN MAX, as lcall), the same
for the answer on NUM rows whose answer is a number token of the context (their mode label becomes 0; they keep T1's GEN targets), and the
stop head's BCE on every number token of the context (go on inside the token, stop at the char left of it). Number tokens for these labels:
the prompt-number regex (digit runs, unsigned; the regex Amendment 2 already discloses) on the prompt and signed digit runs on the
calculator's entries; they label training targets only and never reach the model at test time. New modules are created last (every T1 weight starts as in T1 at the same seed).
Size (vocab 108, S cfg): 3,277,393 + 33,667 = 3,311,060 (+2.2% vs 3.24M)."""
import math, re
import numpy as np
import torch
import torch.nn as nn
from custom_io.data import EOS, PAD, UNK, word_spans
from custom_io.models import progparse as pp
from custom_io.models.ledger import Ledger, COMM, GEN_MAX, N_CTRL, N_NUM, N_RES, OPS, R0, W_MAX, BIG

CELLS = 11          # operand cells: up to 9 digits and a sign, then EOS
LE = 40             # chars per tape entry
NAMES = [o.lower() for o in OPS]
INT_RE = re.compile(r'-?\d+')
ENT_NUM = re.compile(r'-?\d+')       # number tokens of an entry (the calculator's own text): span-copy training labels only
SPAN_MAX = LE                         # span copy ceiling: the longest string the tape holds (the stop is learned)


def calc(op, a, b, swap=False):
    """The outside calculator: plain Python over the call TEXT. op a name ('add'), a / b operand strings -> result string, '?' if it cannot run."""
    if op not in NAMES[1:] or not INT_RE.fullmatch(a or '') or not INT_RE.fullmatch(b or ''):
        return '?'
    if swap and op in ('add', 'sub'):
        op = 'sub' if op == 'add' else 'add'
    x, y = int(a), int(b)
    if abs(x) >= BIG or abs(y) >= BIG:
        return '?'
    v = pp.ex(op.upper(), x, y)
    return '?' if v is None or abs(v) >= BIG else str(v)


def entry(op, a, b, r):
    return f'{op} {a} {b} = {r}'[:LE]


def rand_digits(rng, lo=1, hi=9):
    L = rng.randint(lo, hi)
    return str(rng.randrange(10 ** (L - 1) if L > 1 else 0, 10 ** L))


class Tool(Ledger):
    LESIONS = ['shuffle_state', 'zero_state', 'noexec', 'opswap', 'nocopy', 'nowordc']

    def __init__(self, vocab, d=256, n_heads=4, reader_layers=2, blocks=2, n_loops=8, mlp=4.8, dk=64, w_noop=0.1, wpos=True, span_copy=False, **kw):
        assert not kw.get('eg_embed') and not kw.get('eg_teach') and not kw.get('span') and not kw.get('round_readout'), 'T1 is B2 + one change'
        kw.pop('copy', None)
        super().__init__(vocab, d=d, n_heads=n_heads, reader_layers=reader_layers, blocks=blocks, n_loops=n_loops, mlp=mlp, dk=dk,
                         w_noop=w_noop, wpos=wpos, copy=True, **kw)
        self.LESIONS = list(Tool.LESIONS)
        for name in ('vcode', 'res_from_z', 'op_emb', 'q_a', 'q_b', 'q_ans', 'k_slot', 'ln_k'):
            delattr(self, name)
        self.W_a, self.W_b, self.tape_emb = nn.Linear(d, d), nn.Linear(d, d), nn.Embedding(N_RES, d)      # created last
        for m in (self.W_a, self.W_b, self.tape_emb):
            nn.init.normal_(m.weight, std=0.02)
            if getattr(m, 'bias', None) is not None:
                nn.init.zeros_(m.bias)
        self._gold, self._full_tape = {}, False
        self.span_copy = bool(span_copy)
        if self.span_copy:      # T1S: created after every T1 module, so every T1 weight starts identical at the same seed
            self.q_s, self.k_s, self.g_s, self.stop_s = nn.Linear(d, dk), nn.Linear(d, dk), nn.Linear(d, 1), nn.Linear(d, 2)
            for m in (self.q_s, self.k_s, self.g_s, self.stop_s):
                nn.init.normal_(m.weight, std=0.02)
                nn.init.zeros_(m.bias)

    # ---- the tape ----
    def read_texts(self, texts, dev, le=LE):
        """Each string read by the reader on its own -> X [n, le, d], ids [n, le], mask [n, le] (an empty string: all masked, zeros). Only the
        non-empty strings go through the reader (the reader's output is zero wherever the mask is, so this is the same result, faster)."""
        ids = np.full((len(texts), le), PAD, np.int64)
        for i, s in enumerate(texts):
            e = self.vocab.encode(s[:le])
            ids[i, :len(e)] = e
        ids = torch.from_numpy(ids).to(dev)
        mask = ids != PAD
        full = [i for i, s in enumerate(texts) if s]
        X = torch.zeros(len(texts), le, self.d, device=dev)
        if full:
            ix = torch.tensor(full, device=dev)
            Xf, _ = self.reader({'prompt_ids': ids[ix], 'prompt_mask': mask[ix], 'rows': [{'prompt': texts[i][:le]} for i in full]})
            X = X.to(Xf.dtype).index_copy(0, ix, Xf)
        return X, ids, mask

    def tape_of(self, texts, dev, le=None):
        """texts [B][K] -> (X [B, K*le, d] with tape_emb added, ids, mask); le = the longest entry (teacher forcing) or LE (free run). The layout
        only decides where padding sits: the thinker and the copy attention see an entry's chars through the reader's positions and tape_emb[k]."""
        B, K = len(texts), len(texts[0])
        le = le or max(1, max(len(x) for row in texts for x in row))
        X, ids, mask = self.read_texts([x for row in texts for x in row], dev, le)
        X = (X.view(B, K, le, -1) + self.tape_emb.weight[None, :K, None].to(X.dtype)) * mask.view(B, K, le, 1)
        return X.flatten(1, 2), ids.view(B, -1), mask.view(B, -1), le

    def cells(self, z):
        """[B,d] -> [B, 2*CELLS, d]: operand a's cells then b's, units first (cell j = W_k(z) + place row j)."""
        P = self.reader.place.weight[:CELLS]
        return torch.cat([self.W_a(z)[:, None] + P, self.W_b(z)[:, None] + P], 1)

    def decode_cells(self, p):
        ids = p.argmax(-1).tolist()
        return [(self.vocab.decode(r[:CELLS])[::-1], self.vocab.decode(r[CELLS:])[::-1]) for r in ids]

    # ---- span copy (T1S) ----
    def stop_logit(self, c, tape):
        """c [n] char ids, tape [n] bool (the char is in an entry, not the prompt) -> [n] stop logits (>= 0: the copy ends before this char)."""
        import torch.nn.functional as F
        with torch.autocast(c.device.type, enabled=False):
            e = self.reader.tok.weight.detach().float()[c]
            lg = self.stop_s(F.layer_norm(e, e.shape[-1:]))
        return lg.gather(-1, tape.long()[..., None])[..., 0]

    @staticmethod
    def seg_of(T, le, n, dev):
        """[n]: the first position of the string each context position is in (0 for the prompt [0, T), T + k*le for entry k)."""
        pos = torch.arange(n, device=dev)
        return torch.where(pos < T, torch.zeros_like(pos), T + (pos - T).div(le, rounding_mode='floor') * le)

    def span_read(self, logits, ids, mask, T, le):
        """Greedy span copy -> texts in reading order. logits [B, N]: the pointer over the context (prompt [0, T), then entries of le chars);
        the copy starts at its argmax and steps one char left at a time while the char is in the same string, visible, and the stop head goes on."""
        B, N = ids.shape
        p0 = logits.argmax(-1)
        lo = self.seg_of(T, le, N, ids.device)[p0]
        out, alive = [ids.gather(1, p0[:, None])[:, 0]], torch.ones(B, dtype=torch.bool, device=ids.device)
        for i in range(1, SPAN_MAX):
            p = p0 - i
            pc = p.clamp(min=0)
            c = ids.gather(1, pc[:, None])[:, 0]
            alive = alive & (p >= lo) & mask.gather(1, pc[:, None])[:, 0] & (self.stop_logit(c, pc >= T) < 0)
            if not alive.any():
                break
            out.append(torch.where(alive, c, torch.full_like(c, PAD)))
        return [self.vocab.decode([x for x in r if x != PAD])[::-1] for r in torch.stack(out, 1).tolist()]

    def written(self, st):
        """One call round's writer output -> [(a, b)] operand strings: T1's cells, or (T1S) the span where that side's gate chose it."""
        cells = self.decode_cells(st[1])
        if len(st) < 3:
            return cells
        sp = st[2]
        sa, sb = (self.span_read(sp[k], sp['ids'], sp['m'], sp['T'], sp['le']) for k in ('la', 'lb'))
        ga, gb = (sp['ga'] >= 0).tolist(), (sp['gb'] >= 0).tolist()
        return [(sa[i] if ga[i] else a, sb[i] if gb[i] else b) for i, (a, b) in enumerate(cells)]

    def num_tokens(self, prompt, tape, T=None):
        """Span-copy labels -> ([(string index, start, end, text)] number tokens, [(text, regex, is entry)] strings): string 0 = the prompt
        (`\\d+`, a token kept only if it ends within T), string k + 1 = entry k (`-?\\d+`)."""
        strs = [(prompt, pp.NUM_RE, False)] + [(x, ENT_NUM, True) for x in tape]
        toks = [(j, m.start(), m.end(), m.group()) for j, (x, rx, _) in enumerate(strs) for m in rx.finditer(x) if j or T is None or m.end() <= T]
        return toks, strs

    def span_gold(self, rows, T, le, K):
        """-> Ma, Mb [B, N_RES, N] (units-digit positions of every visible occurrence of each call's gold operand strings; entry k is visible
        from call k + 1), Mn [B, N] (the answer's, on mode-0 rows), and stop samples (char ids, in an entry, label: 0 go on / 1 stop)."""
        B, N = len(rows), T + K * le
        Ma, Mb, Mn = np.zeros((B, N_RES, N), bool), np.zeros((B, N_RES, N), bool), np.zeros((B, N), bool)
        cs, ts, ys, enc = [], [], [], self.vocab.stoi
        for i, r in enumerate(rows):
            ops, opd, tape, md, _ = self.row_gold(r)
            toks, strs = self.num_tokens(r['prompt'], tape[:min(len(ops), K)], T)
            pos = lambda j, e: e - 1 if j == 0 else T + (j - 1) * le + e - 1
            for j, a, e, _ in toks:
                x, _, ent = strs[j]
                for q in range(a, e - 1):
                    cs.append(enc.get(x[q], UNK)); ts.append(ent); ys.append(0.0)
                if a > 0:
                    cs.append(enc.get(x[a - 1], UNK)); ts.append(ent); ys.append(1.0)

            def mark(M, want, upto):
                for j, a, e, x in toks:
                    if x == want and j <= upto:
                        M[pos(j, e)] = True
            for k, (sa, sb) in enumerate(opd):
                mark(Ma[i, k], sa, k)
                mark(Mb[i, k], sb, k)
            if md == 0:
                mark(Mn[i], r['answer'], len(ops))
        return Ma, Mb, Mn, (cs, ts, ys)

    def state_of(self, o):
        return (o['R'],) + o['tape'] + (o['lmode'], o['lword']) + ((o['qn'],) if self.span_copy else ())

    # ---- reasoner ----
    def think(self, Z, kvs, kvx, mask, t):
        """One controller iteration through the core blocks (H1 overrides this to checkpoint its extra training rounds)."""
        for b, kx, ks in zip(self.core, kvx, kvs):
            Z = b(Z, ks, kx, mask)
        return Z

    def run(self, batch, loops=None, gold=None, lesion=None, rounds=False, oracle=None, each=None):
        """gold (training): teacher-forced ops and tape. oracle: per-row function (row index, round, call) -> result string (write_copy eval).
        each (H1): called after every iteration t as each(t, state dict) once that iteration's call is written; a True return ends the loop.
        -> dict(R, lmode, lword, wvalid, steps [(op logits, cell probs [B,2*CELLS,V])], X / xm / ids (context: prompt then tape), tape (X, ids, mask),
        calls [B][(t, op, a, b, result)] (free run))."""
        assert not rounds
        X, xm = self.read(batch, talker=True)
        ns, ne, nv, ws, we = self.tokenize(batch)
        B, T, dev = X.shape[0], X.shape[1], X.device
        t_ix = torch.arange(T, device=dev)
        inn = (t_ix >= ns[..., None]) & (t_ix < ne[..., None])
        cnt = inn.sum(-1)
        valid = cnt > 0
        pool = torch.bmm(inn.to(X.dtype), X) / cnt.clamp(min=1)[..., None]
        S0 = (pool + self.ordinal.weight + self.stype.weight[0]) * valid[..., None]
        Kw, wvalid = self.word_keys(ws, we), we > ws
        if lesion != 'nowordc':
            Kw = Kw + self.word_content(X, ws, we)
        kvx = [b.kv_of(X + self.src.weight[1]) for b in self.core]
        kvs0 = [b.kv_of(S0 + self.src.weight[0]) for b in self.core]
        if gold is not None and not self._full_tape:    # teacher forcing: only the entries the longest gold program writes, each as long as the longest
            K = max(1, int((gold['op'] > 0).sum(1).max()))
            texts, le = [row[:K] for row in gold['tape']], None
        elif gold is not None:                          # the same in the free-run layout (tests only)
            K, texts, le = N_RES, [list(row) for row in gold['tape']], LE
        else:
            K, texts, le = N_RES, [[''] * N_RES for _ in range(B)], LE
        Xt, idt, mt, le = self.tape_of(texts, dev, le)
        ent = torch.arange(K * le, device=dev) // le                     # entry index of every tape position
        kvt = [b.kv_of(Xt + self.src.weight[1]) for b in self.core]
        Z = torch.cat([self.ctrl.weight, self.reader.place.weight[:9]]).expand(B, -1, -1)
        steps, calls, n = [], [[] for _ in range(B)], self.n_loops if loops is None else loops
        shown = torch.zeros(B, N_RES, dtype=torch.bool, device=dev)     # entries the thinker may see now
        kvs_of = None
        for t in range(n):
            ts = min(t, self.n_loops - 1)
            vis = mt & shown[:, :K].gather(1, ent.expand(B, -1))
            if kvs_of is not kvt:                                       # rebuilt only when the tape changed (same values either way)
                kvs, kvs_of = [torch.cat([a, c], 3) for a, c in zip(kvs0, kvt)], kvt
            mask = torch.cat([valid, vis, xm], 1)
            Z = self.think(Z + self.step_emb.weight[ts], kvs, kvx, mask, t)
            if lesion == 'ctl27':
                Z = torch.cat([Z[:, :2], torch.zeros_like(Z[:, 2:N_CTRL]), Z[:, N_CTRL:]], 1)
            if 1 <= t <= N_RES:
                z = self.ln_z(Z[:, 0])
                lop = self.op_head(z)
                p, _ = self.gen_copy(self.cells(z), torch.cat([X, Xt], 1), torch.cat([xm, vis], 1), torch.cat([batch['prompt_ids'], idt], 1),
                                     lesion == 'nocopy')
                st = (lop, p)
                if self.span_copy:
                    mc = torch.cat([xm, vis], 1)
                    ks, wa, wb = self.k_s(torch.cat([X, Xt], 1)), self.W_a(z), self.W_b(z)
                    st = st + (dict(la=self.ptr(self.q_s(wa), ks, mc), lb=self.ptr(self.q_s(wb), ks, mc), ga=self.g_s(wa)[:, 0].float(),
                                    gb=self.g_s(wb)[:, 0].float(), ids=torch.cat([batch['prompt_ids'], idt], 1), m=mc, T=T, le=le),)
                steps.append(st)
                k = t - 1
                if gold is not None:
                    shown[:, k] = gold['op'][:, k] > 0
                else:
                    op = lop.argmax(-1).tolist()
                    new = list(texts[i][k] for i in range(B))
                    for i, (sa, sb) in enumerate(self.written(st)):
                        if op[i] == 0:
                            continue
                        if oracle is not None:
                            r = oracle(i, t, (NAMES[op[i]], sa, sb))
                        else:
                            r = '?' if lesion == 'noexec' else calc(NAMES[op[i]], sa, sb, swap=lesion == 'opswap')
                        new[i] = entry(NAMES[op[i]], sa, sb, r)
                        calls[i].append((t, NAMES[op[i]], sa, sb, r))
                    if any(new):
                        for i in range(B):
                            texts[i][k] = new[i]
                        Xk, ik, mk = self.read_texts(new, dev, le)
                        Xk = (Xk + self.tape_emb.weight[k].to(Xk.dtype)) * mk[..., None]
                        sl = slice(k * le, (k + 1) * le)
                        Xt, idt, mt = Xt.clone(), idt.clone(), mt.clone()
                        Xt[:, sl], idt[:, sl], mt[:, sl] = Xk.to(Xt.dtype), ik, mk
                        kvt = [b.kv_of(Xt + self.src.weight[1]) for b in self.core]
                        shown[:, k] = torch.tensor([o > 0 for o in op], device=dev)
            if each is not None and each(t, dict(Z=Z, X=X, xm=xm, Xt=Xt, idt=idt, mt=mt, shown=shown, ent=ent, K=K, Kw=Kw, wvalid=wvalid)):
                break
        vis = mt & shown[:, :K].gather(1, ent.expand(B, -1))
        zf = self.ln_z(Z[:, 1])
        out = dict(R=Z[:, N_CTRL:], lmode=self.mode_head(zf), lword=self.ptr(self.q_word(zf), Kw, wvalid), wvalid=wvalid, steps=steps,
                   X=torch.cat([X, Xt], 1), xm=torch.cat([xm, vis], 1), ids=torch.cat([batch['prompt_ids'], idt], 1),
                   tape=(Xt, idt, vis), calls=calls, le=le, K=K)
        if self.span_copy:
            out['qn'] = self.q_s(zf)
        return out

    def state(self, batch, loops=None, lesion=None, oracle=None):
        return self.state_of(self.run(batch, loops, lesion=lesion, oracle=oracle))

    # ---- talker ----
    def talk(self, state, batch, lesion=None, return_modes=False):
        """GEN copies from the CURRENT rows' prompt and the state's tape (the tape is the reasoner's own work, so a donor's tape comes with its
        state); WORD copies word k of the CURRENT row. Mode NUM is not used by T1 (decoded as GEN); T1S: mode 0 = the span the answer pointer picks,
        over the same context as GEN (the state's tape is the free-run layout: 7 entries of LE chars)."""
        R, Xt, idt, vis, lmode, lword = state[:6]
        X, xm = self.read(batch, talker=True)
        Xc, mc, idc = torch.cat([X, Xt.to(X.dtype)], 1), torch.cat([xm, vis.bool()], 1), torch.cat([batch['prompt_ids'], idt.long()], 1)
        p, _ = self.gen_copy(R, Xc, mc, idc, lesion == 'nocopy')
        span = None
        if self.span_copy:
            assert Xt.shape[1] % N_RES == 0
            span = self.span_read(self.ptr(state[6], self.k_s(Xc), mc), idc, mc, X.shape[1], Xt.shape[1] // N_RES)
        out, modes = self.answers(p.argmax(-1).tolist(), lmode.argmax(-1).tolist(), lword.argmax(-1).tolist(), batch['rows'], span=span)
        return (out, modes) if return_modes else out

    def answers(self, gen_ids, mode, w, rows, spans=None, span=None):
        """Greedy readout -> (answer texts, modes): WORD (mode 1) copies word w of the row's prompt, T1S mode 0 is the span copy `span[i]`,
        anything else is the GEN text."""
        out, modes = [], []
        for i, row in enumerate(rows):
            sp = spans[i] if spans is not None else word_spans(row['prompt'])[:W_MAX]
            if span is not None and mode[i] == 0:
                out.append(span[i]); modes.append(0)
            elif mode[i] == 1 and w[i] < len(sp):
                out.append(row['prompt'][sp[w[i]][0]:sp[w[i]][1]]); modes.append(1)
            else:
                out.append(self.vocab.decode(gen_ids[i])[::-1]); modes.append(2)
        return out, modes

    @torch.no_grad()
    def generate(self, batch, lesion=None):
        if lesion in ('noexec', 'opswap', 'ctl27', 'nowordc'):
            return self.talk(self.state(batch, lesion=lesion), batch)
        if lesion == 'nocopy':
            return self.talk(self.state(batch, lesion='nocopy'), batch, lesion='nocopy')
        return super(Ledger, self).generate(batch, lesion)

    # ---- loss ----
    def row_gold(self, r):
        """-> (ops, operand strings [(a, b)], tape texts, mode (WORD 1 / GEN 2), word targets) from the row's steps; cached by row id."""
        key = (r.get('id'), r['prompt'])
        hit = self._gold.get(key)
        if hit is None:
            if len(self._gold) > 300000:
                self._gold.clear()
            t = pp.row_targets(r)
            nums = pp.prompt_numbers(r['prompt'])
            vals = nums + [None] * (N_NUM - len(nums)) + pp.CONSTS + [s[3] for s in t['prog']]
            ops, opd, tape = [], [], [''] * N_RES
            for s, (o, ca, cb, v) in enumerate(t['prog']):
                sa, sb = str(vals[ca[0]]), str(vals[cb[0]])
                ops.append(o); opd.append((sa, sb))
                tape[s] = entry(NAMES[o], sa, sb, str(v))
            md = 1 if t['mode'] == 1 else 2
            if self.span_copy and t['mode'] == 0 and r['answer'] in {x for *_, x in self.num_tokens(r['prompt'], tape[:len(ops)])[0]}:
                md = 0          # T1S: a NUM row whose answer is a number token of the context answers by span copy (it keeps T1's GEN targets)
            hit = self._gold[key] = (ops, opd, tape, md, t['word'])
        return hit

    def cell_ids(self, s):
        e = self.vocab.encode(s[::-1][:CELLS - 1]) + [EOS]
        return e + [-100] * (CELLS - len(e))

    def gold(self, rows, dev):
        B, L = len(rows), N_RES
        op = np.zeros((B, L), np.int64)
        ca, cb = np.full((B, L, CELLS), -100, np.int64), np.full((B, L, CELLS), -100, np.int64)
        mode, word, gen = np.zeros(B, np.int64), np.zeros((B, W_MAX), bool), np.full((B, 9), -100, np.int64)
        tape = []
        for i, r in enumerate(rows):
            ops, opd, tp, md, wd = self.row_gold(r)
            for s, (o, (sa, sb)) in enumerate(zip(ops, opd)):
                op[i, s], ca[i, s], cb[i, s] = o, self.cell_ids(sa), self.cell_ids(sb)
            mode[i], word[i, list(wd)] = md, True
            if md != 1:
                ids = self.vocab.encode(r['answer'][:GEN_MAX][::-1]) + [EOS]
                gen[i, :len(ids)] = ids
            tape.append(list(tp))
        g = {k: torch.from_numpy(v).to(dev) for k, v in dict(op=op, ca=ca, cb=cb, mode=mode, word=word, gen=gen).items()}
        g['has'] = (g['op'] > 0).any(1)
        g['tape'] = tape
        return g

    def loss(self, batch):
        import torch.nn.functional as F
        dev, B = batch['prompt_ids'].device, len(batch['rows'])
        g = self.gold(batch['rows'], dev)
        o = self.run(batch, gold=g)
        lop, lcall, hits, tot = self.call_loss(o['steps'], g, B)
        marg = lambda lg, m, sel: torch.where(sel, -(torch.logsumexp(lg.masked_fill(~m, -1e9), -1) - torch.logsumexp(lg, -1)), torch.zeros_like(lg[:, 0])).sum() / B
        lmode = F.cross_entropy(o['lmode'].float(), g['mode'])
        lword = marg(o['lword'], g['word'], g['mode'] == 1)
        n_t = (g['gen'] >= 0).sum(1).clamp(min=1)
        p, gate = self.gen_copy(o['R'], o['X'], o['xm'], o['ids'])
        tg = g['gen']
        ce = -torch.log(p.gather(2, tg.clamp(min=0)[..., None])[..., 0] + 1e-6).masked_fill(tg < 0, 0.0)
        lgen = (ce.sum(1) / n_t).mul(g['mode'] != 1).sum() / B
        tm = (tg >= 0) & (tg != EOS) & (g['mode'] != 1)[:, None]
        aux = dict(prog=lop + lcall, op_acc=hits / tot.clamp(min=1), call=lcall, mode=lmode, word=lword, gen=lgen,
                   copy_share=((1 - gate[..., 0]) * tm).sum() / tm.sum().clamp(min=1))
        total = lop + lcall + lmode + lword + lgen
        if self.span_copy:
            ls = self.span_loss(o, g, batch, B)
            total = total + ls['span_call'] + ls['span_ans'] + ls['stop']
            aux.update(ls)
        return total, {k: v.detach() if torch.is_tensor(v) else v for k, v in aux.items()}

    def span_loss(self, o, g, batch, B):
        """T1S losses: call spans (gate + pointer, either order for ADD MUL MIN MAX), answer span (mode-0 rows) and the stop head."""
        import torch.nn.functional as F
        dev, T = batch['prompt_ids'].device, batch['prompt_ids'].shape[1]
        Ma, Mb, Mn, (cs, ts, ys) = self.span_gold(batch['rows'], T, o['le'], o['K'])
        Ma, Mb, Mn = (torch.from_numpy(x).to(dev) for x in (Ma, Mb, Mn))
        lse = lambda lg, M: torch.logsumexp(lg.masked_fill(~M, -1e9), -1) - torch.logsumexp(lg, -1)
        side = lambda lg, gl, M: torch.where(M.any(-1), F.logsigmoid(gl) + lse(lg, M), F.logsigmoid(-gl))
        comm = torch.isin(g['op'], torch.tensor(COMM, device=dev))
        lsc, n_span, n_side = 0.0, 0, 0
        for s, st in enumerate(o['steps']):
            sp, ma, mb, on = st[2], Ma[:, s], Mb[:, s], g['op'][:, s] > 0
            lab = side(sp['la'], sp['ga'], ma) + side(sp['lb'], sp['gb'], mb)
            lba = side(sp['la'], sp['ga'], mb) + side(sp['lb'], sp['gb'], ma)
            nll = -torch.where(comm[:, s] & (ma != mb).any(-1), torch.logaddexp(lab, lba), lab)     # same string twice: one order
            lsc = lsc + (nll * on).sum() / B
            n_span += int((ma.any(-1) & on).sum() + (mb.any(-1) & on).sum()); n_side += 2 * int(on.sum())
        ln = self.ptr(o['qn'], self.k_s(o['X']), o['xm'])
        sel = (g['mode'] == 0) & Mn.any(-1)
        lsn = torch.where(sel, -lse(ln, Mn), torch.zeros_like(ln[:, 0])).sum() / B
        if cs:
            lstop = F.binary_cross_entropy_with_logits(self.stop_logit(torch.tensor(cs, device=dev), torch.tensor(ts, device=dev)),
                                                       torch.tensor(ys, device=dev))
        else:
            lstop = torch.zeros((), device=dev)
        return dict(span_call=lsc, span_ans=lsn, stop=lstop, span_share=n_span / max(n_side, 1))

    def call_loss(self, steps, g, B):
        """The call writer's losses over the call rounds: op CE (NOOP rows weighted w_noop) and -log p of the gold operand strings."""
        import torch.nn.functional as F
        dev = g['op'].device
        w_row = torch.where(g['has'], 1.0, self.w_noop)
        comm = torch.isin(g['op'], torch.tensor(COMM, device=dev))
        lop = lcall = 0.0
        hits = tot = 0
        sc = lambda lp, tg: (lp.gather(2, tg.clamp(min=0)[..., None])[..., 0] * (tg >= 0)).sum(1)
        for s, st in enumerate(steps):
            lg, p = st[0].float(), st[1]
            lop = lop + (F.cross_entropy(lg, g['op'][:, s], reduction='none') * w_row).mean()
            lp = torch.log(p + 1e-6)
            la, lb = lp[:, :CELLS], lp[:, CELLS:]
            ta, tb = g['ca'][:, s], g['cb'][:, s]
            lab, lba = sc(la, ta) + sc(lb, tb), sc(la, tb) + sc(lb, ta)
            nll = -torch.where(comm[:, s], torch.logaddexp(lab, lba), lab)
            lcall = lcall + (nll * (g['op'][:, s] > 0)).sum() / B
            hits += ((lg.argmax(-1) == g['op'][:, s]) & g['has']).sum()
            tot += g['has'].sum()
        return lop, lcall, hits, tot

    # ---- replay of the model's own calls (opswap, write_copy) ----
    @staticmethod
    def sources(calls, prompt):
        """Where each operand of each call came from, by text: ('e', k) = the result of the k-th earlier call (the latest one with that text
        wins), ('v', int) = a literal (a prompt number or a constant written from the vocabulary); None = not a number."""
        out = []
        for j, (_, op, a, b, r) in enumerate(calls):
            src = []
            for x in (a, b):
                ks = [k for k in range(j) if calls[k][4] == x]
                src.append(('e', ks[-1]) if ks else (('v', int(x)) if INT_RE.fullmatch(x or '') else None))
            out.append(src)
        return out

    @staticmethod
    def replay(calls, srcs, swap=False):
        vals = []
        for (_, op, a, b, r), src in zip(calls, srcs):
            xs = []
            for s in src:
                if s is None or (s[0] == 'e' and vals[s[1]] is None):
                    xs = None; break
                xs.append(vals[s[1]] if s[0] == 'e' else s[1])
            v = None if xs is None else calc(op, str(xs[0]), str(xs[1]), swap)
            vals.append(None if v in (None, '?') else int(v))
        return vals

    # ---- extra evals (train.py --final-eval) ----
    @torch.no_grad()
    def extra_evals(self, ctx):
        import os, random
        from custom_io.data import collate, Dataset, load_rows, to_device
        from custom_io.evalx import CHAIN5, evaluate, is_hit, subsample
        was = self.training
        self.eval()
        root = ctx.get('big') or ctx['data']
        rows = load_rows(os.path.join(root, 'dev', 'in_dist.jsonl'))
        dev, bs, amp = ctx['device'], ctx['batch_size'], ctx['amp']
        cov = pp.coverage(rows)
        fams = sorted(f for f, c in cov['by_family'].items() if c['prog'] >= 50)
        prows = [r for r in rows if pp.row_targets(r)['prog']]
        out = dict(coverage=cov, program_families=fams, n_dev=len(rows), n_prog=len(prows), size=self.size())

        def batches(rs, size=bs):
            for s in range(0, len(rs), size):
                yield to_device(collate([Dataset(rs[s:s + size], self.vocab, strict=False)[i] for i in range(len(rs[s:s + size]))]), dev)

        # call accuracy: teacher-forced (gold tape) vs free run; a call is right when the op and both operand strings are the gold ones
        sl = subsample(prows, 400)
        acc = {m: dict(ops=0, steps=0, calls=0, n_calls=0, prog=0) for m in ('teacher_forced', 'free_run')}
        su = dict(sides=0, span=0, rows=0, ans_span=0)
        fr_ans = 0
        for b in batches(sl):
            g = self.gold(b['rows'], dev)
            for m, gd in (('teacher_forced', g), ('free_run', None)):
                with amp():
                    o = self.run(b, gold=gd)
                a = acc[m]
                okrow = torch.ones(len(b['rows']), dtype=torch.bool, device=dev)
                for s, st in enumerate(o['steps']):
                    op = st[0].argmax(-1)
                    okop = op == g['op'][:, s]
                    wr = self.written(st)
                    if m == 'free_run' and self.span_copy:
                        on = op > 0
                        su['sides'] += 2 * int(on.sum()); su['span'] += int(((st[2]['ga'] >= 0) & on).sum() + ((st[2]['gb'] >= 0) & on).sum())
                    for i, r in enumerate(b['rows']):
                        ops, opd = self.row_gold(r)[:2]
                        if s < len(ops):
                            sa, sb = opd[s]
                            good = bool(okop[i]) and (wr[i] == (sa, sb) or (ops[s] in COMM and wr[i] == (sb, sa)))
                            a['calls'] += good; a['n_calls'] += 1
                            okrow[i] &= good
                        else:
                            okrow[i] &= bool(okop[i])
                    a['ops'] += okop.sum().item(); a['steps'] += okop.numel()
                a['prog'] += okrow.sum().item()
                if m == 'free_run':
                    with amp():
                        fr_ans += sum(is_hit(p_, r) for p_, r in zip(self.generate(b), b['rows']))
                    su['rows'] += len(b['rows']); su['ans_span'] += int((o['lmode'].argmax(-1) == 0).sum())
        n = len(sl)
        pc = lambda x, d: 100 * x / max(d, 1)
        out['op_acc'] = {m: dict(op=pc(a['ops'], a['steps']), call=pc(a['calls'], a['n_calls']), program=pc(a['prog'], n)) for m, a in acc.items()}
        out['op_acc']['n'] = n
        out['op_acc']['free_run']['answer'] = pc(fr_ans, n)
        if self.span_copy:      # free run on the call-accuracy rows: share of written operands that took the span path, of answers in mode 0
            out['span_use'] = dict(operand=pc(su['span'], su['sides']), answer=pc(su['ans_span'], su['rows']), n_sides=su['sides'], n_rows=su['rows'])
        # tool off (mark 3): the B2 noexec set (NUM rows whose gold answer slots are all result slots), calculator returns '?'
        tg = {r['id']: pp.row_targets(r) for r in rows}
        fr_rows = subsample([r for r in rows if r['family'] in fams], 3000)
        ex_rows = [r for r in fr_rows if tg[r['id']]['mode'] == 0 and all(x >= R0 for x in tg[r['id']]['ans'])]
        with amp():
            nx = evaluate(self, ex_rows, bs, dev, 'noexec') if ex_rows else dict(exact=None, n=0)
            ne = evaluate(self, fr_rows, bs, dev, 'noexec')
            it = evaluate(self, ex_rows, bs, dev, None) if ex_rows else dict(exact=None)
        out['noexec'] = dict(program_families=nx['exact'], n=nx['n'], intact=it['exact'], exec_families=sorted({r['family'] for r in ex_rows}),
                             all_program_families=ne['exact'], n_all=ne['n'], by_family=ne['by_family'], families=fams)
        c5 = [r for r in rows if r['family'] in CHAIN5]
        c5n = [r for r in c5 if tg[r['id']]['mode'] == 0]
        c5w = [r for r in c5 if tg[r['id']]['mode'] == 1]
        les = {}
        for name in ('intact', 'loops:1', 'loops:2', 'noexec'):
            les[name] = {}
            for tag, rs in (('all', c5), ('num', c5n), ('word', c5w)):
                if rs:
                    with amp():
                        les[name][tag] = evaluate(self, rs, bs, dev, None if name == 'intact' else name)['exact']
        out['chain5_lesions'] = dict(n_all=len(c5), n_num=len(c5n), n_word=len(c5w), **les)
        out['noexec']['chain5'] = les['noexec'].get('all')

        # opswap (mark 5): rows right when intact whose answer text is a call result; expected = the model's own calls replayed with add <-> sub
        def run_rows(rs, lesion=None, oracle=None):
            res = []
            for b in batches(rs):
                with amp():
                    o = self.run(b, lesion=lesion, oracle=None if oracle is None else (lambda i, t, c, _b=b: oracle(_b['rows'][i], t, c)))
                    ans = self.talk(self.state_of(o), b)
                for i, r in enumerate(b['rows']):
                    res.append((r, o['calls'][i], ans[i]))
            return res

        def swap_stats(rs):
            sm = dict(n=0, aff=0, match=0, invalid=0, unchanged=0, intact=0)
            base = [x for x in run_rows(rs) if is_hit(x[2], x[0])]
            keep = []
            for r, calls, ans in base:
                ks = [k for k in range(len(calls)) if calls[k][4] == ans]
                if not ks:
                    continue
                sm['n'] += 1
                v2 = self.replay(calls, self.sources(calls, r['prompt']), swap=True)[ks[-1]]
                if v2 is None:
                    sm['invalid'] += 1
                elif str(v2) == ans:
                    sm['unchanged'] += 1
                else:
                    keep.append((r, str(v2)))
            want = {r['id']: w for r, w in keep}
            for r, _, ans in run_rows([r for r, _ in keep], lesion='opswap'):
                sm['aff'] += 1; sm['match'] += ans == want[r['id']]; sm['intact'] += is_hit(ans, r)
            return sm
        s5, sa = swap_stats(c5), swap_stats(fr_rows)
        out['opswap'] = dict(swap_match=pc(s5['match'], s5['aff']), n_affected=s5['aff'], n_invalid_swap=s5['invalid'], n_unchanged=s5['unchanged'],
                             n_from_call=s5['n'], stays_intact=pc(s5['intact'], s5['aff']), swap_match_all=pc(sa['match'], sa['aff']), n_all=sa['aff'])

        # write_copy (D0 writing, on these checkpoints): every result becomes a random 1-9 digit string (fixed per row and round);
        # operand copy = a later call whose operand (in the intact run) was an earlier result now writes that random string exactly;
        # answer copy = rows whose intact answer was a call result now answer that call's random string (1-8 digits only: GEN holds 8 chars;
        # T1S: 1-9, a span answer has no register limit)
        def oracle(r, t, c):
            return rand_digits(random.Random(f"{r['id']}|{t}"), 1, 9)
        base = {r['id']: (calls, ans) for r, calls, ans in run_rows(prows if len(prows) <= 3000 else subsample(prows, 3000))}
        wc = dict(op_n=0, op_ok=0, op_by_len={}, ans_n=0, ans_ok=0, ans_by_len={}, too_long=0, path_changed=0)
        rs = [r for r in rows if r['id'] in base]
        for r, calls, ans in run_rows(rs, oracle=oracle):
            c0, a0 = base[r['id']]
            src = self.sources(c0, r['prompt'])
            if [c[:2] for c in calls[:len(c0)]] != [c[:2] for c in c0]:
                wc['path_changed'] += 1
                continue
            for j, sj in enumerate(src):
                for side, s in enumerate(sj):
                    if s is not None and s[0] == 'e':
                        want, got = calls[s[1]][4], calls[j][2 + side]
                        L = str(len(want))
                        d = wc['op_by_len'].setdefault(L, [0, 0])
                        d[0] += 1; d[1] += got == want
                        wc['op_n'] += 1; wc['op_ok'] += got == want
            ks = [k for k in range(len(c0)) if c0[k][4] == a0]
            if ks and is_hit(a0, r):
                want = calls[ks[-1]][4]
                if len(want) > GEN_MAX and not self.span_copy:
                    wc['too_long'] += 1
                    continue
                d = wc['ans_by_len'].setdefault(str(len(want)), [0, 0])
                d[0] += 1; d[1] += ans == want
                wc['ans_n'] += 1; wc['ans_ok'] += ans == want
        wc['operand_copy'] = pc(wc['op_ok'], wc['op_n'])
        wc['answer_copy'] = pc(wc['ans_ok'], wc['ans_n'])
        out['write_copy'] = wc
        out['write_copy_u'] = self.write_copy_u(ctx)
        out['copy_gate'] = self.copy_gate_eval(rows, ctx)
        self.train(was)
        return out

    @torch.no_grad()
    def write_copy_u(self, ctx, min_n=200, max_passes=8):
        """write_copy as amended (MARKS-D0-T1-2026-10-07.md Amendment 4): the same rows, oracle and copy events as write_copy, each scored only
        when UNAMBIGUOUS: the operand's text (in the intact run) equals exactly one earlier call result and no prompt number or constant (an
        answer: exactly one call result, no prompt number or constant); the others are counted apart as ambiguous. Pass 0 is write_copy's own
        oracle draw; while an unambiguous cell (operand or answer, length 1-9) has n < min_n, another pass re-draws every random string on
        the same rows (oracle seed + '|pass'), up to max_passes. The rule reads only texts and n, never whether the model was right."""
        import os, random
        from custom_io.data import collate, Dataset, load_rows, to_device
        from custom_io.evalx import is_hit, subsample
        was = self.training
        self.eval()
        root = ctx.get('big') or ctx['data']
        rows = load_rows(os.path.join(root, 'dev', 'in_dist.jsonl'))
        prows = [r for r in rows if pp.row_targets(r)['prog']]
        rs = prows if len(prows) <= 3000 else subsample(prows, 3000)
        dev, bs, amp = ctx['device'], ctx['batch_size'], ctx['amp']
        consts = {str(c) for c in pp.CONSTS}

        def run_rows(oracle=None):
            res = []
            for s0 in range(0, len(rs), bs):
                b = to_device(collate([Dataset(rs[s0:s0 + bs], self.vocab, strict=False)[i] for i in range(len(rs[s0:s0 + bs]))]), dev)
                with amp():
                    o = self.run(b, oracle=None if oracle is None else (lambda i, t, c, _b=b: oracle(_b['rows'][i], t, c)))
                    ans = self.talk(self.state_of(o), b)
                res += [(r, o['calls'][i], ans[i]) for i, r in enumerate(b['rows'])]
            return res
        base = {r['id']: (calls, ans) for r, calls, ans in run_rows()}
        cells = {k: {} for k in ('operand', 'operand_ambiguous', 'answer', 'answer_ambiguous')}

        def add(key, want, ok):
            d = cells[key].setdefault(str(len(want)), [0, 0])
            d[0] += 1; d[1] += ok
        unamb = lambda x, res, pn: sum(y == x for y in res) == 1 and x not in pn and x not in consts
        passes, path_changed, too_long = 0, 0, 0
        while passes < max_passes:
            tag = '' if passes == 0 else f'|{passes}'
            for r, calls, ans in run_rows(lambda r, t, c: rand_digits(random.Random(f"{r['id']}|{t}{tag}"), 1, 9)):
                c0, a0 = base[r['id']]
                if [c[:2] for c in calls[:len(c0)]] != [c[:2] for c in c0]:
                    path_changed += 1
                    continue
                pn = {m.group() for m in pp.NUM_RE.finditer(r['prompt'])}
                for j in range(len(c0)):
                    earlier = [c0[k][4] for k in range(j)]
                    for side in (0, 1):
                        x = c0[j][2 + side]
                        if x in earlier:            # write_copy's own copy event (its text label)
                            k = max(k for k in range(j) if c0[k][4] == x)
                            add('operand' if unamb(x, earlier, pn) else 'operand_ambiguous', calls[k][4], calls[j][2 + side] == calls[k][4])
                res = [c[4] for c in c0]
                ks = [k for k in range(len(c0)) if c0[k][4] == a0]
                if ks and is_hit(a0, r):
                    want = calls[ks[-1]][4]
                    if len(want) > GEN_MAX and not self.span_copy:
                        too_long += 1
                        continue
                    add('answer' if unamb(a0, res, pn) else 'answer_ambiguous', want, ans == want)
            passes += 1
            if all(cells[k].get(str(L), [0])[0] >= min_n for k in ('operand', 'answer') for L in range(1, 10)):
                break
        self.train(was)
        pc = lambda d: {L: dict(n=v[0], exact=100 * v[1] / v[0]) for L, v in sorted(d.items(), key=lambda x: int(x[0]))}
        return dict({k: pc(v) for k, v in cells.items()}, counts=cells, passes=passes, min_n=min_n, path_changed=path_changed, too_long=too_long,
                    n_rows=len(rs))

    @torch.no_grad()
    def copy_gate_eval(self, rows, ctx):
        """Mean (1 - g) over the answer registers that hold a target char, on GEN rows (here: every former NUM row too), per family."""
        from custom_io.data import collate, Dataset, to_device
        from custom_io.evalx import subsample
        gen_rows = subsample([r for r in rows if self.row_gold(r)[3] == 2], 3000)
        dev, bs, amp = ctx['device'], ctx['batch_size'], ctx['amp']
        tot, cnt = {}, {}
        for s in range(0, len(gen_rows), bs):
            rs = gen_rows[s:s + bs]
            b = to_device(collate([Dataset(rs, self.vocab, strict=False)[i] for i in range(len(rs))]), dev)
            with amp():
                o = self.run(b)
                _, gate = self.gen_copy(o['R'], o['X'], o['xm'], o['ids'])
            tgt = self.gold(rs, dev)['gen']
            hold = (tgt >= 0) & (tgt != EOS)
            share = ((1 - gate[..., 0]) * hold).sum(1).tolist()
            for i, r in enumerate(rs):
                f = r['family']
                tot[f], cnt[f] = tot.get(f, 0.0) + share[i], cnt.get(f, 0) + int(hold[i].sum())
        return dict(by_family={f: tot[f] / cnt[f] for f in sorted(cnt) if cnt[f]}, n_regs={f: cnt[f] for f in sorted(cnt)},
                    overall=sum(tot.values()) / max(sum(cnt.values()), 1), n_rows=len(gen_rows))
