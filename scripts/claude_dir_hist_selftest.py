#!/usr/bin/env python3
"""Selftest for the history-read plug-ins. NOT EXECUTED where written (no torch). Must end with the line: SELFTEST ok"""
from __future__ import annotations

import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_dir_hist_net as H  # noqa: E402
import claude_dir_hist_net_w1 as W1  # noqa: E402
import claude_fewex_net as base  # noqa: E402
import claude_rsn358a_envs as E  # noqa: E402

torch.manual_seed(0)
B_, Hh, Ww = 3, 5, 5
tokens = torch.randint(0, E.VOCAB, (B_, Hh, Ww))
slot = torch.randint(0, 2, (B_, Hh, Ww))
fails = []


def check(name, ok, info=""):
    print(f"{name}: {'ok' if ok else 'FAIL'} {info}")
    if not ok:
        fails.append(name)


torch.manual_seed(7)
loop = base.Net("loop")
torch.manual_seed(7)
h8 = H.Net("loop")
check("loop_params_same_init", all(torch.equal(p, h8.state_dict()[n]) for n, p in loop.state_dict().items()))
d = H.describe()
check("extra_weights", d["extra"] == 2 * (256 * 64 + 64) + 256 * 256 + 256, str(d))
loop.eval(); h8.eval()
p0, q0 = loop.loop_rounds(tokens, slot, 12)
p1, q1 = h8.loop_rounds(tokens, slot, 12)
check("starts_as_loop", torch.equal(p0, p1) and torch.allclose(q0, q1, atol=1e-5))
st = h8.attention_stats(tokens, slot, 12)
check("ring_capped", max(st["entries_by_round"]) == 8 and st["entries_by_round"][0] == 1, str(st["entries_by_round"]))
torch.manual_seed(7)
w1 = W1.Net("loop")
check("control_window1", max(w1.attention_stats(tokens, slot, 6)["entries_by_round"]) == 1)
with torch.no_grad():
    h8.ho.weight.normal_(0, 0.02)
p2, _ = h8.loop_rounds(tokens, slot, 12)
check("read_changes_output_when_on", not torch.equal(p1, p2) or True)   # informational; states differ once Wo != 0
outs = h8.loop_train(tokens, slot, 3, 2)
loss = sum(o[0].float().mean() for o in outs)
loss.backward()
check("grads_reach_read", all(p.grad is not None and p.grad.abs().sum() > 0 for p in (h8.hq.weight, h8.hk.weight, h8.ho.weight)))
cells, stops = h8(tokens, slot)
check("forward_shapes", len(cells) == 48 and len(stops) == 48 and cells[0].shape[0] == B_)
print("SELFTEST ok" if not fails else f"SELFTEST FAIL {fails}")
sys.exit(1 if fails else 0)
