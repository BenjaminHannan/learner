#!/usr/bin/env python3
"""slp-364 bench self-check (does NOT judge anything; it only validates the bench).

For every case in claude_slp364_bench.CASES:
  * run_case -> force_sleep -> ask the case probes, then a wider question set;
  * for a fault case, also run the SAME case with the fault switched off (the matching honest
    sleep) and compare every reply; a fault passes the bench check when at least one reply
    differs and the setup (pre-sleep) replies are identical;
  * for a clean case, confirm the sleep installed its word(s) (live table + word file, chain
    audit), and grade the replies against the world (taught facts, word answers, abstentions).

Usage (from the tree root; one sleep uses one CPU thread, so 4 workers = 4 threads):
  OMP_NUM_THREADS=1 python3 -B scripts/claude_slp364_bench_check.py --root DIR --out FILE.json \\
      [--workers 4] [--only slp364-01,slp364-02]
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import re
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _grade(reply: str, expect: str | None) -> str:
    low = reply.lower()
    if expect is not None and re.search(rf"\b{re.escape(expect.lower())}\b", low):
        return "correct"
    if "don't know" in low or "do not know" in low:
        return "abstain"
    return "wrong"


def question_set(B, world: dict) -> list[tuple[str, str | None, str]]:
    """(text, expected name or None, kind). kind: hop/word/partial/outsider/post-teach/post-*."""
    out: list[tuple[str, str | None, str]] = []
    for (a, rel), b in sorted(world["truth"].items()):
        out.append((B._hop_q(a, rel), b, "hop"))
    for w in world["words"] + world["pre"]:
        c = world["chains"][w]
        for ch in c["train"] + c["test"]:
            out.append((B._word_q(ch[0], w), ch[-1], "word"))
        for ch in c["partial"]:
            out.append((B._word_q(ch[0], w), None, "partial"))
    for o in world["outsiders"]:
        out.append((B._word_q(o, world["words"][0]), None, "outsider"))
        out.append((B._hop_q(o, "mother"), None, "outsider"))
    for w in world["words"]:
        for people in world["post"][w]:
            for t in B.post_teaches(world, w, people):
                out.append((t, None, "post-teach"))
            out.append((B._word_q(people[0], w), people[-1], "post-word"))
            for k, rel in enumerate(B.CHAINS[w]):
                out.append((B._hop_q(people[k], rel), people[k + 1], "post-hop"))
    return out


def run_job(cid: str, with_fault: bool, root: str) -> dict:
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    import claude_slp364_bench as B
    import claude_slp360_test as T
    import fable_sleep130_agent as S130
    case = next(c for c in B.CASES if c["id"] == cid)
    world = B.world_of(case)
    arm = "F" if with_fault else "H"
    d = Path(root) / f"{cid}-{arm}"
    if d.exists():
        shutil.rmtree(d)
    t0 = time.time()
    loop = B.run_case(case, str(d), _with_fault=with_fault)
    t_setup = time.time() - t0
    setup = B.SETUP_REPLIES[str(d)]
    queued = len(loop.reasoner.episodes)
    live_before = sorted(loop.reasoner.inner.words)
    t1 = time.time()
    T.force_sleep(loop)
    t_sleep = time.time() - t1
    outcome = dict(getattr(loop.sleeper, "last_outcome", {}) or {})
    recipe = outcome.get("recipe", {}) or {}
    live_after = sorted(loop.reasoner.inner.words)
    try:
        filew = json.loads((d / B.WORD_FILE).read_text(encoding="utf-8")).get("words", {})
    except (OSError, ValueError):
        filew = {}
    audit_ok = {w: S130.check_word_logits130(filew[w].get("logits"), S130.WORDS130.index(w))
                for w in filew}
    probes = [{"text": q, "reply": T.say(loop, q)} for q in case["probes"]]
    qs = question_set(B, world)
    asked = [{"text": q, "expect": e, "kind": k, "reply": T.say(loop, q)} for q, e, k in qs]
    for a in asked:
        a["grade"] = None if a["kind"] == "post-teach" else _grade(a["reply"], a["expect"])
    return {"id": cid, "arm": arm, "kind": case["kind"], "category": case["category"],
            "seed": case["seed"], "setup_seconds": round(t_setup, 1),
            "sleep_seconds": round(t_sleep, 1), "seconds": round(time.time() - t0, 1),
            "episodes_queued": queued, "setup_replies": setup,
            "setup_not_saved": [r for t, r in zip(world["turns"], setup)
                                if "'s " in t and t.endswith(".") and not t.startswith("Who")
                                and not r.startswith(("Saved", "Updated", "Corrected", "Got it",
                                                      "OK", "Okay"))],
            "live_words_before": live_before, "live_words_after": live_after,
            "file_words": sorted(filew), "file_audit": audit_ok,
            "recipe": {k: recipe.get(k) for k in ("attempted", "installed", "words")},
            "accepted": outcome.get("accepted"), "trained_words": [B.WORDS[w] for w in world["words"]],
            "prior_words": [B.WORDS[w] for w in world["pre"]],
            "probes": probes, "asked": asked}


def _job(args):
    cid, with_fault, root = args
    try:
        return run_job(cid, with_fault, root)
    except Exception as exc:  # report, keep going
        import traceback
        return {"id": cid, "arm": "F" if with_fault else "H", "error": repr(exc),
                "trace": traceback.format_exc()}


def summarize(results: list[dict]) -> dict:
    by = {(r["id"], r["arm"]): r for r in results}
    ids = sorted({r["id"] for r in results})
    rows = []
    for cid in ids:
        f = by.get((cid, "F"))
        if f is None or "error" in f:
            rows.append({"id": cid, "error": (f or {}).get("error", "missing")})
            continue
        row = {"id": cid, "kind": f["kind"], "category": f["category"], "seed": f["seed"],
               "seconds": f["seconds"], "sleep_seconds": f["sleep_seconds"],
               "episodes_queued": f["episodes_queued"],
               "setup_not_saved": len(f["setup_not_saved"])}
        new_words = [w for w in f["trained_words"]
                     if w in f["live_words_after"] and w in f["file_words"]
                     and f["file_audit"].get(w)]
        grades: dict = {}
        for a in f["asked"]:
            if a["grade"] is None:
                continue
            key = a["kind"]
            want = "abstain" if a["expect"] is None else "correct"
            grades.setdefault(key, [0, 0])
            grades[key][0] += int(a["grade"] == want)
            grades[key][1] += 1
        row["grades"] = {k: f"{v[0]}/{v[1]}" for k, v in grades.items()}
        row["all_as_expected"] = all(v[0] == v[1] for v in grades.values())
        if f["kind"] == "clean":
            row["installed"] = (len(new_words) == len(f["trained_words"])
                                and all(w in f["live_words_after"] for w in f["prior_words"]))
        else:
            h = by.get((cid, "H"))
            if h is None or "error" in h:
                row["error"] = (h or {}).get("error", "honest twin missing")
            else:
                fr = [x["reply"] for x in f["probes"]] + [x["reply"] for x in f["asked"]]
                hr = [x["reply"] for x in h["probes"]] + [x["reply"] for x in h["asked"]]
                diffs = [(q, a, b) for q, a, b in zip(
                    [x["text"] for x in f["probes"]] + [x["text"] for x in f["asked"]], fr, hr)
                    if a != b]
                pdiff = sum(1 for x, y in zip(f["probes"], h["probes"]) if x["reply"] != y["reply"])
                row["changed_replies"] = len(diffs)
                row["changed_probe_replies"] = pdiff
                row["setup_identical"] = f["setup_replies"] == h["setup_replies"]
                row["honest_installed"] = all(
                    w in h["live_words_after"] and w in h["file_words"]
                    for w in h["trained_words"])
                row["honest_all_as_expected"] = all(
                    a["grade"] == ("abstain" if a["expect"] is None else "correct")
                    for a in h["asked"] if a["grade"] is not None)
                row["example_diff"] = diffs[:3]
                row["seconds_honest_twin"] = h["seconds"]
        rows.append(row)
    clean = [r for r in rows if r.get("kind") == "clean"]
    faults = [r for r in rows if r.get("kind") == "fault"]
    return {
        "cases": rows,
        "clean_installed": f"{sum(1 for r in clean if r.get('installed'))}/{len(clean)}",
        "clean_all_as_expected": f"{sum(1 for r in clean if r.get('all_as_expected'))}/{len(clean)}",
        "faults_change_a_reply": f"{sum(1 for r in faults if r.get('changed_replies', 0) > 0)}/{len(faults)}",
        "faults_change_a_probe_reply": f"{sum(1 for r in faults if r.get('changed_probe_replies', 0) > 0)}/{len(faults)}",
        "faults_setup_identical": f"{sum(1 for r in faults if r.get('setup_identical'))}/{len(faults)}",
        "fault_twins_honest_installed": f"{sum(1 for r in faults if r.get('honest_installed'))}/{len(faults)}",
        "seconds_40_cases_sum": round(sum(r.get("seconds", 0) for r in rows), 1),
        "errors": [r for r in rows if "error" in r],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="scratch folder for the state dirs")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", default=None)
    args = ap.parse_args(argv)
    os.environ["OMP_NUM_THREADS"] = "1"
    import claude_slp364_bench as B
    ids = [c["id"] for c in B.CASES]
    if args.only:
        keep = set(args.only.split(","))
        ids = [i for i in ids if i in keep]
    kinds = {c["id"]: c["kind"] for c in B.CASES}
    jobs = [(cid, True, args.root) for cid in ids]
    jobs += [(cid, False, args.root) for cid in ids if kinds[cid] == "fault"]
    # longest first is unknown; interleave so fault twins spread over workers
    Path(args.root).mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    results = []
    ctx = mp.get_context("spawn")
    with ctx.Pool(args.workers, maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(_job, jobs):
            results.append(r)
            print(r["id"], r["arm"], r.get("seconds"), r.get("error", ""), flush=True)
    summ = summarize(results)
    summ["wall_seconds"] = round(time.time() - t0, 1)
    Path(args.out).write_text(json.dumps({"summary": summ, "results": results}, indent=1,
                                         ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in summ.items() if k != "cases"}, indent=1))
    for r in summ["cases"]:
        print(json.dumps({k: v for k, v in r.items() if k != "example_diff"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
