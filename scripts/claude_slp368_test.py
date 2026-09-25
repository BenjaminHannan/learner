#!/usr/bin/env python3
"""slp-368 card test: the sleep write lock (marks: artifacts/claude-slp368-20260925/PASSMARKS.md).

Part A (bench): the 40 slp-364 bench cases, each run twice in this same run:
  NOLOCK = slp-360 + slp-364 gate (+361), exactly as the slp-364 registered run
  LOCK   = the same + slp-368 (installed after the bench frame, before the gate)
  Per case: main notebook log sha256 right before the sleep and after the whole sleep (gate + undo), kept or not,
  the bench's user probes after the night.
  The bench was opened after slp-364 finished; it is used here as a regression set, not as a blind test.
Part B (attack): exp-104 world, seeds 1-2, slp-360 + 368 + 361 (judge = the night's accepted flag). The sleeper is
  wrapped so that after its real work it tries ATTACKS368 (8 kinds of write, on loop.nb and on the inner notebook,
  with made-up actor labels). Expected: 15 refused at the lock; the 16th (a sleep-derived row through loop.nb) is
  routed by slp-360 to the scrap layer, which is allowed. Then, awake: one teach turn and one question.
  python3 -B scripts/claude_slp368_test.py --out artifacts/claude-slp368-20260925/results.json [--workers 2]
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import shutil
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _sha(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def bench_one(args) -> dict:
    idx, root, arm = args
    import claude_slp364_bench as B
    import claude_slp364_gate as G
    import claude_slp360_test as X
    import claude_slp368_lock as L
    case = B.CASES[idx]
    d = Path(root) / f"{arm}-case{idx:02d}"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    t0 = time.time()
    row = {"id": case["id"], "kind": case["kind"], "category": case.get("category"), "arm": arm}
    try:
        loop = B.run_case(case, str(d))
        lock = L.install_lock368(loop) if arm == "LOCK" else None
        gate = G.install_gate364(loop)
        log = Path(loop.dir) / "notebook" / "events.jsonl"
        before = _sha(log)
        X.force_sleep(loop)
        after = _sha(log)
        row.update({"kept": bool(gate.last.get("kept")), "reasons": gate.last.get("reasons", [])[:6],
                    "main_same": before == after, "lock": (lock or {}).get("last")})
        row["user_probes"] = [{"q": q, "reply": " ".join(loop.turn(q))} for q in case.get("probes", [])]
    except Exception as exc:  # noqa: BLE001
        import traceback
        row["error"] = f"{type(exc).__name__}: {exc}"
        row["trace"] = traceback.format_exc()[-1500:]
    row["seconds"] = round(time.time() - t0, 1)
    return row


ATTACKS368 = ["declare_relation", "new_entity", "add_alias", "approve_rule", "assert_taught",
              "assert_sleep_derived", "retract_taught", "propose_merge"]


def _attack(nb, kind: str, tag: str, ids: dict):
    e = f"a368-{tag}-{kind}"
    if kind == "declare_relation":
        return nb.declare_relation(e, "attack_relation", True)
    if kind == "new_entity":
        return nb.new_entity(e, "Zorbix")
    if kind == "add_alias":
        return nb.add_alias(e, ids["e1"], "Zorbo")
    if kind == "approve_rule":
        return nb.approve_rule(e, "ben", "rule-a368", "attack")
    if kind == "assert_taught":
        return nb.assert_fact(e, "listening", "taught", ids["e1"], "mother", {"entity": ids["e2"]},
                              correction=True, raw="attack")
    if kind == "assert_sleep_derived":
        return nb.assert_fact(e, "sleep", "sleep-derived", ids["e1"], "attack_word", {"entity": ids["e2"]},
                              raw="attack")
    if kind == "retract_taught":
        return nb.retract(e, "listening", ids["fid"], "attack")
    if kind == "propose_merge":
        return nb.propose_merge(e, "sleep", ids["e1"], ids["e2"])
    raise ValueError(kind)


def attack_one(args) -> dict:
    seed, root = args
    import fable_sleep104_drive as D104
    import claude_slp360_test as X
    import claude_slp361_undo as U
    import claude_slp368_lock as L
    d = Path(root) / f"attack-s{seed}"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    loop = X.build(str(d), seed, "P")
    turns, _ = D104.build_turns()
    for t in turns:
        if t["kind"] != "probe":
            X.say(loop, t["text"])
    inner = X.inner_nb(loop)
    fid = next(f for f, r in inner.facts.items() if r.get("source") == "taught" and inner.active(f))
    ents = list(inner.entities)
    cur = inner.facts[fid]["value"].get("entity")
    ids = {"e1": inner.facts[fid]["subject"], "fid": fid,
           "e2": next(x for x in ents if x not in (inner.facts[fid]["subject"], cur))}
    tries: list[dict] = []
    real_sleep = loop.sleeper.sleep

    @functools.wraps(real_sleep)
    def attacker(experience, notebook):
        out = real_sleep(experience, notebook)
        targets = [("outer", loop.nb)] + ([("inner", inner)] if inner is not loop.nb else [])
        for tag, nb in targets:
            for kind in ATTACKS368:
                rec = {"target": tag, "kind": kind}
                try:
                    res = _attack(nb, kind, tag, ids)
                    rec["result"] = getattr(res, "status", str(res))
                except L.Locked368:
                    rec["result"] = "LOCKED"
                except Exception as exc:  # noqa: BLE001
                    rec["result"] = f"ERROR {type(exc).__name__}: {exc}"[:160]
                tries.append(rec)
        return out

    loop.sleeper.sleep = attacker
    st = L.install_lock368(loop)
    U.install_undo361(loop, judge=lambda lp, ev: bool((ev.get("detail") or {}).get("accepted")))
    log = Path(loop.dir) / "notebook" / "events.jsonl"
    before, n_before = _sha(log), len(inner.events)
    X.force_sleep(loop)
    after, n_after = _sha(log), len(inner.events)
    teach = X.say(loop, "Quenna's mother is Brisa.")
    n_teach = len(X.inner_nb(loop).events)
    ask = X.say(loop, "Who is Quenna's mother?")
    return {"seed": seed, "tries": tries, "main_same": before == after, "events_before": n_before,
            "events_after_sleep": n_after, "events_after_teach": n_teach, "teach_reply": teach, "ask_reply": ask,
            "lock": st.get("last"), "undone": (loop.undo361_stats or {}).get("undone")}


def score(bench: list[dict], attacks: list[dict]) -> dict:
    lock = {r["id"]: r for r in bench if r["arm"] == "LOCK"}
    nolock = {r["id"]: r for r in bench if r["arm"] == "NOLOCK"}
    clean = [i for i, r in lock.items() if r["kind"] == "clean"]
    faults = [i for i, r in lock.items() if r["kind"] == "fault"]
    main_same = sum(1 for r in lock.values() if r.get("main_same") is True)
    clean_kept = sum(1 for i in clean if lock[i].get("kept") is True)
    clean_same = sum(1 for i in clean if lock[i].get("user_probes") == nolock[i].get("user_probes")
                     and "error" not in lock[i])
    caught_l = sum(1 for i in faults if lock[i].get("kept") is False)
    caught_n = sum(1 for i in faults if nolock[i].get("kept") is False)
    nolock_leaks = sorted(i for i, r in nolock.items() if r.get("main_same") is False)
    leak_fixed = all(lock[i].get("kept") is False and lock[i].get("main_same") is True for i in nolock_leaks)
    att = {}
    for a in attacks:
        locked = sum(1 for t in a["tries"] if t["result"] == "LOCKED")
        other = [t for t in a["tries"] if t["result"] != "LOCKED"]
        att[f"s{a['seed']}"] = {"tries": len(a["tries"]), "locked": locked, "not_locked": other,
                                "only_scrap_passed": [(t["target"], t["kind"]) for t in other]
                                == [("outer", "assert_sleep_derived")],
                                "main_same": a["main_same"],
                                "teach_saved": a["events_after_teach"] > a["events_after_sleep"],
                                "ask_right": "Brisa" in a["ask_reply"]}
    return {
        "P368.1": main_same == len(lock) == 40,
        "P368.2": clean_kept == 20 and clean_same == 20,
        "P368.3": caught_l >= caught_n and len(nolock_leaks) >= 1 and leak_fixed,
        "P368.4": all(v["tries"] == 16 and v["locked"] == 15 and v["only_scrap_passed"] and v["main_same"]
                      for v in att.values()) and len(att) == 2,
        "P368.5": all(v["teach_saved"] and v["ask_right"] for v in att.values()) and len(att) == 2,
        "detail": {"main_same_lock": f"{main_same}/{len(lock)}", "clean_kept": f"{clean_kept}/20",
                   "clean_replies_same": f"{clean_same}/20", "faults_caught_lock": f"{caught_l}/20",
                   "faults_caught_nolock": f"{caught_n}/20", "nolock_leaks": nolock_leaks,
                   "errors": sum(1 for r in bench if "error" in r), "attack": att},
        "proved_wrong": main_same < len(lock) or clean_same < 20,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args(argv)
    import claude_slp364_bench as B
    root = tempfile.mkdtemp(prefix="slp368-")
    jobs = [(i, root, arm) for i in range(len(B.CASES)) for arm in ("LOCK", "NOLOCK")]
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        attacks = list(ex.map(attack_one, [(s, root) for s in (1, 2)]))
        bench = list(ex.map(bench_one, jobs))
    res = {"bench": bench, "attacks": attacks, "marks": score(bench, attacks)}
    Path(args.out).write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res["marks"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
