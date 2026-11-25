"""Param counts: tall vs 4-wide at matched total params (meta build, no weights). Uses vendored v2 code read-only."""
import sys, json
sys.path.insert(0, sys.argv[1])  # 5-scale-recipe dir (vendor + scale)
sys.path.insert(0, sys.argv[1] + "/vendor")
from dataclasses import replace
from scale.sizes import make_cfg
from premonition_core_v2.board_swarm import build, build_on_meta, active_param_count

def count(cfg):
    m = build_on_meta(lambda: build(cfg)); t, e, a = active_param_count(m); return t, a

out = {}
for name, d, L in [("S_tall", 320, 6), ("P_tall", 896, 16)]:
    base = make_cfg("S" if name == "S_tall" else "P")
    t, a = count(base); out[name] = dict(d=d, blocks=L, total_M=t/1e6, active_M=a/1e6)
    # search d (multiple of 64, heads = d//64) for 4 blocks matching total
    best = None
    for dw in range(d, 4 * d + 1, 64):
        c = replace(base, d_inner=dw, n_blocks=4, n_heads=dw // 64, expert_hidden=dw)
        tw, aw = count(c)
        if best is None or abs(tw - t) < abs(best[1] - t): best = (dw, tw, aw)
    out[name.replace("tall", "wide4")] = dict(d=best[0], blocks=4, total_M=best[1]/1e6, active_M=best[2]/1e6)
print(json.dumps(out, indent=1))
