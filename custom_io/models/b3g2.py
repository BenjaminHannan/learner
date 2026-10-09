"""B3 group 2 (architecture/B3-GROUP2-BUILD-2026-10-09.md; model 'b3g2'): B3 group 1 with ONE learned byte writer (models/writer.py) in place of every hand-made
head on the answer path. Group 2 = no_slots (N1) + no_place (P1) + bytes (V1) + as_written (L1) + the writer (O1), all cfg keys of this class (the first three are
Ledger / B3 keys, passed through). ST1 (custom_io/st1.py) runs on its checkpoints: sample_traces / trace_loss below are its interface.
Everything B3 group 1 builds is built (any_round, gap_p, eg_embed, span_copy / span_idx / span_end / ans_drill, H1's 'settled' stop head, in B3's init order), then the heads the
writer replaces are DELETED (so no other weight's init changes) and the ByteWriter is created LAST, tied to the reader's byte table (self.reader.tok): the op head,
W_a / W_b, the span pointer (q_s, k_s, g_s, stop_s), the mode head, the word pointer and its keys (q_word, k_word, len_emb, ln_wc, k_wc) and the GEN pointer-generator
(ln_t, q_cp, k_cp, g_cp, bias). e_s / e_e stay: they are the writer's learned layout terms on its copy keys (which string, how far from its end; judged allowed J2, J3).
Writer cap WCAP = max(tool.LE, data.MAX_ANS) + 1 steps; cfg writer_inner (default d / 2), writer_mlp (2.0), writer_heads (4), writer_refine (1: Addendum B).

The loop (B3.loop without number slots and word keys). After each round t >= 1 the writer is asked "call?" (mode 0): writing EOS first = no call; else the text
is a call, split at its first space: the first word names a tool of the registry {name: fn(rest text) -> reply text}; the calculator registers add sub mul div mod min max
cmp (the rest must be exactly two whitespace-separated tokens, else '?'), `note` runs nothing and replies ''; an unknown name replies '?'. The tape entry is `call = reply`
(a note: the call text alone), at most LE units (counted `tape_entry_over`, never silently cut), the row's next free entry (TAPE), visible from round t + 1. A call refused by a
full tape is not run and is counted (tape_full). Lesions act inside the dispatch: noexec (every calculator reply '?'), opswap (add <-> sub). calls are recorded (t, name, a, b, reply)
with a, b the two tokens (else rest, ''), so Tool.sources / replay / write_copy / opswap work unchanged; records [(t, call text, reply)] are the full text, for ST1.
Teacher forcing (loss): B3's schedule (calls at rounds 1..L, or gap rounds with p gap_p); the gold calls are progtext.steps_of(row, as_written) as text (notes included);
the tape holds the TOOL'S real reply (never the label's: a difference is counted `reply_mismatch`; a drill row carries its drawn strings). Rounds with a call: target = the
call text; rounds after the row's last call: EOS only; gap rounds: no target. Context [prompt X; tape Xt] masked by the entries visible BEFORE the round's call; Z = every thinker
vector; the call loss is the sum over rounds of the mean over rows of nll * w_row (1.0 with calls, w_noop without) over the rows that have a target. The per-round answer
(H1's rule): at every round t >= the row's last call round the writer is asked "answer" (mode 1), teacher forced; the answer loss is the row's mean over those rounds;
rounds t >= 8 are gradient-checkpointed. "Right at round t" = writer.right (every teacher-forced argmax is the gold byte); with the selective-read feedback it approximates greedy
decoding (extra_evals reports how often the label agrees with real greedy decoding). The stop head is H1's on ln_z(control 1), detached, BCE on the 'settled' (or 'right')
label; 'settled' only counts in a batch that ran the whole turn (stop_w, H1's rule). Rows before their last call round get label inputs "not right" (no answer pass is run there).
Free run: writer.greedy on every row still running; an unfinished write (no EOS within WCAP) is not a call (counted `unended`); `each` / the learned stop exactly as B3.run.
state = (Z, Xt, idt, vis); talk(state, batch) = writer.greedy(mode 1) over [the CURRENT prompt; the state's tape], so donor swaps work as today. Lessons that act on Z:
zero_state, shuffle_state; nocopy forces the writer's gate (calls and answer); loops:K. nowordc is gone (no word-content keys). Counters: capcount steps_unparsed (rows with
steps and no readable calls), no_trace (rows with steps and no usable trace), writer_over (a call or answer longer than WCAP gets no target), steps_over (more steps than tape),
tape_entry_over."""
import math, random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.checkpoint import checkpoint
from custom_io import capcount, data as D
from custom_io.data import BOS, EOS
from custom_io.models import progtext
from custom_io.models.b3 import B3, FAR, GAPS
from custom_io.models.ledger import N_CTRL, N_REG, N_RES
from custom_io.models.tool import LE, NAMES, calc
from custom_io.models.tool_h1 import CAP, KS, P_STOP, norm, settled
from custom_io.models.writer import ByteWriter

CKPT_FROM = 8           # rounds t >= 8 (the 9th on) are gradient-checkpointed, thinker and writer alike (H1's rule)
DELETED = ('op_head', 'W_a', 'W_b', 'q_s', 'k_s', 'g_s', 'stop_s', 'mode_head', 'q_word', 'k_word', 'len_emb', 'ln_wc', 'k_wc', 'ln_t', 'q_cp', 'k_cp', 'g_cp', 'bias')


class B3G2(B3):
    OPERAND_CELLS = False
    LESIONS = ['shuffle_state', 'zero_state', 'noexec', 'opswap', 'nocopy']      # nowordc is gone: there are no word-content keys

    def __init__(self, vocab, as_written=True, writer_refine=1, writer_inner=None, writer_mlp=2.0, writer_heads=4, **kw):
        super().__init__(vocab, **kw)
        assert self.any_round, 'b3g2 calls at any round: it needs any_round'
        self.as_written, self.refine = bool(as_written), int(writer_refine)
        for name in DELETED:        # deleted after everything is built: no RNG draw changes, every other weight starts as in B3
            if hasattr(self, name):
                delattr(self, name)
        self.LESIONS = list(B3G2.LESIONS)
        self.WCAP = max(LE, D.MAX_ANS) + 1
        self.writer = ByteWriter(self.d, self.reader.tok, self.WCAP, dk=self.dk, heads=writer_heads, inner=writer_inner or self.d // 2, mlp=writer_mlp)      # created LAST
        self.calc_names = tuple(NAMES[1:])
        self.tools = {n: (lambda rest, n=n: self.calculator(n, rest)) for n in self.calc_names}
        self.tools['note'] = lambda rest: ''
        self._tr = {}
        self.trace_stats = dict(rows=0, with_steps=0, calls=0, notes=0, unreadable=0, no_trace=0, over_tape=0, reply_mismatch=0, writer_over=0)
        self.free_stats = dict(unended=0)

    # ---- the tools ----
    @staticmethod
    def calculator(name, rest, swap=False):
        """The registered calculator: `rest` must be exactly two whitespace-separated tokens, else '?'."""
        toks = rest.split()
        return '?' if len(toks) != 2 else calc(name, toks[0], toks[1], swap)

    def dispatch(self, text, i, t, lesion=None, oracle=None):
        """One written call -> the record (t, name, a, b, reply). The harness splits at the first space; an unknown tool replies '?'; the lesions act here."""
        name, _, rest = text.partition(' ')
        fn = self.tools.get(name)
        if fn is None:
            return (t, name, rest, '', '?')
        if name not in self.calc_names:
            return (t, name, rest, '', fn(rest))
        toks = rest.split()
        a, b = (toks[0], toks[1]) if len(toks) == 2 else (rest, '')
        if len(toks) == 2 and oracle is not None:
            r = oracle(i, t, (name, a, b))
        elif lesion == 'noexec':
            r = '?'
        else:
            r = self.tools[{'add': 'sub', 'sub': 'add'}.get(name, name) if lesion == 'opswap' else name](rest)
        return (t, name, a, b, r)

    def entry_text(self, call, reply):
        """The tape entry: `call = reply` (a tool that replies nothing, like note: the call alone); longer than LE is counted, and the tape holds LE units."""
        s = call if reply == '' else f'{call} = {reply}'
        if self.vocab.length(s) > LE:
            capcount.hit('tape_entry_over')
        return self.vocab.clip(s, LE)

    # ---- the gold (training) ----
    def ids_of(self, text):
        """-> the writer's target ids of a string, counting a string that cannot fit WCAP (the row then has no target for it, never a cut one)."""
        ids = self.vocab.encode(text)
        if len(ids) + 1 > self.WCAP:
            capcount.hit('writer_over')
            self.trace_stats['writer_over'] += 1
        return ids

    def make_gold(self, texts, entries, answer, drill=False):
        return dict(texts=list(texts), ids=[self.ids_of(x) for x in texts], tape=list(entries), ans=answer, ans_ids=self.ids_of(answer), drill=drill)

    def trace_of(self, r):
        """Cached per (id, prompt): the row's gold (calls and notes as text, the tool's real replies, the answer) and its steps; the trace counters are counted here once."""
        key = (r.get('id'), r['prompt'])
        hit = self._tr.get(key)
        if hit is None:
            if len(self._tr) > 300000:
                self._tr.clear()
            hit = self._tr[key] = self.build_trace(r)
        return hit

    def build_trace(self, r):
        st = self.trace_stats
        st['rows'] += 1
        steps, calls = r.get('steps'), []
        if steps:
            st['with_steps'] += 1
            calls, why = progtext.steps_of(r, self.as_written)
            if calls is None:           # worked steps that cannot be read: the row would train on the answer alone (the no-answer-only rule)
                capcount.hit('steps_unparsed'); capcount.hit('no_trace')
                st['unreadable'] += 1; st['no_trace'] += 1
                calls = []
            elif not calls:
                capcount.hit('no_trace'); st['no_trace'] += 1
            elif len(calls) > self.tape:
                capcount.hit('steps_over'); capcount.hit('no_trace')
                st['over_tape'] += 1; st['no_trace'] += 1
                calls = []
        texts, entries = [], []
        for c in calls:
            txt = progtext.text(c)
            if c['op'] == 'note':
                rep, st['notes'] = '', st['notes'] + 1
            else:
                rep = calc(c['op'], c['a'], c['b'])         # the tool's real reply; the label's result is only checked
                st['calls'] += 1
                if rep != c['result']:
                    st['reply_mismatch'] += 1
            texts.append(txt)
            entries.append(self.entry_text(txt, rep))
        return dict(calls=calls, gold=self.make_gold(texts, entries, r['answer']))

    def drilled(self, steps, answer):
        """A progtext.drill result -> the gold: its call texts, the entries with the DRAWN results (the tool's reply is replaced by random digits), the drawn answer."""
        texts = [progtext.text(c) for c in steps]
        return self.make_gold(texts, [self.entry_text(x, '' if c['op'] == 'note' else c['result']) for x, c in zip(texts, steps)], answer, True)

    def train_golds(self, rows):
        """Per-row gold. In training, a row whose answer is a call's result is, with probability ans_drill, drilled (progtext.drill; the model's own random stream)."""
        out = []
        for r in rows:
            tr = self.trace_of(r)
            g = None
            if self.ans_drill and self.training and any(c['op'] != 'note' and c['result'] == r['answer'] for c in tr['calls']):
                self.drill_stats['eligible'] += 1
                if self._drill_rng.random() < self.ans_drill:
                    d = progtext.drill(tr['calls'], r['answer'], self._drill_rng)
                    if d == 'too_long':
                        self.drill_stats['too_long'] += 1
                    elif d is not None:
                        self.drill_stats['drilled'] += 1
                        g = self.drilled(*d)
            self.drill_stats['rows'] += 1
            out.append(g or tr['gold'])
        return out

    def plain_golds(self, rows):
        return [self.trace_of(r)['gold'] for r in rows]

    def trace_gold(self, t):
        """ST1: a sampled trace dict(calls=[(call text, reply)], answer) -> the gold, the model's own calls with the tool's real replies."""
        texts = [c for c, _ in t['calls']]
        return self.make_gold(texts, [self.entry_text(c, rep) for c, rep in t['calls']], t['answer'])

    # ---- the schedule ----
    def plan(self, Ls, B, dev):
        """B3.plan over call counts Ls (width = the tape): -> (sched [B, tape] call rounds or -1, each row's last call round). Same draws, same order."""
        sched = np.full((B, self.tape), -1, np.int64)
        for i, L in enumerate(Ls):
            if not L:
                continue
            self.plan_stats['rows'] += 1
            gs = [0] * L
            if self.gap_p and self.training and self._gap_rng.random() < self.gap_p:
                gs = [self._gap_rng.choice(GAPS) for _ in range(L)]
                if L + sum(gs) + 1 > CAP:
                    self.plan_stats['fallback'] += 1
                    gs = [0] * L
                else:
                    self.plan_stats['gapped'] += 1
            r = 0
            for j in range(L):
                r += 1 + gs[j]
                sched[i, j] = r
        sched = torch.from_numpy(sched).to(dev)
        return sched, sched.max(1).values.clamp(min=0)

    # ---- the writer ----
    def ckeys(self, N, T, le, mask):
        """The writer's copy-key layout terms (e_s: which string, e_e: distance from its end) over the context, or None without span_idx."""
        terms = self.layout_terms(N, T, le, mask, mask.device)
        out = None
        for x in terms:
            out = x if out is None else out + x
        return out

    @staticmethod
    def pick(x, sel, full):
        return x if full else x[sel]

    def ans_pass(self, Z, Xc, cmask, cids, ck, inp, tgt, fb, nocopy=False):
        """The answer asked of the writer (mode 1), teacher forced -> (nll [B], right [B], copy mass over the non-EOS target bytes [B], their count [B])."""
        B = Z.shape[0]
        logp, gate, _ = self.writer(Z, torch.ones(B, Z.shape[1], dtype=torch.bool, device=Z.device), Xc, cmask, cids, torch.ones(B, dtype=torch.long, device=Z.device), inp, fb,
                                    nocopy, ck, self.refine)
        tm = (tgt >= 0) & (tgt != EOS)
        return ByteWriter.nll(logp, tgt), ByteWriter.right(logp, tgt), ((1 - gate.detach()) * tm).sum(1), tm.sum(1)

    def forced_answer(self, state, batch, answers, nocopy=False):
        """Teacher-forced answer pass on a state (Z, Xt, idt, vis) and the CURRENT batch -> ans_pass's four [B] tensors (evals)."""
        Z, Xt, idt, vis = state[:4]
        X, xm = self.read(batch, talker=True)
        Xc, cmask, cids = torch.cat([X, Xt.to(X.dtype)], 1), torch.cat([xm, vis.bool()], 1), torch.cat([batch['prompt_ids'], idt.long()], 1)
        T, le = X.shape[1], Xt.shape[1] // self.tape
        te = ByteWriter.teacher([self.vocab.encode(a) for a in answers], cids, cmask, self.WCAP, BOS, EOS)
        return self.ans_pass(Z, Xc, cmask, cids, self.ckeys(Xc.shape[1], T, le, cmask), te['inp'], te['tgt'], te['fb'], nocopy)

    # ---- the loop ----
    def loop(self, batch, n, lesion=None, oracle=None, each=None, g=None, sched=None, halt=None, temperature=0.0, generator=None, rec=False):
        """n rounds. g (teacher forcing) = dict(L [B] call counts, ids [B][L] call target ids, tape [B][L] entries, has [B] bool) on `sched` [B, tape] (call rounds, -1 = none); the
        call losses are returned (lcall; call_hit / call_n / eos_hit / eos_n; rec: per call round [(row, k, text right, name right)]). Else a free run: halt [B] (rounds used, 0 =
        running) keeps stopped rows from calling; temperature > 0 samples the writer (ST1). -> dict(Z, tape (Xt, idt, vis), calls, records, le, K, tape_full, ...)."""
        X, xm = self.read(batch, talker=True)
        B, T, dev = X.shape[0], X.shape[1], X.device
        ns, ne = (None, None) if self.no_slots else self.tokenize(batch)[:2]
        valid, S0 = self.num_memory(X, ns, ne)
        Xk, km = self.tok_spots(X, xm, batch) if self.tok_think else (X, xm)
        kvx = [b.kv_of(Xk + self.src.weight[1]) for b in self.core]
        kvs0 = self.slot_kv(S0)
        tf = g is not None
        if tf:
            K = max(1, max(g['L']))
            texts, le = [(list(e) + [''] * K)[:K] for e in g['tape']], None
            last = sched.max(1).values.clamp(min=0)
            w_row = torch.where(g['has'], 1.0, self.w_noop)
        else:
            K, texts, le = self.tape, [[''] * self.tape for _ in range(B)], LE
        Xt, idt, mt, le = self.tape_of(texts, dev, le)
        ent = torch.arange(K * le, device=dev) // le
        kvt = [b.kv_of(Xt + self.src.weight[1]) for b in self.core]
        Z = torch.cat([self.ctrl.weight, self.reader.place.weight[:N_REG]]).expand(B, -1, -1)
        shown = torch.zeros(B, self.tape, dtype=torch.bool, device=dev)
        nk = [0] * B
        calls, recs, full_ev = [[] for _ in range(B)], [[] for _ in range(B)], []
        cround = torch.full((B, self.tape), FAR, dtype=torch.long, device=dev)
        nocopy = lesion == 'nocopy'
        lcall, hits = 0.0, dict(call_hit=0, call_n=0, eos_hit=0, eos_n=0)
        crec = []
        kvs_of = None
        pids = batch['prompt_ids']
        for t in range(n):
            ts = min(t, self.n_loops - 1)
            vis = mt & shown[:, :K].gather(1, ent.expand(B, -1))
            if kvs_of is not kvt:
                kvs, kvs_of = self.join_kv(kvs0, kvt), kvt
            mask = torch.cat([valid, vis, km], 1)
            Z = self.think(Z + self.step_emb.weight[ts], kvs, kvx, mask, t)
            if lesion == 'ctl27':
                Z = torch.cat([Z[:, :2], torch.zeros_like(Z[:, 2:N_CTRL]), Z[:, N_CTRL:]], 1)
            if t >= 1:
                Xc, cmask, cids = torch.cat([X, Xt.to(X.dtype)], 1), torch.cat([xm, vis], 1), torch.cat([pids, idt], 1)
                if tf:
                    at = sched == t
                    call, kk = at.any(1), at.int().argmax(1)
                    cl, kl, aft = call.tolist(), kk.tolist(), (t > last).tolist()
                    tgt = [g['ids'][i][kl[i]] if cl[i] else ([] if aft[i] else None) for i in range(B)]
                    sel = [i for i in range(B) if tgt[i] is not None]
                    if sel:
                        full = len(sel) == B
                        si = torch.tensor(sel, device=dev)
                        pk = lambda x: self.pick(x, si, full)
                        te = ByteWriter.teacher([tgt[i] for i in sel], pk(cids), pk(cmask), self.WCAP, BOS, EOS)
                        ck = self.ckeys(Xc.shape[1], T, le, pk(cmask))
                        Zs = pk(Z)
                        logp, gate, _ = self.writer(Zs, torch.ones(Zs.shape[:2], dtype=torch.bool, device=dev), pk(Xc), pk(cmask), pk(cids),
                                                    torch.zeros(len(sel), dtype=torch.long, device=dev), te['inp'], te['fb'], nocopy, ck, self.refine)
                        nll = ByteWriter.nll(logp, te['tgt'])
                        lcall = lcall + (nll * pk(w_row)).sum() / B
                        ok = ByteWriter.right(logp, te['tgt']).tolist()
                        for j, i in enumerate(sel):
                            if cl[i]:
                                hits['call_n'] += 1; hits['call_hit'] += ok[j]
                            else:
                                hits['eos_n'] += 1; hits['eos_hit'] += ok[j]
                        if rec:
                            pred = logp.argmax(-1).tolist()
                            for j, i in enumerate(sel):
                                if cl[i]:
                                    gw = self.vocab.decode(tgt[i]).split(' ')[0]
                                    pw = self.vocab.decode(pred[j]).split(' ')[0]
                                    crec.append((i, kl[i], bool(ok[j]), pw == gw))
                    rows = call.nonzero()[:, 0]
                    cround[rows, kk[rows]] = t
                    shown[rows, kk[rows]] = True
                else:
                    alive = [True] * B if halt is None else (halt == 0).tolist()
                    sel = [i for i in range(B) if alive[i]]
                    if sel:
                        full = len(sel) == B
                        si = torch.tensor(sel, device=dev)
                        pk = lambda x: self.pick(x, si, full)
                        cm = pk(cmask)
                        Zs = pk(Z)
                        outs, ended = self.writer.greedy(Zs, torch.ones(Zs.shape[:2], dtype=torch.bool, device=dev), pk(Xc), cm, pk(cids),
                                                         torch.zeros(len(sel), dtype=torch.long, device=dev), nocopy=nocopy,
                                                         ckeys=self.ckeys(Xc.shape[1], T, le, cm), temperature=temperature, generator=generator)
                        new_k, placed = {}, []
                        for j, i in enumerate(sel):
                            if not bool(ended[j]):
                                self.free_stats['unended'] += 1
                                continue
                            txt = self.vocab.decode(outs[j])
                            if txt == '':
                                continue
                            if nk[i] >= self.tape:
                                full_ev.append((i, t))
                                continue
                            r_ = self.dispatch(txt, i, t, lesion, oracle)
                            calls[i].append(r_)
                            recs[i].append((t, txt, r_[4]))
                            new_k.setdefault(nk[i], [''] * B)[i] = self.entry_text(txt, r_[4])
                            cround[i, nk[i]] = t
                            placed.append((i, nk[i]))
                            nk[i] += 1
                        if new_k:
                            Xt, idt, mt = Xt.clone(), idt.clone(), mt.clone()
                            for k, new in new_k.items():
                                sl_ = torch.tensor([bool(x) for x in new], device=dev)
                                Xn, inn_, mn = self.read_texts(new, dev, le)
                                Xn = (Xn + self.tape_emb.weight[k].to(Xn.dtype)) * mn[..., None]
                                sl = slice(k * le, (k + 1) * le)
                                Xt[:, sl] = torch.where(sl_[:, None, None], Xn.to(Xt.dtype), Xt[:, sl])
                                idt[:, sl] = torch.where(sl_[:, None], inn_, idt[:, sl])
                                mt[:, sl] = torch.where(sl_[:, None], mn, mt[:, sl])
                                shown[sl_, k] = True
                            kvt = [b.kv_of(Xt + self.src.weight[1]) for b in self.core]
            if each is not None and each(t, dict(Z=Z, X=X, xm=xm, Xt=Xt, idt=idt, mt=mt, shown=shown, ent=ent, K=K)):
                break
        vis = mt & shown[:, :K].gather(1, ent.expand(B, -1))
        out = dict(Z=Z, X=X, xm=xm, tape=(Xt, idt, vis), calls=calls, records=recs, le=le, K=K, tape_full=full_ev, cround=cround)
        if tf:
            out.update(lcall=lcall, crec=crec, **hits)
        return out

    # ---- the run ----
    def run(self, batch, loops=None, gold=None, lesion=None, rounds=False, oracle=None, each=None, force=None, temperature=0.0, generator=None):
        """loops / each: a forced run (the stop head ignored). Else the learned stop (B3.run): the batch runs until every row has stopped; each row's state (Z, tape) and calls are
        the ones at its own stop round. -> dict(Z, tape, calls, records, rounds, tape_full_rows, ...); last_rounds / last_tape_full are set."""
        assert gold is None and force is None and not rounds, 'b3g2 trains through loss(); teacher forcing is internal'
        B, dev = batch['prompt_ids'].shape[0], batch['prompt_ids'].device
        if loops is not None or each is not None:
            n = self.n_loops if loops is None else loops
            o = self.loop(batch, n, lesion, oracle, each, temperature=temperature, generator=generator)
            if each is None:
                self.last_rounds = [n] * B
                self.last_tape_full = [any(i == j for j, _ in o['tape_full']) for i in range(B)]
            return o
        used = torch.zeros(B, dtype=torch.long, device=dev)
        keep = []

        def stop_here(t, st):
            Z = st['Z']
            vis = st['mt'] & st['shown'][:, :st['K']].gather(1, st['ent'].expand(Z.shape[0], -1))
            s = (Z, st['Xt'], st['idt'], vis)
            new = (used == 0) & ((self.p_stop(self.ln_z(Z[:, 1])) >= P_STOP) | (t + 1 >= self.cap))
            if new.any():
                if not keep:
                    keep.extend(x.clone() for x in s)
                else:
                    for x, y in zip(keep, s):
                        x[new] = y[new].to(x.dtype)
                used[new] = t + 1
            return bool((used > 0).all())

        o = self.loop(batch, self.cap, lesion, oracle, stop_here, halt=used, temperature=temperature, generator=generator)
        Z, Xt, idt, vis = keep
        u = used.tolist()
        full = [False] * B
        for i, t in o['tape_full']:
            full[i] |= t < u[i]
        self.last_rounds, self.last_tape_full = u, full
        return dict(o, Z=Z, tape=(Xt, idt, vis), calls=[[c for c in cs if c[0] < u[i]] for i, cs in enumerate(o['calls'])],
                    records=[[c for c in cs if c[0] < u[i]] for i, cs in enumerate(o['records'])], rounds=u, tape_full_rows=full)

    def state_of(self, o):
        return (o['Z'],) + o['tape']

    # ---- the talker ----
    def talk(self, state, batch, lesion=None, return_modes=False, temperature=0.0, generator=None):
        """The writer asked for the answer (mode 1) over [the CURRENT batch's prompt; the state's tape] with the state's Z (the tape is the reasoner's own work, so a donor's
        tape comes with its state). return_modes: also a mode per row (always 2: one writer, no modes)."""
        Z, Xt, idt, vis = state[:4]
        X, xm = self.read(batch, talker=True)
        Xc, cmask, cids = torch.cat([X, Xt.to(X.dtype)], 1), torch.cat([xm, vis.bool()], 1), torch.cat([batch['prompt_ids'], idt.long()], 1)
        T, le = X.shape[1], Xt.shape[1] // self.tape
        outs, _ = self.writer.greedy(Z, torch.ones(Z.shape[:2], dtype=torch.bool, device=Z.device), Xc, cmask, cids, torch.ones(Z.shape[0], dtype=torch.long, device=Z.device),
                                     nocopy=lesion == 'nocopy', ckeys=self.ckeys(Xc.shape[1], T, le, cmask), temperature=temperature, generator=generator)
        out = [self.vocab.decode(o) for o in outs]
        return (out, [2] * len(out)) if return_modes else out

    @torch.no_grad()
    def generate(self, batch, lesion=None):
        if lesion in ('ctl27',):
            return self.talk(self.state(batch, lesion=lesion), batch)
        name, arg = self.check_lesion(lesion)
        if name in ('noexec', 'opswap', 'nocopy'):
            return self.talk(self.state(batch, lesion=name), batch, lesion=name)
        st = self.state(batch, arg if name == 'loops' else None)
        if name == 'zero_state':
            st = (torch.zeros_like(st[0]),) + tuple(st[1:])
        elif name == 'shuffle_state':
            st = (st[0].roll(1, 0),) + tuple(st[1:])
        return self.talk(st, batch)

    # ---- ST1 ----
    @torch.no_grad()
    def sample_traces(self, batch, temperature, generator):
        """ST1: a free run whose calls and answer are SAMPLED from the writer -> per row dict(calls=[(call text, reply)], answer)."""
        o = self.run(batch, temperature=temperature, generator=generator)
        ans = self.talk(self.state_of(o), batch, temperature=temperature, generator=generator)
        return [dict(calls=[(txt, rep) for _, txt, rep in o['records'][i]], answer=ans[i]) for i in range(len(ans))]

    def trace_loss(self, batch, traces):
        """ST1: the normal loss with the given traces (the model's own calls, the tool's real replies, its answer) in place of progtext's."""
        assert len(traces) == len(batch['rows'])
        return self._loss(batch, [self.trace_gold(t) for t in traces])

    # ---- loss ----
    def loss(self, batch):
        return self._loss(batch, self.train_golds(batch['rows']))

    def _loss(self, batch, golds):
        dev, B = batch['prompt_ids'].device, len(batch['rows'])
        Ls = [len(x['texts']) for x in golds]
        sched, last = self.plan(Ls, B, dev)                                     # B3's schedule: the calls' rounds
        K = KS[int(torch.randint(len(KS), (1,)))]
        n = max(K, int(last.max()) + 1)
        g = dict(L=Ls, ids=[x['ids'] for x in golds], tape=[x['tape'] for x in golds], has=torch.tensor([bool(L) for L in Ls], device=dev))
        per = []

        def keep_round(t, st):
            per.append((t, st['Z']))
            return False

        o = self.loop(batch, n, g=g, sched=sched, each=keep_round)
        Xt, idt, vis = o['tape']
        T, le = o['X'].shape[1], o['le']
        Xc, cmask, cids = torch.cat([o['X'], Xt.to(o['X'].dtype)], 1), torch.cat([o['xm'], vis], 1), torch.cat([batch['prompt_ids'], idt], 1)
        ck = self.ckeys(Xc.shape[1], T, le, cmask)
        te = ByteWriter.teacher([x['ans_ids'] for x in golds], cids, cmask, self.WCAP, BOS, EOS)       # fixed over the rounds t >= last: the whole tape is visible
        acc, cnt = torch.zeros(B, device=dev), torch.zeros(B, device=dev)
        right = torch.zeros(len(per), B, dtype=torch.bool, device=dev)
        zs, share = [], None
        for t, Z in per:
            zs.append(self.ln_z(Z[:, 1].detach()))          # the stop head reads the state detached: its loss trains ln_z and the head, never the loop
            ok = last <= t                                                     # the writer is asked "answer" at every round t >= the row's last call round
            if not ok.any():
                continue
            si = ok.nonzero()[:, 0]
            full = bool(ok.all())
            pk = lambda x: x if full else x[si]
            args = (pk(Z), pk(Xc), pk(cmask), pk(cids), ck if ck is None or ck.dim() == 2 or full else ck[si], pk(te['inp']), pk(te['tgt']), pk(te['fb']))
            if self.training and torch.is_grad_enabled() and t >= CKPT_FROM:
                nll, rt, sn, sd = checkpoint(self.ans_pass, *args, use_reentrant=False)
            else:
                nll, rt, sn, sd = self.ans_pass(*args)
            acc = acc + torch.zeros(B, device=dev).index_add(0, si, nll.float())
            cnt = cnt + ok.float()
            right[t, si] = rt
            if t == n - 1:
                share = sn.sum() / sd.sum().clamp(min=1)
        lans = (acc / cnt.clamp(min=1)).sum() / B
        y = (settled(right) if self.label == 'settled' else right).to(dev).float()
        logit = self.stop(torch.stack(zs)).float()[..., 0]
        lstop = F.binary_cross_entropy_with_logits(logit, y)
        w_stop = 1.0 if self.label == 'right' or n >= self.cap else 0.0         # H1's rule: 'settled' needs the whole turn (B13-2)
        total = o['lcall'] + lans + w_stop * lstop
        aux = dict(prog=o['lcall'], call=o['lcall'], ans=lans, stop=lstop, stop_y=y.mean(), stop_acc=((logit >= 0).float() == y).float().mean(), right_last=right[-1].float().mean(),
                   rounds=float(n), copy_share=share, stop_w=w_stop, call_acc=o['call_hit'] / max(o['call_n'], 1), eos_acc=o['eos_hit'] / max(o['eos_n'], 1))
        aux.update({f'plan_{k}': float(v) for k, v in self.plan_stats.items()})
        if self.ans_drill:
            aux['drill_share'] = sum(x['drill'] for x in golds) / B
        return total, {k: v.detach() if torch.is_tensor(v) else v for k, v in aux.items()}

    # ---- extra evals ----
    def call_evals(self, out, prows, batches, ctx):
        """Tool.extra_evals' call accuracy, on the call TEXT: teacher forced (the gold tape, calls at rounds 1..L, the writer asked after each round) and free run (the learned
        stop); a call is right when its text equals the gold call text, `op` = its first word (the tool) equals, a program is right when every call is right (free run: and no
        other call is written). Into out['op_acc'] (same keys as Tool's) and out['call_text'] (the teacher-forced stop-calling accuracy: EOS first after the last call)."""
        from custom_io.evalx import is_hit, subsample
        dev, amp = ctx['device'], ctx['amp']
        sl = subsample(prows, 400)
        acc = {m: dict(calls=0, names=0, n_calls=0, prog=0) for m in ('teacher_forced', 'free_run')}
        fr_ans, eos = 0, [0, 0]
        for b in batches(sl):
            rows, B = b['rows'], len(b['rows'])
            golds = self.plain_golds(rows)
            Ls = [len(x['texts']) for x in golds]
            sched, last = self.plan(Ls, B, dev)
            g = dict(L=Ls, ids=[x['ids'] for x in golds], tape=[x['tape'] for x in golds], has=torch.tensor([bool(L) for L in Ls], device=dev))
            with amp():
                o = self.loop(b, max(max(Ls) + 1, 2), g=g, sched=sched, rec=True)
            a, okrow = acc['teacher_forced'], [True] * B
            for i, k, good, name in o['crec']:
                a['calls'] += good; a['names'] += name; a['n_calls'] += 1
                okrow[i] &= good
            a['prog'] += sum(okrow)
            eos[0] += o['eos_hit']; eos[1] += o['eos_n']
            with amp():
                o = self.run(b)
                ans = self.talk(self.state_of(o), b)
            a = acc['free_run']
            for i, (r, gd) in enumerate(zip(rows, golds)):
                rec = o['records'][i]
                good = True
                for k, txt in enumerate(gd['texts']):
                    w = k < len(rec) and rec[k][1] == txt
                    a['calls'] += w; a['names'] += k < len(rec) and rec[k][1].split(' ')[0] == txt.split(' ')[0]; a['n_calls'] += 1
                    good &= w
                a['prog'] += good and len(rec) == len(gd['texts'])
                fr_ans += is_hit(ans[i], r)
        n = len(sl)
        pc = lambda x, d: 100 * x / max(d, 1)
        out['op_acc'] = {m: dict(op=pc(a['names'], a['n_calls']), call=pc(a['calls'], a['n_calls']), program=pc(a['prog'], n)) for m, a in acc.items()}
        out['op_acc']['n'] = n
        out['op_acc']['free_run']['answer'] = pc(fr_ans, n)
        out['call_text'] = dict(n_calls=acc['teacher_forced']['n_calls'], stop_calling=pc(eos[0], eos[1]), n_stop_rounds=eos[1])

    def copy_gate_eval(self, rows, ctx):
        return dict(dropped="B3G2 has no GEN pointer-generator gate to read: the writer's copy share is extra['g2']['agreement']['copy_share'] and the train log's copy_share")

    @torch.no_grad()
    def extra_evals(self, ctx):
        out = dict(counters_at_start=capcount.snapshot())
        out.update(super().extra_evals(ctx))
        out['g2'] = self.g2_evals(ctx)
        out['g2']['counters_at_start'] = out.pop('counters_at_start')
        return out

    @torch.no_grad()
    def g2_evals(self, ctx):
        """Group 2's sealed items beyond Tool / H1 / B3's evals (those run first and are in extra[...]): the trace counters (and the capcount snapshot when the evals began),
        the writer's size and copy share, teacher-forced 'right' vs real greedy decoding on dev rows (the stop label's honesty), exact match on the dev rows the inverse rewrite
        touches (B3G2-4: rows with a 'hidden' operand under as_written, rows whose calls change, all rows of the families that have a hidden row; and the sealed 300-row
        missing_dev file when ctx['missing_dev'], $B3G2_MISSING_DEV or DATA/missing_dev.jsonl exists), and the inventory counts (hidden rows and their exact match, note rows)."""
        import os
        from custom_io.data import DEV_SPLITS, collate, Dataset, load_rows, to_device
        from custom_io.evalx import _dev_rows, evaluate, is_hit, subsample
        was = self.training
        self.eval()
        dev, bs, amp = ctx['device'], ctx['batch_size'], ctx['amp']
        out = dict(as_written=self.as_written, writer=dict(params=self.writer.size(), wcap=self.WCAP, refine=self.refine, inner=self.writer.inner, d=self.d),
                   train_counts=dict(trace=dict(self.trace_stats), drill=dict(self.drill_stats), plan=dict(self.plan_stats)), free_unended=self.free_stats['unended'])
        rows, seen = [], set()
        srcs = [_dev_rows(ctx['data'], sp, None) for sp in DEV_SPLITS] + ([_dev_rows(ctx['big'], 'in_dist', None)] if ctx.get('big') else [])
        for rs in srcs:
            for r in rs:
                if r['id'] not in seen:
                    seen.add(r['id'])
                    rows.append(r)
        hidden, differ, notes, unread, withsteps = [], [], 0, [], 0
        for r in rows:
            if not r.get('steps'):
                continue
            withsteps += 1
            s1, _ = progtext.steps_of(r, True)
            s0, _ = progtext.steps_of(r, False)
            if s1 is None:
                unread.append(r['id'])
                continue
            notes += any(c['op'] == 'note' for c in s1)
            if any('hidden' in (c.get('a_src'), c.get('b_src')) for c in s1):
                hidden.append(r)
            if s0 != s1:
                differ.append(r)
        fams = sorted({r['family'] for r in hidden})
        famrows = [r for r in rows if r['family'] in fams]
        out['dev_rows'] = dict(n=len(rows), with_steps=withsteps, unreadable=len(unread), unreadable_ids=unread[:20], note_rows=notes, hidden_rows=len(hidden),
                               differ_rows=len(differ), hidden_families=fams)

        def batches(rs, size=bs):
            for s in range(0, len(rs), size):
                yield to_device(collate([Dataset(rs[s:s + size], self.vocab, strict=False)[i] for i in range(len(rs[s:s + size]))]), dev)

        def exact(rs):
            if not rs:
                return dict(n=0, exact=None)
            with amp():
                r = evaluate(self, rs, bs, dev, None)
            return dict(n=r['n'], exact=r['exact'], by_family=r['by_family'])
        out['inverse'] = dict(hidden=exact(hidden), differ=exact(differ), families=dict(exact(famrows), families=fams))
        path = ctx.get('missing_dev') or os.environ.get('B3G2_MISSING_DEV') or os.path.join(ctx['data'], 'missing_dev.jsonl')
        if os.path.exists(path):
            md = load_rows(path)
            out['inverse']['missing_dev'] = dict(exact(md), path=path, hidden=sum(any('hidden' in (c.get('a_src'), c.get('b_src')) for c in (progtext.steps_of(r, True)[0] or [])) for r in md))
        sample = subsample(rows, 600)
        cells = dict(both=0, tf_only=0, greedy_only=0, neither=0)
        sn = sd = 0.0
        for b in batches(sample):
            with amp():
                o = self.run(b)
                st = self.state_of(o)
                ans = self.talk(st, b)
                nll, rt, a, c = self.forced_answer(st, b, [r['answer'] for r in b['rows']])
            sn, sd = sn + float(a.sum()), sd + float(c.sum())
            for i, r in enumerate(b['rows']):
                tf, gr = bool(rt[i]), norm(ans[i]) == norm(r['answer'])
                cells['both' if tf and gr else 'tf_only' if tf else 'greedy_only' if gr else 'neither'] += 1
        n = max(len(sample), 1)
        out['agreement'] = dict(n=len(sample), agree=100 * (cells['both'] + cells['neither']) / n, cells=cells, tf_right=100 * (cells['both'] + cells['tf_only']) / n,
                                greedy_right=100 * (cells['both'] + cells['greedy_only']) / n, copy_share=sn / max(sd, 1.0), copy_bytes=sd)
        self.train(was)
        return out
