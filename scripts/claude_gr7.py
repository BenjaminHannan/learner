#!/usr/bin/env python3
"""gr-7: gr-6's reader trained for 3 more epochs (Plain-English puzzles thread, 2026-09-27; PASSMARKS-gr7.md).

The one change from gr-6: gr-6's adapter is loaded and trained for 3 more epochs on gr-6's training rows, at the same
constant learning rate (gr-5's recipe has no warmup and no schedule), with fresh AdamW moments and shuffle/dropout seed
5070. The prompt, grammar, greedy decode, rows, dev split and panel are gr-6's. Dev is one pass that prints every count
PASSMARKS-gr7 decides on and the outcome (PROVED-WRONG, INCONCLUSIVE, DEV-FAIL or PASS). If it passes, the unread gr-6
panel is run once with L7 in L6's place, and scored under gr-6's marks.

  python -B scripts/claude_gr7.py --selftest
  python -B scripts/claude_gr7.py train --model BASE --rows ROWS.jsonl --start GR6_ADAPTER.pt --adapter ADAPTER.pt
  python -B scripts/claude_gr7.py dev --model BASE --rows ROWS.jsonl --adapter ADAPTER.pt --loss LOSS
  python -B scripts/claude_gr7.py run --task squares|lookalikes|unseen|general --arm L7|G5 --model BASE \
      --adapter ADAPTER.pt --panel-dir PD --out OUT
  python -B scripts/claude_gr7.py score --out OUT --panel-dir PD --score SCOREDIR
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_gr5 as G5  # noqa: E402

SEED7 = 5070
EXTRA_EPOCHS = 3
ARM = "L7"


# ------------------------------------------------------------------ train: continue from gr-6's adapter
def train(a) -> None:
    import claude_sleep02c as SL
    import torch
    one_b = G5.load(a.model, a.start)                       # gr-6's A and B copied into the LoRA layers
    rows = [r for r in G5._load(a.rows) if r["split"] == "train"]
    params = [p for p in one_b.model.parameters() if p.requires_grad]
    assert params and len(params) == 2 * len(SL.lora_mods(one_b.model)), "gr7: only the LoRA A and B may train"
    opt = torch.optim.AdamW(params, lr=G5.LR)                # fresh moments; the same constant rate
    t0 = time.time()
    per_epoch, done = G5._steps(one_b, rows, EXTRA_EPOCHS, SEED7, opt)
    torch.save([(m.A.detach().cpu(), m.B.detach().cpu()) for m in SL.lora_mods(one_b.model)], a.adapter)
    print(json.dumps({"device": one_b.dev, "train_rows": len(rows), "examples_seen": done,
                      "mean_loss_by_epoch_4_to_6": per_epoch, "epoch6_loss": per_epoch[-1],
                      "minutes": round((time.time() - t0) / 60, 1)}))


# ------------------------------------------------------------------ dev: one pass, the PASSMARKS-gr7 outcome
def outcome(st, epoch6_loss):
    old, dev = st["heldout_square_gr5rows_exact"], st["heldout_square_exact"]
    if old <= 66:
        return "PROVED-WRONG " + ("interference-or-capacity" if epoch6_loss <= 0.001 else "optimiser-still-slow")
    if old in (67, 68) or 105 <= dev <= 110:
        return "INCONCLUSIVE"
    if st["heldout_none_wrong"] > 0 or dev <= 104:
        return "DEV-FAIL"
    return "PASS"


def dev(a) -> None:
    import claude_rsn358b2_bridge as B
    import claude_rt02d as RT
    cp = G5.Copier5(G5.load(a.model, a.adapter), plain=False)
    items = []
    sm = G5.ROOT / "artifacts/claude-panel-rsn358b3-smoke-20260926"
    ans = {r["id"]: r for r in map(json.loads, (sm / "answers.jsonl").read_text().splitlines())}
    items += [("smoke", r["message"], ans[r["id"]]["puz"]) for r in map(json.loads, (sm / "panel.jsonl").read_text()
                                                                         .splitlines())][:10]
    for s in (4, 5, 6, 7):
        items += [("fresh", q["text"], q["puz"]) for q in B.make_requests(487000 + s, 6, s, False)]
    items = items[:10] + [it for it in items[10:] if it[0] == "fresh"][:10]
    items += [("nosquare", t, None) for t, _ in RT.dev_cases()][:10]
    for r in G5._load(a.rows):
        if r["split"] == "dev" and r["grid"] is not None:
            src = "new" if r["kind"] == "sq_new" else "gr5rows"
            items.append((("heldout_square", "heldout_square_" + src), r["text"], r["grid"]))
        elif r["split"] == "dev":
            items.append(("heldout_none", r["text"], None))
        elif r["split"] == "devlayout":
            items.append(("devlayout_square", r["text"], r["grid"]))
    st = Counter()
    t0 = time.time()
    for kinds, text, truth in items:
        g = cp.copy(text)["grid"]
        for kind in (kinds if isinstance(kinds, tuple) else (kinds,)):
            st[kind + "_n"] += 1
            st[kind + "_exact"] += int(g == truth)
            st[kind + "_wrong"] += int(g is not None and g != truth)
            st[kind + "_none"] += int(g is None)
    st["seconds_per_message"] = round((time.time() - t0) / max(1, len(items)), 1)
    loss = float(a.loss)
    res = dict(sorted(st.items()))
    res["epoch6_loss"] = loss
    res["epoch6_loss_at_most_0.001"] = loss <= 0.001
    res["outcome"] = outcome(st, loss)
    res["dev_gate"] = "PASS" if res["outcome"] == "PASS" else "FAIL"
    print(json.dumps(res))


# ------------------------------------------------------------------ registered run and score (gr-6's, with L7)
def run(a) -> None:
    import claude_dl1_nights as D1
    if a.arm not in (ARM, "G5"):
        raise SystemExit("gr7: --arm is L7 (the gr-7 adapter) or G5 (the gr-5 adapter)")
    if not a.adapter:
        raise SystemExit("gr7: --adapter is required")
    if a.arm == "G5" and a.task == "general":
        raise SystemExit("gr7: G5 runs squares, lookalikes and unseen only")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{a.arm}_{a.task}.jsonl"
    if path.exists():
        raise SystemExit(f"gr7: {path} exists (each run is launched once)")
    if a.task == "general":
        items = [{"id": "gen-%03d" % i, "text": it["q"]} for i, it in enumerate(D1.harm_panel())]
    else:
        items = G5._load(Path(a.panel_dir) / f"{a.task}.jsonl")
    cp = G5.Copier5(G5.load(a.model, a.adapter), plain=False)
    with path.open("w", encoding="utf-8") as f:
        for it in items:
            t0 = time.time()
            r = cp.copy(it["text"])
            f.write(json.dumps({"id": it["id"], "grid": r["grid"], "complete": r["complete"],
                                "ms": round((time.time() - t0) * 1000, 1)}) + "\n")
            f.flush()
    rows = G5._load(path)
    print(json.dumps({"arm": a.arm, "task": a.task, "rows": len(rows),
                      "read_as_square": sum(r["grid"] is not None for r in rows)}))


def score(a) -> None:
    import claude_dl1_nights as D1
    import claude_puzzle_reader as R
    out, pd = Path(a.out), Path(a.panel_dir)
    tasks = ("squares", "lookalikes", "unseen")
    panel = {t: G5._load(pd / f"{t}.jsonl") for t in tasks}
    got = {arm: {t: {r["id"]: r for r in G5._load(out / f"{arm}_{t}.jsonl")} for t in tasks} for arm in (ARM, "G5")}
    got[ARM]["general"] = {r["id"]: r for r in G5._load(out / f"{ARM}_general.jsonl")}
    for arm in (ARM, "G5"):
        for t in tasks:
            assert set(got[arm][t]) == {r["id"] for r in panel[t]}, (arm, t)
    assert len(got[ARM]["general"]) == 300
    res = {}
    for arm in (ARM, "G5", "C"):
        rd = (lambda t, r: (R.read_latin(r["text"]) or {}).get("grid")) if arm == "C" else \
             (lambda t, r, arm=arm: got[arm][t][r["id"]]["grid"])
        x = {}
        for t in ("squares", "unseen"):
            g = {r["id"]: rd(t, r) for r in panel[t]}
            x[t + "_exact"] = sum(int(g[r["id"]] == r["grid"]) for r in panel[t])
            x[t + "_wrong"] = sum(int(g[r["id"]] is not None and g[r["id"]] != r["grid"]) for r in panel[t])
            x[t + "_none"] = sum(int(g[r["id"]] is None) for r in panel[t])
            by = Counter()
            for r in panel[t]:
                e = int(g[r["id"]] == r["grid"])
                by[f"size{r['size']}"] += e
                by["broken" if r["broken"] else "whole"] += e
                if t == "squares":
                    by[f"layout_{r['layout']}"] += e
                else:
                    by[f"format_{r['format_id']:02d}"] += e
                    by["sep_seen" if r["sep_seen"] else "sep_new"] += e
            x[t + "_exact_by"] = dict(sorted(by.items()))
        x["lookalikes_false_square"] = sum(int(r["square"] is None and rd("lookalikes", r) is not None)
                                           for r in panel["lookalikes"])
        if arm != "C":
            sq = [r for r in panel["lookalikes"] if r["square"] is not None]
            x["lookalikes_with_square_read_as_square"] = sum(int(rd("lookalikes", r) is not None) for r in sq)
            x["lookalikes_with_square_same_grid"] = sum(int(rd("lookalikes", r) == r["square"]) for r in sq)
            x["lookalikes_with_square_read_as_none"] = sum(int(rd("lookalikes", r) is None) for r in sq)
        if arm == ARM:
            x["general_read_as_square"] = sum(int(r["grid"] is not None) for r in got[ARM]["general"].values())
        elif arm == "C":
            x["general_read_as_square"] = sum(int(R.read_latin(it["q"]) is not None) for it in D1.harm_panel())
        res[arm] = x
    L = res[ARM]
    res["unseen_n_sep_seen"] = sum(int(r["sep_seen"]) for r in panel["unseen"])
    res["incomplete_L7"] = sum(int(not r["complete"]) for t in got[ARM] for r in got[ARM][t].values())
    res["lookalikes_truth_none"] = sum(int(r["square"] is None) for r in panel["lookalikes"])
    res["ms_median_squares_L7"] = sorted(r["ms"] for r in got[ARM]["squares"].values())[50]
    res["marks"] = {"R1": L["squares_exact"] >= 97, "R2": L["lookalikes_false_square"] <= 1,
                    "R3": L["squares_wrong"] <= 1, "R4": L["general_read_as_square"] == 0,
                    "U1": L["unseen_exact"] >= 48, "U2": L["unseen_wrong"] <= 2}
    res["gr7_pass"] = all(res["marks"][k] for k in ("R1", "R2", "R3", "R4"))
    res["gr7U_pass"] = res["marks"]["U1"] and res["marks"]["U2"]
    res["proved_wrong_L7_U1_not_above_G5"] = not (L["unseen_exact"] > res["G5"]["unseen_exact"])
    res["prediction_L7_U1_at_least_G5_plus_6"] = L["unseen_exact"] >= res["G5"]["unseen_exact"] + 6
    sd = Path(a.score)
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "gr7_score.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: ({kk: vv for kk, vv in v.items() if not kk.endswith("_by")} if k in (ARM, "G5", "C")
                          else v) for k, v in res.items()}))


def selftest() -> None:
    n = 0
    def st(**kw):
        return Counter(dict(dict(heldout_square_gr5rows_exact=71, heldout_square_exact=112, heldout_none_wrong=0), **kw))
    assert outcome(st(), 0.0005) == "PASS"
    assert outcome(st(heldout_square_gr5rows_exact=66), 0.0005) == "PROVED-WRONG interference-or-capacity"
    assert outcome(st(heldout_square_gr5rows_exact=60), 0.004) == "PROVED-WRONG optimiser-still-slow"
    assert outcome(st(heldout_square_gr5rows_exact=68), 0.0005) == "INCONCLUSIVE"
    assert outcome(st(heldout_square_exact=108), 0.0005) == "INCONCLUSIVE"
    assert outcome(st(heldout_square_exact=104), 0.0005) == "DEV-FAIL"
    assert outcome(st(heldout_none_wrong=1), 0.0005) == "DEV-FAIL"
    n += 1
    print(f"gr7 selftest {n}/{n}")


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        selftest()
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["train", "dev", "run", "score"])
    for k in ("model", "rows", "adapter", "start", "loss", "out", "task", "arm", "panel-dir", "score"):
        ap.add_argument("--" + k, default="")
    a = ap.parse_args()
    {"train": train, "dev": dev, "run": run, "score": score}[a.cmd](a)


if __name__ == "__main__":
    main()
