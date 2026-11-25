"""PROBLEM-7 Forecast5 (Rung 1 / Rank 3): Un-Choked Shared-Brain Experimental Model.

Experimental copy ONLY — canonical `premonition_core_v2` is NEVER edited and its exact
SHA-256 is verified once at install time before binding instance methods.

Three clean, switchable knobs (all 100% learned, zero game-specific rules):
  K1 (`use_signal_path`): Problem-1's 99% signal-path bundle:
     - `ContextRead`: 1 pre-norm masked multi-head self-attention layer over context tokens
       inside `encode_context` (zero-init output proj)
     - `door_floor = 0.15`: `g' = 0.15 + 0.85 * g` on non-pinned slow rows (in BOTH read
       and imagine; pinned rows stay 0)
     - `signal_path_init`: private-generator init (`src_emb ~ N(0,0.02)`, `age_lin ~ N(0,0.02)`
       with bias 0, `row_type_emb ~ N(0,0.02)`, `init_rows ~ N(0,0.05)`, `out_proj ~ N(0,0.1)`
       with bias 0; `row_pos_emb` untouched at vendored std 1.0)
     - Brightness-preserving centered patch input `(frames - 0.5)` (no per-token `rms_level`).
  K2 (`use_act_film`): Intercom FiLM action broadcast to all R rows before `_trunk` during
     context-blind imagination (`h = h * (1 + tanh(gamma(a))) + beta(a)`, zero-init linear)
     plus smooth bounded update `delta = max_delta * tanh(raw_delta / max_delta)` (`max_delta=3.0`)
     and matched `focus = state.focus`.
  K3 (`RowLNDecoder` + joint residual-matched loss in `train_v5.py`):
     - Per-row `LayerNorm(D)` -> per-row `Linear(D, 32)` -> full-rank `Linear(R*32, 768)`
       + zero-init-last `MLP(R*32 -> 512 -> 768)` (zero BatchNorm, zero frozen-ridge Catch-22).
"""
from __future__ import annotations

import __future__
import dataclasses
import hashlib
import inspect
import math
import textwrap
import types
from pathlib import Path

import torch
import torch.nn as nn

from premonition_core_v2.board_swarm import BoardCell, ImagineOutput, ThinkMode, board_summary
from premonition_core_v2.interfaces import Context, Source

PINNED_BOARD_SWARM_SHA256 = "8ffc3fb860547551f10e10a135bcd088176fe0f7b569125c123e0e797e0b6b1d"
H = W = 16
N_PATCH = 16
PATCH = 48
DOOR_FLOOR_DEFAULT = 0.15
MAX_DELTA_DEFAULT = 3.0

_CTX_ANCHOR = "sup = torch.where(m, ctx.support, torch.zeros_like(ctx.support))"
_CTX_INSERT = "e = _context_read(e, m)\n{ind}"
_OLD_GATE = "g_slow = torch.sigmoid(self.gate(torch.cat([slow0, prop], dim=-1)).squeeze(-1)) * gs[:, None].to(prop.dtype)"
_NEW_GATE = (
    "g_raw = torch.sigmoid(self.gate(torch.cat([slow0, prop], dim=-1)).squeeze(-1))\n"
    "{ind}g_slow = _door_floor_gate(g_raw, _DOOR_FLOOR) * gs[:, None].to(prop.dtype)"
)


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_canonical_board_swarm() -> str:
    """Verify canonical premonition_core_v2/board_swarm.py matches the pinned SHA-256."""
    import premonition_core_v2.board_swarm as bs

    p = Path(bs.__file__).resolve()
    have = _file_sha256(p)
    if have != PINNED_BOARD_SWARM_SHA256:
        raise RuntimeError(
            f"forecast5: board_swarm.py sha {have} != pinned {PINNED_BOARD_SWARM_SHA256} ({p})"
        )
    return have


def _door_floor_gate(g: torch.Tensor, floor: float) -> torch.Tensor:
    return floor + (1.0 - floor) * g


class ContextRead(nn.Module):
    """Exact Problem-1 pre-norm masked multi-head self-attention over context rows (zero-init out)."""

    def __init__(self, d: int, n_heads: int = 4, init_seed: int = 101):
        super().__init__()
        if d % n_heads != 0:
            raise ValueError(f"ContextRead: width {d} not divisible by {n_heads} heads")
        self.d, self.h = int(d), int(n_heads)
        self.norm = nn.LayerNorm(d)
        self.qkv = nn.Linear(d, 3 * d, bias=False)
        self.out = nn.Linear(d, d, bias=False)
        g = torch.Generator().manual_seed(int(init_seed))
        with torch.no_grad():
            bound = 1.0 / math.sqrt(d)
            self.qkv.weight.copy_((torch.rand(self.qkv.weight.shape, generator=g) * 2.0 - 1.0) * bound)
            self.out.weight.zero_()

    def forward(self, e: torch.Tensor, m: torch.Tensor) -> torch.Tensor:
        B, C, d = e.shape
        hd = d // self.h
        a = self.norm(e)
        q, k, v = self.qkv(a).chunk(3, dim=-1)
        q = q.view(B, C, self.h, hd).transpose(1, 2)
        k = k.view(B, C, self.h, hd).transpose(1, 2)
        v = v.view(B, C, self.h, hd).transpose(1, 2)
        att = (q.float() @ k.float().transpose(-1, -2)) * (1.0 / math.sqrt(hd))
        keym = m[:, None, None, :].to(torch.bool)
        att = att.masked_fill(~keym, float("-inf"))
        any_key = keym.any(-1, keepdim=True)
        att = torch.where(any_key, att, torch.zeros_like(att))
        p = torch.softmax(att, -1) * any_key.to(att.dtype)
        y = (p.to(v.dtype) @ v).transpose(1, 2).reshape(B, C, d)
        return e + self.out(y).to(e.dtype)


def _patch_line(src: str, anchor: str, replacement_tpl: str, tag: str) -> str:
    n = src.count(anchor)
    if n != 1:
        raise RuntimeError(f"{tag}: expected 1 occurrence of anchor, found {n}")
    i = src.index(anchor)
    ind = src[src.rindex("\n", 0, i) + 1:i]
    if ind.strip():
        raise RuntimeError(f"{tag}: anchor is not alone on its line")
    return src.replace(anchor, replacement_tpl.format(ind=ind))


def install_signal_path_v5(cell: BoardCell, ctx_read_layer: ContextRead, floor: float = DOOR_FLOOR_DEFAULT):
    """Bind patched encode_context (ContextRead) and tick (door_floor) to THIS cell instance only."""
    if getattr(cell, "learned_sticky", False):
        raise RuntimeError("signal_path_v5 supports fixed_split only")
    verify_canonical_board_swarm()
    import premonition_core_v2.board_swarm as bs

    ns = dict(vars(bs))

    enc_src = textwrap.dedent(inspect.getsource(bs.BoardCell.encode_context))
    enc_patched = _patch_line(enc_src, _CTX_ANCHOR, _CTX_INSERT + _CTX_ANCHOR, "context_read")
    ns["_context_read"] = ctx_read_layer
    exec(
        compile(enc_patched, "<forecast5 encode_context>", "exec",
                flags=__future__.annotations.compiler_flag, dont_inherit=True),
        ns,
    )
    enc_fn = ns["encode_context"]

    tick_src = textwrap.dedent(inspect.getsource(bs.BoardCell.tick))
    tick_patched = _patch_line(tick_src, _OLD_GATE, _NEW_GATE, "door_floor")
    ns.update(_door_floor_gate=_door_floor_gate, _DOOR_FLOOR=float(floor))
    exec(
        compile(tick_patched, "<forecast5 tick>", "exec",
                flags=__future__.annotations.compiler_flag, dont_inherit=True),
        ns,
    )
    tick_fn = ns["tick"]

    cell.encode_context = types.MethodType(enc_fn, cell)
    cell.tick = types.MethodType(tick_fn, cell)


def signal_path_init_v5(cell: BoardCell, seed: int = 42) -> None:
    """Exact Problem-1 private-CPU-generator init (leaves row_pos_emb at vendored std 1.0)."""
    g = torch.Generator().manual_seed(int(seed) * 10007 + 9137)
    with torch.no_grad():
        cell.src_emb.weight.normal_(0.0, 0.02, generator=g)
        cell.age_lin.weight.normal_(0.0, 0.02, generator=g)
        cell.age_lin.bias.zero_()
        cell.row_type_emb.weight.normal_(0.0, 0.02, generator=g)
        cell.init_rows.normal_(0.0, 0.05, generator=g)
        cell.out_proj.weight.normal_(0.0, 0.1, generator=g)
        cell.out_proj.bias.zero_()


class RowLNDecoder(nn.Module):
    """Per-row LayerNorm + compact row bottleneck + full-rank linear skip + zero-init-last MLP.
    No BatchNorm (zero train/eval stat drift, zero eps=1e-3 signal crushing).
    """

    def __init__(self, R: int, D: int, row_bottleneck: int = 32, hidden: int = 512):
        super().__init__()
        self.R, self.D = int(R), int(D)
        self.ln = nn.LayerNorm(D)
        self.row_proj = nn.Linear(D, row_bottleneck)
        flat = R * row_bottleneck
        self.lin = nn.Linear(flat, H * W * 3)
        self.mlp = nn.Sequential(
            nn.Linear(flat, hidden),
            nn.GELU(),
            nn.Linear(hidden, H * W * 3),
        )
        nn.init.zeros_(self.mlp[-1].weight)
        nn.init.zeros_(self.mlp[-1].bias)

    def forward(self, rows: torch.Tensor) -> torch.Tensor:
        # rows: [B, R, D] -> [B, 16, 16, 3]
        z = self.row_proj(self.ln(rows)).flatten(1)
        return (self.lin(z) + self.mlp(z)).reshape(-1, H, W, 3)


def _unit_rms(x: torch.Tensor) -> torch.Tensor:
    return x / x.pow(2).mean(-1, keepdim=True).sqrt().clamp_min(1e-6)


class WorldModelV5(nn.Module):
    """Un-choked shared-brain experimental world model (P7 Rung 1 / Rank 3)."""

    def __init__(
        self,
        cfg,
        *,
        use_signal_path: bool = True,
        use_act_film: bool = True,
        door_floor: float = DOOR_FLOOR_DEFAULT,
        max_delta: float = MAX_DELTA_DEFAULT,
        row_bottleneck: int = 32,
        dec_hidden: int = 512,
        seed: int = 42,
    ):
        super().__init__()
        verify_canonical_board_swarm()
        self.cfg = cfg
        self.D = int(cfg.dims.d_board)
        self.R = int(cfg.dims.board_rows)
        self.d = int(cfg.d_inner)
        self.use_signal_path = bool(use_signal_path)
        self.use_act_film = bool(use_act_film)
        self.door_floor = float(door_floor) if use_signal_path else 0.0
        self.max_delta = float(max_delta)

        # Shared modules created FIRST in fixed order so all 4 arms share bit-identical init RNG
        self.cell = BoardCell(cfg)
        self.reader = nn.Linear(PATCH, self.D)
        self.pos = nn.Parameter(torch.empty(N_PATCH, self.D))
        nn.init.normal_(self.pos, std=0.02)
        self.action_emb = nn.Embedding(17, self.D)
        self.dec = RowLNDecoder(self.R, self.D, row_bottleneck=row_bottleneck, hidden=dec_hidden)

        # Optional arm-specific modules created LAST (zero RNG shift on shared modules!)
        if self.use_signal_path:
            n_h = min(4, cfg.n_heads) if (cfg.d_inner % min(4, cfg.n_heads) == 0) else cfg.n_heads
            self.ctx_read = ContextRead(cfg.d_inner, n_heads=n_h, init_seed=seed + 101)
            install_signal_path_v5(self.cell, self.ctx_read, floor=self.door_floor)
            signal_path_init_v5(self.cell, seed=seed)
        else:
            self.ctx_read = None

        if self.use_act_film:
            self.act_film = nn.Linear(self.D, 2 * self.d)
            nn.init.zeros_(self.act_film.weight)
            nn.init.zeros_(self.act_film.bias)
        else:
            self.act_film = None

    def encode_frame(self, frames: torch.Tensor):
        """Encode 16x16x3 frames into 16 spatial patch tokens (brightness-preserving: no per-token rms_level)."""
        B = frames.shape[0]
        centered = frames - 0.5
        p = centered.reshape(B, 4, 4, 4, 4, 3).permute(0, 1, 3, 2, 4, 5).reshape(B, N_PATCH, PATCH)
        tok = self.reader(p) + self.pos[None]
        ctx = Context(
            tokens=tok,
            mask=torch.ones(B, N_PATCH, dtype=torch.bool, device=tok.device),
            support=torch.ones(B, N_PATCH, device=tok.device),
            source=torch.full((B, N_PATCH), int(Source.SIGHT), dtype=torch.long, device=tok.device),
            age_s=torch.zeros(B, N_PATCH, device=tok.device),
            epoch=torch.zeros(B, dtype=torch.long, device=tok.device),
            q_hash=torch.zeros(B, dtype=torch.long, device=tok.device),
        )
        return self.cell.encode_context(ctx)

    def encode_action_ctx(self, action_embed_unit: torch.Tensor):
        """100% context-blind imagination memory: ONLY the action token (zero frame-t photo leaked)."""
        B = action_embed_unit.shape[0]
        at = action_embed_unit[:, None, :]
        dev = at.device
        ctx = Context(
            tokens=at,
            mask=torch.ones(B, 1, dtype=torch.bool, device=dev),
            support=torch.ones(B, 1, device=dev),
            source=torch.full((B, 1), int(Source.SIGHT), dtype=torch.long, device=dev),
            age_s=torch.zeros(B, 1, device=dev),
            epoch=torch.zeros(B, dtype=torch.long, device=dev),
            q_hash=torch.zeros(B, dtype=torch.long, device=dev),
        )
        return self.cell.encode_context(ctx)

    def read_frame(self, state, enc):
        """2 shared THINK ticks reading one encoded frame (returns (new_state, aux_loss))."""
        o1 = self.cell.run_tick(state, enc, noise=False)
        o2 = self.cell.run_tick(o1.state, enc, noise=False)
        return o2.state, 0.5 * (o1.aux_loss + o2.aux_loss)

    def real_board(self, x_prev: torch.Tensor, x_curr: torch.Tensor):
        """Canonical 2-frame real board: read x_{t-1} (2 ticks), then x_t (2 ticks)."""
        st0 = self.cell.init_state(x_curr.shape[0], 1, device=x_curr.device, dtype=torch.float32)
        st1, aux1 = self.read_frame(st0, self.encode_frame(x_prev))
        st2, aux2 = self.read_frame(st1, self.encode_frame(x_curr))
        return st2, 0.5 * (aux1 + aux2)

    def _imagine_core(self, cell, act_film, rows, enc, action_embed_unit, focus, gs, pin, clock):
        B, K, R, D = rows.shape
        N = B * K
        ns = cell.ns
        bidx = torch.arange(B, device=rows.device).repeat_interleave(K)
        x0 = rows.reshape(N, R, D)
        a = (
            action_embed_unit.reshape(B, 1, D).expand(B, K, D)
            if action_embed_unit.dim() == 2
            else action_embed_unit
        ).reshape(N, D).to(x0.dtype)
        rd = cell._reading(clock, B, rows.device)
        cemb = cell.clock_enc(rd)[bidx].to(x0.dtype)
        mode = cell.mode_emb.weight[int(ThinkMode.IMAGINE_NEXT_STATE)].to(x0.dtype)
        h = (
            cell.in_proj(x0)
            + cell.row_type_emb(cell.row_type)[None].to(x0.dtype)
            + cell.row_pos_emb[None].to(x0.dtype)
            + mode
            + cemb[:, None]
        )
        if act_film is not None:
            gamma, beta = act_film(a).chunk(2, dim=-1)
            h = h * (1.0 + torch.tanh(gamma)[:, None, :]).to(x0.dtype) + beta[:, None, :].to(x0.dtype)
        ha = cell.action_in(a) + cell.action_pos.to(x0.dtype) + mode + cemb
        h_all = torch.cat([h, ha[:, None]], dim=1)
        mem = enc.memory
        age_now = mem["age0"][bidx] + rd.elapsed_s.float()[bidx][:, None]
        h_all, aux_loss, counts, _ = cell._trunk(h_all, mem, bidx, focus.to(x0.dtype), age_now, None, R)
        hn = cell.norm_f(h_all)
        raw_delta = cell.out_proj(hn[:, :R]).to(x0.dtype)
        if self.max_delta > 0.0:
            delta = (self.max_delta * torch.tanh(raw_delta / self.max_delta)).to(x0.dtype)
        else:
            delta = raw_delta

        # Same doorman update law as tick (with door_floor when K1 is enabled, pins respected, no noise)
        slow0, fast0 = x0[:, :ns], x0[:, ns:]
        d_s, d_f = delta[:, :ns], delta[:, ns:]
        prop = slow0 + d_s
        g_raw = torch.sigmoid(cell.gate(torch.cat([slow0, prop], dim=-1)).squeeze(-1))
        g_slow = _door_floor_gate(g_raw, self.door_floor) * gs[:, None].to(prop.dtype)
        g_slow = torch.where(pin[:, :ns], torch.zeros_like(g_slow), g_slow)
        slow = (slow0.float() + g_slow.float()[..., None] * d_s.float()).to(x0.dtype)
        fast = torch.where(pin[:, ns:][..., None], fast0, fast0 + d_f)
        next_rows = torch.cat([slow, fast], dim=1)
        z_pred = board_summary(x0, ns) + cell.imagine_head(hn[:, R]).to(x0.dtype)
        return ImagineOutput(
            z_pred=z_pred.view(B, K, D),
            next_rows=next_rows.view(B, K, R, D),
            aux_loss=aux_loss,
            expert_counts=counts,
        )

    def imagine_step(self, state, act_or_embed: torch.Tensor, clock=None, *, wm_grad: bool = True) -> ImagineOutput:
        """One context-blind imagination step through the shared sparse-MoE trunk.

        `act_or_embed`: LongTensor [B] of action IDs OR FloatTensor [B, D] action embedding.
        When `wm_grad=False` (planning): cell weights, act_film, enc_act, and start board are
        strictly detached (anti-wishful-thinking), so value gradients only reach `act_or_embed`.
        """
        is_int_act = act_or_embed.dtype in (torch.int64, torch.int32, torch.int16, torch.int8)
        if is_int_act:
            a_raw = self.action_emb(act_or_embed)
            a_unit = _unit_rms(a_raw.detach() if not wm_grad else a_raw)
        else:
            a_unit = _unit_rms(act_or_embed)
        focus = state.focus.reshape(-1)
        gs = state.gate_scale.reshape(-1)
        pin = state.row_pin.reshape(state.rows.shape[0] * state.rows.shape[1], self.R)

        if wm_grad:
            enc = self.encode_action_ctx(a_unit)
            return self._imagine_core(self.cell, self.act_film, state.rows, enc, a_unit, focus, gs, pin, clock)

        # Anti-wishful-thinking planning path: detach ALL model params and start state
        rows_d = state.rows.detach()
        focus_d = focus.detach()
        gs_d = gs.detach()
        # Functional call with detached parameters so gradients can ONLY flow to `a_unit`
        cell_params = {n: p.detach() for n, p in self.cell.named_parameters()}
        cell_bufs = dict(self.cell.named_buffers())
        ctx_params = ({n: p.detach() for n, p in self.ctx_read.named_parameters()}
                      if self.ctx_read is not None else None)
        film_params = ({n: p.detach() for n, p in self.act_film.named_parameters()}
                       if self.act_film is not None else None)

        # Run context-blind action encoding with detached weights
        B = a_unit.shape[0]
        dev = a_unit.device
        at = a_unit[:, None, :]
        ctx = Context(
            tokens=at,
            mask=torch.ones(B, 1, dtype=torch.bool, device=dev),
            support=torch.ones(B, 1, device=dev),
            source=torch.full((B, 1), int(Source.SIGHT), dtype=torch.long, device=dev),
            age_s=torch.zeros(B, 1, device=dev),
            epoch=torch.zeros(B, dtype=torch.long, device=dev),
            q_hash=torch.zeros(B, dtype=torch.long, device=dev),
        )
        # Use torch.func.functional_call on a lightweight wrapper module
        class _DetachedRunner(nn.Module):
            def __init__(self_r, parent):
                super().__init__()
                self_r.cell = parent.cell
                self_r.ctx_read = parent.ctx_read
                self_r.act_film = parent.act_film
                self_r._parent = [parent]

            def forward(self_r, a_u):
                enc_d = self_r.cell.encode_context(ctx)
                return self_r._parent[0]._imagine_core(
                    self_r.cell, self_r.act_film, rows_d, enc_d, a_u, focus_d, gs_d, pin, clock
                )

        runner = _DetachedRunner(self)
        all_params = {f"cell.{k}": v for k, v in cell_params.items()}
        if ctx_params is not None:
            all_params.update({f"ctx_read.{k}": v for k, v in ctx_params.items()})
        if film_params is not None:
            all_params.update({f"act_film.{k}": v for k, v in film_params.items()})
        all_bufs = {f"cell.{k}": v for k, v in cell_bufs.items()}
        return torch.func.functional_call(runner, (all_params, all_bufs), (a_unit,))

    @torch.no_grad()
    def rollout(self, state_0, x0: torch.Tensor, acts_k: torch.Tensor):
        """Open-loop k-step rollout initialized ONCE from (state_0, x0). Zero intermediate peeking!
        Returns dict with pred_res [B,16,16,3], pred_abs [B,16,16,3], final_rows [B,1,R,D].
        """
        start_dec = self.dec(state_0.rows[:, 0])
        st = state_0
        for j in range(acts_k.shape[1]):
            o = self.imagine_step(st, acts_k[:, j], wm_grad=True)
            st = dataclasses.replace(st, rows=o.next_rows)
        pred_abs = self.dec(st.rows[:, 0])
        pred_res = x0 + (pred_abs - start_dec)
        return {"pred_res": pred_res, "pred_abs": pred_abs, "final_rows": st.rows}

    def board_burial_stats(self, rows_batch: torch.Tensor) -> dict:
        """Diagnostic: measure static offset RMS vs cross-screen per-coordinate spread RMS."""
        r = rows_batch.detach().float()
        if r.dim() == 4:
            r = r[:, 0]
        static_rms = float(r.mean(0).pow(2).mean().sqrt())
        spread_rms = float(r.std(0, correction=0).pow(2).mean().sqrt())
        return {
            "static_rms": static_rms,
            "spread_rms": spread_rms,
            "burial_ratio": static_rms / max(spread_rms, 1e-12),
        }
