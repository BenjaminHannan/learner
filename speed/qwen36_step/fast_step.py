"""Opt-in speed patches for sleepb.Trainer.step (Qwen3.6-35B-A3B LoRA sleep training). Nothing runs until install() is called; sleepb.py is untouched.
Each option keeps the loss and the LoRA gradients (float summation order and, on GPU, bf16 batch-shape noise aside); all off = the original Trainer.step.

  (always on in the fast step) use_cache=False: the baseline's decoder call builds a DynamicCache in training, so every GDN layer runs its kernel with
              output_final_state=True and copies conv/recurrent state into the cache for nothing, and the full-attention layers keep their K/V alive. Same outputs.
  sync_free   target rows are gathered with CPU-built index tensors (the bool-mask indexing `x[tm]` is a host sync, 3 per micro-batch), and the per-micro-batch
              float(part.detach()) syncs become one tensor sum read only when the curve is logged (every 10th step).
  kl_cache    the KL guard's reference is lm_head(h_base) where h_base, the adapter-off final hidden states at the target positions, is computed once per replay example
              and kept (n_targets x 2048 bf16). Valid because nothing changes the base between steps (SHY / merge / delta_w touch only LoRA and delta_w, which
              disable_adapter() switches off; q4 fake-quantization runs before training). base_fingerprint() is re-checked every `kl_check` steps and clears the cache if it moved.
  packed      padding-free micro-batches: sequences concatenated into one row of <= budget real tokens (first-fit decreasing), position_ids reset per sequence so
              transformers builds a block-diagonal causal mask for the 10 full-attention layers (sdpa), and cu_seq_lens_q goes to the 30 Gated DeltaNet layers (fla
              chunk kernel with cu_seqlens; the short conv needs fla_conv or the torch loop below, HF's torch conv would leak 3 tokens across sequences).
  fla_conv    HF's GDN short conv (torch F.conv1d + a separate silu, no causal-conv1d package) -> fla's Triton causal_conv1d (fused silu, cu_seqlens aware). GPU only.
  fast_experts  frozen routed experts: one Triton grouped GEMM launch per call (fast_experts.py) instead of torch 2.9's per-expert mm loop on sm_120 (143k mm/step). Needs experts_implementation
              "grouped_mm". Exact up to float summation order. experts_backend "auto" (Triton on CUDA, original elsewhere) | "triton" | "torch" (tests).
  fused_norms torch.compile'd Qwen3_5MoeRMSNorm / RMSNormGated (7 fp32 elementwise kernels each -> 1).
  python:  import fast_step; undo = fast_step.install(sleepb, sync_free=True, kl_cache=True, packed=True, fla_conv=True); ...; undo()
"""
import torch
import torch.nn.functional as F

OPTS = {"sync_free": False, "kl_cache": False, "packed": False, "fla_conv": False, "fused_norms": False, "fast_experts": False, "experts_backend": "auto", "kl_cache_mb": 512, "kl_check": 100}
_CU_CPU = [None]  # packed micro-batch's cu_seqlens on the host: fla's conv would otherwise sync to build its chunk indices
_CACHE = {}  # (token ids, loss_start) -> adapter-off hidden states at the target positions [n, hidden]; process-wide (the base never changes)
_SB = [None]  # the patched sleepb module
_STATE = {"bytes": 0, "steps": 0, "fp": None, "hits": 0, "miss": 0}


def base_fingerprint(m):  # cheap checksum of a few frozen base tensors (lm_head, first and last layer's norm / router); changes if the base is edited in place
    ps = [m.lm_head.weight, m.model.norm.weight, m.model.layers[0].input_layernorm.weight, m.model.layers[-1].mlp.gate.weight if hasattr(m.model.layers[-1].mlp, "gate") else m.model.layers[-1].input_layernorm.weight]
    return tuple(float(p.detach().float().abs().sum()) for p in ps)


def clear_cache():
    _CACHE.clear()
    _STATE.update(bytes=0, fp=None, hits=0, miss=0)


# ------------------------------------------------------------------ layouts
def pgroups(seqs, budget):  # first-fit decreasing bins of <= budget real tokens (a longer sequence gets its own bin); the padding-free analogue of sleepb.groups
    bins = []
    for x in sorted(seqs, key=lambda x: -len(x[0])):
        for b in bins:
            if b[0] + len(x[0]) <= budget:
                b[0] += len(x[0])
                b[1].append(x)
                break
        else:
            bins.append([len(x[0]), [x]])
    return [b[1] for b in bins]


class Lay:
    """One forward's input (kw for m.model), the flat indices of the shifted target positions in its [B*T] hidden states, their labels, per-example target counts."""

    def __init__(s, L, mb, packed):
        dev = L.device
        s.counts = [len(e) - max(st, 1) for e, st, *_ in mb]
        if packed:
            ns = [len(e) for e, *_ in mb]
            offs = [sum(ns[:r]) for r in range(len(ns))]
            ids = torch.tensor([t for e, *_ in mb for t in e]).view(1, -1)
            pos = torch.cat([torch.arange(n) for n in ns]).view(1, -1)
            cu = torch.tensor([0] + [sum(ns[:r + 1]) for r in range(len(ns))], dtype=torch.int32)
            _CU_CPU[0] = cu.long()
            mx = max(ns)
            s.kw = dict(use_cache=False, input_ids=ids.to(dev), position_ids=pos.to(dev), cu_seq_lens_q=cu.to(dev), cu_seq_lens_k=cu.to(dev), max_length_q=mx, max_length_k=mx)
        else:
            ids, mask = L.pad_right([e for e, *_ in mb])
            T = ids.size(1)
            offs = [r * T for r in range(len(mb))]
            s.kw = dict(use_cache=False, input_ids=ids, attention_mask=mask)
        idx, lab = [], []
        for o, (e, st, *_) in zip(offs, mb):
            j0 = max(st, 1) - 1
            idx += range(o + j0, o + len(e) - 1)
            lab += e[j0 + 1:]
        s.idx, s.lab = torch.tensor(idx).to(dev), torch.tensor(lab).to(dev)
        s.w = None
        if any(len(x) > 2 for x in mb):  # per-target loss weights of the weighted path (x[2]); examples without one weigh 1
            s.w = torch.tensor([x[2] if len(x) > 2 else 1.0 for x, c in zip(mb, s.counts) for _ in range(c)]).to(dev)


def target_hidden(m, lay):  # decoder only; final hidden states at lay.idx. [n, hidden]
    h = m.model(**lay.kw).last_hidden_state
    return h.reshape(-1, h.size(-1)).index_select(0, lay.idx)


def ref_hidden(s, m, mb, lay, packed):  # adapter-off hidden states of a replay micro-batch, from the cache where possible
    keys = [(tuple(e), st) for e, st, *_ in mb]
    miss = [i for i, k in enumerate(keys) if k not in _CACHE]
    _STATE["hits"] += len(keys) - len(miss)
    _STATE["miss"] += len(miss)
    if miss:
        sub = [mb[i] for i in miss]
        sl = lay if len(miss) == len(mb) else Lay(s.L, sub, packed)
        with torch.no_grad(), s.pm.disable_adapter():
            h = target_hidden(m, sl)
        parts = h.split(sl.counts)
        for i, p in zip(miss, parts):
            if _STATE["bytes"] + p.numel() * p.element_size() <= OPTS["kl_cache_mb"] * 2 ** 20:
                _CACHE[keys[i]] = p.clone()
                _STATE["bytes"] += p.numel() * p.element_size()
        got = dict(zip(miss, parts))
        return torch.cat([got[i] if i in got else _CACHE[keys[i]] for i in range(len(keys))])
    return torch.cat([_CACHE[k] for k in keys])


def prefill_kl_cache(s):  # fill the cache for every replay example now (one no-grad adapter-off pass over the pool); returns the number cached. Only for benchmarking steady state.
    m = s.pm.get_base_model() if hasattr(s.pm, "get_base_model") else s.pm
    packed = OPTS["packed"]
    grp = (lambda x: pgroups(x, _SB[0].TOK_BUDGET)) if packed else (lambda x: _SB[0].groups(sorted(x, key=lambda y: -len(y[0])), _SB[0].TOK_BUDGET))
    for mb in grp(s.replay):
        ref_hidden(s, m, mb, Lay(s.L, mb, packed), packed)
    return len(_CACHE)


def lm_plain(m):  # lm_head untouched by hooks / delta_w / LoRA: the same condition as sleepb.tgt_logits's FAST branch
    h = m.lm_head
    return not (h._forward_hooks or h._forward_pre_hooks or hasattr(h, "delta_w") or hasattr(h, "lora_A"))


# ------------------------------------------------------------------ the step
def make_step(sb, orig):
    def step(s, batch):
        O = OPTS
        m = s.pm.get_base_model() if hasattr(s.pm, "get_base_model") else s.pm
        if not (O["sync_free"] or O["kl_cache"] or O["packed"]) or not batch or not lm_plain(m) or not sb.FAST:
            return orig(s, batch)  # all off (or an lm_head the fast path cannot take): the original code
        a, packed = s.a, O["packed"]
        lr = a.lr * 0.5 * (1 + sb.math.cos(sb.math.pi * s.i / s.n))
        for g in s.opt.param_groups:
            g["lr"] = lr
        s.pm.train()
        rb = s.rng.sample(s.replay, min(a.replay_bsz, len(s.replay))) if s.replay and a.kl_weight > 0 else []  # same rng use as the original
        grp = (lambda x: pgroups(x, sb.TOK_BUDGET)) if packed else (lambda x: sb.groups(sorted(x, key=lambda y: -len(y[0])), sb.TOK_BUDGET))
        gb, gr = grp(batch), grp(rb)
        dev = s.L.device
        weighted = s.force_w or any(len(x) > 2 and x[2] != 1 for x in batch)
        if O["kl_cache"] and rb:
            _STATE["steps"] += 1
            if _STATE["steps"] % O["kl_check"] == 1:
                fp = base_fingerprint(m)
                if _STATE["fp"] is not None and fp != _STATE["fp"]:
                    clear_cache()
                _STATE["fp"] = fp
        s.opt.zero_grad(set_to_none=True)
        ntgt = sum(len(e) - max(st, 1) for e, st, *_ in batch)
        ce_sum = torch.zeros((), device=dev)
        kl_sum = torch.zeros((), device=dev)
        for mb in gb:
            lay = Lay(s.L, mb, packed)
            lg = m.lm_head(target_hidden(m, lay)).float()
            if weighted:
                part = (F.cross_entropy(lg, lay.lab, reduction="none") * lay.w).sum() / ntgt
            else:
                part = F.cross_entropy(lg, lay.lab, reduction="sum") / ntgt
            part.backward()
            ce_sum = ce_sum + part.detach()
            if not O["sync_free"]:
                float(part.detach())  # keep the baseline's sync when only the other options are on (clean A/B)
        if rb:
            npos = sum(len(e) - max(st, 1) for e, st, *_ in rb)
            for mb in gr:
                lay = Lay(s.L, mb, packed)
                cur = m.lm_head(target_hidden(m, lay)).float()
                if O["kl_cache"]:
                    with torch.no_grad():
                        ref = m.lm_head(ref_hidden(s, m, mb, lay, packed)).float()
                else:
                    with torch.no_grad(), s.pm.disable_adapter():
                        ref = m.lm_head(target_hidden(m, lay)).float()
                part = F.kl_div(F.log_softmax(cur, -1), F.log_softmax(ref, -1), log_target=True, reduction="sum") / npos
                (a.kl_weight * part).backward()
                kl_sum = kl_sum + part.detach()
                if not O["sync_free"]:
                    float(part.detach())
        torch.nn.utils.clip_grad_norm_(s.params, 1.0)
        s.opt.step()
        s.i += 1
        if weighted:
            s.wsteps += 1
            s.wex += sum(1 for x in batch if len(x) > 2 and x[2] != 1)
        if s.i % 10 == 1 or s.i == s.n:
            s.curve.append({"step": s.i, "ce": float(ce_sum), "kl": float(kl_sum), "lr": lr})
        s.pm.eval()
    return step


# ------------------------------------------------------------------ kernels
def fla_causal_conv1d_fn(hidden_states, weight, bias=None, activation=None, **kw):  # HF GDN short conv, [B, D, T] in and out; fla Triton kernel, cu_seqlens from the packed layout
    from fla.modules.causal_conv1d import causal_conv1d
    y, _ = causal_conv1d(hidden_states.transpose(1, 2), weight, bias, activation=activation, backend="triton", cu_seqlens=kw.get("cu_seq_lens_q"), cu_seqlens_cpu=_CU_CPU[0] if kw.get("cu_seq_lens_q") is not None else None)
    return y.transpose(1, 2)


def torch_varlen_patches(mod):  # pure-torch packed-sequence support for CPU tests / boxes without fla: the HF torch ops run once per sequence of the pack. Returns undo.
    conv0, chunk0 = mod.causal_conv1d_fn, mod.torch_chunk_gated_delta_rule

    def seg(cu):
        c = cu.tolist()
        return list(zip(c[:-1], c[1:]))

    def conv(x, weight, bias=None, activation=None, **kw):  # x [1, D, T]
        cu = kw.get("cu_seq_lens_q")
        if cu is None:
            return conv0(x, weight, bias, activation=activation)
        return torch.cat([conv0(x[:, :, a:b], weight, bias, activation=activation) for a, b in seg(cu)], dim=-1)

    def chunk(q, k, v, g, beta, cu_seqlens=None, **kw):  # [1, T, H, d]
        kw = {n: x for n, x in kw.items() if n in ("chunk_size", "initial_state", "output_final_state", "use_qk_l2norm_in_kernel")}
        if cu_seqlens is None:
            return chunk0(q, k, v, g=g, beta=beta, **kw)
        outs = [chunk0(q[:, a:b], k[:, a:b], v[:, a:b], g=g[:, a:b], beta=beta[:, a:b], **kw)[0] for a, b in seg(cu_seqlens)]
        return torch.cat(outs, dim=1), None

    mod.causal_conv1d_fn, mod.torch_chunk_gated_delta_rule = conv, chunk

    def undo():
        mod.causal_conv1d_fn, mod.torch_chunk_gated_delta_rule = conv0, chunk0
    return undo


def _rms0(x, w, eps):  # Qwen3_5MoeRMSNorm.forward
    o = x.float()
    o = o * torch.rsqrt(o.pow(2).mean(-1, keepdim=True) + eps)
    return (o * (1.0 + w.float())).type_as(x)


def _rmsg(x, gate, w, eps):  # Qwen3_5MoeRMSNormGated.forward (norm before gate, silu gate)
    dt = x.dtype
    v = x.float()
    v = v * torch.rsqrt(v.pow(2).mean(-1, keepdim=True) + eps)
    v = w * v.to(dt)
    return (v * F.silu(gate.float())).to(dt)


def compile_norms(mod):
    import torch._dynamo.config as dc
    for k in ("recompile_limit", "cache_size_limit"):  # the norms see 2-D / 3-D inputs with and without grad: more than the default 8 variants
        if hasattr(dc, k):
            setattr(dc, k, 64)
    c0, c1 = torch.compile(_rms0, dynamic=True), torch.compile(_rmsg, dynamic=True)
    n0, n1 = mod.Qwen3_5MoeRMSNorm.forward, mod.Qwen3_5MoeRMSNormGated.forward
    mod.Qwen3_5MoeRMSNorm.forward = lambda self, x: c0(x, self.weight, self.eps)
    mod.Qwen3_5MoeRMSNormGated.forward = lambda self, x, gate: c1(x, gate, self.weight, self.variance_epsilon)

    def undo():
        mod.Qwen3_5MoeRMSNorm.forward, mod.Qwen3_5MoeRMSNormGated.forward = n0, n1
    return undo


def install(sb, **opts):
    """Patch sleepb's Trainer.step (and the HF Qwen3.5-MoE module for fla_conv / fused_norms) per opts; returns undo()."""
    import transformers.models.qwen3_5_moe.modeling_qwen3_5_moe as mod
    unknown = set(opts) - set(OPTS)
    assert not unknown, unknown
    old_opts, orig = dict(OPTS), sb.Trainer.step
    OPTS.update(opts)
    undos = []
    _SB[0] = sb
    sb.Trainer.step = make_step(sb, orig)
    if OPTS["fla_conv"]:
        c0 = mod.causal_conv1d_fn
        mod.causal_conv1d_fn = fla_causal_conv1d_fn
        undos.append(lambda: setattr(mod, "causal_conv1d_fn", c0))
    if OPTS["fused_norms"]:
        undos.append(compile_norms(mod))
    if OPTS["fast_experts"]:
        import fast_experts
        undos.append(fast_experts.install(OPTS["experts_backend"]))

    def undo():
        for u in undos:
            u()
        sb.Trainer.step = orig
        OPTS.clear()
        OPTS.update(old_opts)
        clear_cache()
    return undo
