#!/usr/bin/env python3
"""slp-364c bench self-check (does NOT judge anything; it only validates the bench).

For every case in claude_slp364c_bench.CASES:
  * run_case -> force_sleep -> ask a wide question set about the day's world (graded), then the
    case probes in order (new people taught, a correction, a new person corrected; graded with
    the expectation at that point);
  * restart: rebuild the loop from the state folder and ask the wide set plus every probe
    question again (graded against the final state, all probe teaches applied);
  * a FAULT case is also run with the fault switched off (its honest twin). It passes the bench
    check when the setup replies are identical and at least one reply differs from the twin,
    live (after the sleep) or after the restart. Both counts are reported, so a fault that shows
    only after a restart (or only live) is visible. The state files right after the sleep (word
    file, notebook log, scrap log) are compared with the twin's: identical = memory-only fault;
  * a CLEAN case passes when the sleep installed its word(s) (live table + word file + chain
    audit + after restart, earlier words kept, >= 10 episodes per word) and every graded reply,
    live and after restart, is right.
The honest twins of the faults are graded the same way as clean cases (sanity of the twin).

Usage (from the tree root; one sleep uses one CPU thread):
  OMP_NUM_THREADS=1 python3 -B scripts/claude_slp364c_bench_check.py --root DIR --out FILE.json \\
      [--workers 3] [--only slp364c-01,slp364c-02] [--no-twins]
"""

from __future__ import annotations

import argparse
import hashlib
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

_Q_RE = re.compile(r"^Who is (?P<name>\S+)'s (?P<phrase>.+)\?$")


def grade(question: str, reply: str, expect: str | None) -> str:
    """correct = the reply claims exactly "<name>'s <asked phrase> is <expected>";
    abstain = it makes no claim for the asked phrase; wrong = it claims some other answer."""
    m = _Q_RE.match(question)
    if not m:
        return "wrong"
    claim = re.search(rf"\b{re.escape(m['name'])}'s {re.escape(m['phrase'])} is "
                      rf"(?P<ans>[A-Za-z0-9]+)", reply)
    if claim is None:
        return "abstain"
    if expect is not None and claim["ans"] == expect:
        return "correct"
    return "wrong"


def _want(expect) -> str:
    return "abstain" if expect is None else "correct"


def _ask(T, loop, qs):
    out = []
    for q, e, k in qs:
        r = T.say(loop, q)
        out.append({"text": q, "expect": e, "kind": k, "reply": r,
                    "grade": None if k in ("teach", "fix") else grade(q, r, e)})
    return out


def _file_words(B, d: Path) -> dict:
    try:
        return json.loads((d / B.WORD_FILE).read_text(encoding="utf-8")).get("words", {})
    except (OSError, ValueError):
        return {}


def _log_digest(p: Path) -> str | None:
    """sha256 of a JSONL log with the per-run event ids and hash links removed (event ids
    carry a per-run tag, so two runs of the same case differ there and nowhere else)."""
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    norm = []
    for line in lines:
        try:
            ev = json.loads(line)
        except ValueError:
            norm.append(line)
            continue
        norm.append(json.dumps({k: v for k, v in ev.items() if k not in ("event_id", "prev")},
                               sort_keys=True))
    return hashlib.sha256("\n".join(norm).encode("utf-8")).hexdigest()


def _state_files(B, d: Path) -> dict:
    return {"words": json.dumps(_file_words(B, d), sort_keys=True),
            "notebook": _log_digest(d / "notebook" / "events.jsonl"),
            "scrap": _log_digest(d / "scrap360" / "scrap.jsonl")}


def run_job(cid: str, with_fault: bool, root: str) -> dict:
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    import claude_slp364c_bench as B
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
    queued: dict = {}
    for ep in loop.reasoner.episodes:
        queued[ep["word_name"]] = queued.get(ep["word_name"], 0) + 1
    live_before = sorted(loop.reasoner.inner.words)
    t1 = time.time()
    T.force_sleep(loop)
    t_sleep = time.time() - t1
    files_after_sleep = _state_files(B, d)
    outcome = dict(getattr(loop.sleeper, "last_outcome", {}) or {})
    recipe = outcome.get("recipe", {}) or {}
    live_after = sorted(loop.reasoner.inner.words)
    filew = _file_words(B, d)
    audit = {w: S130.check_word_logits130(filew[w].get("logits"), S130.WORDS130.index(w))
             for w in filew if w in S130.WORDS130}
    wide = _ask(T, loop, B.question_set(world))
    plan = B.probe_plan(world)
    assert [p[0] for p in plan] == case["probes"]
    probes = _ask(T, loop, plan)
    del loop
    restart_error = None
    try:
        loop2 = T.build(str(d), case["seed"], "P")      # restart from the state folder
        restart = _ask(T, loop2, B.restart_plan(world))
        live_restart = sorted(loop2.reasoner.inner.words)
    except Exception as exc:  # a state folder that will not boot is a user-visible reply too
        restart_error = repr(exc)
        restart = [{"text": q, "expect": e, "kind": k, "reply": f"<restart failed: {exc!r}>",
                    "grade": "abstain"} for q, e, k in B.restart_plan(world)]
        live_restart = []
    return {"id": cid, "arm": arm, "kind": case["kind"], "category": case["category"],
            "seed": case["seed"], "setup_seconds": round(t_setup, 1),
            "sleep_seconds": round(t_sleep, 1), "seconds": round(time.time() - t0, 1),
            "episodes_queued": queued, "setup_replies": setup,
            "live_words_before": live_before, "live_words_after": live_after,
            "live_words_after_restart": live_restart, "restart_error": restart_error,
            "file_words": sorted(filew), "file_audit": audit,
            "files_after_sleep": files_after_sleep,
            "recipe": {k: recipe.get(k) for k in ("attempted", "installed", "words", "reason")},
            "bridge": outcome.get("bridge"), "accepted": outcome.get("accepted"),
            "trained_words": [B.WORDS[w] for w in world["words"]],
            "prior_words": [B.WORDS[w] for w in world["pre"]],
            "wide": wide, "probes": probes, "restart": restart}


def _job(args):
    cid, with_fault, root = args
    try:
        return run_job(cid, with_fault, root)
    except Exception as exc:  # report, keep going
        import traceback
        return {"id": cid, "arm": "F" if with_fault else "H", "error": repr(exc),
                "trace": traceback.format_exc()}


def _grades(r: dict, phases) -> dict:
    g: dict = {}
    for ph in phases:
        for a in r[ph]:
            if a["grade"] is None:
                continue
            key = f"{ph}:{a['kind']}"
            g.setdefault(key, [0, 0])
            g[key][0] += int(a["grade"] == _want(a["expect"]))
            g[key][1] += 1
    return g


def _installed(r: dict) -> bool:
    new_ok = all(w in r["live_words_after"] and w in r["file_words"] and r["file_audit"].get(w)
                 and w in r["live_words_after_restart"] for w in r["trained_words"])
    prior_ok = all(w in r["live_words_after"] and w in r["file_words"]
                   and w in r["live_words_after_restart"] for w in r["prior_words"])
    enough = all(r["episodes_queued"].get(w, 0) >= 10 for w in r["trained_words"])
    return new_ok and prior_ok and enough


def _diffs(f: dict, h: dict, phases) -> list:
    out = []
    for ph in phases:
        for x, y in zip(f[ph], h[ph]):
            if x["reply"] != y["reply"]:
                out.append({"phase": ph, "text": x["text"], "fault": x["reply"],
                            "honest": y["reply"]})
    return out


def summarize(results: list[dict]) -> dict:
    by = {(r["id"], r["arm"]): r for r in results}
    ids = sorted({r["id"] for r in results})
    rows = []
    for cid in ids:
        f = by.get((cid, "F"))
        if f is None or "error" in f:
            rows.append({"id": cid, "error": (f or {}).get("error", "missing"),
                         "trace": (f or {}).get("trace")})
            continue
        row = {"id": cid, "kind": f["kind"], "category": f["category"], "seed": f["seed"],
               "seconds": f["seconds"], "sleep_seconds": f["sleep_seconds"],
               "episodes_queued": f["episodes_queued"]}
        g = _grades(f, ("wide", "probes", "restart"))
        row["grades"] = {k: f"{v[0]}/{v[1]}" for k, v in g.items()}
        row["grades_bad"] = {k: f"{v[0]}/{v[1]}" for k, v in g.items() if v[0] != v[1]}
        row["all_as_expected"] = all(v[0] == v[1] for v in g.values())
        row["installed"] = _installed(f)
        if f["kind"] == "clean":
            row["pass"] = row["installed"] and row["all_as_expected"]
            if not row["pass"]:
                row["bad_examples"] = [a for ph in ("wide", "probes", "restart") for a in f[ph]
                                       if a["grade"] is not None
                                       and a["grade"] != _want(a["expect"])][:6]
        else:
            h = by.get((cid, "H"))
            if h is None or "error" in h:
                row["error"] = (h or {}).get("error", "honest twin missing")
                row["pass"] = False
            else:
                live = _diffs(f, h, ("wide", "probes"))
                rest = _diffs(f, h, ("restart",))
                row["changed_live"] = len(live)
                row["changed_probes_live"] = sum(1 for x in live if x["phase"] == "probes")
                row["changed_after_restart"] = len(rest)
                row["shows"] = ("live+restart" if live and rest else "live-only" if live
                                else "restart-only" if rest else "never")
                row["setup_identical"] = f["setup_replies"] == h["setup_replies"]
                row["files_differ_after_sleep"] = sorted(
                    k for k in f["files_after_sleep"]
                    if f["files_after_sleep"][k] != h["files_after_sleep"][k])
                row["memory_only"] = not row["files_differ_after_sleep"]
                row["restart_error"] = f.get("restart_error")
                gh = _grades(h, ("wide", "probes", "restart"))
                row["twin_installed"] = _installed(h)
                row["twin_all_as_expected"] = all(v[0] == v[1] for v in gh.values())
                row["twin_grades_bad"] = {k: f"{v[0]}/{v[1]}" for k, v in gh.items()
                                          if v[0] != v[1]}
                row["example_diff"] = (live + rest)[:4]
                row["seconds_twin"] = h["seconds"]
                row["pass"] = (row["setup_identical"] and (len(live) + len(rest)) > 0
                               and row["twin_installed"] and row["twin_all_as_expected"])
        rows.append(row)
    clean = [r for r in rows if r.get("kind") == "clean"]
    faults = [r for r in rows if r.get("kind") == "fault"]
    cats: dict = {}
    for r in faults:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    return {
        "clean_pass": f"{sum(1 for r in clean if r.get('pass'))}/{len(clean)}",
        "clean_installed": f"{sum(1 for r in clean if r.get('installed'))}/{len(clean)}",
        "clean_all_as_expected": f"{sum(1 for r in clean if r.get('all_as_expected'))}/{len(clean)}",
        "fault_pass": f"{sum(1 for r in faults if r.get('pass'))}/{len(faults)}",
        "faults_change_a_reply": f"{sum(1 for r in faults if r.get('changed_live', 0) + r.get('changed_after_restart', 0) > 0)}/{len(faults)}",
        "faults_change_a_probe_reply_live": f"{sum(1 for r in faults if r.get('changed_probes_live', 0) > 0)}/{len(faults)}",
        "faults_setup_identical": f"{sum(1 for r in faults if r.get('setup_identical'))}/{len(faults)}",
        "fault_twins_installed": f"{sum(1 for r in faults if r.get('twin_installed'))}/{len(faults)}",
        "fault_twins_all_as_expected": f"{sum(1 for r in faults if r.get('twin_all_as_expected'))}/{len(faults)}",
        "fault_shows": {s: sorted(r["id"] for r in faults if r.get("shows") == s)
                        for s in ("live-only", "restart-only", "live+restart", "never")},
        "memory_only_faults": sorted(r["id"] for r in faults if r.get("memory_only")),
        "file_faults": sorted(r["id"] for r in faults if r.get("memory_only") is False),
        "fault_categories": cats,
        "seconds_sum": round(sum(r.get("seconds", 0) + r.get("seconds_twin", 0) for r in rows), 1),
        "errors": [r for r in rows if "error" in r],
        "cases": rows,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="scratch folder for the state dirs")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--only", default=None)
    ap.add_argument("--no-twins", action="store_true")
    ap.add_argument("--merge", default=None,
                    help="re-summarize earlier --out file(s), comma-separated (later files win "
                         "per case/arm), plus this run's results if any cases are selected")
    args = ap.parse_args(argv)
    os.environ["OMP_NUM_THREADS"] = "1"
    merged: dict = {}
    if args.merge:
        for path in args.merge.split(","):
            for r in json.loads(Path(path).read_text(encoding="utf-8"))["results"]:
                merged[(r["id"], r["arm"])] = r
    import claude_slp364c_bench as B
    ids = [c["id"] for c in B.CASES]
    if args.only:
        keep = set(args.only.split(","))
        ids = [i for i in ids if i in keep]
    elif args.merge:
        ids = []
    kinds = {c["id"]: c["kind"] for c in B.CASES}
    jobs = []
    for cid in ids:
        jobs.append((cid, True, args.root))
        if kinds[cid] == "fault" and not args.no_twins:
            jobs.append((cid, False, args.root))
    Path(args.root).mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if jobs:
        ctx = mp.get_context("spawn")
        with ctx.Pool(min(args.workers, 3), maxtasksperchild=1) as pool:
            for r in pool.imap_unordered(_job, jobs):
                merged[(r["id"], r["arm"])] = r
                print(r["id"], r["arm"], r.get("seconds"), r.get("error", ""), flush=True)
    results = list(merged.values())
    summ = summarize(results)
    summ["wall_seconds"] = round(time.time() - t0, 1)
    Path(args.out).write_text(json.dumps({"summary": summ, "results": results}, indent=1,
                                         ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in summ.items() if k != "cases"}, indent=1))
    for r in summ["cases"]:
        print(json.dumps({k: v for k, v in r.items() if k not in ("example_diff", "grades")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
