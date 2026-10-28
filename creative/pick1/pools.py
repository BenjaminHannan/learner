"""Build Pick-1 pools: 2 arms x 2 seeds x 48 tasks of 12 transcripts, with judge text. Usage: pools.py [--results DIR] [--out pools.jsonl]"""
import argparse, json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa


def akey(arm, seed):
    return arm if seed == 1 else f"{arm}.s{seed}"


def build(rows, T, g=None, cut=300):
    """rows: Guess-1 result records; T: task ids. Returns pool-member dicts (IND/IND.s2 use try_idx < 12 only)."""
    g = g or load_guess1()
    want = {akey(a, s): (a, s) for a in BASE_ARMS for s in SEEDS}
    Tset, seen, out = set(T), set(), []
    for r in rows:
        if r["arm"] not in want or r["task_id"] not in Tset or r["try_idx"] >= N_TRIES:
            continue
        k = (r["task_id"], r["arm"], r["try_idx"])
        if k in seen:
            continue
        seen.add(k)
        arm, seed = want[r["arm"]]
        user = r["transcript"][0]["content"]
        out.append(dict(pool=f"{r['task_id']}|{r['arm']}", task=r["task_id"], arm=arm, seed=seed, try_idx=r["try_idx"],
                        success=bool(r["success"]), signature=g.signature(r), judge_text=g.r1.render(user, r["transcript"], cut)))
    out.sort(key=lambda x: (x["task"], x["arm"], x["seed"], x["try_idx"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=DEFAULT_RESULTS, help="dir with results.jsonl and target.json")
    ap.add_argument("--cut", type=int, default=300, help="truncate tool results at this many chars")
    ap.add_argument("--out", default=os.path.join(HERE, "pools.jsonl"))
    a = ap.parse_args()
    T = json.load(open(os.path.join(a.results, "target.json")))["T"]
    rows = read_jsonl(os.path.join(a.results, "results.jsonl"))
    recs = build(rows, T, cut=a.cut)
    with open(a.out, "w") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    pools = defaultdict(int)
    for r in recs:
        pools[r["pool"] + r["arm"]] += 1
    short = {p: n for p, n in pools.items() if n != N_TRIES}
    print(f"{len(pools)} pools, {len(recs)} transcripts -> {a.out}; pools not of size {N_TRIES}: {len(short)}")


if __name__ == "__main__":
    main()
