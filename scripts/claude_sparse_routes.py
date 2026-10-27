#!/usr/bin/env python3
"""Report-only routing diagnostic for the Test D sparse loop (the paper's mechanism).

For saved weights and a puzzle set: per block, the share of cells whose two
chosen experts differ from the previous round (none, one or both), expert use
(share of routing slots and share of cell-rounds), and experts used by under 1%
of cell-rounds. Only expert choices are read; no answer is checked or scored.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_bench as B  # noqa: E402
import claude_fewex_data as D  # noqa: E402
import claude_sparse_net as S  # noqa: E402


def load(path):
    net = S.Net("loop")
    net.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
    return net.eval()


def route_stats(net, items, rounds=48, batch=32):
    blocks = None
    for i in range(0, len(items), batch):
        t, s, _ = S.base.tensors(items[i:i + batch])
        tr = net.route_trace(t, s, rounds)                 # per block [b, n, T, 2]
        blocks = tr if blocks is None else [torch.cat([a, b], 0) for a, b in zip(blocks, tr)]
    out = []
    for tr in blocks:
        tr = tr.long()
        n_exp = S.EXPERTS
        one_hot = torch.nn.functional.one_hot(tr, n_exp).sum(-2)          # [P, n, T, E] in {0,1}
        # change between consecutive rounds: how many of this round's 2 experts are new
        kept = (one_hot[:, 1:] * one_hot[:, :-1]).sum(-1)                  # [P, n-1, T] in {0,1,2}
        new = 2 - kept
        per_pair = [{"rounds": f"{r}->{r + 1}",
                     **{k: float((new[:, r - 1] == v).float().mean()) for k, v in
                        (("none", 0), ("one", 1), ("both", 2))}} for r in range(1, rounds)]

        def span(lo, hi):
            x = new[:, lo - 2:hi - 1]
            return {k: float((x == v).float().mean()) for k, v in (("none", 0), ("one", 1), ("both", 2))}
        slot_share = one_hot.float().sum((0, 1, 2)) / (2 * one_hot.shape[0] * one_hot.shape[1] * one_hot.shape[2])
        cell_share = one_hot.float().mean((0, 1, 2))
        out.append({"change_rounds_2_to_8": span(2, 8), "change_rounds_9_to_48": span(9, rounds),
                    "change_all_pairs": span(2, rounds), "change_per_pair": per_pair,
                    "slot_share": [round(float(x), 5) for x in slot_share],
                    "cell_share": [round(float(x), 5) for x in cell_share],
                    "under_1pct_of_cells": [e for e in range(n_exp) if cell_share[e] < .01]})
    return {"puzzles": len(items), "rounds": rounds, "blocks": out}


def main(ckpts, sets, out):
    res = {}
    panel = None
    for name in sets:
        if name in ("guard_sums4", "guard_grids5"):
            items = D.old_panels(D.SOURCE_SEED + 300)[name.split("_")[1]]
        elif name == "maze9_dev":
            panel = panel or D.panels()[0]
            items = panel["dev"][9]
        else:
            raise ValueError(name)
        for ck in ckpts:
            res[f"{ck}|{name}"] = route_stats(load(ck), items)
            b = res[f"{ck}|{name}"]["blocks"]
            print(json.dumps({"ckpt": str(ck), "set": name,
                              "change_all": [x["change_all_pairs"] for x in b],
                              "under_1pct": [x["under_1pct_of_cells"] for x in b]}), flush=True)
    B.dump(out, res)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ckpt", nargs="+", required=True)
    p.add_argument("--sets", nargs="+", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--threads", type=int, default=2)
    a = p.parse_args()
    torch.set_num_threads(a.threads)
    main(a.ckpt, a.sets, a.out)
