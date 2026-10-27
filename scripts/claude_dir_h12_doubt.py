#!/usr/bin/env python3
"""H12 doubt check (report-only diagnostic, no pass mark): does a LATE stop, or an answer that is still CHANGING,
predict a WRONG answer? The harness saves only counts, so per-maze records need one extra scoring pass over the
saved checkpoints (no training).

    extract  (needs torch; Mac or cloud box)  per-maze records from a run's k*.pt on the dev 9x9 panel
    table    (pure python)                    x of n counts from those records (also usable for any other kind)
    selftest (pure python)                    the table arithmetic on synthetic records

Record schema (one JSON file per tag and seed; `rungs` keys are rung names, values are lists of per-item dicts):
  {"tag": "h12", "seed": 0, "fixed_depth": 16, "panel": "...", "rungs": {"64": [
     {"i": 0, "rounds": 48, "cap": true, "right": false, "right_fixed": false, "changing": true, "path_len": 31}, ...]}}
  rounds = round the learned stop picked (48 if it never fired; the harness rule, claude_fewex_bench.py:76-78);
  cap = rounds == 48; right = the answer at that round is exactly right; right_fixed = the fixed-depth answer is;
  changing = the argmax answers of rounds 46, 47 and 48 of the full 48-round trace are not all identical
  (an answer still moving when the budget ends); path_len is optional (maze difficulty).
Any other kind (for example H2's number puzzles) can be fed to `table` by writing the same schema.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
RUNGS = (1, 4, 16, 64, 256, 1024, 4096, 16384)
POOLED = (64, 256, 1024, 4096, 16384)          # the marks' judged rungs
MAX_ROUNDS = 48


# ---- table (pure python) ----------------------------------------------------------------

def cross(records, flag):
    """wrong = the learned-stop answer is not exact. Counts among flagged items and among the rest."""
    fl = [r for r in records if flag(r)]
    rest = [r for r in records if not flag(r)]
    return {"flagged_n": len(fl), "flagged_wrong": sum(not r["right"] for r in fl),
            "rest_n": len(rest), "rest_wrong": sum(not r["right"] for r in rest)}


def indicators(depth):
    return {"late: stop hit the 48-round cap": lambda r: r["cap"],
            f"late: stop after round {depth} (the fixed depth)": lambda r: r["rounds"] > depth,
            "changing: answers of rounds 46-48 differ": lambda r: r["changing"],
            "cap hit or changing": lambda r: r["cap"] or r["changing"]}


def line(c):
    return (f"{c['flagged_wrong']} of {c['flagged_n']} wrong among flagged | "
            f"{c['rest_wrong']} of {c['rest_n']} wrong among the rest")


def rung_order(names):
    nums = sorted(int(n) for n in names if str(n).isdigit())
    return [str(n) for n in nums] + [n for n in names if not str(n).isdigit()]


def tables(rec):
    """All cross-tabs for one record file; returns {rung: {indicator: counts}} plus a pooled block and a difficulty block."""
    depth = rec.get("fixed_depth", 16)
    inds = indicators(depth)
    out = {"rungs": {}, "pooled_k_ge_64": None, "difficulty": None}
    for k in rung_order(rec["rungs"]):
        out["rungs"][k] = {name: cross(rec["rungs"][k], fn) for name, fn in inds.items()}
        out["rungs"][k]["_all_wrong"] = {"wrong": sum(not r["right"] for r in rec["rungs"][k]), "n": len(rec["rungs"][k])}
    pooled = [r for k in rec["rungs"] if str(k).isdigit() and int(k) in POOLED for r in rec["rungs"][k]]
    if pooled:
        out["pooled_k_ge_64"] = {name: cross(pooled, fn) for name, fn in inds.items()}
        out["pooled_k_ge_64"]["_all_wrong"] = {"wrong": sum(not r["right"] for r in pooled), "n": len(pooled)}
    solved = [r for k in rec["rungs"] if str(k).isdigit() and int(k) >= 256 for r in rec["rungs"][k]
              if r["right"] and r.get("path_len") is not None]
    if len(solved) >= 4:
        lens = sorted(r["path_len"] for r in solved)
        med = lens[len(lens) // 2]
        short = [r for r in solved if r["path_len"] <= med]
        long_ = [r for r in solved if r["path_len"] > med]
        mean = lambda xs: round(sum(r["rounds"] for r in xs) / len(xs), 2) if xs else None
        out["difficulty"] = {"median_path_len": med, "solved_short_n": len(short), "solved_short_mean_rounds": mean(short),
                             "solved_long_n": len(long_), "solved_long_mean_rounds": mean(long_)}
    return out


def print_tables(tag, seed, t):
    print(f"== {tag}, seed {seed}: wrong = learned-stop answer not exact; counts are items of the rung's panel")
    for k, block in t["rungs"].items():
        aw = block["_all_wrong"]
        print(f"-- rung {k}: {aw['wrong']} of {aw['n']} wrong overall")
        for name, c in block.items():
            if not name.startswith("_"):
                print(f"   {name}: {line(c)}")
    if t["pooled_k_ge_64"]:
        aw = t["pooled_k_ge_64"]["_all_wrong"]
        print(f"-- pooled over the judged rungs k >= 64 (descriptive; separate trainings): {aw['wrong']} of {aw['n']} wrong overall")
        for name, c in t["pooled_k_ge_64"].items():
            if not name.startswith("_"):
                print(f"   {name}: {line(c)}")
    if t["difficulty"]:
        d = t["difficulty"]
        print(f"-- solved mazes, rungs k >= 256 pooled: path length <= {d['median_path_len']}: {d['solved_short_n']} mazes, mean rounds {d['solved_short_mean_rounds']}; "
              f"longer: {d['solved_long_n']} mazes, mean rounds {d['solved_long_mean_rounds']}")


def table_cmd(patterns, out):
    result = {}
    for tag, pat in patterns.items():
        for seed in (0, 1):
            path = ROOT / pat.format(seed=seed)
            if not path.exists():
                print(f"-- {tag} seed {seed}: {pat.format(seed=seed)} not found; skipped")
                continue
            rec = json.loads(path.read_text())
            bad = [k for k, v in rec.get("consistency", {}).items() if not v.get("ok")]
            if bad:
                print(f"!! {tag} seed {seed}: recomputed counts did NOT match the harness record at rungs {bad}")
            t = tables(rec)
            result[f"{tag}-s{seed}"] = t
            print_tables(tag, seed, t)
    if out:
        Path(out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


# ---- extract (torch) --------------------------------------------------------------------

def score_items(net, items, depth, B, batch=32):
    """Same computation as claude_fewex_bench.score, but keeps one record per maze and the last three rounds' answers."""
    import torch
    N = B.N
    recs = []
    with torch.no_grad():
        net.eval()
        for i in range(0, len(items), batch):
            chunk = items[i:i + batch]
            t, s, _ = N.tensors(chunk)
            h, w = t.shape[1:]
            ps, qs = net.infer_rounds(t, s, MAX_ROUNDS)
            ps, qs = ps.tolist(), qs.tolist()
            for j, (it, p, q) in enumerate(zip(chunk, ps, qs)):
                r = next((x + 1 for x in range(2, MAX_ROUNDS) if q[x] > .5 and p[x] == p[x - 1] == p[x - 2]), MAX_ROUNDS)
                rows = lambda flat: [flat[a * w:(a + 1) * w] for a in range(h)]
                recs.append({"i": i + j, "rounds": r, "cap": r == MAX_ROUNDS,
                             "right": bool(B.exact(it, rows(p[r - 1]))),
                             "right_fixed": bool(B.exact(it, rows(p[depth - 1]))),
                             "changing": not (p[-1] == p[-2] == p[-3]),
                             "path_len": it.meta.get("path_len")})
    return recs


def extract_cmd(run_dir, adapt_json, tag, out, rungs, threads):
    import torch
    import claude_fewex_bench as B
    import claude_fewex_data as D
    import claude_fewex_net as base
    B.N = base
    torch.set_num_threads(threads)
    run = json.loads(Path(adapt_json).read_text())
    depth = run["fixed_depth"]
    items = D.panels()[0]["dev"][9]
    rec = {"tag": tag, "seed": run["seed"], "arm": run["arm"], "fixed_depth": depth,
           "panel": f"dev 9x9, {len(items)} mazes", "rungs": {}, "consistency": {}}
    for k in rungs:
        net = B.load_model(Path(run_dir) / f"k{k}.pt", run["arm"])
        recs = score_items(net, items, depth, B)
        h = run["rungs"][str(k)]["9"]
        mine = {"right": sum(r["right"] for r in recs), "fixed_right": sum(r["right_fixed"] for r in recs),
                "cap_hits": sum(r["cap"] for r in recs), "mean_rounds": sum(r["rounds"] for r in recs) / len(recs)}
        ok = (mine["right"], mine["fixed_right"], mine["cap_hits"]) == (h["right"], h["fixed_right"], h["cap_hits"]) \
            and abs(mine["mean_rounds"] - h["mean_rounds"]) < 1e-9
        rec["rungs"][str(k)] = recs
        rec["consistency"][str(k)] = {"ok": ok, "harness": {x: h[x] for x in mine}, "recomputed": mine}
        print(json.dumps({"phase": "doubt_extract", "tag": tag, "seed": run["seed"], "k": k, "consistent_with_harness": ok,
                          "right": mine["right"], "cap_hits": mine["cap_hits"]}), flush=True)
    Path(out).write_text(json.dumps(rec, sort_keys=True) + "\n")


# ---- selftest ---------------------------------------------------------------------------

def _rec(rows, depth=16):
    return {"fixed_depth": depth, "rungs": {"64": [dict(zip(("rounds", "cap", "right", "changing", "path_len"), r), i=i)
                                                   for i, r in enumerate(rows)]}}


def selftest():
    # (rounds, cap, right, changing, path_len)
    rows = [(48, True, False, True, 30), (48, True, False, False, 28), (48, True, True, False, 12),
            (20, False, False, False, 26), (10, False, True, False, 9), (12, False, True, False, 11),
            (8, False, True, False, 7), (9, False, False, False, 8)]
    t = tables(_rec(rows))["rungs"]["64"]
    assert t["_all_wrong"] == {"wrong": 4, "n": 8}
    cap = t["late: stop hit the 48-round cap"]
    assert cap == {"flagged_n": 3, "flagged_wrong": 2, "rest_n": 5, "rest_wrong": 2}, cap
    late = t["late: stop after round 16 (the fixed depth)"]
    assert late == {"flagged_n": 4, "flagged_wrong": 3, "rest_n": 4, "rest_wrong": 1}, late
    chg = t["changing: answers of rounds 46-48 differ"]
    assert chg == {"flagged_n": 1, "flagged_wrong": 1, "rest_n": 7, "rest_wrong": 3}, chg
    both = t["cap hit or changing"]
    assert both == cap, both                                        # the changing item is also a cap hit here
    assert line(cap) == "2 of 3 wrong among flagged | 2 of 5 wrong among the rest"
    # an empty flagged group and an empty rest group give zero counts, not errors
    assert cross([], lambda r: True) == {"flagged_n": 0, "flagged_wrong": 0, "rest_n": 0, "rest_wrong": 0}
    assert cross(_rec(rows)["rungs"]["64"], lambda r: True)["rest_n"] == 0
    # pooled and difficulty blocks
    rec = {"fixed_depth": 16, "rungs": {"64": _rec(rows)["rungs"]["64"], "256": _rec(rows)["rungs"]["64"], "3": _rec(rows)["rungs"]["64"]}}
    tt = tables(rec)
    assert tt["pooled_k_ge_64"]["_all_wrong"] == {"wrong": 8, "n": 16}        # rungs 64 and 256 only; the "3" rung is not pooled
    assert tt["pooled_k_ge_64"]["late: stop hit the 48-round cap"]["flagged_n"] == 6
    d = tt["difficulty"]                                                       # solved, k >= 256: 4 mazes with path_len 12, 9, 11, 7
    assert d["median_path_len"] == 11 and d["solved_short_n"] == 3 and d["solved_long_n"] == 1
    assert d["solved_short_mean_rounds"] == round((10 + 12 + 8) / 3, 2) and d["solved_long_mean_rounds"] == 48.0
    assert rung_order(["256", "64", "held-out", "1"]) == ["1", "64", "256", "held-out"]
    print(json.dumps({"selftest": "ok"}))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    e = sub.add_parser("extract")
    e.add_argument("--run-dir", required=True, help="folder with k<rung>.pt checkpoints")
    e.add_argument("--adapt-json", required=True, help="that run's adapt.json (harness counts, used as a consistency check)")
    e.add_argument("--tag", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--rungs", type=int, nargs="+", default=list(RUNGS))
    e.add_argument("--threads", type=int, default=1)
    t = sub.add_parser("table")
    t.add_argument("--h12", default="artifacts/claude-dir-h12-stop-20260928/doubt/doubt-items-h12-s{seed}.json")
    t.add_argument("--baseline", default="artifacts/claude-dir-h12-stop-20260928/doubt/doubt-items-baseline-s{seed}.json")
    t.add_argument("--out")
    a = p.parse_args()
    if a.cmd == "selftest":
        selftest()
    elif a.cmd == "extract":
        extract_cmd(a.run_dir, a.adapt_json, a.tag, a.out, a.rungs, a.threads)
    else:
        table_cmd({"h12": a.h12, "baseline": a.baseline}, a.out)


if __name__ == "__main__":
    main()
