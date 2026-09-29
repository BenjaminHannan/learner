#!/usr/bin/env python3
"""Runs the sealed driver (claude_moe_deep_run.py) with the deep-expert configs added.

  python3 -B scripts/claude_moe_deepx_run.py selftest2                 # CPU checks of the deep experts (no training)
  python3 -B scripts/claude_moe_deepx_run.py source --cfg L8-E64-X4 --seed 0 --device cuda
  python3 -B scripts/claude_moe_deepx_run.py dev --cfg L8-E64-X4 --seed 0 --init pre --device cuda --no-stages
Every other command and flag is the sealed driver's, unchanged. Importing claude_moe_deepx_net first adds the configs
L8-E64-X4 and L8-E64-X8 to the sealed module's CFGS before the driver builds its argument parser.
"""
import json
import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402

import claude_moe_deepx_net as X  # noqa: E402,F401  (patches claude_moe_deep_net)
import claude_moe_deep_net as M  # noqa: E402

ART = Path(__file__).resolve().parents[1] / "artifacts" / "claude-moe-deepx-20260929"


def selftest2():
    torch.set_num_threads(2)
    rep, ok = {}, True
    for name, c in X.DEEPX.items():
        rep[f"{name}_per_expert"] = X.expert_weights(c["hidden"], c["xl"])
        ok &= abs(rep[f"{name}_per_expert"] / X.expert_weights(64, 1) - 1) < 0.015
    # dispatch equals a naive per-cell computation, both paths, values and gradients
    for name in X.DEEPX:
        M.set_cfg(name)
        torch.manual_seed(1)
        moe = M.MoE(256, 64, 8, 1, M.cfg()["hidden"], 0.5)
        x = torch.randn(2, 49, 256, requires_grad=True)
        fl = x.reshape(-1, 256)
        tp, ti = moe.router(fl).float().softmax(-1).topk(8, -1)
        gate = tp / tp.sum(-1, keepdim=True)

        def expert(n, j):
            e = ti[n, j]
            h = F.gelu(fl[n] @ moe.w1[e] + moe.b1[e])
            for i in range(moe.xl - 1):
                h = h + F.gelu(h @ moe.wm[i, e] + moe.bm[i, e])
            return h @ moe.w2[e] + moe.b2[e]
        ref = torch.stack([moe.shared(fl[n]) + sum(gate[n, j] * expert(n, j) for j in range(8)) for n in range(fl.shape[0])])
        gy = torch.randn(2, 49, 256)
        g2 = torch.autograd.grad((ref.view(2, 49, 256) * gy).sum(), (x, moe.w1, moe.wm, moe.router.weight), retain_graph=True)
        for path in ("padded", "segments"):
            moe.path = path
            yp = moe(x)
            g1 = torch.autograd.grad((yp * gy).sum(), (x, moe.w1, moe.wm, moe.router.weight))
            dv = float((yp.reshape(-1, 256) - ref).abs().max())
            dg = max(float((u - v).abs().max()) for u, v in zip(g1, g2))
            di = float((moe(x[:1]) - yp[:1]).abs().max())
            rep[f"{name}_{path}"] = {"value": dv, "grad": dg, "batch_indep": di}
            ok &= dv < 1e-5 and dg < 1e-4 and di < 1e-6
        # sizes, and the sealed behaviour when xl is absent
        d = M.describe(name)
        rep[f"{name}_size"] = {"stored": d["stored"], "active": d["active_per_cell_round"],
                               "stored_vs_main": d["stored"] / M.describe(M.MAIN)["stored"],
                               "active_vs_main": d["active_per_cell_round"] / M.describe(M.MAIN)["active_per_cell_round"]}
        ok &= abs(rep[f"{name}_size"]["stored_vs_main"] - 1) < 0.03 and abs(rep[f"{name}_size"]["active_vs_main"] - 1) < 0.03
    M.set_cfg(M.MAIN)
    torch.manual_seed(1)
    a = M.MoE(256, 8, 2, 1, 64, 0.5)
    b = X._Sealed(256, 8, 2, 1, 64, 0.5)
    b.load_state_dict(a.state_dict())
    z = torch.randn(2, 9, 256)
    rep["main_config_identical_to_sealed"] = float((a(z) - b(z)).abs().max())
    ok &= rep["main_config_identical_to_sealed"] == 0.0
    rep["selftest2"] = "ok" if ok else "FAIL"
    ART.mkdir(parents=True, exist_ok=True)
    (ART / "selftest2.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))
    if not ok:
        raise SystemExit("SELFTEST2-FAIL")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest2":
        selftest2()
    else:
        sys.argv[0] = str(Path(__file__).with_name("claude_moe_deep_run.py"))
        runpy.run_path(sys.argv[0], run_name="__main__")
