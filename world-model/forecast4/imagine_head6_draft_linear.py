"""STEP 6 variant: imagination gets its OWN zero-initialised output layer `imagine_out` (Linear d->D) on top of the
SHARED trunk (no imagine_alpha). Zero init = starts as "board unchanged" but, unlike a zero scale, its weights get
direct gradients. Everything else as step 5.
P7 EXPERIMENTAL copy of BoardCell._imagine_impl (premonition_core_v2/board_swarm.py:551-574) with a DAMPED update.
The canonical core is NOT edited; forecast3.py calls damped_imagine() instead of cell.imagine().
Change vs the original (everything else copied as is):
  1. the imagined update uses the SAME doorman-gated rule as run_tick (board_swarm.py:443-480): slow rows move by
     gate * delta (gate * gate_scale), pinned rows do not move, no noise;
  2. focus comes from the board state (as run_tick), not a hard-coded 1.0 (which switched on the MoE FiLM path that
     reading never uses);
  3. ReZero-style damping: the imagined change is scaled by a learnable per-row scalar `imagine_alpha` [R], initialised
     to 0.02 (~ real change / raw imagined change), applied after the gate, so imagination starts close to "the board
     stays the same" but has live gradients (Neon step-5 bug hunt: alpha=0 is a zero-gradient saddle). (Probe: the gate alone left
     the imagined change at rms 0.35 while real next-frame boards differ by ~0.3 sd per coordinate.)"""
import torch
from premonition_core_v2.board_swarm import ImagineOutput, ThinkMode, board_summary

def add_head(cell):
    if not hasattr(cell, "imagine_out"):
        lin = torch.nn.Linear(cell.d, cell.D).to(device=cell.init_rows.device, dtype=cell.init_rows.dtype)
        torch.nn.init.zeros_(lin.weight); torch.nn.init.zeros_(lin.bias); cell.add_module("imagine_out", lin)

def damped_imagine(self, state, enc, action_embed, clock=None):
    rows = state.rows; B, K, R, D = rows.shape; N = B * K; ns = self.ns
    bidx = torch.arange(B, device=rows.device).repeat_interleave(K)
    x0 = rows.reshape(N, R, D)
    a = action_embed.reshape(B, 1, D).expand(B, K, D) if action_embed.dim() == 2 else action_embed
    a = a.reshape(N, D).to(x0.dtype)
    rd = self._reading(clock, B, rows.device)
    cemb = self.clock_enc(rd)[bidx].to(x0.dtype)
    mode = self.mode_emb.weight[int(ThinkMode.IMAGINE_NEXT_STATE)].to(x0.dtype)
    h = (self.in_proj(x0) + self.row_type_emb(self.row_type)[None].to(x0.dtype)
         + self.row_pos_emb[None].to(x0.dtype) + mode + cemb[:, None])
    ha = self.action_in(a) + self.action_pos.to(x0.dtype) + mode + cemb
    h_all = torch.cat([h, ha[:, None]], dim=1)
    mem = enc.memory
    age_now = mem["age0"][bidx] + rd.elapsed_s.float()[bidx][:, None]
    focus = state.focus.reshape(-1).to(x0.dtype)                                   # CHANGE 2
    h_all, aux_loss, counts, _ = self._trunk(h_all, mem, bidx, focus, age_now, None, R)
    hn = self.norm_f(h_all)
    delta = (self.imagine_out(hn[:, :R]) * self.imagine_scale).to(x0.dtype)   # STEP 6: own output layer, in units of
    # the per-coordinate spread of REAL boards (imagine_scale [R, D], set by the harness from train boards)
    al = torch.ones(1, R, 1, device=x0.device, dtype=x0.dtype)   # CHANGE 3: applied AFTER the gate (the gate sees the undamped proposal)
    gs = state.gate_scale.reshape(-1); pin = state.row_pin.reshape(N, R)          # CHANGE 1 (copied from run_tick)
    if self.learned_sticky:
        prop = x0 + delta
        logit = self.gate(torch.cat([x0, prop], dim=-1)).squeeze(-1) + self.row_bias[None].to(x0.dtype)
        g = torch.sigmoid(logit)
        g = torch.cat([g[:, :ns] * gs[:, None].to(g.dtype), g[:, ns:]], dim=1)
        g = torch.where(pin, torch.zeros_like(g), g)
        next_rows = (x0.float() + al.float() * g.float()[..., None] * delta.float()).to(x0.dtype)
    else:
        slow0, fast0 = x0[:, :ns], x0[:, ns:]
        d_s, d_f = delta[:, :ns], delta[:, ns:]
        prop = slow0 + d_s
        g_slow = torch.sigmoid(self.gate(torch.cat([slow0, prop], dim=-1)).squeeze(-1)) * gs[:, None].to(prop.dtype)
        g_slow = torch.where(pin[:, :ns], torch.zeros_like(g_slow), g_slow)
        slow = (slow0.float() + al[:, :ns].float() * g_slow.float()[..., None] * d_s.float()).to(x0.dtype)
        fast = torch.where(pin[:, ns:][..., None], fast0, fast0 + al[:, ns:].to(x0.dtype) * d_f)
        next_rows = torch.cat([slow, fast], dim=1)
    z_pred = board_summary(x0, self.ns) + self.imagine_head(hn[:, R]).to(x0.dtype)
    return ImagineOutput(z_pred=z_pred.view(B, K, D), next_rows=next_rows.view(B, K, R, D), aux_loss=aux_loss,
                         expert_counts=counts)
