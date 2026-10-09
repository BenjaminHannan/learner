"""H1 (roadmap 2d; sealed spec /mnt/project-files/architecture/redesign-ideas-2026-10-07.md section 8b; PASS-MARKS.md addendum 21): T1 where the
model picks how many thinking rounds a turn gets, instead of a fixed 8. Everything else is T1 (model 'tool', same init order, so every T1 weight
starts identical at the same seed); the one new part is the stop head, created last.

A turn = answering one question. Rounds = T1's controller iterations: round t (t = 1..7) writes T1's call t (or NOOP), exactly as in T1; rounds
8..32 are thinking only (T1's tape holds 7 entries; K1 lifts that later). The round embedding stays at T1's last one after round 8, as T1's loops:K does.
- Per-round readout (spec (a)): after EVERY round the answer heads (mode, word pointer, GEN pointer-generator over the prompt and the entries
  written so far) read the state, each with T1's normal loss; each row's mean over its rounds t >= L (L = the row's gold calls, so its calls
  are on the tape) is the answer loss, weight 1.0. The call heads keep T1's rounds 1..7 and losses.
- Stop head (spec (b)): stop = Linear(d, 1) (257 params) on ln_z(control 1) after each round (the state the mode and word heads read), trained by
  BCE on a label from the model's OWN readout: label 'right' (the first sealed spec, the default) = this round's greedy answer equals the target
  answer; label 'settled' (cfg {"label": "settled"}, SEALED for the H1 screen by amendment 1, section 8c) = right now, or no later round of this
  turn (up to the cap, 32) is right, so the model also learns to stop when more rounds will not help. A batch of n < 32 rounds cannot
  see the later rounds: there, 'no later round is right' and 'the right round comes after n' look the same, and the label would say stop.
  So the 'settled' stop loss counts only in batches that ran the whole turn (n >= 32, the K = 32 draws: about 1 batch in 4, about half
  of all trained rounds); in shorter batches its weight is 0 (logged as stop_w). K is drawn before any row is read, so which batches
  count never depends on how a row did. 'right' reads one round at a time and counts in every batch. The stop head's input is
  detached, so the stop loss never moves the loop (the spec's note on jointly trained halt gates).
- Run rule (inference, `generate()` with no loops lesion): the turn ends after the first round with sigmoid(stop) >= 0.5 (P_STOP, fixed), at
  least 1 round, hard cap 32 (CAP). No other threshold exists. The batch keeps running until every row has stopped (rows are independent, so
  this only costs time); each row's state, tape and calls are the ones at its own stop round. Rounds used per row: self.last_rounds.
- Training rounds (spec (c)): each batch draws K from {4, 8, 16, 32} (torch's RNG) and runs n = max(K, longest gold program in the batch + 1)
  rounds, so every row's program and answer are trained in every batch, as in T1 (disclosed: K = 4 then mostly runs 8). Rounds 9..32 are
  gradient-checkpointed (same values, less memory); answer heads are checkpointed every round.
- loops:K (lesion and forced runs) = exactly K rounds with the stop head ignored; loops:8 is T1's own computation (tested).
Size (vocab 108, S cfg): T1's 3,277,393 + 257 = 3,277,650.

H1R (H1 on T1SDR, cfg {"label": "settled", "span_copy": true, "span_idx": true, "span_end": true, "ans_drill": 0.25}; 3,314,132 + 257 = 3,314,389):
everything not H1 is T1SDR (the stop head is still created last). The span answer is read every round too: the round state also carries qn =
q_s(ln_z(control 1)), kept at each row's own stop round; the per-round answer loss adds the span answer term (the answer pointer over the prompt and
the tape visible that round) and GEN covers every non-WORD row, as in T1SDR; the call-writing span losses (calls and the span stop head) are T1SDR's,
once. Stop labels read each round's greedy answer including the span (mode 0), against the row's own target (a drill row's drawn answer). With
span_copy, H1's stop loss is logged as 'halt' ('stop' is the span stop head's)."""
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.checkpoint import checkpoint
from custom_io.data import EOS, word_spans
from custom_io.models.ledger import N_CTRL, N_RES, W_MAX
from custom_io.models.tool import CELLS, Tool

CAP = 32
KS = (4, 8, 16, 32)
P_STOP = 0.5
LABELS = ('right', 'settled')


def norm(s):
    return ' '.join(s.strip().lower().split())


def settled(right):
    """right [n, B] bool -> label [n, B]: right now, or no later round is right."""
    later = torch.zeros_like(right)
    if right.shape[0] > 1:
        later[:-1] = right.flip(0).cummax(0).values.flip(0)[1:]
    return right | ~later


class ToolH1(Tool):
    LOOP_SWEEP = (0, 1, 2, 8, 16, 32)       # train.lesion_names: loops:8 = T1's own count, loops:32 = H-a

    def __init__(self, vocab, label='right', **kw):
        assert label in LABELS, label
        super().__init__(vocab, **kw)
        self.label, self.cap = label, CAP
        self.stop = nn.Linear(self.d, 1)                                  # created last: every T1 weight starts as in T1
        nn.init.normal_(self.stop.weight, std=0.02)
        nn.init.zeros_(self.stop.bias)
        self.last_rounds = None

    def think(self, Z, kvs, kvx, mask, t):
        if self.training and torch.is_grad_enabled() and t >= self.n_loops:
            return checkpoint(super().think, Z, kvs, kvx, mask, t, use_reentrant=False)
        return super().think(Z, kvs, kvx, mask, t)

    def round_state(self, st):
        """The state after a round -> (zf, T1's talker state (R, Xt, idt, vis, lmode, lword))."""
        Z = st['Z']
        vis = st['mt'] & st['shown'][:, :st['K']].gather(1, st['ent'].expand(Z.shape[0], -1))
        zf = self.ln_z(Z[:, 1])
        s = (Z[:, N_CTRL:], st['Xt'], st['idt'], vis, self.mode_head(zf), self.ptr(self.q_word(zf), st['Kw'], st['wvalid']))
        return zf, s + ((self.q_s(zf),) if self.span_copy else ())            # H1R: + qn, the answer pointer's query (Tool.state_of's state[6])

    def noop_step(self, B, dev, ref=None):
        """(op logits that pick NOOP, empty cells) for a call a stopped row never makes; H1R: + a span dict that copies nothing (gates off).
        ref = the run's output, for the span layout."""
        lop = torch.full((B, self.op_head.out_features), -1e4, device=dev)
        lop[:, 0] = 1e4
        st = (lop, torch.zeros(B, 2 * CELLS, self.reader.tok.weight.shape[0], device=dev))
        if self.span_copy and ref is not None:
            T, le = ref['ids'].shape[1] - self.tape * ref['le'], ref['le']
            st += (dict(la=torch.zeros(B, T + self.tape * le, device=dev), lb=torch.zeros(B, T + self.tape * le, device=dev), ga=torch.full((B,), -1e4, device=dev),
                        gb=torch.full((B,), -1e4, device=dev), ids=torch.zeros(B, T + self.tape * le, dtype=torch.long, device=dev),
                        m=torch.zeros(B, T + self.tape * le, dtype=torch.bool, device=dev), T=T, le=le),)
        return st

    def p_stop(self, zf):
        return torch.sigmoid(self.stop(zf).float())[:, 0]

    def run(self, batch, loops=None, gold=None, lesion=None, rounds=False, oracle=None, each=None):
        if gold is not None or loops is not None or each is not None:            # forced: T1's loop, the stop head ignored
            o = super().run(batch, loops, gold, lesion, rounds, oracle, each)
            if gold is None and each is None:
                self.last_rounds = [self.n_loops if loops is None else loops] * len(batch['rows'])
            return o
        B, dev = batch['prompt_ids'].shape[0], batch['prompt_ids'].device
        used = torch.zeros(B, dtype=torch.long, device=dev)                      # rounds used; 0 = not stopped yet
        keep = []

        def stop_here(t, st):
            zf, s = self.round_state(st)
            new = (used == 0) & ((self.p_stop(zf) >= P_STOP) | (t + 1 >= self.cap))
            if new.any():
                if not keep:
                    keep.extend(x.clone() for x in s)
                else:
                    for x, y in zip(keep, s):
                        x[new] = y[new].to(x.dtype)
                used[new] = t + 1
            return bool((used > 0).all())

        o = super().run(batch, self.cap, None, lesion, rounds, oracle, stop_here)
        R, Xt, idt, vis, lmode, lword, *qn = keep
        u = used.tolist()
        T = batch['prompt_ids'].shape[1]
        steps = []
        for k in range(N_RES):            # call k is written at iteration k + 1: it counts only for rows still running then (used > k + 1)
            st = o['steps'][k] if k < len(o['steps']) else self.noop_step(B, dev, o)
            lop = st[0]
            off = used <= k + 1
            if off.any():
                lop = lop.clone()
                lop[off] = self.noop_step(1, dev, o)[0].to(lop.dtype)
            steps.append((lop,) + tuple(st[1:]))
        self.last_rounds = u
        return dict(o, **({'qn': qn[0]} if qn else {}), R=R, lmode=lmode, lword=lword, X=torch.cat([o['X'][:, :T], Xt.to(o['X'].dtype)], 1), xm=torch.cat([o['xm'][:, :T], vis], 1),
                    ids=torch.cat([batch['prompt_ids'], idt], 1), tape=(Xt, idt, vis), steps=steps,
                    calls=[[c for c in cs if c[0] < u[i]] for i, cs in enumerate(o['calls'])], rounds=u)

    # ---- loss ----
    def plan(self, g, B, dev):
        """-> (call rounds [B, N_RES] or None, each row's last call round): T1's schedule, call k at round k + 1."""
        return None, (g['op'] > 0).sum(1)

    def run_tf(self, batch, n, g, sched, each):
        return Tool.run(self, batch, n, gold=g, each=each)

    def op_losses(self, o, g, B):
        return self.call_loss(o['steps'], g, B)

    def loss(self, batch):
        dev, B = batch['prompt_ids'].device, len(batch['rows'])
        rows = batch['rows']
        sc = self.span_copy
        g = self.gold(rows, dev, self.train_golds(rows) if self.ans_drill else None)
        sched, last = self.plan(g, B, dev)                                     # B3 any_round: the calls' rounds; here call k at round k + 1, last = L
        K = KS[int(torch.randint(len(KS), (1,)))]
        n = max(K, int(last.max()) + 1)
        per = []

        def keep_round(t, st):            # `shown` changes in place each round, so this round's visible tape is taken now
            vis = st['mt'] & st['shown'][:, :st['K']].gather(1, st['ent'].expand(B, -1))
            per.append((t, st['Z'], vis, st['Kw'], st['wvalid']))
            return False

        o = self.run_tf(batch, n, g, sched, keep_round)
        lop, lcall, hits, tot = self.op_losses(o, g, B)
        T = batch['prompt_ids'].shape[1]
        Xc, idc = o['X'], o['ids']                                             # prompt + the (teacher-forced) tape, fixed over the rounds
        xmp = o['xm'][:, :T]
        n_t = (g['gen'] >= 0).sum(1).clamp(min=1)
        tg = g['gen']
        gmode = (g['mode'] != 1) if sc else (g['mode'] == 2)                   # GEN's rows: T1SDR's rule (mode 0 rows keep GEN targets) / plain T1's
        if sc:
            ls, Mn = self.span_terms(o, g, batch, B)
            selw = (g['mode'] == 0) & Mn.any(-1)
            le = o['le']

        def heads(R, zf, vis, Kw, wvalid):
            p, gate = self.gen_copy(R, Xc, torch.cat([xmp, vis], 1), idc)
            out = (p, gate, self.mode_head(zf), self.ptr(self.q_word(zf), Kw, wvalid))
            if sc:
                m = torch.cat([xmp, vis], 1)
                out += (self.ptr(self.q_s(zf), self.span_keys(Xc, T, le, m), m),)
            return out

        acc = torch.zeros(B, device=dev)
        asp = torch.zeros(B, device=dev)
        cnt = torch.zeros(B, device=dev)
        zs, picks, spk = [], [], []
        share = None
        for t, Z, vis, Kw, wvalid in per:
            zf = self.ln_z(Z[:, 1])
            r = checkpoint(heads, Z[:, N_CTRL:], zf, vis, Kw, wvalid, use_reentrant=False)
            p, gate, lmode, lword = r[:4]
            lm = F.cross_entropy(lmode.float(), g['mode'], reduction='none')
            lw = torch.where(g['mode'] == 1, -(torch.logsumexp(lword.masked_fill(~g['word'], -1e9), -1) - torch.logsumexp(lword, -1)), torch.zeros_like(lm))
            ce = -torch.log(p.gather(2, tg.clamp(min=0)[..., None])[..., 0] + 1e-6).masked_fill(tg < 0, 0.0)
            lg = (ce.sum(1) / n_t) * gmode
            ok = (t >= last).float()
            row = lm + lw + lg
            if sc:
                ln = r[4]
                lsn = torch.where(selw, -(torch.logsumexp(ln.masked_fill(~Mn, -1e9), -1) - torch.logsumexp(ln, -1)), torch.zeros_like(lm))
                row = row + lsn
                asp = asp + lsn * ok
                with torch.no_grad():                                          # the greedy span this round reads, for the stop labels
                    spk.append(self.span_read(ln.detach(), idc, torch.cat([xmp, vis], 1), T, le))
            acc = acc + row * ok
            cnt = cnt + ok
            zs.append(zf.detach())
            picks.append(torch.cat([p.detach().argmax(-1), lmode.detach().argmax(-1)[:, None], lword.detach().argmax(-1)[:, None]], 1))
            if t == n - 1:
                tm = (tg >= 0) & (tg != EOS) & gmode[:, None]
                share = ((1 - gate.detach()[..., 0]) * tm).sum() / tm.sum().clamp(min=1)
        lans = (acc / cnt.clamp(min=1)).sum() / B
        # the stop head's labels: the model's own greedy readout after each round, against the target answer (a drill row's own drawn answer)
        picks = torch.stack(picks).tolist()                                    # [n][B][9 + 2]
        spans = [word_spans(r['prompt'])[:W_MAX] for r in rows]
        want = [norm(g['rowg'][i][5] if sc and g['rowg'][i][6] else r['answer']) for i, r in enumerate(rows)]
        right = torch.zeros(n, B, dtype=torch.bool)
        memo = {}
        for t in range(n):
            for i in range(B):
                key = (i, tuple(picks[t][i]), spk[t][i] if sc else None)
                hit = memo.get(key)
                if hit is None:
                    c = picks[t][i]
                    txt = self.answers([c[:-2]], [c[-2]], [c[-1]], [rows[i]], [spans[i]], span=[spk[t][i]] if sc else None)[0][0]
                    hit = memo[key] = norm(txt) == want[i]
                right[t, i] = hit
        y = (settled(right) if self.label == 'settled' else right).to(dev).float()
        logit = self.stop(torch.stack(zs)).float()[..., 0]                    # [n, B]
        lstop = F.binary_cross_entropy_with_logits(logit, y)
        # 'settled' asks about every later round of the turn; a batch shorter than the cap cannot see them (B13-2), so its settled loss is off
        w_stop = 1.0 if self.label == 'right' or n >= self.cap else 0.0
        total = lop + lcall + lans + w_stop * lstop
        aux = dict(prog=lop + lcall, op_acc=hits / tot.clamp(min=1), call=lcall, ans=lans, stop=lstop, stop_y=y.mean(), stop_acc=((logit >= 0).float() == y).float().mean(),
                   right_last=right[-1].float().mean(), rounds=float(n), copy_share=share, stop_w=w_stop)
        if sc:                      # 'stop' is T1S's span stop head there: H1's own loss is logged as 'halt'
            total = total + ls['span_call'] + ls['stop']
            aux.update(halt=lstop, span_call=ls['span_call'], span_ans=(asp / cnt.clamp(min=1)).sum() / B, stop=ls['stop'], span_share=ls['span_share'])
            if self.ans_drill:
                aux['drill_share'] = sum(x[6] for x in g['rowg']) / B
        return total, {k: v.detach() if torch.is_tensor(v) else v for k, v in aux.items()}

    # ---- extra evals ----
    @torch.no_grad()
    def extra_evals(self, ctx):
        out = super().extra_evals(ctx)
        out['h1'] = self.h1_evals(ctx)
        return out

    @torch.no_grad()
    def h1_evals(self, ctx):
        """Rounds used at the model's own stop: per dev split (the small build's 6 splits) and per split x family cell, per family / per gold
        program length on the big build's in_dist (chain-5 vs one-step = H-c), with per-row rounds for the pooled-5 rows. Each stats block also
        splits the stops into already right / settled as wrong / at the cap (amendment 1, 8c reporting)."""
        import os, statistics
        from custom_io.data import DEV_SPLITS, collate, Dataset, to_device
        from custom_io.evalx import CHAIN5, ONE_STEP, _dev_rows, is_hit
        from custom_io.models import progparse as pp
        was = self.training
        self.eval()
        dev, bs, amp = ctx['device'], ctx['batch_size'], ctx['amp']

        def rounds_of(rs):
            res = []
            for s in range(0, len(rs), bs):
                ch = rs[s:s + bs]
                b = to_device(collate([Dataset(ch, self.vocab, strict=False)[i] for i in range(len(ch))]), dev)
                with amp():
                    ans = self.talk(self.state(b), b)
                res += [(r, u, is_hit(a, r)) for r, u, a in zip(ch, self.last_rounds, ans)]
            return res

        def stats(res):
            us = [u for _, u, _ in res]
            if not us:
                return dict(n=0)
            hit = [u for _, u, h in res if h]
            miss = [u for _, u, h in res if not h]
            early = [h for _, u, h in res if u < self.cap]           # stops the head made (before the cap): already right vs settled as wrong
            return dict(n=len(us), mean=sum(us) / len(us), median=statistics.median(us), at_cap=100 * sum(u >= self.cap for u in us) / len(us),
                        hist={str(k): us.count(k) for k in sorted(set(us))}, mean_right=sum(hit) / len(hit) if hit else None,
                        mean_wrong=sum(miss) / len(miss) if miss else None, exact=100 * sum(h for _, _, h in res) / len(res),
                        stops=dict(right=sum(early), wrong=len(early) - sum(early), cap=len(us) - len(early),
                                   right_share=100 * sum(early) / len(early) if early else None))
        out = dict(cap=self.cap, p_stop=P_STOP, label=self.label, splits={}, rows={})
        pooled = []
        for sp in DEV_SPLITS:
            res = rounds_of(_dev_rows(ctx['data'], sp, None))
            out['splits'][sp] = stats(res)
            cells = {}
            for x in res:
                cells.setdefault(x[0]['family'], []).append(x)
            out.setdefault('split_family', {})[sp] = {f: stats(v) for f, v in sorted(cells.items())}
            if sp != 'family':
                out['rows'][sp] = {r['id']: u for r, u, _ in res}
                pooled += res
        out['pooled5'] = stats(pooled)
        big = rounds_of(_dev_rows(ctx.get('big') or ctx['data'], 'in_dist', None))
        out['rows']['big_in_dist'] = {r['id']: u for r, u, _ in big}
        fam = {}
        for x in big:
            fam.setdefault(x[0]['family'], []).append(x)
        out['big_in_dist'] = stats(big)
        out['by_family'] = {f: stats(v) for f, v in sorted(fam.items())}
        c5, one = [x for x in big if x[0]['family'] in CHAIN5], [x for x in big if x[0]['family'] in ONE_STEP]
        out['chain5'], out['one_step'] = stats(c5), stats(one)
        out['hc_gap'] = out['chain5']['mean'] - out['one_step']['mean'] if c5 and one else None
        by_len = {}
        for r, u, h in big:
            by_len.setdefault(str(len(pp.row_targets(r)['prog'])), []).append((r, u, h))
        out['by_program_len'] = {k: stats(v) for k, v in sorted(by_len.items())}
        self.train(was)
        return out
