#!/usr/bin/env python3
"""Experiment 121 marks: T4 packed-fact probes + loop102 marks P2/P3/P4 vs loop121.

Copy of the exp-113 marks shape with ONLY the agent class changed (agent
class swap, as prior briefs allow): every Loop113Daemon/build_agent113
reference now points at Loop121Daemon/build_agent121; reports land under the
exp-121 artifact folder (never in another experiment's folder). Sealed
artifacts and other modules are read, never written.

  T4  R110 L1 + L2 + L4 re-run through Loop121Daemon, judged with the
      unchanged redteam110 judge, plus the brief's literal probe
      ("Mira's city is Oslo and Tom's pet is a cat."): every probe must
      refuse with the one-fact-at-a-time clarify and write zero new facts
      on every turn.
  P2  all 64 sealed red-team-98 cases through Loop121Daemon; 0 OK->BUG vs the
      sealed run-2 verdicts; every change listed.
  P3  loop96 marks L1-L6 re-run with the loop121 agent swapped in (runtime
      monkeypatch of the imported module objects only; no file edited).
  P4  30 sealed innocent sentences through Loop121Daemon; false refusals gate
      (must equal the sealed loop102 outcome: 0 false refusals, 0 nonpass).

Run (Mac CPU, offline; only AFTER PASSMARKS are sealed, as part of the
registered exp-121 wave):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop121_marks.py --mark all
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop121_agent as L121  # noqa: E402 (this experiment's agent)
import fable_redteam110_cases as R110C  # noqa: E402 (T4 cases, read-only)
import fable_redteam110_runner as R110  # noqa: E402 (T4 judge, read-only)
import fable_redteam98_cases as RC  # noqa: E402 (sealed steps+expect, read-only)
import fable_redteam98_runner as R98  # noqa: E402 (judge, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-bench121-20260922" / "regression"
ART98 = ROOT / "artifacts" / "fable-redteam98-20260921"
ART102 = ROOT / "artifacts" / "fable-loop102-20260921"
PY121 = [sys.executable, "-B", str(SCRIPTS / "fable_loop121_agent.py")]

T4_IDS = ["L1", "L2", "L4"]
T4_LITERAL = "Mira's city is Oslo and Tom's pet is a cat."


def cfg121(state_dir) -> dict:
    cfg = copy.deepcopy(L121.DEFAULT_CONFIG121)
    cfg["state_dir"] = str(state_dir)
    cfg["sleep_threshold"] = 10 ** 9
    return cfg


def new_daemon121(root: Path):
    return L121.Loop121Daemon(root, cfg={"sleep_threshold": 100000},
                              idle_seconds=3600.0)


def process_pending(daemon, root: Path, log: list) -> None:
    for path in sorted((root / "inbox").glob("*.txt")):
        before = R98.fact_count(daemon)
        try:
            daemon.process_file(path)
            writes = R98.fact_count(daemon) - before
            reply = (root / "outbox" / path.name).read_text(encoding="utf-8")
            statuses = [r.get("status", r.get("kind", "?"))
                        for r in daemon.loop.last_records]
        except Exception as exc:  # noqa: BLE001 -- observed, never raised
            reply = f"HARNESS-CAUGHT {type(exc).__name__}: {exc}"
            statuses = ["EXCEPTION"]
            writes = 0
            try:
                os.replace(path, root / "done" / path.name)
            except OSError:
                pass
        log.append({"file": path.name, "reply": reply, "statuses": statuses,
                    "fact_writes": writes})


def do_kill9_burst(root: Path, log: list, script: Path) -> dict:
    out: dict = {"phase": "kill9"}
    cmd = [sys.executable, "-B", str(script),
           "--daemon", "--dir", str(root), "--idle-seconds", "3600"]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    try:
        for _ in range(900):
            if (root / "daemon_status.json").exists():
                break
            if proc.poll() is not None:
                break
            time.sleep(0.1)
        texts, gold = [], {}
        for i in range(30):
            tag = f"{i:02d}"
            texts.append((f"b_{len(texts):02d}.txt",
                          f"The capital of C{tag} is V{tag}"))
            if i == 10:
                texts.append((f"b_{len(texts):02d}.txt",
                              "The capital of C10 is W10"))
            gold[f"C{i:02d}"] = "W10" if i == 10 else f"V{i:02d}"
        for name, text in texts:
            (root / "inbox" / name).write_text(text, encoding="utf-8")
        time.sleep(0.5)
        try:
            os.kill(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=60)
        out["killed"] = True
        out["done_before_death"] = len(list((root / "done").glob("*.txt")))
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=60)
    try:
        daemon = new_daemon121(root)
        out["boot_ok"] = True
        out["boot_notes"] = list(daemon.loop.notes)
    except Exception as exc:  # noqa: BLE001
        out["boot_ok"] = False
        out["boot_error"] = f"{type(exc).__name__}: {exc}"
        out["gold"] = gold
        return out
    correct = wrong = abstained = 0
    detail = []
    others = set(gold.values())
    for subj, want in sorted(gold.items()):
        (root / "inbox" / f"q_{subj}.txt").write_text(
            f"Who is {subj}'s capital?", encoding="utf-8")
        process_pending(daemon, root, log)
        reply = log[-1]["reply"]
        bad = [v for v in others - {want} if v in reply]
        if want in reply and not bad:
            correct += 1
        elif bad:
            wrong += 1
        else:
            abstained += 1
        detail.append({"ask": subj, "want": want, "got": reply.strip()[:80],
                        "verdict": "correct" if (want in reply and not bad)
                        else ("WRONG" if bad else "abstain")})
    out.update({"gold": gold, "correct": correct, "wrong": wrong,
                "abstained": abstained, "detail": detail})
    log.append({"file": "KILL9-SUMMARY",
                "reply": f"correct={correct} wrong={wrong} abstained={abstained}",
                "statuses": [], "fact_writes": 0})
    return out


def run_case(case: dict, workroot: Path, factory) -> dict:
    root = Path(tempfile.mkdtemp(prefix=case["id"] + "_", dir=str(workroot)))
    (root / "inbox").mkdir(exist_ok=True)
    log: list = []
    info: dict = {"boot_ok_count": 0, "boot_refused": None,
                   "torn_repaired": False}
    try:
        daemon = factory(root)
    except Exception as exc:  # noqa: BLE001
        return {"id": case["id"], "group": case["group"], "root": str(root),
                "log": log, "info": info, "observed": f"boot failed: {exc}",
                "verdict": "UNCLEAR", "reason": "fresh daemon would not boot"}
    auto = 0
    batch: list[Path] = []

    def next_name(explicit=None):
        nonlocal auto
        if explicit:
            return explicit
        name = f"msg_{auto:02d}.txt"
        auto += 1
        return name

    def flush_batch():
        if batch:
            stamp = time.time()
            for p in batch:
                os.utime(p, (stamp, stamp))
            batch.clear()
        process_pending(daemon, root, log)

    for step in case["steps"]:
        op = step["op"]
        if op == "send":
            name = next_name(step.get("file"))
            p = root / "inbox" / name
            p.write_text(step["text"], encoding="utf-8")
            if step.get("same_second"):
                batch.append(p)
            else:
                flush_batch()
        elif op == "send_bytes":
            flush_batch()
            auto += 1
            (root / "inbox" / f"msg_{auto:02d}.txt").write_bytes(
                bytes.fromhex(step["data_hex"]))
            process_pending(daemon, root, log)
        elif op == "restart":
            flush_batch()
            try:
                daemon = factory(root)
                info["boot_ok_count"] += 1
                if any("repaired a torn notebook tail" in n
                        for n in daemon.loop.notes):
                    info["torn_repaired"] = True
                log.append({"file": "RESTART", "reply": "boot_ok",
                            "statuses": [], "fact_writes": 0,
                            "notes": list(daemon.loop.notes)})
            except Exception as exc:  # noqa: BLE001
                info["boot_refused"] = f"{type(exc).__name__}: {exc}"
                log.append({"file": "RESTART",
                            "reply": f"BOOT-REFUSED {type(exc).__name__}: {exc}",
                            "statuses": [], "fact_writes": 0})
                break
        elif op == "tear_tail":
            flush_batch()
            ev = root / "notebook" / "events.jsonl"
            lines = ev.read_text(encoding="utf-8").split("\n")
            if lines and lines[-1] == "":
                lines.pop()
            lines[-1] = lines[-1][: max(10, len(lines[-1]) * 4 // 10)]
            ev.write_text("\n".join(lines), encoding="utf-8")
            log.append({"file": "TEAR-TAIL", "reply": "last line truncated",
                        "statuses": [], "fact_writes": 0})
        elif op == "kill9_burst":
            flush_batch()
            info["kill9"] = do_kill9_burst(root, log,
                                           SCRIPTS / "fable_loop121_agent.py")
        else:
            raise ValueError(f"unknown op {op!r}")
    flush_batch()
    return {"id": case["id"], "group": case["group"], "root": str(root),
            "log": log, "info": info}


# ------------------------------------------------------------------ T4
def run_t4(out: Path) -> dict:
    t0 = time.time()
    workroot = out / "t4-tmp"
    workroot.mkdir(parents=True, exist_ok=True)
    by_id = {c["id"]: c for c in R110C.CASES}
    rows = []
    for cid in T4_IDS:
        case = by_id[cid]
        res = run_case(case, workroot, new_daemon121)
        verdict = R110.judge(case, res)
        writes = [e.get("fact_writes", 0) for e in res["log"]]
        rows.append({
            "id": cid, "group": case["group"],
            "verdict": verdict["verdict"],
            "reason": verdict.get("reason", "")[:200],
            "max_writes": max(writes) if writes else 0,
            "total_writes": sum(writes),
            "final": next(
                (e["reply"] for e in reversed(res["log"])
                 if e["file"] not in ("RESTART", "TEAR-TAIL", "KILL9-SUMMARY",
                                      "KILL9-SKIP")),
                "")[:160]})
        print(f"T4 {cid}: verdict={verdict['verdict']} "
              f"writes={sum(writes)}", flush=True)
    # Brief literal probe: packed "and" teach must be refused, 0 writes.
    root = Path(tempfile.mkdtemp(prefix="t4literal_", dir=str(workroot)))
    (root / "inbox").mkdir(exist_ok=True)
    daemon = new_daemon121(root)
    log: list = []
    (root / "inbox" / "msg_00.txt").write_text(T4_LITERAL + "\n",
                                               encoding="utf-8")
    process_pending(daemon, root, log)
    reply = log[-1]["reply"]
    refused = ("split that" in reply.lower()
               and log[-1]["fact_writes"] == 0)
    rows.append({"id": "LITERAL", "group": "brief-probe",
                 "verdict": "OK" if refused else "BUG",
                 "reason": "" if refused else f"reply={reply[:120]!r}",
                 "max_writes": log[-1]["fact_writes"],
                 "total_writes": log[-1]["fact_writes"],
                 "final": reply[:160]})
    print(f"T4 LITERAL: {'OK' if refused else 'BUG'} :: {reply[:100]!r}",
          flush=True)
    ok = all(r["verdict"] == "OK" and r["total_writes"] == 0 for r in rows)
    rep = {"mark": "T4", "n": len(rows), "pass": bool(ok),
           "seconds": round(time.time() - t0, 1), "rows": rows}
    (out / "t4-report-loop121.json").write_text(json.dumps(rep, indent=1),
                                                encoding="utf-8")
    print(f"T4: -> {'PASS' if rep['pass'] else 'FAIL'}")
    return rep


# ------------------------------------------------------------------ P2
def run_p2(out: Path) -> dict:
    t0 = time.time()
    workroot = out / "p2-tmp"
    workroot.mkdir(parents=True, exist_ok=True)
    sealed = json.loads((ART98 / "fable_redteam98_results.json").read_text(
        encoding="utf-8"))
    base_verdict = {c["id"]: (c.get("verdict"),
                              c.get("observed_final", "")[:160])
                    for c in sealed["cases"]}
    rows = []
    for case in RC.CASES:
        res = run_case(case, workroot, new_daemon121)
        verdict = R98.judge(case, res)
        final = next(
            (e["reply"] for e in reversed(res["log"])
             if e["file"] not in ("RESTART", "TEAR-TAIL", "KILL9-SUMMARY",
                                  "KILL9-SKIP")),
            "")[:160]
        b_verdict, b_final = base_verdict[case["id"]]
        rows.append({"id": case["id"], "group": case["group"],
                     "sealed_verdict": b_verdict,
                     "loop121_verdict": verdict["verdict"],
                     "reason": verdict.get("reason", "")[:200],
                     "reply_changed": (final != b_final),
                     "loop121_final": final})
        print(f"P2 {case['id']}: sealed={b_verdict} "
              f"loop121={verdict['verdict']}", flush=True)
    ok_to_bug = [r["id"] for r in rows
                 if r["sealed_verdict"] == "OK"
                 and r["loop121_verdict"] == "BUG"]
    bug_to_ok = [r["id"] for r in rows
                 if r["sealed_verdict"] == "BUG"
                 and r["loop121_verdict"] == "OK"]
    still_bug = [r["id"] for r in rows
                 if r["loop121_verdict"] == "BUG"]
    reply_changed_ok = [r["id"] for r in rows
                        if r["sealed_verdict"] == "OK"
                        and r["loop121_verdict"] == "OK"
                        and r["reply_changed"]]
    rep = {"mark": "P2-vs-loop121", "n": len(rows), "ok_to_bug": ok_to_bug,
           "bug_to_ok": bug_to_ok, "still_bug": still_bug,
           "reply_changed_ok_ok": reply_changed_ok,
           "pass": len(ok_to_bug) == 0 and len(still_bug) == 0,
           "seconds": round(time.time() - t0, 1), "rows": rows}
    (out / "p2-report-loop121.json").write_text(json.dumps(rep, indent=1),
                                                encoding="utf-8")
    print(f"P2: OK->BUG={ok_to_bug} BUG->OK={bug_to_ok} "
          f"stillBUG={still_bug} okReplyChanged={reply_changed_ok} "
          f"-> {'PASS' if rep['pass'] else 'FAIL'}")
    return rep


# ------------------------------------------------------------------ P3
def run_p3(out: Path, only: str | None = None) -> dict:
    t0 = time.time()
    import fable_loop96_agent as L96  # noqa: E402 (patched at runtime only)
    import fable_loop96_marks as M96  # noqa: E402 (runners reused, read-only)
    p3out = out / "p3"
    p3out.mkdir(parents=True, exist_ok=True)
    # Agent swap by runtime attribute patch only; no file is edited.
    L96.build_agent96 = L121.build_agent121
    L96.DEFAULT_CONFIG96 = L121.DEFAULT_CONFIG121
    M96.PY96 = list(PY121)

    def daemon_cfg121(state_dir: Path) -> dict:
        return cfg121(state_dir)
    M96.daemon_cfg96 = daemon_cfg121
    runners = {"l1": M96.run_l1, "l2": M96.run_l2, "l3": M96.run_l3,
               "l4": M96.run_l4, "l5z1": M96.run_l5z1, "l5z2": M96.run_l5z2,
               "l6": M96.run_l6}
    selected = [only] if only else list(runners)
    reps = {}
    ok = True
    for name in selected:
        rep = runners[name](p3out)
        reps[name] = {"pass": bool(rep["pass"]),
                      "seconds": rep.get("seconds")}
        ok = ok and bool(rep["pass"])
    rep = {"mark": "P3-vs-loop121", "selected": selected, "pass": bool(ok),
           "seconds": round(time.time() - t0, 1), "marks": reps}
    (out / f"p3-report-loop121-{only or 'all'}.json").write_text(
        json.dumps(rep, indent=1), encoding="utf-8")
    print(f"P3({only or 'all'}): -> {'PASS' if rep['pass'] else 'FAIL'}")
    return rep


# ------------------------------------------------------------------ P4
def show_value(nb, value: dict) -> str:
    if "entity" in value:
        return nb.entities.get(value["entity"], f"?{value['entity']}")
    return str(value.get("literal"))


def run_p4(out: Path) -> dict:
    t0 = time.time()
    (out / "p4-tmp").mkdir(parents=True, exist_ok=True)
    p4 = json.loads((ART102 / "p4-innocent-30.json").read_text(
        encoding="utf-8"))
    rows = []
    for item in p4["sentences"]:
        root = Path(tempfile.mkdtemp(prefix="p4_", dir=str(out / "p4-tmp")))
        (root / "inbox").mkdir(exist_ok=True)
        d = new_daemon121(root)
        log: list = []
        nb = d.loop.nb
        steps = list(item.get("setup", [])) + [item["text"]]
        for j, text in enumerate(steps):
            if j == len(steps) - 1:
                before_facts = set(nb.facts)
                before_entities = dict(nb.entities)
            p = root / "inbox" / f"s{j:02d}.txt"
            p.write_text(text, encoding="utf-8")
            process_pending(d, root, log)
        exp = item.get("expect", {})
        row = {"id": item["id"], "text": item["text"],
               "replies": [e["reply"].strip()[:160] for e in log]}
        if "stored_value" in exp or "stored_entity_suffix" in exp:
            last = log[-1]
            new_facts = [(fid, nb.facts[fid]["relation"],
                          show_value(nb, nb.facts[fid]["value"]))
                         for fid in set(nb.facts) - before_facts
                         if fid in nb.facts]
            new_entities = [name for eid, name in nb.entities.items()
                            if eid not in before_entities]
            lits = [v for _, _, v in new_facts]
            ents = list(new_entities)
            if "stored_value" in exp:
                row.update({"stored": lits,
                            "pass": exp["stored_value"] in lits})
            else:
                row.update({"stored_entities": ents,
                            "pass": any(exp["stored_entity_suffix"] in e
                                        for e in ents)})
            row["false_refusal"] = (not row["pass"]
                                    and last["fact_writes"] == 0)
        else:
            got = log[-1]["reply"]
            row.update({"pass": exp["ask_contains"] in got,
                        "false_refusal": exp["ask_contains"] not in got})
        rows.append(row)
        print(f"P4 {item['id']}: {'PASS' if row['pass'] else 'FAIL'}",
              flush=True)
    refusals = [r["id"] for r in rows if r.get("false_refusal")]
    bad = [r["id"] for r in rows if not r["pass"]]
    rep = {"mark": "P4-vs-loop121", "n": len(rows),
           "false_refusals": refusals, "nonpass": bad,
           "pass": len(refusals) == 0 and len(bad) == 0,
           "seconds": round(time.time() - t0, 1), "rows": rows}
    (out / "p4-report-loop121.json").write_text(json.dumps(rep, indent=1),
                                                encoding="utf-8")
    print(f"P4: false_refusals={refusals} nonpass={bad} "
          f"-> {'PASS' if rep['pass'] else 'FAIL'}")
    return rep


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 121 marks T4+P2+P3+P4")
    parser.add_argument("--mark", choices=("t4", "p2", "p3", "p4", "l1",
                                           "l2", "l3", "l4", "l5z1",
                                           "l5z2", "l6", "all"),
                        required=True)
    parser.add_argument("--out", default=str(ART))
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    oks = []
    if args.mark in ("t4", "all"):
        oks.append(bool(run_t4(out)["pass"]))
    if args.mark in ("p2", "all"):
        oks.append(bool(run_p2(out)["pass"]))
    if args.mark == "p3":
        oks.append(bool(run_p3(out)["pass"]))
    elif args.mark in ("l1", "l2", "l3", "l4", "l5z1", "l5z2", "l6"):
        oks.append(bool(run_p3(out, args.mark)["pass"]))
    if args.mark == "all":
        for name in ("l1", "l2", "l3", "l4", "l5z1", "l5z2", "l6"):
            oks.append(bool(run_p3(out, name)["pass"]))
    if args.mark in ("p4", "all"):
        oks.append(bool(run_p4(out)["pass"]))
    print(f"MARKS121 {'PASS' if all(oks) else 'FAIL'} "
          f"({round(time.time() - t0, 1)} s)")
    return 0 if all(oks) else 1


if __name__ == "__main__":
    sys.exit(main())
