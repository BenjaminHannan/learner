#!/usr/bin/env python3
"""rsn-358c1 (sleep research thread, 2026-09-26): does judging "thinking has settled" on the ANSWER cells only fix the
loop's stop? ONE change, evaluation only: no training, 358a's own saved loop checkpoints, fresh puzzles (never the
sealed test files in artifacts/claude-rsn358a-20260925/tests/).

Why: an outside review (Ben, 2026-09-26 01:54 and 02:11 UTC) noted that 358a v2's stop rule
(scripts/claude_rsn358a2_run.py: stop from round 3 on when p > 0.5 and the prediction is unchanged for two rounds)
compares the WHOLE predicted grid, including cells that get no training and may flicker. Here the same rule compares
only the answer cells. Everything else (checkpoint, stop head, 48-round cap, p > 0.5) is fixed.

Two fresh sets per family, 300 each:
  pick   chooses the fixed round budget (the best of 1/2/4/8/12/16/24/32/48 rounds; ties -> fewer rounds)
  check  scores: v2 rule, answer-cell rule, and the fixed budget chosen on "pick"
Families: sums4/6/8, grids5/6/7, numbers5 (numbers4's held-out hands are the sealed test, so no fresh set exists).

With --plain, the same-seed plain checkpoint is also scored on the same "check" sets (one pass, no rounds), so the
loop with the answer-cell stop can be compared with plain on fresh puzzles (marks in artifacts/claude-rsn358c-20260926/).

  python -B scripts/claude_rsn358c1_stop.py --ckpt W/loop-s1/final.pt --plain W/plain-s1/final.pt --out W/stop358c1-s1.json
  python -B scripts/claude_rsn358c1_stop.py smoke
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_envs as E  # noqa: E402
import claude_rsn358a_run as R  # noqa: E402
import claude_rsn358a2_run as V  # noqa: E402

FAMILIES = [("sums4", "sums", 4), ("sums6", "sums", 6), ("sums8", "sums", 8),
            ("grids5", "grids", 5), ("grids6", "grids", 6), ("grids7", "grids", 7), ("numbers5", "numbers", 5)]
PICK_SEED, CHECK_SEED = 36000, 36100          # + family index; the sealed tests use 35811-35832


def answer_cells(p, it):
    flat = [c for row in it.slot for c in row]
    return tuple(t for t, m in zip(p, flat) if m)


def stop_answer_cells(p, q, n, it):
    a = [answer_cells(x, it) for x in p]
    return next((r for r in range(2, n) if q[r] > 0.5 and a[r] == a[r - 1] == a[r - 2]), n - 1)


@torch.no_grad()
def rounds_table(net, items, device, bs=100):
    """per item: right at every round (list of 0/1), v2 stop round, answer-cell stop round."""
    net.eval()
    n = R.TEST_ROUNDS
    rows = []
    for i in range(0, len(items), bs):
        chunk = items[i:i + bs]
        t, s, _, env = R.tensors(chunk, device)
        preds, qs = net.loop_rounds(t, s, env, n)
        for it, p, q in zip(chunk, preds.tolist(), qs.tolist()):
            ok = [int(E.check(it, R.grid_of(p[r], it))) for r in range(n)]
            rows.append((ok, V.stop_round(p, q, n), stop_answer_cells(p, q, n, it)))
    return rows


@torch.no_grad()
def plain_right(net, items, device, bs=100):
    net.eval()
    right = 0
    for i in range(0, len(items), bs):
        chunk = items[i:i + bs]
        t, s, _, env = R.tensors(chunk, device)
        preds = net.plain_forward(t, s, env).argmax(-1).tolist()
        right += sum(E.check(it, R.grid_of(p, it)) for it, p in zip(chunk, preds))
    return right


def family_items(env, size, seed, n):
    return R.make_test(None, env, size, seed, n)


def run(a):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    net = R.load(a.ckpt, device)
    assert net.arm == "loop"
    plain = R.load(a.plain, device) if a.plain else None
    assert plain is None or plain.arm == "plain"
    res = {"ckpt": str(a.ckpt), "n": a.n, "families": {}}
    for i, (name, env, size) in enumerate(FAMILIES):
        pick = rounds_table(net, family_items(env, size, PICK_SEED + i, a.n), device)
        by_r = {r: sum(ok[r - 1] for ok, _, _ in pick) for r in R.FIXED_REPORT}
        best = max(R.FIXED_REPORT, key=lambda r: (by_r[r], -r))
        check_items = family_items(env, size, CHECK_SEED + i, a.n)
        chk = rounds_table(net, check_items, device)
        f = {"pick_fixed": {str(r): v for r, v in by_r.items()}, "budget": best,
             "fixed_budget_right": sum(ok[best - 1] for ok, _, _ in chk),
             "v2_right": sum(ok[s2] for ok, s2, _ in chk),
             "answer_cell_right": sum(ok[sa] for ok, _, sa in chk),
             "v2_mean_rounds": round(sum(s2 + 1 for _, s2, _ in chk) / len(chk), 2),
             "answer_cell_mean_rounds": round(sum(sa + 1 for _, _, sa in chk) / len(chk), 2),
             "check_fixed": {str(r): sum(ok[r - 1] for ok, _, _ in chk) for r in R.FIXED_REPORT},
             "check_any_round": sum(any(ok) for ok, _, _ in chk)}
        if plain is not None:
            f["plain_right"] = plain_right(plain, check_items, device)
        res["families"][name] = f
        print(name, json.dumps(f), flush=True)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")


def smoke(_):
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    net = R.Net("loop")
    torch.save({"arm": "loop", "seed": 0, "state": net.state_dict()}, tmp / "final.pt")
    torch.save({"arm": "plain", "seed": 0, "state": R.Net("plain").state_dict()}, tmp / "plain.pt")
    global FAMILIES
    FAMILIES = FAMILIES[:1] + FAMILIES[3:4] + FAMILIES[6:]
    run(argparse.Namespace(ckpt=tmp / "final.pt", plain=tmp / "plain.pt", out=tmp / "o.json", n=6))
    d = json.loads((tmp / "o.json").read_text())
    assert set(d["families"]) == {"sums4", "grids5", "numbers5"}
    assert all("plain_right" in f for f in d["families"].values())
    it = E.make_sum(__import__("random").Random(0), 3)
    flat = [c for row in it.slot for c in row]
    assert len(answer_cells(list(range(len(flat))), it)) == sum(flat)
    print("smoke ok", tmp)


def main():
    if sys.argv[1:] == ["smoke"]:
        return smoke(None)
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--plain", default=None)
    ap.add_argument("--n", type=int, default=300)
    run(ap.parse_args())


if __name__ == "__main__":
    main()
