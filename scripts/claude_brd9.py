#!/usr/bin/env python3
"""brd-9: do three nights in a row, each practised by the model that slept the night before, clear problem 7's bar?
(creative research thread, 2026-09-26; problem 7, turning lucky hits into lasting skill; follow-up to brd-5..8)

Why: one night on the model's own checked hits beat no sleep in brd-5, 6 and 7 (intervals above 0 each time) but
cleared +24 of 240 in every seed only once (brd-6). Ben's loop repeats every night. This tests the loop as a loop.

Practice: A, B, C = puzzles(seed 9, 1200) in three parts of 400 (A and B are brd-8's sets; C is new).
Per LoRA seed s (0/1/2):
- Night 1: the base model practises A (greedy, then 30 rule-kept blurts at the DEV temperature on a miss, first hit
  wins; claude_brd8.gather). N1 = LoRA from base on A's examples, 3 epochs.
- Night 2: N1 practises B. N2 = fresh LoRA from base on A + B examples, 3 epochs.
- Night 3: N2 practises C. N3 = fresh LoRA from base on A + B + C examples, 3 epochs.
The base model's practice of A is shared by all seeds. Every model is trained from the base weights on everything
kept so far (replay of all earlier days), so a later night cannot overwrite an earlier one.
Test: a panel FIXED BEFORE REGISTRATION (artifacts/claude-brd9-20260926/test_puzzles.jsonl); 30 samples each, for
base, N1, N2 and N3.

  python -B scripts/claude_brd9.py --model M --out DIR --temps 1.0,1.5 --dev-puzzles F --test-puzzles T
  python -B scripts/claude_brd9.py --selftest
  python -B scripts/claude_brd9.py --make-panel OUT --dev-puzzles F --banned-panels P1,P2,...
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt1 as B1  # noqa: E402
import claude_blurt2 as B2  # noqa: E402
import claude_blurt5s as S5  # noqa: E402
import claude_brd8 as R8  # noqa: E402

NIGHTS = 3


def keys_of(ps):
    return {(tuple(p["nums"]), p["target"]) for p in ps}


def read_jsonl(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def make_panel(banned, seed=802, pool=1500, n3=80, n4=160):
    """Fresh test panel. The 3-number world is small (1,346 solvable puzzles: numbers 1-9, targets 5-40) and practice,
    DEV and brd-5..8 panels use 1,180 of them, so the 3-number part is drawn from ALL unused ones (enumerated, shuffled
    with seed). The 4-number part (target 24) is the blurt-2 recipe from puzzles(seed, pool), overlap dropped."""
    three = [{"nums": list(n), "target": t} for n in itertools.combinations_with_replacement(range(1, 10), 3)
             for t in range(5, 41) if (n, t) not in banned and B1.solve(list(n), t) is not None]
    random.Random(seed).shuffle(three)
    three = [{"id": f"pz-b9-{i + 1:03d}"} | p for i, p in enumerate(three[:n3])]
    ps = [p for p in B2.puzzles(seed, pool) if (tuple(p["nums"]), p["target"]) not in banned]
    four = [p for p in ps if len(p["nums"]) == 4][:n4]
    assert len(three) == n3 and len(four) == n4
    return three + four


def transfer_panel(banned, seed=803, n=80):
    """Report-only transfer set: a kind NO practice set has. 4 numbers (1-13) with a target from 10-40 other than 24
    (every 4-number practice puzzle has target 24), solvable, distinct, not in banned."""
    rng, out, seen = random.Random(seed), [], set(banned)
    while len(out) < n:
        nums = sorted(rng.randint(1, 13) for _ in range(4))
        target = rng.choice([t for t in range(10, 41) if t != 24])
        key = (tuple(nums), target)
        if key in seen or B1.solve(nums, target) is None:
            continue
        seen.add(key)
        out.append({"id": f"pz-b9x-{len(out) + 1:03d}", "nums": nums, "target": target})
    return out


def split30(stream, test):
    """cov@30 on the 3-number and on the 4-number puzzles."""
    reach = [f > 0 for f, _ in stream]
    return {"cov@30_3num": sum(r for r, p in zip(reach, test) if len(p["nums"]) == 3),
            "cov@30_4num": sum(r for r, p in zip(reach, test) if len(p["nums"]) == 4)}


def run(a):
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    temp, res = B2.pick_temp(s, a)
    prac = B2.puzzles(a.train_seed, NIGHTS * a.n_part)
    parts = [prac[k * a.n_part:(k + 1) * a.n_part] for k in range(NIGHTS)]
    test = read_jsonl(a.test_puzzles)
    keys = keys_of(prac) | (keys_of(read_jsonl(a.dev_puzzles)) if a.dev_puzzles else set())
    assert not any((tuple(p["nums"]), p["target"]) in keys for p in test), "panel overlaps practice or DEV"
    res.update({"n_test": len(test), "temp": temp, "n_test_3num": sum(len(p["nums"]) == 3 for p in test)})
    xfer = read_jsonl(a.transfer_puzzles) if a.transfer_puzzles else []
    assert not any((tuple(p["nums"]), p["target"]) in keys for p in xfer), "transfer set overlaps practice or DEV"
    assert not any(len(p["nums"]) == 4 and p["target"] == 24 for p in xfer), "transfer set must avoid target 24"
    xs = {"base": [S5.coverage_stream(s, xfer, a.n, temp)]} if xfer else {}
    if xfer:
        res["transfer_base"] = S5.summarize(xs["base"][0])
    base = S5.coverage_stream(s, test, a.n, temp)
    res["base"] = S5.summarize(base) | split30(base, test)
    res["base_unreached"] = len(test) - res["base"]["cov@30"]
    res["bar_pass"] = 0.2 * res["base_unreached"]
    print(f"[brd9] base {res['base']}", flush=True)
    ex_a, rows_a = R8.gather(s, parts[0], a.n, temp)
    res["night1_practice"] = R8.counts(rows_a)
    log = {"night1": rows_a}
    streams = {f"N{k}": [] for k in range(1, NIGHTS + 1)}
    for sd in [int(x) for x in a.lora_seeds.split(",")]:
        ex, m = list(ex_a), None
        for k in range(1, NIGHTS + 1):
            if k > 1:
                ex_k, rows_k = R8.gather(s, parts[k - 1], a.n, temp, m)
                ex += ex_k
                res[f"night{k}_practice_seed{sd}"] = R8.counts(rows_k)
                log[f"night{k}_seed{sd}"] = rows_k
                print(f"[brd9] seed {sd} night {k} practice {res[f'night{k}_practice_seed{sd}']}", flush=True)
                del m
                if s.dev == "cuda":
                    s.torch.cuda.empty_cache()
            m = B2.train_lora(s, list(ex), a.epochs, sd)
            st = S5.coverage_stream(s, test, a.n, temp, m)
            streams[f"N{k}"].append(st)
            res[f"N{k}_seed{sd}"] = S5.summarize(st) | split30(st, test) | {"examples": len(ex)}
            print(f"[brd9] N{k} seed {sd}: {res[f'N{k}_seed{sd}']}", flush=True)
            if xfer:
                xst = S5.coverage_stream(s, xfer, a.n, temp, m)
                xs.setdefault(f"N{k}", []).append(xst)
                res[f"transfer_N{k}_seed{sd}"] = S5.summarize(xst)
        del m
        if s.dev == "cuda":
            s.torch.cuda.empty_cache()
        (out / "practice.json").write_text(json.dumps(log), encoding="utf-8")
    for k in range(1, NIGHTS + 1):
        res[f"ci95_N{k}_minus_base_cov30_pct"] = S5.boot_ci(test, streams[f"N{k}"], [base])
    res["ci95_N3_minus_N1_cov30_pct"] = S5.boot_ci(test, streams["N3"], streams["N1"])
    for k in range(1, NIGHTS + 1):
        if xfer:
            res[f"transfer_ci95_N{k}_minus_base_cov30_pct"] = S5.boot_ci(xfer, xs[f"N{k}"], xs["base"])
    if xfer:
        (out / "transfer_streams.json").write_text(json.dumps(xs), encoding="utf-8")
    (out / "streams.json").write_text(json.dumps({"base": base, **streams}), encoding="utf-8")
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "brd9_summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


def selftest():
    p12 = B2.puzzles(9, 1200)
    assert p12[:800] == B2.puzzles(9, 800) and len(keys_of(p12)) == 1200
    ps = [{"nums": [1, 2, 3], "target": 6}, {"nums": [1, 2, 3, 4], "target": 24}]
    assert keys_of(ps) == {((1, 2, 3), 6), ((1, 2, 3, 4), 24)}
    assert split30([(3, 1), (0, 0)], ps) == {"cov@30_3num": 1, "cov@30_4num": 0}
    tp = transfer_panel(set(), n=5)
    assert len(tp) == 5 and all(len(p["nums"]) == 4 and p["target"] != 24 for p in tp)
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--train-seed", type=int, default=9)
    ap.add_argument("--n-part", type=int, default=400)
    ap.add_argument("--test-puzzles", default="")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lora-seeds", default="0,1,2")
    ap.add_argument("--temps", default="1.0,1.5")
    ap.add_argument("--dev-puzzles", default="")
    ap.add_argument("--transfer-puzzles", default="")
    ap.add_argument("--make-panel", default="")
    ap.add_argument("--make-transfer", default="")
    ap.add_argument("--banned-panels", default="")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.make_transfer:
        banned = keys_of(B2.puzzles(a.train_seed, NIGHTS * a.n_part)) | keys_of(read_jsonl(a.dev_puzzles))
        Path(a.make_transfer).write_text("".join(json.dumps(p) + "\n" for p in transfer_panel(banned)),
                                         encoding="utf-8")
    elif a.make_panel:
        banned = keys_of(B2.puzzles(a.train_seed, NIGHTS * a.n_part)) | keys_of(read_jsonl(a.dev_puzzles))
        for f in a.banned_panels.split(","):
            banned |= keys_of(read_jsonl(f))
        Path(a.make_panel).write_text("".join(json.dumps(p) + "\n" for p in make_panel(banned)), encoding="utf-8")
    else:
        run(a)


if __name__ == "__main__":
    main()
