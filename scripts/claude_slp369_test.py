#!/usr/bin/env python3
"""slp-369 card test: put the main notebook back after a night that changed it (marks:
artifacts/claude-slp369-20260925/PASSMARKS.md). CPU, $0.

Arm R = slp-360 + slp-368 lock + slp-369 restore + slp-364c gate (v3, with restart check), for every case.
Part A: all 60 faulty nights of the three opened benches (slp-364, 364b, 364c). After each night, a fixed
        "after" sequence: teach two new people, ask, correct one, ask again (graded by the truth).
Part B: the 20 honest nights of the 364c bench; user replies compared with 364c's registered v3 arm (same gate,
        no 369), read from artifacts/claude-slp364c-20260925/results.json.
Part C: exp-104 world, seeds 1-2: after its real work the sleeper appends a RETRACT line straight to the log file
        with its own open() and also adds it to the in-memory event list (the slp364c-05 pattern), then the
        "after" sequence.
  python3 -B scripts/claude_slp369_test.py --out artifacts/claude-slp369-20260925/results.json [--workers 4]
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

AFTER369 = [("Aldrenka's mother is Belvoria.", None), ("Belvoria's mother is Cindrelle.", None),
            ("Who is Aldrenka's mother?", "Belvoria"), ("Who is Belvoria's mother?", "Cindrelle"),
            ("Actually, Aldrenka's mother is Cindrelle.", None), ("Who is Aldrenka's mother?", "Cindrelle")]


def _sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def _after(loop) -> dict:
    rows, ok = [], 0
    for text, want in AFTER369:
        rep = " ".join(loop.turn(text))
        good = (want is None and rep.startswith("Saved")) or (want is not None and want in rep
                                                                and "don't know" not in rep)
        if text.startswith("Actually") and want is None:
            good = "Cindrelle" in rep and "Aldrenka" in rep
        rows.append({"q": text, "reply": rep, "ok": good})
        ok += int(good)
    return {"rows": rows, "ok": ok, "n": len(AFTER369)}


def _install(loop, seed):
    import claude_slp364c_gate as GC
    import claude_slp368_lock as L
    import claude_slp369_restore as R
    import claude_slp360_test as X
    L.install_lock368(loop)
    rs = R.install_restore369(loop)
    gate = GC.install_gate364c(loop, rebuild=lambda sd: X.build(sd, seed, "P"))
    return rs, gate


def bench_one(args) -> dict:
    mod, idx, root, part = args
    import importlib
    import claude_slp360_test as X
    B = importlib.import_module(mod)
    case = B.CASES[idx]
    d = Path(root) / f"{case['id']}"
    t0 = time.time()
    row = {"id": case["id"], "kind": case["kind"], "category": case.get("category"), "part": part}
    try:
        loop = B.run_case(case, str(d / "state"))
        rs, gate = _install(loop, case["seed"])
        log = Path(loop.dir) / "notebook" / "events.jsonl"
        before = _sha(log)
        X.force_sleep(loop)
        row.update({"kept": bool(gate.last.get("kept")), "main_same": _sha(log) == before,
                    "restored": rs["restored"], "restore_last": rs["last"],
                    "aside": sorted(str(p.relative_to(d)) for p in (d / "state" / "undo361").glob("main369-*/*"))
                    if (d / "state" / "undo361").exists() else [],
                    "reasons": gate.last.get("reasons", [])[:4]})
        if part == "A":
            row["after"] = _after(loop)
        else:
            row["user_probes"] = [{"q": q, "reply": " ".join(loop.turn(q))} for q in case.get("probes", [])]
    except Exception as exc:  # noqa: BLE001
        import traceback
        row["error"] = f"{type(exc).__name__}: {exc}"
        row["trace"] = traceback.format_exc()[-1500:]
    row["seconds"] = round(time.time() - t0, 1)
    return row


def attack_one(args) -> dict:
    seed, root = args
    import fable_notebook_contract as C
    import fable_sleep104_drive as D104
    import claude_slp360_test as X
    d = Path(root) / f"attack-s{seed}"
    loop = X.build(str(d), seed, "P")
    for t in D104.build_turns()[0]:
        if t["kind"] != "probe":
            X.say(loop, t["text"])
    inner = X.inner_nb(loop)
    real = loop.sleeper.sleep

    @functools.wraps(real)
    def writer(experience, notebook):
        out = real(experience, notebook)
        fid = next(f for f, r in inner.facts.items() if r.get("source") == "taught" and inner.active(f))
        event = {"kind": "RETRACT", "event_id": f"a369-{fid}", "fact_id": fid, "actor": "sleep",
                 "reason": "attack", "n": len(inner.events) + 1, "prev": inner.last_sha, "v": C.FORMAT_VERSION}
        line = json.dumps(event, sort_keys=True, ensure_ascii=False)
        with open(inner.path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        inner.events.append(event)
        inner.event_ids.add(event["event_id"])
        inner.retracted.add(fid)
        inner.last_sha = C._sha(line)
        return out

    loop.sleeper.sleep = writer
    rs, gate = _install(loop, seed)
    log = Path(loop.dir) / "notebook" / "events.jsonl"
    before, n_before = _sha(log), len(inner.events)
    X.force_sleep(loop)
    res = {"seed": seed, "kept": bool(gate.last.get("kept")), "main_same": _sha(log) == before,
           "events_same": len(inner.events) == n_before, "restored": rs["restored"], "restore_last": rs["last"],
           "aside": [str(p.name) for p in (Path(loop.dir) / "undo361").glob("main369-*/*")]}
    res["after"] = _after(loop)
    return res


def score(rows, attacks) -> dict:
    A = [r for r in rows if r["part"] == "A"]
    Bc = [r for r in rows if r["part"] == "B"]
    ref = {r["id"]: r for r in json.load(open(ROOT / "artifacts" / "claude-slp364c-20260925" / "results.json"))["rows"]
           if r["arm"] == "V2"}
    a_main = sum(1 for r in A if r.get("main_same") is True)
    restored = [r for r in A if r.get("restored")]
    a_after = sum(1 for r in restored if r.get("after", {}).get("ok") == len(AFTER369))
    aside_ok = all(r.get("aside") for r in restored)
    b_kept = sum(1 for r in Bc if r.get("kept") is True)
    b_same = sum(1 for r in Bc if r.get("user_probes") == ref[r["id"]]["user_probes"])
    c_ok = all(a["main_same"] and a["events_same"] and not a["kept"] and a["restored"] == 1 and a["aside"]
               and a["after"]["ok"] == len(AFTER369) for a in attacks) and len(attacks) == 2
    return {"P369.1": a_main == len(A) == 60, "P369.2": a_after == len(restored) >= 1,
            "P369.3": b_kept == 20 and b_same == 20, "P369.4": c_ok, "P369.5": aside_ok and len(restored) >= 1,
            "detail": {"A_main_same": f"{a_main}/{len(A)}", "A_after_right_on_restored": f"{a_after}/{len(restored)}",
                       "A_after_right_all": f"{sum(1 for r in A if r.get('after', {}).get('ok') == len(AFTER369))}/{len(A)}",
                       "A_restored_nights": [r["id"] for r in restored],
                       "A_kept_faulty": [r["id"] for r in A if r.get("kept")],
                       "B_kept": f"{b_kept}/{len(Bc)}", "B_replies_same_as_364c_v3": f"{b_same}/{len(Bc)}",
                       "errors": sum(1 for r in rows if "error" in r),
                       "attacks": [{k: v for k, v in a.items() if k != "after"} | {"after_ok": a["after"]["ok"]}
                                   for a in attacks]},
            "proved_wrong": a_main < len(A) or b_same < 20}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)
    import importlib
    root = tempfile.mkdtemp(prefix="slp369-")
    jobs = []
    for mod in ("claude_slp364_bench", "claude_slp364b_bench", "claude_slp364c_bench"):
        B = importlib.import_module(mod)
        for i, c in enumerate(B.CASES):
            if c["kind"] == "fault":
                jobs.append((mod, i, root, "A"))
            elif mod == "claude_slp364c_bench":
                jobs.append((mod, i, root, "B"))
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        attacks = list(ex.map(attack_one, [(s, root) for s in (1, 2)]))
        rows = list(ex.map(bench_one, jobs))
    res = {"rows": rows, "attacks": attacks, "marks": score(rows, attacks)}
    Path(args.out).write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res["marks"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
