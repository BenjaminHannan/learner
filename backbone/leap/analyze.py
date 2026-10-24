"""Leap-1 tables + the check-then-escalate cascade, from results pulled off the boxes.

  python3 backbone/leap/analyze.py DIR      # DIR holds result_*.json, eval*_*.jsonl (any nesting)

Cascade: the worker searches (16 samples, keeps the first program that reproduces the examples); if nothing checks out
it hands the puzzle to a bigger model's first try. Reports accuracy and how often the big model is called.
"""
import json
import sys
from pathlib import Path


def load_jsonl(p):
    return {r["id"]: r for r in (json.loads(l) for l in open(p) if l.strip())}


def mean_by_depth(recs):
    d = {}
    for r in recs:
        d.setdefault(r["depth"], []).append(r["correct"])
    bd = {k: sum(v) / len(v) for k, v in sorted(d.items())}
    return sum(bd.values()) / len(bd), bd


def main():
    root = Path(sys.argv[1])
    res = {p.name: json.loads(p.read_text()) for p in root.rglob("result_*.json")}
    out = {"curves": {}, "refs": {}, "cascade": {}}
    for name, r in sorted(res.items()):
        if r.get("arm") == "ref" or "ref" in name:
            e = r["eval"] if "eval" in r else r["rounds"][0]["eval"]
            out["refs"][r.get("model", name)] = {"first_try": e["mean"], "by_depth": e["by_depth"],
                                                "c16": (r.get("c16") or (r.get("rounds") or [{}])[0].get("c16") or {}).get("mean")}
            continue
        tag = f"{r['arm']}_s{r['seed']}"
        out["curves"][tag] = [{"round": x["round"], "mean": round(x["eval"]["mean"], 4), "d4_6": round(sum(x["eval"]["by_depth"][str(d)] for d in (4, 5, 6)) / 3, 4),
                               "frontier": x["frontier"], "arc": x.get("arc_easy"), "c16": (x.get("c16") or {}).get("mean"),
                               "verified": (x.get("explore") or {}).get("verified_puzzles"), "pairs": (x.get("explore") or {}).get("pairs")} for x in r["rounds"]]
    bigs = {f"{p.parent.name}/{p.stem}": load_jsonl(p) for p in root.rglob("eval_ref_*_r0.jsonl")}
    workers = {p.stem.replace("evalc16_", ""): load_jsonl(p) for p in root.rglob("evalc16_*_r*.jsonl") if "_ref_" not in p.name and "ref" not in p.parent.name}
    for wn, w in sorted(workers.items()):
        for bn, b in sorted(bigs.items()):
            recs, calls = [], 0
            for pid, x in w.items():
                if x["answered"]:
                    recs.append(x)
                else:
                    calls += 1
                    recs.append(b[pid])
            m, bd = mean_by_depth(recs)
            out["cascade"][f"{wn} -> {bn}"] = {"acc": round(m, 4), "big_called": round(calls / len(w), 4), "by_depth": bd}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
