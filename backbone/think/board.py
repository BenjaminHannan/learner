"""Think-1 board: G-STS (gated silent think slots) for Qwen3.5 (see PREREG.md, DESIGN.md, IMPL-SPEC.md section 2).

K slot vectors (input-embedding space) run through the frozen model on a fork of the prompt cache, lap after lap; a small refiner
turns each lap's slot states into the next slots. The answer tokens read the final slots' keys/values through zero-started gates.
Every slot pass and every answer pass uses its own fork of the prompt cache, so the cache `C` is never written.
"""
from __future__ import annotations

import contextlib
import copy
import sys
import types
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from train import MAX_NEW, left_pad  # noqa: E402
from xent import fixed_cross_entropy  # noqa: E402

THINK_TEXT = " Let me think about where each thing is now and why."


# ---------------------------------------------------------------- cache fork

def _linear_layer_cls():
    from transformers.cache_utils import LinearAttentionLayer

    class AssignLinearLayer(LinearAttentionLayer):
        """Linear-attention cache layer that ASSIGNS new states (HF writes them in place with copy_), so a fork never writes its parent."""

        def update_conv_state(self, conv_states, state_idx=0, conv_kernel_size=None, **kwargs):
            if not self.is_conv_states_initialized[state_idx]:
                self.lazy_initialization(conv_states=conv_states, state_idx=state_idx, conv_kernel_size=conv_kernel_size)
            k = self.conv_kernel_size[state_idx]
            if not self.has_previous_state[state_idx]:
                full = conv_states
                self.has_previous_state[state_idx] = True
                if full.shape[-1] < k:
                    full = F.pad(full, (k - full.shape[-1], 0))
            else:
                full = torch.cat([self.conv_states[state_idx], conv_states], dim=-1)
            self.conv_states[state_idx] = full[..., -k:]
            return full

        def update_recurrent_state(self, recurrent_states, state_idx=0, **kwargs):
            if not self.is_recurrent_states_initialized[state_idx]:
                self.lazy_initialization(recurrent_states=recurrent_states, state_idx=state_idx)
            self.recurrent_states[state_idx] = recurrent_states
            return recurrent_states

    return AssignLinearLayer


AssignLinearLayer = _linear_layer_cls()


def fork_cache(C, clone=False):
    """New cache sharing C's tensors by reference. Attention layers: update() cats and reassigns, so C is never mutated.
    Linear layers: AssignLinearLayer. clone=True copies the conv/recurrent states (needed for 1-token steps, whose fused conv update is in place)."""
    from transformers.cache_utils import LinearAttentionCacheLayerMixin
    f = copy.copy(C)
    layers = []
    for l in C.layers:
        if isinstance(l, LinearAttentionCacheLayerMixin):
            n = AssignLinearLayer(number_of_states=l.number_of_states)
            for i in range(l.number_of_states):
                for name in ("conv_states", "recurrent_states"):
                    t = getattr(l, name)[i]
                    getattr(n, name)[i] = t.clone() if (clone and t is not None) else t
            for name in ("is_conv_states_initialized", "is_recurrent_states_initialized", "has_previous_state", "conv_kernel_size"):
                setattr(n, name, dict(getattr(l, name)))
            n.device, n.dtype, n.record_past = l.device, l.dtype, l.record_past
            layers.append(n)
        else:
            layers.append(copy.copy(l))
    f.layers = layers
    return f


# ---------------------------------------------------------------- gated read patch

def _patched_forward(self, hidden_states, position_embeddings, attention_mask, past_key_values=None, **kwargs):
    """Qwen3_5Attention.forward, op for op, plus the board read (only when self.board and self.gate are set)."""
    mq = _mq()
    input_shape = hidden_states.shape[:-1]
    hidden_shape = (*input_shape, -1, self.head_dim)

    query_states, gate = torch.chunk(self.q_proj(hidden_states).view(*input_shape, -1, self.head_dim * 2), 2, dim=-1)
    gate = gate.reshape(*input_shape, -1)

    query_states = self.q_norm(query_states.view(hidden_shape)).transpose(1, 2)
    key_states = self.k_norm(self.k_proj(hidden_states).view(hidden_shape)).transpose(1, 2)
    value_states = self.v_proj(hidden_states).view(hidden_shape).transpose(1, 2)

    cos, sin = position_embeddings
    query_states, key_states = mq.apply_rotary_pos_emb(query_states, key_states, cos, sin)

    if past_key_values is not None:
        key_states, value_states = past_key_values.update(key_states, value_states, self.layer_idx)

    attention_interface = mq.ALL_ATTENTION_FUNCTIONS.get_interface(self.config._attn_implementation, mq.eager_attention_forward)

    attn_output, attn_weights = attention_interface(
        self, query_states, key_states, value_states, attention_mask,
        dropout=0.0 if not self.training else self.attention_dropout, scaling=self.scaling, **kwargs)

    if self.board is not None and self.gate is not None:
        ks, vs = self.board
        r = F.scaled_dot_product_attention(query_states, mq.repeat_kv(ks, self.num_key_value_groups),
                                           mq.repeat_kv(vs, self.num_key_value_groups), scale=self.scaling)
        r = r.transpose(1, 2) * self.gate.to(r.dtype)[None, None, :, None]  # [B, T, H, D]
        if self.read_from is not None:  # reference decodes without a cache: only queries at index >= read_from read the board
            r = r * (torch.arange(r.shape[1], device=r.device) >= self.read_from).to(r.dtype)[None, :, None, None]
        attn_output = attn_output + r

    attn_output = attn_output.reshape(*input_shape, -1).contiguous()
    attn_output = attn_output * torch.sigmoid(gate)

    attn_output = self.o_proj(attn_output)
    return attn_output, attn_weights


def _mq():
    import transformers.models.qwen3_5.modeling_qwen3_5 as mq
    return mq


def attn_modules(runner):
    """The full-attention modules in layer order, patched (idempotent) so that they read `.board` with `.gate`."""
    out = []
    for layer in runner.lm.model.layers:
        if layer.block_type != "full_attention":
            continue
        a = layer.self_attn
        if not getattr(a, "_think_patched", False):
            a.board = a.gate = a.read_from = None
            a.forward = types.MethodType(_patched_forward, a)
            a._think_patched = True
        out.append(a)
    return out


def unpatch(runner):
    for layer in runner.lm.model.layers:
        if layer.block_type == "full_attention" and getattr(layer.self_attn, "_think_patched", False):
            del layer.self_attn.forward
            layer.self_attn._think_patched = False


@contextlib.contextmanager
def reading(runner, gate, slot_kv, read_from=None):
    """Answer-side queries read slot_kv (list over full-attention layers of (k, v) [B, kv_heads, K, hd]) with gate [n_attn, heads]."""
    mods = attn_modules(runner)
    try:
        if slot_kv is not None and gate is not None:
            for j, a in enumerate(mods):
                a.board, a.gate, a.read_from = slot_kv[j], gate[j], read_from
        yield
    finally:
        for a in mods:
            a.board = a.gate = a.read_from = None


# ---------------------------------------------------------------- layer loop

def model_dtype(runner):
    return runner.lm.model.embed_tokens.weight.dtype


def model_device(runner):
    return runner.lm.model.embed_tokens.weight.device


def tap_layers(n):
    """Layers whose output the refiner reads (11 and 17 of 24; 3 and 5 of 8)."""
    return (n // 2 - 1, 3 * n // 4 - 1)


def run_layers(runner, x, mask, pos, cache=None, taps=()):
    """Mirrors Runner.hidden on embeddings. x [B,T,d], mask 2-D [B, past+T], pos [B,T]. Returns (final-normed h, {layer: output})."""
    from transformers.masking_utils import create_causal_mask, create_recurrent_attention_mask
    m, cfg = runner.lm.model, runner.cfg
    pe = m.rotary_emb(x, pos[None].expand(3, *pos.shape))
    kw = dict(config=cfg, inputs_embeds=x, attention_mask=mask, past_key_values=cache, position_ids=pos)
    masks = {"full_attention": create_causal_mask(**kw), "linear_attention": create_recurrent_attention_mask(**kw)}
    tap = {}
    for i, layer in enumerate(m.layers):
        x = layer(x, position_embeddings=pe, attention_mask=masks[cfg.layer_types[i]], position_ids=pos,
                  past_key_values=cache, use_cache=cache is not None)
        if i in taps:
            tap[i] = x
    return m.norm(x), tap


def full_idx(runner):
    return [i for i, t in enumerate(runner.cfg.layer_types) if t == "full_attention"]


# ---------------------------------------------------------------- board module

def clamp_rms(e, rho):
    """Scale each slot down to RMS rho if it exceeds it (never up)."""
    r = e.pow(2).mean(-1, keepdim=True).sqrt()
    return e * (rho / r.clamp(min=1e-12)).clamp(max=1.0)


def f32(x):
    return x if x.dtype == torch.float64 else x.float()


def rms_norm(x, eps=1e-6):
    x = f32(x)
    return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + eps)


class RefineBlock(nn.Module):
    def __init__(self, h=256, heads=4, mlp=1024):
        super().__init__()
        self.heads = heads
        self.n1, self.n2 = nn.LayerNorm(h, bias=False), nn.LayerNorm(h, bias=False)
        self.qkv, self.o = nn.Linear(h, 3 * h, bias=False), nn.Linear(h, h, bias=False)
        self.fc1, self.fc2 = nn.Linear(h, mlp), nn.Linear(mlp, h)

    def forward(self, x):  # x [B, K, h]; attention only among the K slots of one row
        B, K, h = x.shape
        q, k, v = self.qkv(self.n1(x)).view(B, K, 3, self.heads, h // self.heads).permute(2, 0, 3, 1, 4)
        a = F.scaled_dot_product_attention(q, k, v).transpose(1, 2).reshape(B, K, h)
        x = x + self.o(a)
        return x + self.fc2(F.gelu(self.fc1(self.n2(x))))


def init_token_ids(tok, K, vocab):
    """First K distinct token ids of THINK_TEXT, padded with further distinct ids (fixed order) if there are fewer."""
    ids = []
    for t in tok(THINK_TEXT, add_special_tokens=False)["input_ids"]:
        if t not in ids and t < vocab:
            ids.append(t)
    for t in [*range(1000, vocab), *range(min(1000, vocab))]:
        if len(ids) >= K:
            break
        if t not in ids:
            ids.append(t)
    return ids[:K]


class ThinkBoard(nn.Module):
    def __init__(self, d, rho, e0_hat, n_attn=6, n_heads=8, hid=256):
        super().__init__()
        self.K = e0_hat.shape[0]
        self.register_buffer("rho", torch.tensor(float(rho), dtype=torch.float32))
        self.e0_hat = nn.Parameter(e0_hat.detach().clone().float())
        self.eta = nn.Parameter(torch.full((d,), 0.1))
        self.alpha = nn.Parameter(torch.zeros(n_attn, n_heads))
        self.w_in = nn.Linear(3 * d, hid)
        self.blocks = nn.ModuleList([RefineBlock(hid) for _ in range(2)])
        self.norm = nn.LayerNorm(hid, bias=False)
        self.w_out = nn.Linear(hid, d)

    @classmethod
    def from_model(cls, lm, tok, K=16):
        """rho = median row RMS of the embedding table; e0_hat = embeddings of K distinct tokens of THINK_TEXT / rho."""
        W = lm.model.embed_tokens.weight.detach().float()
        rho = W.pow(2).mean(-1).sqrt().median().item()
        ids = init_token_ids(tok, K, W.shape[0])
        n_attn = sum(t == "full_attention" for t in lm.config.layer_types)
        return cls(W.shape[1], rho, W[ids] / rho, n_attn=n_attn, n_heads=lm.config.num_attention_heads)

    def clamp(self, e):
        return clamp_rms(e, self.rho)

    def start(self, B):
        return self.clamp(self.rho * self.e0_hat)[None].expand(B, -1, -1)

    def gate(self):
        return torch.tanh(self.alpha)

    def delta(self, taps):
        """taps [B, K, 3d] fp32 -> bounded update rho * eta * tanh(W_out(norm(u)))."""
        u = self.w_in(taps)
        for b in self.blocks:
            u = b(u)
        return self.rho * self.eta * torch.tanh(self.w_out(self.norm(u)))


# ---------------------------------------------------------------- passes

@torch.no_grad()
def prefill(runner, prompts):
    """Frozen prefill of prompt[:-1] (left-padded). Returns the cache C, the 2-D mask [B, T] and p_i = len(prompt_i) - 1."""
    from transformers import DynamicCache
    dev = model_device(runner)
    ids, mask = left_pad([p[:-1] for p in prompts])
    ids, mask = ids.to(dev), mask.to(dev)
    pos = (mask.cumsum(1) - 1).clamp(min=0)
    C = DynamicCache(config=runner.cfg)
    run_layers(runner, runner.lm.model.embed_tokens(ids), mask, pos, C)
    return C, mask, torch.tensor([len(p) - 1 for p in prompts], device=dev)


def last_ids(prompts, device):
    return torch.tensor([p[-1] for p in prompts], device=device)


def slot_pass(runner, e, C, mask, p):
    """One backbone pass of the slots e [B,K,d] on their own fork of C. Returns (taps [B,K,3d] fp32, slot K/V per full-attention layer)."""
    B, K, _ = e.shape
    x = e.to(model_dtype(runner))
    pos = p[:, None].expand(B, K)
    mask2 = torch.cat([mask, torch.ones(B, K, dtype=mask.dtype, device=mask.device)], 1)
    fork = fork_cache(C, clone=K == 1)
    t1, t2 = tap_layers(runner.n)
    h, tap = run_layers(runner, x, mask2, pos, fork, taps=(t1, t2))
    taps = torch.cat([rms_norm(tap[t1]), rms_norm(tap[t2]), f32(h)], -1)
    kv = [(fork.layers[i].keys[..., -K:, :], fork.layers[i].values[..., -K:, :]) for i in full_idx(runner)]
    return taps, kv


def _stats(e_prev, pre, e, rho):
    with torch.no_grad():
        rms = lambda x: x.pow(2).mean(-1).sqrt()
        return dict(step=(rms(e - e_prev) / rho).mean(), clamp=(rms(pre) > rho * (1 + 1e-6)).float().mean(),
                    clamp5=(rms(pre) > rho * 1.05).float().mean())


def _cos(e):
    with torch.no_grad():
        en = F.normalize(f32(e), dim=-1)
        B, K, _ = en.shape
        off = lambda s, n: (s.sum((-1, -2)) - s.diagonal(dim1=-2, dim2=-1).sum(-1)) / max(n * (n - 1), 1)
        within = off(en @ en.transpose(1, 2), K).mean()
        across = off(torch.einsum("ikd,jkd->kij", en, en), B).mean() if B > 1 else torch.tensor(float("nan"))
        return within, across


def think(board, runner, C, mask, p, L, keep=None, swap=None, repeat_delta1=False, stats=True):
    """Laps 0..L. Returns ({lap: slot K/V} for every lap in keep, stats). stats: pen[t] (grad-carrying mean((delta/rho)^2) of each refinement),
    step[t-1] (mean rms(e_t - e_{t-1})/rho), clamp[t-1] (fraction of slots whose rms before the clamp exceeds rho at all; clamp5: by more than 5%), cos_slots[t] / cos_rows[t] (mean pairwise slot cosine
    within a board / of the same slot across rows), e[t] (the boards). swap: LongTensor, row i reads the board of row swap[i].
    repeat_delta1: the update after pass 0 is reused for every lap; backbone passes only at lap 0 and at the laps in keep."""
    keep = {L} if keep is None else set(keep)
    rho = board.rho
    e = board.start(len(p))
    out, st = {}, dict(pen=[], step=[], clamp=[], clamp5=[], cos_slots=[], cos_rows=[], e=[e])

    def note(prev, pre, new):
        st["pen"].append(((pre - prev) / rho).pow(2).mean())
        if stats:
            s = _stats(prev, pre, new, rho)
            st["step"].append(s["step"]), st["clamp"].append(s["clamp"]), st["clamp5"].append(s["clamp5"])
            w, a = _cos(new)
            st["cos_slots"].append(w), st["cos_rows"].append(a)

    if stats:
        w, a = _cos(e)
        st["cos_slots"].append(w), st["cos_rows"].append(a)
    d0 = None
    for t in range(L + 1):
        if repeat_delta1 and t > 0:
            pre = e + d0
            new = board.clamp(pre)
            note(e, pre, new)
            e = new
            st["e"].append(e)
            if t in keep:
                out[t] = slot_pass(runner, e, C, mask, p)[1]
            continue
        taps, kv = slot_pass(runner, e, C, mask, p)
        if t in keep:
            out[t] = kv
        if t == L:
            break
        d0 = board.delta(taps)
        if repeat_delta1:  # lap 0 only supplies the update; laps 1..L apply it
            continue
        pre = e + d0
        new = board.clamp(pre)
        note(e, pre, new)
        e = new
        st["e"].append(e)
    if swap is not None:
        out = {t: swap_kv(kv, swap) for t, kv in out.items()}
    return out, st


def swap_kv(kv, idx):
    return [(k[idx], v[idx]) for k, v in kv]


def mean_kv(kv):
    return [(k.mean(0, keepdim=True).expand_as(k), v.mean(0, keepdim=True).expand_as(v)) for k, v in kv]


def swap_index(groups):
    """For each row the nearest following row (cyclic) of a different group (story). None if every row has the same group."""
    n = len(groups)
    idx = []
    for i in range(n):
        j = next((j for j in ((i + s) % n for s in range(1, n)) if groups[j] != groups[i]), None)
        if j is None:
            return None
        idx.append(j)
    return torch.tensor(idx)


def answer_logits(runner, gate, C, mask, p, last_tok, ans, slot_kv):
    """Teacher-forced answer pass on its own fork of C: inputs [last_tok] + ans[:-1] at positions p_i, p_i+1, ... (right-padded across rows),
    board read active when slot_kv is given. Returns (logits [N, V] fp32 at the real answer positions, targets [N], row of each position)."""
    dev = model_device(runner)
    B, n = len(ans), max(len(a) for a in ans)
    ids = torch.zeros(B, n, dtype=torch.long)
    rm = torch.zeros(B, n, dtype=mask.dtype)
    for b, a in enumerate(ans):
        ids[b, :len(a)] = torch.tensor([0] + list(a[:-1]))
        rm[b, :len(a)] = 1
    ids, rm = ids.to(dev), rm.to(dev)
    ids[:, 0] = last_tok
    pos = p[:, None] + torch.arange(n, device=dev)[None]
    mask2 = torch.cat([mask, rm], 1)
    fork = fork_cache(C, clone=n == 1)
    with reading(runner, gate, slot_kv):
        h, _ = run_layers(runner, runner.lm.model.embed_tokens(ids), mask2, pos, fork)
    sel_b = torch.tensor([b for b, a in enumerate(ans) for _ in a], device=dev)
    sel_t = torch.tensor([k for a in ans for k in range(len(a))], device=dev)
    tgt = torch.tensor([t for a in ans for t in a], device=dev)
    return f32(runner.logits(h[sel_b, sel_t])), tgt, sel_b


def answer_ce(runner, board, C, mask, p, last_tok, ans, slot_kv, gates=None):
    """Summed fixed CE over the real answer tokens, and their count. gates overrides board.gate() (e.g. zeros)."""
    gate = (board.gate() if gates is None else gates) if board is not None else None
    logits, tgt, _ = answer_logits(runner, gate, C, mask, p, last_tok, ans, slot_kv)
    return fixed_cross_entropy(logits, tgt, reduction="sum"), len(tgt)


@torch.no_grad()
def decode(runner, board, C, mask, p, last_tok, slot_kv, max_new=MAX_NEW, eos=1, gates=None):
    """Greedy cached decode on fork_cache(C, clone=True) with the board read at every step. Returns generated id lists (no EOS).
    slot_kv None (or zero gates) gives arm a's greedy output."""
    B, dev = len(p), model_device(runner)
    gate = (board.gate() if gates is None else gates) if board is not None else None
    fork = fork_cache(C, clone=True)
    out = [[] for _ in range(B)]
    done = torch.zeros(B, dtype=torch.bool, device=dev)
    cur, pos = last_tok[:, None], p[:, None]
    with reading(runner, gate, slot_kv):
        for _ in range(max_new):
            mask = torch.cat([mask, torch.ones(B, 1, dtype=mask.dtype, device=dev)], 1)
            h, _ = run_layers(runner, runner.lm.model.embed_tokens(cur), mask, pos, fork)
            nxt = runner.logits(h[:, -1]).argmax(-1)
            for b in range(B):
                if not done[b]:
                    t = int(nxt[b])
                    if t == eos:
                        done[b] = True
                    else:
                        out[b].append(t)
            if bool(done.all()):
                break
            cur, pos = torch.where(done, torch.full_like(nxt, eos), nxt)[:, None], pos + 1
    return out


def train_loss(board, runner, C, mask, p, last_tok, ans, L_max, n_norm=None, row_frac=1.0, lam=0.01):
    """Loss of one micro-batch: mean over laps t = 0..L_max of answer CE (read from board t) / n_norm + lam * row_frac * mean penalty.
    n_norm: answer tokens of the whole optimizer-step batch (default: this micro-batch); row_frac: this micro-batch's share of its rows.
    Returns (loss, info)."""
    kv, st = think(board, runner, C, mask, p, L_max, keep=range(L_max + 1), stats=False)
    ces, n = [], None
    for t in range(L_max + 1):
        s, n = answer_ce(runner, board, C, mask, p, last_tok, ans, kv[t])
        ces.append(s)
    ce = torch.stack(ces).mean()
    pen = torch.stack(st["pen"]).mean() if st["pen"] else ce.new_zeros(())
    loss = ce / (n_norm or n) + lam * row_frac * pen
    return loss, dict(ce_sum=[c.item() for c in ces], n=n, pen=pen.item())
