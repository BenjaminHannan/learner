#!/usr/bin/env python3
"""dl-4: does a KL anchor to the base on general text stop the slow forgetting that copy-practice nights cause?
(Fix-sleep thread, 2026-09-26; marks: artifacts/claude-dl4-20260926/PASSMARKS.md)

Why. dl-2 (registered PASS): a week of copy-practice nights lifted right guesses on fresh puzzles 64 -> 237/249,
but lost 26 of the 200 general panel items the base got right. dl-3 (registered FAIL, artifacts/claude-dl3-20260926/)
mixed the base's own GREEDY answers to base-written general questions into each night as ordinary copy targets; it
did not cut losses (night 7: 20/36 vs no-replay 39/24) and its drift from the base on general replies roughly doubled
(KL 0.28 vs 0.13-0.17), already at night 1 (0.15-0.17 vs 0.03-0.04). Likely cause (suggested, not shown): copying the
base's single greedy answer sharpens the model instead of keeping it where it was. Research (REPORT.md Q1-Q3: RL's
Razor, forgetting tracks KL to the base; Dark Experience Replay keeps old OUTPUT DISTRIBUTIONS, not only old answers)
points to matching the base's whole next-token distribution instead.

ONE change from dl-2's S arm: each night also trains a KL ANCHOR on as many general items as puzzle examples. An
anchor item is a question the BASE wrote + the BASE's own answer tokens (dl-3's pool recipe, a new seed); its loss is
KL(base || current) over the full vocabulary at every answer position, where "base" is the same network with every
LoRA scale set to 0 (no second model). Puzzle items keep dl-2's cross-entropy. Both kinds are shuffled together
through dl-2's loop (3 epochs, lr 2e-4, batch 8). Arms:
  S  dl-2's night unchanged (claude_dl1_nights.train_copy).
  K  S + the KL anchor (weight 1.0).
Same day, TEST, HARM (lost = right at base and wrong now), KL measure as dl-2/dl-3. New seeds 6 and 7, TEST seed 3690,
pool seed 3691.

  python -B scripts/claude_dl4_anchor.py --model M --out DIR        (registered run)
  python -B scripts/claude_dl4_anchor.py --selftest
  python -B scripts/claude_dl4_anchor.py --model M --out DIR --dev  (plumbing rehearsal)
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt2 as B2  # noqa: E402
import claude_dl1_nights as D1  # noqa: E402
import claude_dl3_replay as R  # noqa: E402

TEST_SEED = 3690
POOL_SEED = 3691
BETA = 1.0


def lora_mods(m):
    return [x for x in m.modules() if hasattr(x, "A") and hasattr(x, "scale")]


def anchor_loss(s, m, item):
    """KL(base || current), summed over the vocabulary, mean over the answer positions of a (question, answer) item."""
    import torch
    pr, full = R._pair_ids(s, ("replay",) + tuple(item))
    ids = full.unsqueeze(0).to(s.dev)
    lo, hi = len(pr) - 1, ids.shape[1] - 1
    mods = lora_mods(m)
    saved = [x.scale for x in mods]
    with torch.no_grad():
        for x in mods:
            x.scale = 0.0
        base = m(input_ids=ids).logits[0, lo:hi].float().log_softmax(-1)
        for x, sc in zip(mods, saved):
            x.scale = sc
    cur = m(input_ids=ids).logits[0, lo:hi].float().log_softmax(-1)
    return (base.exp() * (base - cur)).sum(-1).mean()


def train_anchor(s, m, puzzle_ex, anchor_items, seed, epochs=D1.S_RECIPE["epochs"], lr=D1.S_RECIPE["lr"]) -> dict:
    """claude_dl1_nights.train_copy's loop (same optimizer, batch 8, shuffle) over puzzle items (cross-entropy on the
    answer) and anchor items (BETA x KL to the base)."""
    import torch
    torch.manual_seed(seed)
    opt = torch.optim.AdamW([p for p in m.parameters() if p.requires_grad], lr=lr)
    rng, last, last_kl = random.Random(seed), 0.0, 0.0
    items = [("puzzle", p, e) for p, e in puzzle_ex] + [("anchor",) + tuple(it) for it in anchor_items]
    m.train()
    for ep in range(epochs):
        ex = list(items)
        rng.shuffle(ex)
        for i in range(0, len(ex), 8):
            batch = ex[i:i + 8]
            tot, kl = 0.0, 0.0
            for it in batch:
                if it[0] == "puzzle":
                    pr, full = D1._ids(s, it[1], it[2])
                    ids = full.unsqueeze(0).to(s.dev)
                    lab = ids.clone()
                    lab[0, :len(pr)] = -100
                    loss = m(input_ids=ids, labels=lab).loss / len(batch)
                else:
                    k = anchor_loss(s, m, it[1:])
                    loss = BETA * k / len(batch)
                    kl += float(k.detach())
                loss.backward()
                tot += float(loss.detach())
            opt.step()
            opt.zero_grad()
            last, last_kl = tot, kl
    m.eval()
    return {"examples": len(items), "anchor": len(anchor_items), "last_loss": round(last, 4),
            "last_batch_anchor_kl": round(last_kl, 5)}


def run_arm(s, arm, seed, a, test, panel, replies, base_harm, pool) -> dict:
    s.torch.manual_seed(seed)
    m = D1.fresh_model(s)
    nights, prev = [], base_harm
    for d in range(1, a.nights + 1):
        t0 = time.time()
        day = B2.puzzles(D1.DAY_SEED + a.seed_shift + 100 * seed + d, a.n_day)
        groups = D1.gather(s, m, day, a.n_guess)
        right = D1.copy_examples(groups)
        rec = {"night": d, "day_greedy_right": sum(g["greedy_right"] for g in groups),
               "day_right_guesses": sum(sum(g["rewards"]) for g in groups), "right_examples": len(right)}
        if not right:
            rec["train"] = {"examples": 0}
        elif arm == "S":
            rec["train"] = D1.train_copy(s, m, right, seed * 1000 + d)
        else:
            anc = random.Random(seed * 1000 + d).sample(pool, min(len(pool), len(right)))
            rec["train"] = train_anchor(s, m, right, anc, seed * 1000 + d)
        meas = D1.measure(s, m, test, a.n_guess_test, panel, replies)
        rec["test"] = {k: meas[k] for k in ("lucky", "reached", "greedy")}
        rec["harm"] = D1.flips(base_harm, meas["harm"])
        rec["harm_vs_prev"] = D1.flips(prev, meas["harm"])
        rec["harm_items"] = meas["harm"]
        prev = meas["harm"]
        rec["kl"] = meas["kl"]
        rec["minutes"] = round((time.time() - t0) / 60, 1)
        nights.append(rec)
        print(f"[dl4] {arm} s{seed} night {d}: " + json.dumps({k: v for k, v in rec.items() if k != "harm_items"}),
              flush=True)
    del m
    if s.dev == "cuda":
        s.torch.cuda.empty_cache()
    return {"arm": arm, "seed": seed, "nights": nights}


def score(res: dict) -> dict:
    """The registered marks (PASSMARKS.md): dl-3's F1-F5 with K in place of A."""
    sub = {"base": res["base"], "pool_size": res.get("pool_size", 0),
           "arms": [dict(r, arm="A" if r["arm"] == "K" else r["arm"]) for r in res["arms"]]}
    m3 = R.score(sub)
    return {k.replace("A_", "K_").replace(": A ", ": K ").replace(" A ", " K "): v for k, v in m3.items()}


def run(a) -> None:
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    seeds = [int(x) for x in a.seeds.split(",")]
    keys = {(tuple(p["nums"]), p["target"]) for sd in seeds for d in range(1, a.nights + 1)
            for p in B2.puzzles(D1.DAY_SEED + a.seed_shift + 100 * sd + d, a.n_day)}
    test = [p for p in B2.puzzles(TEST_SEED + a.seed_shift, a.n_test + 300)
            if (tuple(p["nums"]), p["target"]) not in keys][:a.n_test]
    panel = D1.harm_panel()[:a.n_harm]
    pool = R.make_pool(s, a.n_ask, POOL_SEED + a.seed_shift)
    res = {"config": {k: v for k, v in vars(a).items() if k != "model"}, "n_test": len(test), "n_harm": len(panel),
           "temp": D1.TEMP, "test_seed": TEST_SEED, "pool_size": len(pool), "beta": BETA}
    (out / "anchor_pool.json").write_text(json.dumps(pool, indent=0), encoding="utf-8")
    print(f"[dl4] anchor pool: {len(pool)} items", flush=True)
    base = s.model
    replies = [(q, D1.free_answer(s, q, base, 40)) for q in
               (D1.CHAT_PROMPTS + [it["q"] for it in panel[::5]])[:a.n_kl]]
    bm = D1.measure(s, base, test, a.n_guess_test, panel)
    res["base"] = {k: bm[k] for k in ("lucky", "reached", "greedy")}
    res["base"]["harm_right"] = sum(bm["harm"])
    res["base_harm_items"] = bm["harm"]
    print(f"[dl4] base: {res['base']}", flush=True)
    res["arms"] = []
    for arm in a.arms.split(","):
        for sd in seeds:
            res["arms"].append(run_arm(s, arm, sd, a, test, panel, replies, bm["harm"], pool))
            (out / "dl4_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    if set(a.arms.split(",")) >= {"S", "K"}:
        res["marks"] = score(res)
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "dl4_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res.get("marks", {}), indent=1))


def selftest() -> None:
    def arm(name, sd, lucky, lost, reached=40):
        return {"arm": name, "seed": sd, "nights": [{"test": {"lucky": v, "reached": reached},
                                                      "harm": {"lost": l}} for v, l in zip(lucky, lost)]}
    res = {"base": {"lucky": 60, "reached": 35}, "pool_size": 400,
           "arms": [arm("S", 6, [90, 100, 110, 120, 125, 130, 140], [5, 8, 12, 16, 18, 24, 26]),
                    arm("S", 7, [80, 95, 90, 110, 120, 128, 135], [6, 9, 11, 15, 20, 28, 25]),
                    arm("K", 6, [85, 100, 105, 118, 120, 125, 130], [3, 4, 6, 5, 7, 8, 9]),
                    arm("K", 7, [85, 92, 99, 110, 115, 120, 128], [4, 5, 4, 6, 8, 7, 10])]}
    m = score(res)
    assert m["verdict"] == "PASS" and not m["proved_wrong"], m
    assert any(k.startswith("F1") and ": K " in k for k in m), list(m)
    res["arms"][2]["nights"][-1]["harm"]["lost"] = 26
    assert score(res)["verdict"] == "FAIL"
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--arms", default="S,K")
    ap.add_argument("--seeds", default="6,7")
    ap.add_argument("--nights", type=int, default=7)
    ap.add_argument("--n-day", type=int, default=150)
    ap.add_argument("--n-guess", type=int, default=30)
    ap.add_argument("--n-test", type=int, default=100)
    ap.add_argument("--n-guess-test", type=int, default=20)
    ap.add_argument("--n-harm", type=int, default=300)
    ap.add_argument("--n-kl", type=int, default=60)
    ap.add_argument("--n-ask", type=int, default=1500)
    ap.add_argument("--seed-shift", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dev", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.dev:
        a.nights, a.n_day, a.n_guess, a.n_test, a.n_guess_test, a.n_harm, a.n_kl, a.n_ask = 1, 4, 4, 3, 3, 12, 4, 12
        a.seed_shift, a.seeds = a.seed_shift or 60000, "6"
    run(a)


if __name__ == "__main__":
    main()
