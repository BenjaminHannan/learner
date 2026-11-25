"""STEP 6 (pinned 2026-11-24): the SHARED trunk, reader and readout are FROZEN; imagination gets its OWN small trainable
layers `imagine_out` = Linear(d,d) -> GELU -> Linear(d,D) with the LAST layer zero-initialised (starts as "board unchanged",
but unlike step 5's zero scale imagine_alpha the last layer gets direct gradients). Output is in units of the per-coordinate
spread of REAL train boards (imagine_scale [R,D], set by the harness). Trainable = imagine_out + action_emb/action_in/action_pos.
Experimental copy of BoardCell._imagine_impl (premonition_core_v2/board_swarm.py:551-574); canonical core NOT edited.
Kept from step 5: run_tick's doorman-gated update (pins respected, no noise) and focus from the board state.
imagine_alpha is removed (al = 1)."""
import torch
from premonition_core_v2.board_swarm import ImagineOutput, ThinkMode, board_summary

def add_head(cell):
    if not hasattr(cell, "imagine_out"):
        g = torch.Generator().manual_seed(42)  # own generator: the global RNG stream is untouched
        l1 = torch.nn.Linear(cell.d, cell.d); l2 = torch.nn.Linear(cell.d, cell.D)
        with torch.no_grad():
            l1.weight.copy_(torch.randn(l1.weight.shape, generator=g) / cell.d ** 0.5); l1.bias.zero_()
            l2.weight.zero_(); l2.bias.zero_()
        head = torch.nn.Sequential(l1, torch.nn.GELU(), l2).to(device=cell.init_rows.device, dtype=cell.init_rows.dtype)
        cell.add_module("imagine_out", head)

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
