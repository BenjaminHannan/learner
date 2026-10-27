#!/usr/bin/env python3
"""Self-check for the slp-364e bench (no gate involved).

For every case it runs the case and its fault-off twin (run_case(..., fault=False)):
day, then the night (force_sleep), then the probes live, then the probes again on a
loop rebuilt from a copy of the state dir taken right after the night (restart).

Pass marks:
  clean case: every expected word installed (live + in the word file, and after the
              restart) and every graded probe right, live and after the restart;
  fault case: day replies identical to the twin's, and at least one probe reply
              differs from the twin's, live or after the restart;
  every twin: installs its words and answers its graded probes right.

  OMP_NUM_THREADS=1 python3 -B scripts/claude_slp364e_bench_check.py --out OUT.json [--workers 2]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _words_in_file(d: Path) -> list[str]:
    try:
        data = json.loads((d / "sleep145-words.json").read_text(encoding="utf-8"))
        return sorted((data.get("words") or {}).keys())
    except (OSError, ValueError):
        return []


def run_arm(case: dict, root: Path, fault: bool) -> dict:
    import claude_slp360_test as T
    import claude_slp364e_bench as B
    tag = "fault" if fault else "twin"
    d = root / tag
    rs = root / f"{tag}-restart"
    for p in (d, rs):
        shutil.rmtree(p, ignore_errors=True)
    t0 = time.time()
    loop = B.run_case(case, d, fault=fault)
    day = [list(x) for x in loop.bench364e_day]
    eps = dict(loop.bench364e_episodes)
    T.force_sleep(loop)
    live_words = sorted(getattr(loop.sleeper.reasoner.inner, "words", {}) or {})
    file_words = _words_in_file(d)
    shutil.copytree(d, rs)
    live = [T.say(loop, p) for p in case["probes"]]
    del loop
    loop2 = T.build(str(rs), case["seed"], "P")
    restart_words = sorted(getattr(loop2.reasoner.inner, "words", {}) or {})
    restart = [T.say(loop2, p) for p in case["probes"]]
    del loop2
    shutil.rmtree(d, ignore_errors=True)
    shutil.rmtree(rs, ignore_errors=True)
    return {"day": day, "episodes_at_night": eps, "live": live, "restart": restart,
            "live_words": live_words, "file_words": file_words,
            "restart_words": restart_words, "seconds": round(time.time() - t0, 1)}


def judge_arm(arm: dict, words: list[str], grades: list, B) -> dict:
    inst_live = all(w in arm["live_words"] and w in arm["file_words"] for w in words)
    inst_restart = all(w in arm["restart_words"] for w in words)
    g_live = [B.grade(r, g) for r, g in zip(arm["live"], grades)]
    g_rest = [B.grade(r, g) for r, g in zip(arm["restart"], grades)]
    bad_live = [i for i, v in enumerate(g_live) if v is False]
    bad_rest = [i for i, v in enumerate(g_rest) if v is False]
    teach_ok = all(r.startswith(("Saved", "Updated")) for t, r in arm["day"]
                   if t != "#NIGHT" and not t.rstrip().endswith("?")
                   and "'s " in t and " is " in t and not t.startswith(("Tell me",)))
    return {"installed_live": inst_live, "installed_restart": inst_restart,
            "graded": sum(v is not None for v in g_live),
            "wrong_live": bad_live, "wrong_restart": bad_rest, "day_teaches_saved": teach_ok,
            "ok": inst_live and inst_restart and not bad_live and not bad_rest and teach_ok}


def one(case_id: str, out: str) -> int:
    import claude_slp364e_bench as B
    case = next(c for c in B.CASES if c["id"] == case_id)
    root = Path(tempfile.mkdtemp(prefix=f"b364e-{case_id}-",
                                 dir=os.environ.get("B364E_TMP") or None))
    res = {"id": case_id, "kind": case["kind"], "category": case["category"]}
    try:
        res["case"] = run_arm(case, root, fault=True)
        res["twin"] = run_arm(case, root, fault=False)
    except Exception as exc:  # noqa: BLE001
        import traceback
        res["error"] = f"{exc!r}\n{traceback.format_exc()}"
    shutil.rmtree(root, ignore_errors=True)
    Path(out).write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


def evaluate(results: list[dict]) -> dict:
    import claude_slp364e_bench as B
    rows = []
    for r in results:
        cid = r["id"]
        case = next(c for c in B.CASES if c["id"] == cid)
        row = {"id": cid, "kind": r["kind"], "category": r["category"]}
        if "error" in r:
            row.update(ok=False, error=r["error"][-2000:])
            rows.append(row)
            continue
        words = B.expected_words(cid)
        grades = B.expectations(cid)
        a, t = r["case"], r["twin"]
        jt = judge_arm(t, words, grades, B)
        day_same = [x[1] for x in a["day"]] == [x[1] for x in t["day"]]
        diff_live = [i for i, (x, y) in enumerate(zip(a["live"], t["live"])) if x != y]
        diff_rest = [i for i, (x, y) in enumerate(zip(a["restart"], t["restart"])) if x != y]
        row.update(twin=jt, day_identical=day_same, diff_live=diff_live, diff_restart=diff_rest,
                   episodes_at_night=t["episodes_at_night"],
                   seconds=[a["seconds"], t["seconds"]])
        if r["kind"] == "clean":
            ja = judge_arm(a, words, grades, B)
            row["case"] = ja
            row["ok"] = ja["ok"] and jt["ok"] and day_same and not diff_live and not diff_rest
        else:
            shows = ("both" if diff_live and diff_rest else
                     "live only" if diff_live else "restart only" if diff_rest else "none")
            row["shows"] = shows
            row["changed_probes"] = [
                {"probe": case["probes"][i], "twin": t["live"][i], "fault": a["live"][i],
                 "when": "live"} for i in diff_live][:3] + [
                {"probe": case["probes"][i], "twin": t["restart"][i],
                 "fault": a["restart"][i], "when": "restart"} for i in diff_rest][:3]
            row["ok"] = jt["ok"] and day_same and bool(diff_live or diff_rest)
        rows.append(row)
    clean_ok = sum(1 for x in rows if x["kind"] == "clean" and x["ok"])
    fault_ok = sum(1 for x in rows if x["kind"] == "fault" and x["ok"])
    return {"clean_pass": f"{clean_ok}/20", "fault_pass": f"{fault_ok}/20",
            "passed": clean_ok == 20 and fault_ok == 20, "cases": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--one")
    ap.add_argument("--one-out")
    ap.add_argument("--parts", default=None, help="folder for per-case results (reused)")
    ap.add_argument("--eval-only", action="store_true", help="only re-judge saved parts")
    args = ap.parse_args(argv)
    if args.one:
        return one(args.one, args.one_out)
    import claude_slp364e_bench as B
    ids = [c["id"] for c in B.CASES if not args.only or c["id"] in args.only]
    parts = Path(args.parts or tempfile.mkdtemp(prefix="b364e-parts-"))
    parts.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    workers = max(1, min(2, args.workers))
    pending = [] if args.eval_only else list(ids)
    running: list = []
    while pending or running:
        while pending and len(running) < workers:
            cid = pending.pop(0)
            out = parts / f"{cid}.json"
            p = subprocess.Popen([sys.executable, "-B", __file__, "--one", cid,
                                  "--one-out", str(out)], env=env)
            running.append((cid, p, time.time()))
        time.sleep(1.0)
        for item in list(running):
            cid, p, t0 = item
            if p.poll() is not None:
                running.remove(item)
                print(f"{cid} done rc={p.returncode} {time.time() - t0:.0f}s", flush=True)
    results = []
    for cid in [c["id"] for c in B.CASES]:
        f = parts / f"{cid}.json"
        if f.exists():
            results.append(json.loads(f.read_text(encoding="utf-8")))
    summary = evaluate(results)
    summary["parts"] = str(parts)
    if args.out:
        Path(args.out).write_text(json.dumps(summary, indent=1, ensure_ascii=False),
                                  encoding="utf-8")
    print(summary["clean_pass"], summary["fault_pass"], "passed" if summary["passed"] else "FAILED")
    for x in summary["cases"]:
        if not x.get("ok"):
            print("FAIL", json.dumps(x, ensure_ascii=False)[:1500])
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
