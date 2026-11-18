"""Prefetch Wikipedia evidence for the PopQA-400 set (same rows and order as tricks1.build_sets(seed=0)).
Runs in the cloud container (network, no GPU). Harness-enforced lookup: the query is PopQA's subject name (--query subj, default) or the raw question (--query question); the model never chooses.
Output: tricks/mac/popqa_lookup.jsonl {id, q, gold, bucket, evidence}; a rerun refetches only the errored rows.
The Mac run (tricks/mac/run_mac.py) needs no network.
Usage: python3 tricks/prefetch_lookup.py [--out tricks/mac/popqa_lookup.jsonl] [--workers 4]"""
import argparse, json, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import tricks1 as t

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).parent / "mac" / "popqa_lookup.jsonl"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--query", choices=["subj", "question"], default="subj")
    a = ap.parse_args()
    rows = t.build_sets(seed=0)["popqa"]
    if a.query == "subj":
        from datasets import load_dataset
        p = load_dataset("akariasai/PopQA", split="test")
        for r in rows:
            r["query"] = p[int(r["id"].split("-")[1])]["subj"]
    else:
        for r in rows:
            r["query"] = r["q"]
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    rows_q = {r["id"]: r["query"] for r in rows}
    old = {r["id"]: r["evidence"] for r in map(json.loads, out.open()) if r.get("query") == rows_q.get(r["id"])} if out.exists() else {}
    evs = [old.get(r["id"], "Error: not fetched") for r in rows]
    t0 = time.time()
    for rnd in range(4):  # search_wikipedia does not cache errors, so another pass retries them (slower each time)
        redo = [i for i, e in enumerate(evs) if e.startswith("Error:")]
        if not redo:
            break
        print(f"[pass {rnd + 1}] fetching {len(redo)} rows", flush=True)
        if rnd:
            time.sleep(10 * rnd)
        with ThreadPoolExecutor(a.workers if rnd < 2 else 1) as ex:
            for i, e in zip(redo, ex.map(lambda i: t.search_wikipedia(rows[i]["query"]), redo)):
                evs[i] = e
    out.write_text("".join(json.dumps({"id": r["id"], "q": r["q"], "gold": r["gold"], "bucket": r["bucket"], "query": r["query"], "evidence": e}) + "\n"
                           for r, e in zip(rows, evs)))
    nerr = sum(e.startswith("Error:") for e in evs); nno = sum(e == "No results." for e in evs)
    nb = {b: sum(r["bucket"] == b for r in rows) for b in ("rare", "pop")}
    hit = sum(t.popqa_match(e, r["gold"]) for r, e in zip(rows, evs))
    print(f"[done] {len(rows)} rows {nb} -> {out} errors={nerr} no_results={nno} mean_evidence_chars={sum(map(len, evs)) / len(evs):.0f} "
          f"gold_in_evidence={hit}/{len(rows)} t={time.time() - t0:.0f}s", flush=True)

if __name__ == "__main__":
    main()
