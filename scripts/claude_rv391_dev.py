#!/usr/bin/env python3
"""rv-391 DEV (thought-memory thread, 2026-09-26): which signal from the loop net itself tells a wrong written guess
from a right one? Unregistered measurement on PRACTICE grids only (rv-390's p-grids6/p-grids7, seeds 39113-39114);
no test grid is touched. It decides which trigger the registered go-back test (rv-391) uses.

Why: rv-387 (artifacts/claude-rv387-20260926/RESULTS.md): going back when the stop head q falls never fired, because q
rises after anything is written on the page. Brain first (Ben, 16:05 UTC): people go back when something clashes, not
when they feel less sure; a frontal region (anterior cingulate cortex) responds to conflict and errors and triggers a
change of strategy. Textbook-level; the mapping to this net is a guess. So the candidates are conflict signals the net
produces itself, measured 8 rounds after each guess (the next check round), over the cells that were open when the
guess was written:
  dq          change in the stop head q (rv-387's trigger; a drop = wrong)
  d_mean_ent  change in the mean read-out entropy over those cells (a rise = two answers competing = wrong)
  d_max_ent   change in the largest read-out entropy over those cells
  flips       how often those cells' top symbol changed during the 8 rounds (an unsettled net = wrong)
  p_written   the net's own read-out probability of the written symbol at the written cell (low = the net "wants"
              something else there = wrong; silent if the net just copies what is written)
  clash       rule-based comparison only, never a candidate under Ben's 16:04 redirect: duplicate symbols in a row or
              column of the page plus the net's read-out
Right/wrong uses each practice item's own solution (fine for practice; the registered test's trigger never sees it).
The search is rv-387's GUESS (claude_rv390.Worker logic), instrumented; it never goes back.

  python -B scripts/claude_rv391_dev.py measure --ckpt F --out F.json [--rounds 96]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import claude_rv390 as W  # noqa: E402

V = W.V
SETS = ["p-grids7", "p-grids6"]
SIGNALS = {  # name -> sign, so that a larger signed value should mean "wrong"
    "dq": -1, "d_mean_ent": 1, "d_max_ent": 1, "flips": 1, "p_written": -1, "clash_rule_based": 1}


def ent(p):
    return -(p * p.clamp_min(1e-9).log()).sum(-1)


def clash(page, it, arg, idx_open, names_set, Wd):
    s = it.size
    g = [row[:s] for row in page.tokens[:s]]
    for i in idx_open:
        r, c = divmod(i, Wd)
        t = arg[i]
        g[r][c] = t if t in names_set else -1
    dup = 0
    for line in g + [[g[r][c] for r in range(s)] for c in range(s)]:
        vals = [t for t in line if t >= 0]
        dup += len(vals) - len(set(vals))
    return dup


@torch.no_grad()
def measure_item(w, it, rounds):
    E, net = w.E, w.net
    names = [E.SYM + n for n in it.meta["names"]]
    names_set = set(names)
    Wd = len(it.tokens[0])
    page = W.AnyPage(it, E)
    e, (dr, dc) = w.embed(page)
    h = torch.zeros_like(e)
    rows, pend, since, prev, solved = [], None, 0, None, False
    for used in range(1, rounds + 1):
        h = net.step(h, e, dr, dc)
        lg, qq = net.read(h)
        q = float(torch.sigmoid(qq.float())[0])
        arg = lg[0].argmax(-1)
        if pend is not None and prev is not None:
            pend["flips"] += int((arg[pend["idx_t"]] != prev[pend["idx_t"]]).sum())
        prev = arg
        solved = E.check(it, w.final(page, arg.tolist()))
        since += 1
        at_check = since >= V.CHECK_EVERY
        if pend is not None and (solved or at_check or used == rounds):
            p = torch.softmax(lg[0][pend["idx_t"]][:, names].float(), -1)
            r, c = pend["cell"]
            pw = float(torch.softmax(lg[0][r * Wd + c, names].float(), -1)[names.index(pend["tok"])])
            rows.append({"k": pend["k"], "right": pend["right"], "rounds_after": used - pend["round"],
                         "dq": q - pend["q0"], "d_mean_ent": float(ent(p).mean()) - pend["h0"],
                         "d_max_ent": float(ent(p).max()) - pend["m0"], "flips": pend["flips"], "p_written": pw,
                         "clash_rule_based": clash(page, it, arg.tolist(), pend["idx"], names_set, Wd),
                         "solved_next": solved})
            pend = None
        if solved:
            break
        if not at_check:
            continue
        since = 0
        if q >= V.CUT:
            continue
        cell, cands = w.pick(page, lg[0], names)
        if cell is None:
            continue
        r, c = cell
        tok = cands[0]
        page.write(r, c, tok)
        idx = [rr * Wd + cc for rr, cc in page.open_cells()]
        if idx:
            p0 = torch.softmax(lg[0][idx][:, names].float(), -1)
            pend = {"k": sum(1 for _ in page.written) - 1, "cell": cell, "tok": tok, "right": tok == it.target[r][c],
                    "round": used, "q0": q, "h0": float(ent(p0).mean()), "m0": float(ent(p0).max()), "flips": 0,
                    "idx": idx, "idx_t": torch.tensor(idx, device=h.device)}
        e, (dr, dc) = w.embed(page)
    return rows, solved


def auc(wrong, right):
    """P(a wrong guess's signed signal > a right guess's), ties count half."""
    if not wrong or not right:
        return None
    rs = sorted(right)
    import bisect
    tot = 0.0
    for x in wrong:
        lo, hi = bisect.bisect_left(rs, x), bisect.bisect_right(rs, x)
        tot += lo + 0.5 * (hi - lo)
    return round(tot / (len(wrong) * len(rs)), 4)


def summarise(rows):
    out = {"guesses": len(rows), "wrong": sum(not r["right"] for r in rows),
           "first_guesses": sum(r["k"] == 0 for r in rows)}
    for sub, rr in (("all", rows), ("first", [r for r in rows if r["k"] == 0])):
        out[sub] = {s: auc([sg * r[s] for r in rr if not r["right"]], [sg * r[s] for r in rr if r["right"]])
                    for s, sg in SIGNALS.items()}
    return out


def measure(a):
    _, R, E = W.mods()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    net = R.load(a.ckpt, dev).eval()
    w = W.Worker(net, E, dev)
    items = W.load(R, a.day, SETS)
    res = {"ckpt": str(a.ckpt), "sha256": V.sha256(a.ckpt), "rounds": a.rounds, "sets": {}}
    all_rows = []
    for name in SETS:
        d = W.day_pass(net, R, E, items[name], dev)
        unf = [it for it, r in zip(items[name], d) if not r["right"]][:a.limit or None]
        rows, solved = [], 0
        for i, it in enumerate(unf):
            rr, sv = measure_item(w, it, a.rounds)
            solved += sv
            rows += [dict(x, set=name, item=i) for x in rr]
        res["sets"][name] = dict(summarise(rows), unfinished=len(unf), solved=solved)
        all_rows += rows
        print(name, json.dumps(res["sets"][name]), flush=True)
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    Path(a.out).with_suffix(".rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in all_rows))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["measure"])
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--day", default=str(ROOT / "artifacts/claude-rv390-20260926/day"))
    ap.add_argument("--rounds", type=int, default=96)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    measure(a)


if __name__ == "__main__":
    main()
