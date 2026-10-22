"""b3g2_defer: the DEFERRED BATCHED WRITER for B3G2 training (train.py --speed-arms defer). DRAFT: a port of results/8a-g/speedup/launch/defer.py (the code the GPU runs 4 and 5 tested)
for production; it stays a draft until the coordinator has code-reviewed it. Off by default (B3G2.speed_defer False): with the flag off nothing in this file runs and training is bitwise the original.

WHAT IT DOES
In teacher-forced training B3G2._loss runs B3G2.loop(g=..., sched=...): a thinker round, then (rounds >= 1) a call pass on the rows that have a target and (every round) an answer pass on the
rows that may answer, each with several host reads (~10 syncs a round). Nothing the writer computes feeds back into the thinker (G2f: the writer reads Z alone, line_context), so here the whole
micro-batch is done as ONE thinker-only loop, then ONE batched call pass (two buckets: the pairs that write a call, padded to the longest call, and the EOS-only pairs at width 1) and ONE batched
answer pass over all (round, row) pairs (rounds < CKPT_FROM plain, rounds >= CKPT_FROM gradient-checkpointed as the original does). Every host-side list (who calls when, who has a target, who may
answer) comes from the numpy schedule of B3G2.plan_np, never read back from the device; the host arrays go over in one copy.

WHEN IT RUNS (B3G2.loss decides; _loss is the base text; trace_loss calls _loss directly and never comes here, but ST1's ordinary half-batches call loss(), so with the flag on they take this path): speed_defer True and the model is training, autograd is on, talk_rounds == 'last' and the writer has
no copy path. Anything else (eval, no_grad, talk_rounds 'all', a copy writer) counts defer_counts['fallback'] and runs _loss; a run of the deferred path counts defer_counts['deferred'] (plain
attribute, not a *_stats dict, so train.py's model_streams does not store it and a flag-off checkpoint keeps the g2fa4 format; a flag-ON run keeps the counts in its checkpoint sidecar and restores them
on --resume). defer_counts also carries defer.py's per-micro-batch sizes (call / EOS-only / answer pairs, call width, rounds, rows); stats(m) turns them into defer.py's means for RESULT.json.
SOURCE GUARD: the first deferred call on a model checks SRC_HASH (sha1[:12] of the source of every method this file re-implements or relies on, resolved on type(m) and type(m.writer)) and raises RuntimeError on a mismatch.

NUMERICS-CHANGING ('near'): the per-row maths is identical but floating-point rounding is not: batched GEMMs, a longer padded call width, parameter gradients reduced in ONE backward over all pairs
(another summation order). fp32 on a CPU: about 1e-7 relative; bf16 on a GPU: see the GPU-RUN-4/5 readouts. The thinker is bit-identical. Not 'same maths bit for bit'. A run with it is a different
run from one without: fresh runs from update 0 under new names only (train.py puts --speed-arms in the config hash, so --resume refuses to cross a change of it).
WHAT IS NOT CHANGED: the thinker, the tape, the stop head and its loss, w_stop, the aux keys and values, plan's draws (gap rng), train_golds' draws (drill rng), the K draw (torch.randint once per
micro-batch, after plan), the order of the call-loss sum and of the answer-loss accumulation.
"""
import hashlib, inspect
import numpy as np
import torch
from torch.utils.checkpoint import checkpoint
from custom_io.models import b3g2 as B3G2M

# sha1 (first 12 hex) of the source of each method this file re-implements or relies on, trailing blanks stripped (defer.py's src_hash). B3G2 methods are those of the PORT tree, resolved on type(m)
# (plan and plan_np and loss are the port's own; _loss is the base text, the one deferred_loss re-implements and which still calls plan). A different source means this file was written against other code.
SRC_HASH = dict(loop='173236f31248', call_pass='3aa7d3d707b2', ans_pass='5f2387af6a2b', answer_teacher='a33b2f2ef2b7', line_context='ee62580e169e', plan='c5a2cb0e4052', plan_np='c093c8d2edb3', _loss='349e3f1eaaff', loss='0dedb8e3d9b0')
SRC_HASH_WRITER = dict(teacher='c6d7f0df92ca', nll='ebaa4f2fc55f', right='1c885a0c60b2')
SRC_HASH_TOOL = dict(think='6ccf66237406', tape_of='22b5b8101693')


def src_hash(fn):
    return hashlib.sha1('\n'.join(ln.rstrip() for ln in inspect.getsource(inspect.unwrap(fn)).splitlines()).encode()).hexdigest()[:12]


def source_hashes(m):
    """-> {name: (sha1[:12], expected)} of every guarded method, as resolved on type(m) (B3G2 methods, think, tape_of) and type(m.writer): a subclass that overrides one is seen."""
    cls, wcls = type(m), type(m.writer)
    out = {f'{cls.__name__}.{n}': (src_hash(getattr(cls, n)), h) for n, h in {**SRC_HASH, **SRC_HASH_TOOL}.items()}
    out.update({f'{wcls.__name__}.{n}': (src_hash(getattr(wcls, n)), h) for n, h in SRC_HASH_WRITER.items()})
    return out


def applies_statically(m):
    """True when the model can ever take the deferred path: talk_rounds 'last' and a writer without a copy path (the rest of the rule, training and autograd on, is checked per call by B3G2.loss)."""
    return m.talk_rounds == 'last' and not m.writer.copy


NUMERICS = "NUMERICS-CHANGING ('near'): per-row maths identical, floating-point rounding is not (batched GEMMs, a longer padded call width, one-shot parameter-gradient reductions); the thinker is bit-identical"


def stats(m):
    """defer.py's Defer.stats() from m.defer_counts (python ints only): the counts and the per-micro-batch means, for RESULT.json."""
    c, d = m.defer_counts, m.defer_counts['deferred']
    per = lambda k: c[k] / d if d else None
    return dict(numerics=NUMERICS, deferred_losses=d, fallback_losses=c['fallback'], call_pairs_per_micro_batch=per('call_pairs'), eos_only_pairs_per_micro_batch=per('eos_pairs'),
                answer_pairs_per_micro_batch=per('answer_pairs'), mean_call_width=per('call_width_sum'), max_call_width=c['call_width_max'], mean_rounds=per('rounds_sum'), mean_rows_per_micro_batch=per('rows_sum'))


def check_source(m):
    """Raises RuntimeError naming the first method whose source is not the one this port was written against."""
    for name, (got, want) in source_hashes(m).items():
        if got != want:
            raise RuntimeError(f'b3g2_defer: the source of {name} is not the custom_io this port was written against: sha1 {got} != {want}')


def to_device_async(v, device):
    """A CPU tensor to the device without waiting for the stream: pinned staging + non_blocking on CUDA; the same values either way. CPU: plain .to."""
    if device.type != 'cuda' or v.numel() == 0:
        return v.to(device)
    return v.pin_memory().to(device, non_blocking=True)


# ------------------------------------------------------------------------------------------------------------------------------------------------------
# host-side pure functions (numpy only: no device read, testable without a model)
# ------------------------------------------------------------------------------------------------------------------------------------------------------
def teacher_np(targets, cap, bos, eos, pad=-100):
    """ByteWriter.teacher's inp / tgt / over for the empty line_context (cids [P, 1] zeros, cmask [P, 1] False), built with numpy: targets = list of id lists WITHOUT EOS or None.
    -> (inp [P, L] int64, tgt [P, L] int64 (EOS appended, pad after), over [P] bool). The teacher's fb [P, L, 1] is ALWAYS zero here (its `hit` needs a visible context position and
    the mask is all False), so it is not built; callers use zeros. len + 1 > cap -> over, an all-pad row (inp = EOS after BOS), never a cut one."""
    P = len(targets)
    ok = [t is not None and len(t) + 1 <= cap for t in targets]
    over = np.array([t is not None and len(t) + 1 > cap for t in targets], dtype=bool)
    L = max([len(t) + 1 for t, o in zip(targets, ok) if o] + [1])
    inp = np.full((P, L), eos, dtype=np.int64)
    tgt = np.full((P, L), pad, dtype=np.int64)
    inp[:, 0] = bos
    for b, (t, o) in enumerate(zip(targets, ok)):
        if o:
            n = len(t)
            tgt[b, :n] = t
            tgt[b, n] = eos
            if n:
                inp[b, 1:n + 1] = t
    return inp, tgt, over


def last_of(sched):
    """Each row's last call round (0 for a row without a call): B3.loop's `sched.max(1).values.clamp(min=0)`, from the numpy schedule."""
    return np.maximum(sched.max(1), 0) if sched.shape[1] else np.zeros(sched.shape[0], np.int64)


def schedule_lists(sched, golds_ids, n):
    """From the numpy schedule [B, tape] and each row's call ids: everything the original read back from the device, per round t = 1..n-1.
    -> (last [B] int64 = each row's last call round or 0, per_round: list of (t, rows [S] int, targets [S] list: the call's ids, [] (EOS only, t > last), is_call [S] bool); a row with no
    target at that round is absent, a round with no row is absent)."""
    B = sched.shape[0]
    last = last_of(sched)
    per_round = []
    for t in range(1, n):
        hit = sched == t
        call = hit.any(1)
        kk = hit.argmax(1)
        aft = t > last
        rows = [i for i in range(B) if call[i] or aft[i]]
        if rows:
            per_round.append((t, rows, [golds_ids[i][kk[i]] if call[i] else [] for i in rows], [bool(call[i]) for i in rows]))
    return last, per_round


def answer_pairs(last, has, n):
    """(t_idx, i_idx) of the answer pairs, rounds ascending then rows ascending: ok_t = (t > last) | ~has for t in 0..n-1 (the original's per-round `ok`)."""
    ok = (np.arange(n)[:, None] > last[None, :]) | ~has[None, :]
    t, i = np.nonzero(ok)
    return t.astype(np.int64), i.astype(np.int64), ok


class Pack:
    """Several int64 numpy arrays sent to the device as ONE tensor (one host-to-device copy per micro-batch: pinned + non_blocking on CUDA, plain on the CPU) and viewed back by name."""

    def __init__(self):
        self.parts, self.shapes = [], {}

    def add(self, name, a):
        a = np.ascontiguousarray(a, dtype=np.int64)
        self.shapes[name] = (sum(p.size for p in self.parts), a.shape)
        self.parts.append(a.reshape(-1))

    def send(self, device):
        flat = np.concatenate(self.parts) if self.parts else np.zeros(0, np.int64)
        self.dev = to_device_async(torch.from_numpy(flat), device)
        return self

    def __getitem__(self, name):
        off, shape = self.shapes[name]
        return self.dev[off:off + int(np.prod(shape, dtype=np.int64))].view(*shape)


# ------------------------------------------------------------------------------------------------------------------------------------------------------
# the loss
# ------------------------------------------------------------------------------------------------------------------------------------------------------
def thinker(m, batch, Ls, tapes, sched_dev, n):
    """B3G2.loop's teacher-forced thinker half: the same reads, kv, tape, think calls in the same order; the writer is not called. shown comes from the schedule, as a
    [n, B, K] tensor made at once on the device (no read). -> list of Z_t (t = 0..n-1)."""
    N_REG = B3G2M.N_REG
    X, xm = m.read(batch, talker=True)
    B, T, dev = X.shape[0], X.shape[1], X.device
    ns, ne = (None, None) if m.no_slots else m.tokenize(batch)[:2]
    valid, S0 = m.num_memory(X, ns, ne)
    Xk, km = m.tok_spots(X, xm, batch) if m.tok_think else (X, xm)
    kvx = [b.kv_of(Xk + m.src.weight[1]) for b in m.core]
    kvs0 = m.slot_kv(S0)
    K = max(1, max(Ls))
    texts = [(list(e) + [''] * K)[:K] for e in tapes]
    Xt, idt, mt, le = m.tape_of(texts, dev, None)
    ent = torch.arange(K * le, device=dev) // le
    kvt = [b.kv_of(Xt + m.src.weight[1]) for b in m.core]
    Z = torch.cat([m.ctrl.weight, m.reader.place.weight[:N_REG]]).expand(B, -1, -1)
    kvs = m.join_kv(kvs0, kvt)
    before = torch.arange(-1, n - 1, device=dev)[:, None, None]                  # round t reads the tape as it stood after round t - 1: shown = 1 <= sched <= t - 1
    shown = ((sched_dev[None] >= 1) & (sched_dev[None] <= before))[:, :, :K]       # [n, B, K]
    vis_all = shown.index_select(2, ent) & mt[None]                              # [n, B, K*le]: shown[:, :K].gather(1, ent) & mt, every round at once
    zs = []
    for t in range(n):
        ts = min(t, m.n_loops - 1)
        mask = torch.cat([valid, vis_all[t], km], 1)
        Z = m.think(Z + m.step_emb.weight[ts], kvs, kvx, mask, t)
        zs.append(Z)
    return zs


def deferred_loss(m, batch, golds):
    """B3G2._loss's teacher-forced training loss, deferred and batched (see the header). -> (total, aux) exactly as _loss. Called by B3G2.loss only when it applies."""
    if not getattr(m, '_defer_src_ok', False):                                   # once per model, on its first deferred call (B3G2.loss has already drawn the drill rng in train_golds; the guard draws nothing)
        check_source(m)
        m._defer_src_ok = True
    m.defer_counts['deferred'] += 1
    dev, B = batch['prompt_ids'].device, len(batch['rows'])
    KS, CKPT_FROM, settled, BOS, EOS, F_ = B3G2M.KS, B3G2M.CKPT_FROM, B3G2M.settled, B3G2M.BOS, B3G2M.EOS, B3G2M.F      # module globals read at call time, as _loss reads them
    Ls = [len(x['texts']) for x in golds]
    sched = m.plan_np(Ls, B)                                                     # numpy [B, tape]; the same gap-rng draws and plan_stats as plan()
    K = KS[int(torch.randint(len(KS), (1,)))]                                    # the micro-batch's one draw of the default generator, as the original
    ids = [x['ids'] for x in golds]
    has = np.array([bool(L) for L in Ls], dtype=bool)
    n = max(K, int(last_of(sched).max()) + 2)                                    # +2: a call row's answer rounds start at last+1 (numpy: no device read)
    last, per_round = schedule_lists(sched, ids, n)
    # call pairs: rounds ascending, rows ascending within a round. They run as TWO buckets (memory): the pairs that write a call (padded to the longest call of the micro-batch) and the
    # EOS-only pairs (t > the row's last call round: target [], width 1, as the original's all-EOS rounds), put back into pair order by a permutation before the loss is summed.
    c_rows, c_flat, targets, is_call, segs = [], [], [], [], []
    for t, rows, tg, ic in per_round:
        segs.append((t, len(targets), len(targets) + len(rows)))
        c_rows += rows
        c_flat += [t * B + i for i in rows]
        targets += tg
        is_call += ic
    P = len(targets)
    ic_np = np.array(is_call, dtype=bool)
    cf_np = np.array(c_flat, np.int64)
    i_call, i_eos = np.nonzero(ic_np)[0], np.nonzero(~ic_np)[0]
    n_call = len(i_call)
    c_inv = np.argsort(np.concatenate([i_call, i_eos]), kind='stable')            # bucket order -> pair order
    inp_c, tgt_c, _ = teacher_np([targets[j] for j in i_call], m.WCAP, BOS, EOS)
    inp_e, tgt_e, _ = teacher_np([targets[j] for j in i_eos], m.WCAP, BOS, EOS)
    a_t, a_i, ok = answer_pairs(last, has, n)
    Q = len(a_t)
    n_a0 = int((a_t < CKPT_FROM).sum())                                          # answer pairs of rounds < CKPT_FROM come first (rounds ascending)
    inp_r, tgt_r, _ = teacher_np([x['ans_ids'] for x in golds], m.WCAP, BOS, EOS)       # the answer teacher, built once as the original, rows indexed per pair below
    pk = Pack()
    for name, a in (('sched', sched), ('cf_call', cf_np[i_call]), ('cf_eos', cf_np[i_eos]), ('c_inv', c_inv), ('c_rows', np.array(c_rows, np.int64)), ('inp_c', inp_c), ('tgt_c', tgt_c),
                    ('inp_e', inp_e), ('tgt_e', tgt_e), ('a_flat', a_t * B + a_i), ('a_rows', a_i), ('inp_a', inp_r[a_i]), ('tgt_a', tgt_r[a_i]), ('has', has.astype(np.int64)),
                    ('cnt', ok.sum(0))):
        pk.add(name, a)
    pk.send(dev)                                                                 # the ONE host-to-device copy of this micro-batch
    sched_dev = pk['sched']
    zs_list = thinker(m, batch, Ls, [x['tape'] for x in golds], sched_dev, n)
    nz, d = zs_list[0].shape[1], zs_list[0].shape[2]
    Zall = torch.stack(zs_list).reshape(n * B, nz, d)                            # [n*B, nz, d], row t*B + i = Z_t of row i
    # ---- the batched call pass (mode 0): call bucket, then EOS-only bucket
    lcall, hits = 0.0, dict(call_hit=0, call_n=0, eos_hit=0, eos_n=0)
    right_c = None
    if P:
        nlls, rights = [], []
        for lo, hi, flat_name, inp_name, tgt_name in ((0, n_call, 'cf_call', 'inp_c', 'tgt_c'), (n_call, P, 'cf_eos', 'inp_e', 'tgt_e')):
            if hi > lo:
                _, nll_b, right_b = m.call_pass(Zall.index_select(0, pk[flat_name]), pk[inp_name], pk[tgt_name])
                nlls.append(nll_b); rights.append(right_b)
        nll = (torch.cat(nlls) if len(nlls) > 1 else nlls[0]).index_select(0, pk['c_inv'])     # back in pair order (rounds ascending, rows ascending)
        right_c = torch.cat(rights) if len(rights) > 1 else rights[0]                         # bucket order: the call pairs, then the EOS-only pairs
        w_row = torch.where(pk['has'].bool(), 1.0, m.w_noop)                     # the original's w_row, built on the device from `has`
        prod = nll * w_row.index_select(0, pk['c_rows'])
        for t, s, e in segs:                                                     # rounds in the original order: lcall = lcall + (nll * w).sum() / B
            lcall = lcall + prod[s:e].sum() / B
    # ---- the batched answer pass (mode 1): rounds < CKPT_FROM as one pass, rounds >= CKPT_FROM as one gradient-checkpointed pass (the original checkpoints those rounds' answer pass)
    acc = torch.zeros(B, device=dev)
    right = torch.zeros(n, B, dtype=torch.bool, device=dev)
    share = None
    if Q:                                                                        # Q == 0 only if no round has an ok row (_loss itself always has n - 1 >= last + 1)
        Za = Zall.index_select(0, pk['a_flat'])
        Q_, La = pk['inp_a'].shape
        fb_a = Za.new_zeros(1, 1, 1).expand(Q_, La, 1)
        outs = []
        for lo, hi, ck in ((0, n_a0, False), (n_a0, Q, True)):
            if hi > lo:
                args = (Za[lo:hi], pk['inp_a'][lo:hi], pk['tgt_a'][lo:hi], fb_a[lo:hi])
                outs.append(checkpoint(m.ans_pass, *args, use_reentrant=False) if ck else m.ans_pass(*args))
        nll_a, rt_a, sn, sd = (torch.cat([o[j] for o in outs]) if len(outs) > 1 else outs[0][j] for j in range(4))
        right.view(-1)[pk['a_flat']] = rt_a
        s0 = 0
        for t in range(n):                                                       # acc in the original round order; acc[i] + nll == acc[i] + (0 + nll)
            e0 = s0 + int(ok[t].sum())
            if e0 > s0:
                acc = acc.index_add(0, pk['a_rows'][s0:e0], nll_a[s0:e0].float())
                if t == n - 1:
                    share = sn[s0:e0].sum() / sd[s0:e0].sum().clamp(min=1)      # as the original: the t == n - 1 segment's copy mass over its non-EOS bytes (None: no ok row that round)
            s0 = e0
    cnt = pk['cnt'].float()
    lans = (acc / cnt.clamp(min=1)).sum() / B
    zst = Zall.view(n, B, nz, d)[:, :, 1].detach()
    zs = m.ln_z(zst)                                                             # == the original's torch.stack([ln_z(Z_t[:, 1].detach())]): LayerNorm is per row
    y = (settled(right) if m.label == 'settled' else right).to(dev).float()
    logit = m.stop(zs).float()[..., 0]
    lstop = F_.binary_cross_entropy_with_logits(logit, y)
    w_stop = 1.0 if m.label == 'right' or n >= m.cap else 0.0
    if P:                                                                        # the hit counters: ONE device read, at the end (bucket order: call pairs first)
        rc = right_c.tolist()
        hits['call_n'], hits['call_hit'] = n_call, sum(rc[:n_call])
        hits['eos_n'], hits['eos_hit'] = P - n_call, sum(rc[n_call:])
    total = lcall + lans + w_stop * lstop
    aux = dict(prog=lcall, call=lcall, ans=lans, stop=lstop, stop_y=y.mean(), stop_acc=((logit >= 0).float() == y).float().mean(), right_last=right[-1].float().mean(),
               rounds=float(n), copy_share=share, stop_w=w_stop, call_acc=hits['call_hit'] / max(hits['call_n'], 1), eos_acc=hits['eos_hit'] / max(hits['eos_n'], 1))
    aux.update({f'plan_{k}': float(v) for k, v in m.plan_stats.items()})
    if m.ans_drill:
        aux['drill_share'] = sum(x['drill'] for x in golds) / B
    c = m.defer_counts                                                           # defer.py's per-micro-batch counters: python ints from numpy sizes, no device read
    c['call_pairs'] += P; c['eos_pairs'] += P - n_call; c['answer_pairs'] += Q; c['call_width_sum'] += inp_c.shape[1]; c['call_width_max'] = max(c['call_width_max'], inp_c.shape[1])
    c['rounds_sum'] += n; c['rows_sum'] += B
    return total, {k: v.detach() if torch.is_tensor(v) else v for k, v in aux.items()}
