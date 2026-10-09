"""B3 group 1 (architecture/B3-GROUP1-BUILD-2026-10-09.md): H1R (T1SDR + the learned stop, model 'tool_h1') with three switches, all default off, so 'b3' with no
switches is H1R exactly (tested bit for bit against 17a356e62). Nothing in the switches is a rule: they change what the model may do and what it is shown.
- eg_embed (Part A, a Tool switch): Gemma reads the question as in G1's EGE. The calculator's entries are read by the letter reader alone (Tool.read_texts), so
  Gemma sees each question once per batch (FrozenEG.encode's memo shares the pass between run and talk). Gemma's 271,002,624 weights are frozen and counted in
  size()['whole'] only. Ledger creates the Gemma adapter before the tool's new weights, so B3 at a seed does not start identical to T1SDR at that seed.
- any_round (Part B): a calculator call may be written after ANY round t >= 1 (up to the cap of 32), not only call k at round k + 1. The op head (control 0)
  decides each round, as today; a call goes into the row's next free tape entry (TAPE = max(16, n_res) entries) and its reply is visible from round t + 1. A call
  when the tape is full is not run and is counted (tape_full). Training is teacher forced on a schedule of rounds per row: calls at rounds 1..L, or (with
  probability gap_p per row, drawn from the model's own random.Random so torch's draws and the data order do not change) each call preceded by g extra thinking
  rounds, g uniform on {0, 1, 2}. Op loss: the gold op at each call round, NOOP at every round after the row's last call, NOTHING at gap rounds (no label ever
  says 'wait'); cell, span and gate losses at call rounds; the answer loss from the last call round on; stop labels unchanged. steps / calls are call-ordered,
  so the T1SDR evals (call accuracy, tool off, opswap replay, write_copy) work unchanged. The learned stop is H1's.
- tok_think (a Ledger switch, three lines in Tool.run and in loop()): the thinker reads one spot per Gemma token. Off by default.
Learned: everything H1R learns, plus tape_emb / e_s rows past N_RES (any_round). Hand-written: the calculator, the gap schedule (training only), the tape size."""
import random
import numpy as np
import torch
import torch.nn.functional as F
from custom_io.models.ledger import N_CTRL, N_REG, N_RES
from custom_io.models.tool import LE, NAMES, Tool, calc, entry
from custom_io.models.tool_h1 import CAP, ToolH1

TAPE_MIN = 16           # K1's 16 calls (the inventory's E5 safety cap)
GAPS = (0, 1, 2)
FAR = 10 ** 6
BUCKETS = ((0, 280), (281, 700), (701, 1300), (1301, 2000))


def bucket(n):
    return next((f'{a}-{b}' for a, b in BUCKETS if n <= b), f'{BUCKETS[-1][1]}+')


class B3(ToolH1):
    def __init__(self, vocab, any_round=False, gap_p=0.0, **kw):
        assert 0.0 <= gap_p <= 1.0 and (any_round or not gap_p), 'gap_p schedules calls at gap rounds: it needs any_round'
        if any_round:
            kw['tape'] = max(TAPE_MIN, N_RES)
        super().__init__(vocab, **kw)
        self.any_round, self.gap_p = bool(any_round), float(gap_p)
        self._gap_rng = random.Random(f'gap|{torch.initial_seed()}')            # its own stream (train.py seeds torch first), as ans_drill
        self.plan_stats = dict(rows=0, gapped=0, fallback=0)
        self.last_tape_full = None

    # ---- the schedule (training) ----
    def plan(self, g, B, dev):
        if not self.any_round:
            return super().plan(g, B, dev)
        sched = np.full((B, N_RES), -1, np.int64)
        for i, L in enumerate((g['op'] > 0).sum(1).tolist()):
            if not L:
                continue
            self.plan_stats['rows'] += 1
            gs = [0] * L
            if self.gap_p and self.training and self._gap_rng.random() < self.gap_p:
                gs = [self._gap_rng.choice(GAPS) for _ in range(L)]
                if L + sum(gs) + 1 > CAP:       # the schedule would not fit in the 32 rounds: this row keeps today's
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

    def run_tf(self, batch, n, g, sched, each):
        return self.loop(batch, n, gold=g, sched=sched, each=each) if self.any_round else super().run_tf(batch, n, g, sched, each)

    def op_losses(self, o, g, B):
        if not self.any_round:
            return super().op_losses(o, g, B)
        sched = o['sched']
        last = sched.max(1).values.clamp(min=0)
        w_row = torch.where(g['has'], 1.0, self.w_noop)
        lop, hits, tot = 0.0, 0, 0
        for t, lg in enumerate(o['round_lop'], 1):
            at = sched == t
            lab = (g['op'] * at).sum(1)                                  # the gold op at a call round, NOOP elsewhere
            m = at.any(1) | (t > last)                                   # call rounds and the rounds after the last call; gap rounds carry no label
            lg = lg.float()
            lop = lop + (F.cross_entropy(lg, lab, reduction='none') * w_row * m).mean()
            on = m & g['has']
            hits, tot = hits + ((lg.argmax(-1) == lab) & on).sum(), tot + on.sum()
        _, lcall, _, _ = self.call_loss(o['steps'], g, B, ops=False)
        dev = g['op'].device
        return torch.as_tensor(lop, device=dev), lcall, torch.as_tensor(hits, device=dev), torch.as_tensor(tot, device=dev)

    def loss(self, batch):
        total, aux = super().loss(batch)
        if self.any_round:
            aux.update({f'plan_{k}': float(v) for k, v in self.plan_stats.items()})
        return total, aux

    # ---- the loop ----
    def loop(self, batch, loops=None, gold=None, lesion=None, oracle=None, each=None, sched=None, force=None):
        """Tool.run with calls at any round. gold: teacher forcing on `sched` ([B, N_RES] call rounds, -1 = none; default call k at round k + 1).
        force = (gold, sched): a free run (the tape written as it goes, LE-wide entries) whose calls are the gold ones at the scheduled rounds (tests).
        Else the op head decides every round t >= 1. steps are call-ordered: steps[k] = (op logits, cells, span) of each row's k-th call (a NOOP step for a row
        with no k-th call); round_lop = the op logits of rounds 1..n-1 (teacher forcing: the op loss); cround [B, TAPE] = the round of each call."""
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
        Xk, km = self.tok_spots(X, xm, batch) if self.tok_think else (X, xm)
        kvx = [b.kv_of(Xk + self.src.weight[1]) for b in self.core]
        kvs0 = [b.kv_of(S0 + self.src.weight[0]) for b in self.core]
        tf = gold is not None
        if force is not None:
            gold_f, sched = force
        if tf and sched is None:
            sched = torch.where(gold['op'] > 0, torch.arange(1, N_RES + 1, device=dev)[None], torch.full((1, N_RES), -1, device=dev))
        if tf:
            K = max(1, int((gold['op'] > 0).sum(1).max()))
            texts, le = [row[:K] for row in gold['tape']], None
        else:
            K, texts, le = self.tape, [[''] * self.tape for _ in range(B)], LE
        Xt, idt, mt, le = self.tape_of(texts, dev, le)
        ent = torch.arange(K * le, device=dev) // le
        kvt = [b.kv_of(Xt + self.src.weight[1]) for b in self.core]
        Z = torch.cat([self.ctrl.weight, self.reader.place.weight[:N_REG]]).expand(B, -1, -1)
        n = self.n_loops if loops is None else loops
        shown = torch.zeros(B, self.tape, dtype=torch.bool, device=dev)
        nk = torch.zeros(B, dtype=torch.long, device=dev)
        cround = torch.full((B, self.tape), FAR, dtype=torch.long, device=dev)
        calls, cbuf, rl, full_ev = [[] for _ in range(B)], {}, [], []
        kvs_of = None
        for t in range(n):
            ts = min(t, self.n_loops - 1)
            vis = mt & shown[:, :K].gather(1, ent.expand(B, -1))
            if kvs_of is not kvt:
                kvs, kvs_of = [torch.cat([a, c], 3) for a, c in zip(kvs0, kvt)], kvt
            mask = torch.cat([valid, vis, km], 1)
            Z = self.think(Z + self.step_emb.weight[ts], kvs, kvx, mask, t)
            if lesion == 'ctl27':
                Z = torch.cat([Z[:, :2], torch.zeros_like(Z[:, 2:N_CTRL]), Z[:, N_CTRL:]], 1)
            if t >= 1:
                z = self.ln_z(Z[:, 0])
                lop = self.op_head(z)
                if tf:
                    rl.append(lop)
                if tf or force is not None:
                    at = sched == t
                    call, kk = at.any(1), at.int().argmax(1)
                    opv = (gold if tf else gold_f)['op'].gather(1, kk[:, None])[:, 0] * call
                else:
                    opv = lop.argmax(-1)
                    want = opv > 0
                    full = want & (nk >= self.tape)
                    full_ev += [(i, t) for i in full.nonzero()[:, 0].tolist()]
                    call, kk = want & ~full, nk
                if call.any():
                    p, _ = self.gen_copy(self.cells(z), torch.cat([X, Xt], 1), torch.cat([xm, vis], 1), torch.cat([batch['prompt_ids'], idt], 1), lesion == 'nocopy')
                    st = (lop, p)
                    if self.span_copy:
                        mc = torch.cat([xm, vis], 1)
                        ks, wa, wb = self.span_keys(torch.cat([X, Xt], 1), T, le, mc), self.W_a(z), self.W_b(z)
                        st = st + (dict(la=self.ptr(self.q_s(wa), ks, mc), lb=self.ptr(self.q_s(wb), ks, mc), ga=self.g_s(wa)[:, 0].float(),
                                        gb=self.g_s(wb)[:, 0].float(), ids=torch.cat([batch['prompt_ids'], idt], 1), m=mc, T=T, le=le),)
                    for k in sorted(set(kk[call].tolist())):
                        if k < N_RES:
                            self.place(cbuf, k, call & (kk == k), st, B, dev, idt, le)
                    rows = call.nonzero()[:, 0]
                    cround[rows, kk[rows]] = t
                    if tf:
                        shown[rows, kk[rows]] = True
                    else:
                        wr = [gold_f['rowg'][i][1][int(kk[i])] if bool(call[i]) else None for i in range(B)] if force is not None else self.written(st)
                        op, new_k = opv.tolist(), {}
                        for i in rows.tolist():
                            sa, sb = wr[i]
                            if oracle is not None:
                                r = oracle(i, t, (NAMES[op[i]], sa, sb))
                            else:
                                r = '?' if lesion == 'noexec' else calc(NAMES[op[i]], sa, sb, swap=lesion == 'opswap')
                            calls[i].append((t, NAMES[op[i]], sa, sb, r))
                            new_k.setdefault(int(kk[i]), [''] * B)[i] = entry(NAMES[op[i]], sa, sb, r)
                        Xt, idt, mt = Xt.clone(), idt.clone(), mt.clone()
                        for k, new in new_k.items():
                            sel = torch.tensor([bool(x) for x in new], device=dev)
                            Xn, inn_, mn = self.read_texts(new, dev, le)
                            Xn = (Xn + self.tape_emb.weight[k].to(Xn.dtype)) * mn[..., None]
                            sl = slice(k * le, (k + 1) * le)
                            Xt[:, sl] = torch.where(sel[:, None, None], Xn.to(Xt.dtype), Xt[:, sl])
                            idt[:, sl] = torch.where(sel[:, None], inn_, idt[:, sl])
                            mt[:, sl] = torch.where(sel[:, None], mn, mt[:, sl])
                            shown[sel, k] = True
                        nk = nk + call.long()
                        kvt = [b.kv_of(Xt + self.src.weight[1]) for b in self.core]
            if each is not None and each(t, dict(Z=Z, X=X, xm=xm, Xt=Xt, idt=idt, mt=mt, shown=shown, ent=ent, K=K, Kw=Kw, wvalid=wvalid)):
                break
        vis = mt & shown[:, :K].gather(1, ent.expand(B, -1))
        zf = self.ln_z(Z[:, 1])
        ref = dict(ids=torch.cat([batch['prompt_ids'], idt], 1), le=le)
        steps = [tuple(cbuf[k]) if k in cbuf else self.noop_step(B, dev, ref) for k in range(max(1, int(gold['op'].gt(0).sum(1).max())) if tf else N_RES)]
        out = dict(R=Z[:, N_CTRL:], lmode=self.mode_head(zf), lword=self.ptr(self.q_word(zf), Kw, wvalid), wvalid=wvalid, steps=steps,
                   X=torch.cat([X, Xt], 1), xm=torch.cat([xm, vis], 1), ids=ref['ids'], tape=(Xt, idt, vis), calls=calls, le=le, K=K,
                   round_lop=rl, sched=sched, cround=cround, tape_full=full_ev)
        if self.span_copy:
            out['qn'] = self.q_s(zf)
        return out

    def place(self, cbuf, k, rows, st, B, dev, idt, le):
        """Put this round's step of the `rows` that make their k-th call into the call-ordered buffer k (a NOOP step elsewhere)."""
        buf = cbuf.get(k)
        if buf is None:
            buf = cbuf[k] = list(self.noop_step(B, dev, dict(ids=st[2]['ids'] if len(st) > 2 else idt, le=le)))
        buf[0] = torch.where(rows[:, None], st[0].to(buf[0].dtype), buf[0])
        buf[1] = torch.where(rows[:, None, None], st[1].to(buf[1].dtype), buf[1])
        if len(st) > 2:
            a, b = buf[2], st[2]
            for f in ('la', 'lb'):
                a[f] = torch.where(rows[:, None], b[f].to(a[f].dtype), a[f])
            for f in ('ga', 'gb'):
                a[f] = torch.where(rows, b[f].to(a[f].dtype), a[f])
            a['ids'], a['m'] = torch.where(rows[:, None], b['ids'], a['ids']), torch.where(rows[:, None], b['m'], a['m'])

    # ---- the run ----
    def run(self, batch, loops=None, gold=None, lesion=None, rounds=False, oracle=None, each=None, force=None):
        if not self.any_round:
            assert force is None
            return super().run(batch, loops, gold, lesion, rounds, oracle, each)
        assert not rounds
        B, dev = batch['prompt_ids'].shape[0], batch['prompt_ids'].device
        if gold is not None or loops is not None or each is not None or force is not None:        # forced: the stop head ignored
            o = self.loop(batch, loops, gold, lesion, oracle, each, None, force)
            if gold is None and each is None:
                self.last_rounds = [self.n_loops if loops is None else loops] * B
                self.last_tape_full = [any(i == j for j, _ in o['tape_full']) for i in range(B)]
            return o
        used = torch.zeros(B, dtype=torch.long, device=dev)
        keep = []

        def stop_here(t, st):
            zf, s = self.round_state(st)
            new = (used == 0) & ((self.p_stop(zf) >= 0.5) | (t + 1 >= self.cap))
            if new.any():
                if not keep:
                    keep.extend(x.clone() for x in s)
                else:
                    for x, y in zip(keep, s):
                        x[new] = y[new].to(x.dtype)
                used[new] = t + 1
            return bool((used > 0).all())

        o = self.loop(batch, self.cap, None, lesion, oracle, stop_here)
        R, Xt, idt, vis, lmode, lword, *qn = keep
        u = used.tolist()
        T = batch['prompt_ids'].shape[1]
        steps = []
        for k, st in enumerate(o['steps']):               # call k counts only for rows still running at its round (round < rounds used)
            lop, off = st[0], o['cround'][:, k] >= used
            if off.any():
                lop = lop.clone()
                lop[off] = self.noop_step(1, dev, o)[0].to(lop.dtype)
            steps.append((lop,) + tuple(st[1:]))
        full = [False] * B
        for i, t in o['tape_full']:
            full[i] |= t < u[i]
        self.last_rounds, self.last_tape_full = u, full
        return dict(o, **({'qn': qn[0]} if qn else {}), R=R, lmode=lmode, lword=lword, X=torch.cat([o['X'][:, :T], Xt.to(o['X'].dtype)], 1),
                    xm=torch.cat([o['xm'][:, :T], vis], 1), ids=torch.cat([batch['prompt_ids'], idt], 1), tape=(Xt, idt, vis), steps=steps,
                    calls=[[c for c in cs if c[0] < u[i]] for i, cs in enumerate(o['calls'])], rounds=u, tape_full_rows=full)

    # ---- extra evals ----
    @torch.no_grad()
    def extra_evals(self, ctx):
        out = super().extra_evals(ctx)
        out['b3'] = self.b3_evals(ctx)
        return out

    @torch.no_grad()
    def b3_evals(self, ctx):
        """Report-only: per dev split, exact match per input-length bucket (<= 280, 281-700, 701-1,300, 1,301-2,000 letters; a bucket with no rows is left out),
        the rounds at which calls happen (histogram), calls per row (histogram), rows with a call refused by a full tape, and the training-time schedule counts."""
        from custom_io.data import DEV_SPLITS, collate, Dataset, to_device
        from custom_io.evalx import _dev_rows, is_hit
        was = self.training
        self.eval()
        dev, bs, amp = ctx['device'], ctx['batch_size'], ctx['amp']
        out = dict(any_round=self.any_round, gap_p=self.gap_p, tape=self.tape, plan=dict(self.plan_stats), splits={})
        for sp in DEV_SPLITS:
            rows = _dev_rows(ctx['data'], sp, None)
            ok, at, per, nfull = {}, {}, {}, 0
            for s in range(0, len(rows), bs):
                ch = rows[s:s + bs]
                b = to_device(collate([Dataset(ch, self.vocab, strict=False)[i] for i in range(len(ch))]), dev)
                with amp():
                    o = self.run(b)
                    ans = self.talk(self.state_of(o), b)
                nfull += sum(self.last_tape_full or [])
                for r, a, cs in zip(ch, ans, o['calls']):
                    e = ok.setdefault(bucket(len(r['prompt'])), [0, 0])
                    e[0] += 1
                    e[1] += is_hit(a, r)
                    per[str(len(cs))] = per.get(str(len(cs)), 0) + 1
                    for c in cs:
                        at[str(c[0])] = at.get(str(c[0]), 0) + 1
            out['splits'][sp] = dict(n=len(rows), by_length={k: dict(n=v[0], exact=100 * v[1] / v[0]) for k, v in sorted(ok.items())},
                                     call_rounds=dict(sorted(at.items(), key=lambda x: int(x[0]))), calls_per_row=dict(sorted(per.items(), key=lambda x: int(x[0]))),
                                     tape_full_rows=nfull)
        self.train(was)
        return out
