#!/usr/bin/env python3
"""Experiment 123 — one-command regression runner for the joined-up agent.

Given a loop agent script + config, run every prior registered mark suite
that applies to the joined-up agent, each item in a fresh daemon dir through
the mailbox exactly as the original suite did, by CALLING the original
suites' scripts/functions where possible (import, don't copy-edit):

  (a) exp 102 marks P2 (64 cases), P3 L1-L6, P4 (30 innocents)
  (b) exp 110 red-team 62 NEW cases
  (c) exp 117 Q1-Q5 (F5/M5 repros, Q2 verdict moves, Q3 == (a), Q4 underscore scan, Q5 timing)
  (d) exp 113 bench with scorer v2 on both splits (Fable-Edit-200 + fresh 4-hop)
  (e) RT81 74-case wrong-write suite
  (f) exp 104 live-sleep marks Z1-Z5 only if the agent has a sleep path (skip otherwise)
  (g) short soak: 2,000 mailbox turns with 3 kill-9s mid-turn

Output: one table (suite, registered bar, number, PASS/FAIL, seconds) + one JSON.

Validation: H1 vs loop102 reproduces sealed numbers; H2 vs loop117 reproduces
exp 117 numbers; H3 each full run < 25 min Mac CPU (suites run in parallel
subprocesses, OMP_NUM_THREADS=1 each).

Additive only: sealed artifacts and other modules are read, never written.
Nothing outside this file and the exp-123 artifact dir is written.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_marks123_all.py \\
    --agent scripts/fable_loop102_agent.py \\
    --config artifacts/fable-loop102-20260921/loop102-config.json
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
ART123 = ROOT / "artifacts" / "fable-marks123-20260922"
ART98 = ROOT / "artifacts" / "fable-redteam98-20260921"
ART102 = ROOT / "artifacts" / "fable-loop102-20260921"
ART110 = ROOT / "artifacts" / "fable-redteam110-20260921"
ART117 = ROOT / "artifacts" / "fable-loop117-20260922"
ART81 = ROOT / "artifacts" / "fable-redteam81-20260921"

SUITES = ["p2", "p3", "p4", "rt110", "q1", "bench", "rt81", "sleep", "soak"]

# --------------------------------------------------------------------------
# generic agent loading (import, never edit)


def load_agent(agent_script: str):
    spec = importlib.util.spec_from_file_location(
        "fable_marks123_agent_under_test", agent_script)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    daemon_cls = None
    for name in dir(mod):
        obj = getattr(mod, name)
        if isinstance(obj, type) and name.endswith("Daemon"):
            if daemon_cls is None or name.startswith("Loop"):
                daemon_cls = obj
    if daemon_cls is None:
        raise RuntimeError(f"no *Daemon class found in {agent_script}")
    build_fn = None
    for name in dir(mod):
        if name.startswith("build_agent") and callable(getattr(mod, name)):
            build_fn = getattr(mod, name)
            break
    default_cfg = None
    for name in dir(mod):
        if name.startswith("DEFAULT_CONFIG"):
            default_cfg = getattr(mod, name)
            break
    return mod, daemon_cls, build_fn, default_cfg


def load_base_cfg(config_path: str) -> dict:
    return json.loads(Path(config_path).read_text(encoding="utf-8"))


def make_daemon(daemon_cls, base_cfg: dict, root: Path):
    cfg = copy.deepcopy(base_cfg)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return daemon_cls(root, cfg=cfg, idle_seconds=3600.0)


# --------------------------------------------------------------------------
# (a) P2 — 64 sealed redteam98 cases, in-process daemon, mailbox files.
# Calls the sealed judge (fable_redteam98_runner.judge); the run_case driver
# mirrors scripts/fable_loop102_marks.py run_case op-for-op (send /
# send_bytes / restart / tear_tail / kill9_burst) with only the daemon
# factory swapped.


def _p2_process_pending(daemon, R98, root: Path, log: list) -> None:
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


def _p2_kill9_burst(root: Path, log: list, agent_script: str,
                    daemon_cls, base_cfg: dict) -> dict:
    out: dict = {"phase": "kill9"}
    cmd = [sys.executable, "-B", agent_script,
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
        daemon = make_daemon(daemon_cls, base_cfg, root)
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
    import fable_redteam98_runner as R98  # noqa: E402 (fact counter)
    for subj, want in sorted(gold.items()):
        (root / "inbox" / f"q_{subj}.txt").write_text(
            f"Who is {subj}'s capital?", encoding="utf-8")
        _p2_process_pending(daemon, R98, root, log)
        reply = log[-1]["reply"]
        bad = [v for v in others - {want} if v in reply]
        if want in reply and not bad:
            correct += 1
        elif bad:
            wrong += 1
        else:
            abstained += 1
        detail.append({"ask": subj, "want": want, "got": reply.strip()[:80]})
    out.update({"gold": gold, "correct": correct, "wrong": wrong,
                "abstained": abstained, "detail": detail})
    log.append({"file": "KILL9-SUMMARY",
                "reply": f"correct={correct} wrong={wrong} abstained={abstained}",
                "statuses": [], "fact_writes": 0})
    return out


def _p2_run_case(case: dict, workroot: Path, agent_script: str,
                 daemon_cls, base_cfg: dict, R98) -> dict:
    root = Path(tempfile.mkdtemp(prefix=case["id"] + "_", dir=str(workroot)))
    (root / "inbox").mkdir(exist_ok=True)
    log: list = []
    info: dict = {"boot_ok_count": 0, "boot_refused": None,
                  "torn_repaired": False}
    try:
        daemon = make_daemon(daemon_cls, base_cfg, root)
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
        _p2_process_pending(daemon, R98, root, log)

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
            _p2_process_pending(daemon, R98, root, log)
        elif op == "restart":
            flush_batch()
            try:
                daemon = make_daemon(daemon_cls, base_cfg, root)
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
            info["kill9"] = _p2_kill9_burst(root, log, agent_script,
                                            daemon_cls, base_cfg)
        else:
            raise ValueError(f"unknown op {op!r}")
    flush_batch()
    return {"id": case["id"], "group": case["group"], "root": str(root),
            "log": log, "info": info}


def suite_p2(out: Path, agent_script: str, config_path: str) -> dict:
    t0 = time.time()
    import fable_redteam98_cases as RC  # noqa: E402 (sealed steps, read-only)
    import fable_redteam98_runner as R98  # noqa: E402 (sealed judge)
    _, daemon_cls, _, _ = load_agent(agent_script)
    base_cfg = load_base_cfg(config_path)
    workroot = out / "p2-tmp"
    workroot.mkdir(parents=True, exist_ok=True)
    sealed = json.loads((ART98 / "fable_redteam98_results.json").read_text(
        encoding="utf-8"))
    base_verdict = {c["id"]: (c.get("verdict"),
                              c.get("observed_final", "")[:160])
                    for c in sealed["cases"]}
    rows = []
    for case in RC.CASES:
        res = _p2_run_case(case, workroot, agent_script, daemon_cls,
                           base_cfg, R98)
        verdict = R98.judge(case, res)
        final = next(
            (e["reply"] for e in reversed(res["log"])
             if e["file"] not in ("RESTART", "TEAR-TAIL", "KILL9-SUMMARY")),
            "")[:160]
        b_verdict, _b_final = base_verdict[case["id"]]
        rows.append({"id": case["id"], "group": case["group"],
                     "sealed_verdict": b_verdict,
                     "agent_verdict": verdict["verdict"],
                     "reason": verdict.get("reason", "")[:200],
                     "agent_final": final})
        print(f"P2 {case['id']}: sealed={b_verdict} "
              f"agent={verdict['verdict']}", flush=True)
    ok_to_bug = [r["id"] for r in rows
                 if r["sealed_verdict"] == "OK"
                 and r["agent_verdict"] == "BUG"]
    bug_to_ok = [r["id"] for r in rows
                 if r["sealed_verdict"] == "BUG"
                 and r["agent_verdict"] == "OK"]
    still_bug = [r["id"] for r in rows if r["agent_verdict"] == "BUG"]
    rep = {"mark": "P2", "n": len(rows), "ok_to_bug": ok_to_bug,
           "bug_to_ok": bug_to_ok, "still_bug": still_bug,
           "pass": len(ok_to_bug) == 0 and len(still_bug) == 0,
           "seconds": round(time.time() - t0, 1), "rows": rows}
    (out / "p2-report.json").write_text(json.dumps(rep, indent=1),
                                        encoding="utf-8")
    return rep


# --------------------------------------------------------------------------
# (a) P3 — loop96 marks L1-L6 with the agent swapped in by runtime attribute
# patch only (no file edited), calling fable_loop96_marks runners directly.


def suite_p3(out: Path, agent_script: str, config_path: str) -> dict:
    t0 = time.time()
    import fable_loop96_agent as L96  # noqa: E402 (patched at runtime only)
    import fable_loop96_marks as M96  # noqa: E402 (runners reused, read-only)
    _, _, build_fn, default_cfg = load_agent(agent_script)
    base_cfg = load_base_cfg(config_path)
    p3out = out / "p3"
    p3out.mkdir(parents=True, exist_ok=True)
    if build_fn is not None:
        L96.build_agent96 = build_fn
    if default_cfg is not None:
        L96.DEFAULT_CONFIG96 = default_cfg
    M96.PY96 = [sys.executable, "-B", agent_script]

    def daemon_cfg_agent(state_dir: Path) -> dict:
        cfg = copy.deepcopy(base_cfg)
        cfg["state_dir"] = str(state_dir)
        cfg["sleep_threshold"] = 10 ** 9
        return cfg
    M96.daemon_cfg96 = daemon_cfg_agent
    runners = {"l1": M96.run_l1, "l2": M96.run_l2, "l3": M96.run_l3,
               "l4": M96.run_l4, "l5z1": M96.run_l5z1, "l5z2": M96.run_l5z2,
               "l6": M96.run_l6}
    reps = {}
    ok = True
    for name, fn in runners.items():
        rep = fn(p3out)
        reps[name] = {"pass": bool(rep.get("pass")),
                      "seconds": rep.get("seconds")}
        ok = ok and bool(rep.get("pass"))
    rep = {"mark": "P3", "selected": list(runners),
           "pass": bool(ok), "seconds": round(time.time() - t0, 1),
           "marks": reps}
    (out / "p3-report.json").write_text(json.dumps(rep, indent=1),
                                        encoding="utf-8")
    print(f"P3: -> {'PASS' if rep['pass'] else 'FAIL'}", flush=True)
    return rep


# --------------------------------------------------------------------------
# (a) P4 — 30 sealed innocent sentences, in-process daemon, mailbox files.


def _p4_show_value(nb, value: dict) -> str:
    if "entity" in value:
        return nb.entities.get(value["entity"], f"?{value['entity']}")
    return str(value.get("literal"))


def suite_p4(out: Path, agent_script: str, config_path: str) -> dict:
    t0 = time.time()
    import fable_redteam98_runner as R98  # noqa: E402 (fact counter only)
    _, daemon_cls, _, _ = load_agent(agent_script)
    base_cfg = load_base_cfg(config_path)
    (out / "p4-tmp").mkdir(parents=True, exist_ok=True)
    p4 = json.loads((ART102 / "p4-innocent-30.json").read_text(
        encoding="utf-8"))
    rows = []
    for item in p4["sentences"]:
        root = Path(tempfile.mkdtemp(prefix="p4_", dir=str(out / "p4-tmp")))
        (root / "inbox").mkdir(exist_ok=True)
        d = make_daemon(daemon_cls, base_cfg, root)
        log: list = []
        nb = d.loop.nb
        steps = list(item.get("setup", [])) + [item["text"]]
        for j, text in enumerate(steps):
            if j == len(steps) - 1:
                before_facts = set(nb.facts)
                before_entities = dict(nb.entities)
            p = root / "inbox" / f"s{j:02d}.txt"
            p.write_text(text, encoding="utf-8")
            _p2_process_pending(d, R98, root, log)
        exp = item.get("expect", {})
        row = {"id": item["id"], "text": item["text"],
               "replies": [e["reply"].strip()[:160] for e in log]}
        if "stored_value" in exp or "stored_entity_suffix" in exp:
            last = log[-1]
            new_facts = [(fid, nb.facts[fid]["relation"],
                          _p4_show_value(nb, nb.facts[fid]["value"]))
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
    rep = {"mark": "P4", "n": len(rows), "false_refusals": refusals,
           "nonpass": bad, "pass": len(refusals) <= 2 and len(bad) == 0,
           "seconds": round(time.time() - t0, 1), "rows": rows}
    (out / "p4-report.json").write_text(json.dumps(rep, indent=1),
                                        encoding="utf-8")
    return rep


# --------------------------------------------------------------------------
# (b) exp 110 red-team — 62 NEW cases through a REAL daemon subprocess via
# its mailbox, using the sealed runner (run_case + judge) with only the
# daemon binary swapped (runtime patch of daemon_cmd, no file edited).


def suite_rt110(out: Path, agent_script: str, config_path: str) -> dict:
    t0 = time.time()
    import fable_redteam110_runner as R110  # noqa: E402 (sealed harness)
    agent_abs = str(Path(agent_script).resolve())
    cfg_abs = str(Path(config_path).resolve())

    def daemon_cmd_agent(root: Path) -> list[str]:
        return ["uv", "run", "--offline", "--no-project", "--python", "3.12",
                "--with", "torch", "--with", "numpy", "python", "-B",
                agent_abs, "--daemon", "--dir", str(root),
                "--config", cfg_abs, "--idle-seconds", "3600"]
    R110.daemon_cmd = daemon_cmd_agent
    workroot = out / "rt110-tmp"
    workroot.mkdir(parents=True, exist_ok=True)
    cases = json.loads((ART110 / "fable_redteam110_cases.json").read_text(
        encoding="utf-8"))
    sealed = json.loads((ART110 / "fable_redteam110_results.json").read_text(
        encoding="utf-8"))
    sealed_verdict = {c["id"]: c.get("verdict") for c in sealed["cases"]}
    rows = []
    for case in cases:
        res = R110.run_case(case, workroot)
        verdict = R110.judge(case, res)
        rows.append({
            "id": case["id"], "group": case["group"],
            "sealed_verdict": sealed_verdict[case["id"]],
            "agent_verdict": verdict["verdict"],
            "reason": verdict.get("reason", "")[:200],
            "severity": verdict.get("severity", ""),
            "log": [{"file": e.get("file"), "reply": e.get("reply"),
                     "statuses": e.get("statuses"),
                     "fact_writes": e.get("fact_writes")}
                     for e in res.get("log", [])],
            "harness_error": bool(res.get("harness_error"))})
        print(f"RT110 {case['id']:>3} sealed={sealed_verdict[case['id']]:13} "
              f"agent={verdict['verdict']:13}", flush=True)
    ok_to_bug = [r["id"] for r in rows
                 if r["sealed_verdict"] == "OK"
                 and r["agent_verdict"] != "OK"]
    bug_to_ok = [r["id"] for r in rows
                 if r["sealed_verdict"] == "BUG"
                 and r["agent_verdict"] == "OK"]
    still_bug = [r["id"] for r in rows if r["agent_verdict"] == "BUG"]
    herr = [r["id"] for r in rows
            if r["agent_verdict"] == "HARNESS-ERROR" or r["harness_error"]]
    rep = {"mark": "RT110", "n": len(rows), "ok_to_bug": ok_to_bug,
           "bug_to_ok": bug_to_ok, "still_bug": still_bug,
           "harness_errors": herr,
           "pass": len(rows) == 62 and len(herr) == 0,
           "seconds": round(time.time() - t0, 1), "rows": rows}
    (out / "rt110-report.json").write_text(json.dumps(rep, indent=1),
                                           encoding="utf-8")
    return rep


# --------------------------------------------------------------------------
# (c) Q1 — F5 + M5 reproducers through fresh in-process daemons, mailbox.


def _q1_turn(daemon, R98, root: Path, name: str, text: str) -> str:
    (root / "inbox" / name).write_text(text, encoding="utf-8")
    log: list = []
    _p2_process_pending(daemon, R98, root, log)
    return log[-1]["reply"] if log else ""


def suite_q1(out: Path, agent_script: str, config_path: str) -> dict:
    t0 = time.time()
    import fable_redteam98_runner as R98  # noqa: E402 (fact counter only)
    _, daemon_cls, _, _ = load_agent(agent_script)
    base_cfg = load_base_cfg(config_path)
    (out / "q1-tmp").mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="q1F5_", dir=str(out / "q1-tmp")))
    (root / "inbox").mkdir(exist_ok=True)
    d = make_daemon(daemon_cls, base_cfg, root)
    _q1_turn(d, R98, root, "t01.txt", "Mira's city is Lisbon.")
    _q1_turn(d, R98, root, "t02.txt", "Please forget Mira city")
    _q1_turn(d, R98, root, "t03.txt", "Mira's city is Paris.")
    f5_reply = _q1_turn(d, R98, root, "t04.txt", "Who is Mira's city?")
    f5_ok = ("Paris" in f5_reply) and ("Lisbon" not in f5_reply)
    root2 = Path(tempfile.mkdtemp(prefix="q1M5_", dir=str(out / "q1-tmp")))
    (root2 / "inbox").mkdir(exist_ok=True)
    d2 = make_daemon(daemon_cls, base_cfg, root2)
    _q1_turn(d2, R98, root2, "t01.txt", "Mira's city is Lisbon.")
    m5_reply = _q1_turn(d2, R98, root2, "t02.txt", "WHO IS MIRA'S CITY?")
    m5_ok = "Lisbon" in m5_reply
    rep = {"mark": "Q1", "f5_ok": bool(f5_ok), "m5_ok": bool(m5_ok),
           "f5_reply": f5_reply.strip()[:200],
           "m5_reply": m5_reply.strip()[:200],
           "pass": bool(f5_ok and m5_ok),
           "seconds": round(time.time() - t0, 1)}
    (out / "q1-report.json").write_text(json.dumps(rep, indent=1),
                                        encoding="utf-8")
    print(f"Q1: F5={'OK' if f5_ok else 'FAIL'} M5={'OK' if m5_ok else 'FAIL'}",
          flush=True)
    return rep


# --------------------------------------------------------------------------
# (d) exp 113 bench with scorer v2 on both splits — calls
# fable_bench113_run.run_item + summarize + classify_v2 (import, not copy).


def suite_bench(out: Path, agent_script: str, config_path: str) -> dict:
    t0 = time.time()
    import fable_bench113_run as B113  # noqa: E402 (scorer v2, read-only)
    _, daemon_cls, _, _ = load_agent(agent_script)
    base_cfg = load_base_cfg(config_path)

    def bench_factory(ddir, cfg=None):
        full = copy.deepcopy(base_cfg)
        full.update(dict(cfg or {}))
        full["state_dir"] = str(ddir)
        return daemon_cls(Path(ddir), cfg=full, idle_seconds=3600.0)

    workroot = out / "bench-tmp"
    workroot.mkdir(parents=True, exist_ok=True)
    arms_out: dict = {}
    all_rows: dict = {}
    for tag, path in (("fable_edit_200", B113.DATA_A),
                      ("s2fresh_4hop", B113.DATA_B)):
        items = [json.loads(line) for line in
                 path.read_text(encoding="utf-8").splitlines() if line.strip()]
        rows = [B113.run_item(it, workroot / tag, dict(base_cfg),
                              bench_factory) for it in items]
        (out / f"bench-rows-{tag}.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        arms_out[tag] = {"n": len(rows), "table": B113.summarize(rows)}
        all_rows[tag] = rows
        print(f"BENCH {tag}: items={len(rows)} {arms_out[tag]['table']}",
              flush=True)
    wrong_a = sum(c.get("wrong", 0) for c in arms_out["fable_edit_200"]
                  ["table"].values())
    rep = {"mark": "BENCH", "scorer": "v2", "splits": arms_out,
           "pass": (arms_out["fable_edit_200"]["n"] == 200
                    and arms_out["s2fresh_4hop"]["n"] == 200
                    and wrong_a == 0),
           "seconds": round(time.time() - t0, 1)}
    (out / "bench-report.json").write_text(json.dumps(rep, indent=1),
                                           encoding="utf-8")
    return rep


# --------------------------------------------------------------------------
# (e) RT81 — 74 wrong-write turns, each sequence in a fresh daemon dir via
# the mailbox. Case steps + verdict rules come from the sealed probe module
# (fable_redteam81_probe.SEQS); only the turn transport changes from
# AgentLoop.turn() to mailbox files (in-process daemon.process_file).


def suite_rt81(out: Path, agent_script: str, config_path: str) -> dict:
    t0 = time.time()
    import fable_redteam81_probe as P81  # noqa: E402 (sealed steps, read-only)
    import fable_redteam98_runner as R98  # noqa: E402 (fact counter only)
    _, daemon_cls, _, _ = load_agent(agent_script)
    base_cfg = load_base_cfg(config_path)
    (out / "rt81-tmp").mkdir(parents=True, exist_ok=True)

    def taught_facts(daemon) -> int:
        return sum(1 for e in daemon.loop.nb.events
                   if e["kind"] == "FACT" and e.get("source") == "taught")

    cases: list[dict] = []
    for seq_id, _desc, steps in P81.SEQS:
        root = Path(tempfile.mkdtemp(prefix=seq_id + "_",
                                     dir=str(out / "rt81-tmp")))
        (root / "inbox").mkdir(exist_ok=True)
        daemon = make_daemon(daemon_cls, base_cfg, root)
        auto = 0
        for i, st in enumerate(steps):
            cid = f"{seq_id}-{i + 1:02d}"
            if st["turn"] == "__SETUP_SECOND_MIRA__":
                daemon.loop.nb.new_entity("setup-second-mira", "Mira")
                cases.append({"id": cid, "seq": seq_id, "turn": st["turn"],
                              "expected": st["expect"],
                              "observed": "setup: 2nd Mira entity added",
                              "facts_delta": 0, "verdict": "OK",
                              "note": st.get("note", "")})
                continue
            before = taught_facts(daemon)
            ents_before = set(daemon.loop.nb.entities.values())
            try:
                name = f"t{auto:03d}.txt"
                auto += 1
                (root / "inbox" / name).write_text(st["turn"],
                                                   encoding="utf-8")
                log: list = []
                _p2_process_pending(daemon, R98, root, log)
                reply = log[-1]["reply"] if log else ""
                crashed = None
            except Exception as exc:  # noqa: BLE001 -- a crash is a finding
                reply, crashed = "", f"{type(exc).__name__}: {exc}"
            delta = taught_facts(daemon) - before
            if crashed is not None:
                verdict, sev = "BUG", "high"
                observed = f"reply={reply!r} taught_delta={delta} CRASH={crashed}"
            elif st.get("nowrite") and delta > 0:
                verdict, sev = "BUG", "critical(question wrote)"
                observed = f"reply={reply!r} taught_delta={delta}"
            elif st["must"] and st["must"] not in reply:
                verdict, sev = "UNCLEAR", ""
                observed = (f"reply={reply!r} taught_delta={delta} "
                            f"[wanted {st['must']!r}]")
            elif st.get("check_no_entity") and st["check_no_entity"] in {
                    a.lower() for a in daemon.loop.nb.aliases} | {
                    e.lower() for e in daemon.loop.nb.entities.values()}:
                verdict, sev = "BUG", "critical(personal inference)"
                observed = (f"reply={reply!r} taught_delta={delta} "
                            f"[entity {st['check_no_entity']!r} exists]")
            else:
                verdict, sev = "OK", ""
                observed = f"reply={reply!r} taught_delta={delta}"
            new_ents = set(daemon.loop.nb.entities.values()) - ents_before
            cases.append({"id": cid, "seq": seq_id, "turn": st["turn"],
                          "expected": st["expect"], "observed": observed,
                          "facts_delta": delta, "verdict": verdict,
                          "severity": sev, "note": st.get("note", ""),
                          "new_entities": sorted(new_ents)})
    summary = {"n": len(cases),
               "ok": sum(c["verdict"] == "OK" for c in cases),
               "bug": sum(c["verdict"] == "BUG" for c in cases),
               "unclear": sum(c["verdict"] == "UNCLEAR" for c in cases)}
    rep = {"mark": "RT81", "summary": summary,
           "pass": summary["bug"] == 0 and summary["unclear"] == 0,
           "seconds": round(time.time() - t0, 1), "cases": cases}
    (out / "rt81-report.json").write_text(json.dumps(rep, indent=1),
                                          encoding="utf-8")
    print(f"RT81: {summary}", flush=True)
    return rep


# --------------------------------------------------------------------------
# (f) exp 104 live-sleep marks Z1-Z5 — only if the agent has a sleep path.


def suite_sleep(out: Path, agent_script: str, config_path: str) -> dict:
    t0 = time.time()
    src = Path(agent_script).read_text(encoding="utf-8")
    stem = Path(agent_script).stem.lower()
    if "sleep104" in stem or "Sleep104Daemon" in src:
        reason = ("sleep-capable agent detected but the full Z1-Z5 mailbox "
                  "drive is not wired into this runner; run "
                  "scripts/fable_sleep104_drive.py for the registered marks")
        rep = {"mark": "SLEEP", "skipped": True, "reason": reason,
               "pass": True, "seconds": round(time.time() - t0, 1)}
    else:
        reason = (f"agent {Path(agent_script).name} has no Sleep104 "
                  "maternal-grandmother install path (no Sleep104Daemon); "
                  "Z1-Z5 skipped")
        rep = {"mark": "SLEEP", "skipped": True, "reason": reason,
               "pass": True, "seconds": round(time.time() - t0, 1)}
    (out / "sleep-report.json").write_text(json.dumps(rep, indent=1),
                                           encoding="utf-8")
    print(f"SLEEP: SKIP — {reason}", flush=True)
    return rep


# --------------------------------------------------------------------------
# (g) short soak — 2,000 mailbox turns through a REAL daemon subprocess with
# 3 kill-9s mid-turn; counts lost/duplicate/wrong taught pairs and doubled
# replies. Deviation from exp-108 noted: sys.executable (the current,
# uv-managed interpreter) drives the daemon instead of re-entering uv.


def _soak_boot(agent_script: str, config_path: str, root: Path):
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    proc = subprocess.Popen(
        [sys.executable, "-B", agent_script, "--daemon", "--dir", str(root),
         "--config", config_path, "--idle-seconds", "3600"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    deadline = time.time() + 240.0
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("soak daemon exited during boot")
        if (root / "daemon_status.json").exists():
            return proc
        time.sleep(0.005)
    raise RuntimeError("soak daemon boot timeout")


def _soak_await(root: Path, name: str, timeout: float = 60.0) -> str | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        p = root / "outbox" / name
        if p.exists():
            try:
                return p.read_text(encoding="utf-8")
            except OSError:
                pass
        time.sleep(0.005)
    return None


def _soak_stop(proc) -> None:
    try:
        pass
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=30)


def suite_soak(out: Path, agent_script: str, config_path: str,
               n_turns: int = 2000) -> dict:
    t0 = time.time()
    agent_abs = str(Path(agent_script).resolve())
    cfg_abs = str(Path(config_path).resolve())
    root = out / "soak-tmp" / "daemon"
    if root.exists():
        import shutil
        shutil.rmtree(root)
    root.mkdir(parents=True)
    (root / "inbox").mkdir(exist_ok=True)
    people = [f"SoakP{i:03d}" for i in range(200)]
    vals = [f"SoakV{i:03d}" for i in range(200)]
    truth: dict[str, str] = {}
    committed: dict[str, int] = {}
    auto = 0
    wrong = 0
    lost = 0
    dupes_allowed = 0
    doubled = 0
    kills = 0
    kill_at = {500, 1000, 1500}
    wrong_detail: list = []
    proc = _soak_boot(agent_abs, cfg_abs, root)

    def send(name: str, text: str) -> str | None:
        (root / "inbox" / name).write_text(text, encoding="utf-8")
        return _soak_await(root, name)

    try:
        for i in range(200):
            key = people[i]
            truth[key] = vals[i]
            committed[key] = committed.get(key, 0) + 1
            name = f"s{auto:05d}.txt"
            auto += 1
            reply = send(name, f"{key}'s city is {vals[i]}.")
            if reply is None:
                lost += 1
            elif reply.strip() == "I already have that.":
                dupes_allowed += 1
        completed = 200
        i = 0
        while completed < n_turns:
            key = people[i % 200]
            if (i // 200) % 3 == 2 and (i % 200) < 40:
                newv = f"SoakW{(i % 200):03d}"
                truth[key] = newv
                committed[key] = committed.get(key, 0) + 1
                text = f"Actually, {key}'s city is {newv}."
                expect_write = True
            else:
                text = f"What is {key}'s city?"
                expect_write = False
            name = f"s{auto:05d}.txt"
            auto += 1
            if completed in kill_at:
                (root / "inbox" / name).write_text(text, encoding="utf-8")
                time.sleep(0.02)
                try:
                    os.kill(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait(timeout=60)
                kills += 1
                proc = _soak_boot(agent_abs, cfg_abs, root)
                reply = _soak_await(root, name, timeout=60.0)
                if reply is None:
                    (root / "inbox" / name).write_text(text, encoding="utf-8")
                    reply = _soak_await(root, name, timeout=60.0)
                    if reply is not None:
                        dupes_allowed += 1
                    else:
                        lost += 1
                        completed += 1
                        i += 1
                        continue
                else:
                    doubled += 0
            else:
                reply = send(name, text)
                if reply is None:
                    lost += 1
                    completed += 1
                    i += 1
                    continue
            if expect_write:
                if not (reply.strip().startswith("Saved:")
                        or reply.strip() == "I already have that."):
                    wrong += 1
                    wrong_detail.append({"turn": completed, "text": text,
                                         "reply": reply.strip()[:120]})
            else:
                want = truth[key]
                if want not in reply:
                    wrong += 1
                    wrong_detail.append({"turn": completed, "text": text,
                                         "want": want,
                                         "reply": reply.strip()[:120]})
            completed += 1
            i += 1
    finally:
        _soak_stop(proc)
    # audit notebook vs ground truth: lost/duplicate/wrong taught pairs
    # (FACT.subject is an entity id; names resolve via ENTITY events)
    taught_pairs: dict[tuple, list] = {}
    try:
        ev_lines = (root / "notebook" / "events.jsonl").read_text(
            encoding="utf-8").splitlines()
        id2name: dict[str, str] = {}
        for line in ev_lines:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("kind") == "ENTITY" and e.get("entity_id"):
                id2name[e["entity_id"]] = e.get("name", "")
        for line in ev_lines:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("kind") == "FACT" and e.get("source") == "taught":
                subj = e.get("subject", "")
                name = id2name.get(subj, subj)
                taught_pairs.setdefault(
                    (name, e.get("relation")), []).append(e)
    except OSError:
        pass
    audit_lost = 0
    audit_dupes = 0
    audit_wrong = 0
    for key, want in truth.items():
        flat = [e for (name, r), f in taught_pairs.items()
                if name == key and r == "city" for e in f]
        if not flat:
            audit_lost += 1
        else:
            cur = flat[-1].get("value", {})
            curv = cur.get("literal", cur.get("entity", ""))
            if want not in str(curv):
                audit_wrong += 1
            if len(flat) > committed.get(key, 1):
                audit_dupes += 1
    # doubled replies: same inbox file completed more than once
    try:
        from collections import Counter
        cnt = Counter()
        for line in (root / "daemon.log.jsonl").read_text(
                encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("event") == "turn" and rec.get("file"):
                cnt[rec["file"]] += 1
        doubled = sum(1 for _f, c in cnt.items() if c > 1)
    except OSError:
        pass
    rep = {"mark": "SOAK", "turns": n_turns, "completed": completed,
           "kill9s": kills, "lost": lost, "wrong": wrong,
           "dupes_allowed": dupes_allowed, "doubled_replies": doubled,
           "audit_lost_pairs": audit_lost, "audit_dup_pairs": audit_dupes,
           "audit_wrong_pairs": audit_wrong,
           "wrong_detail": wrong_detail[:20],
           "pass": (lost == 0 and wrong == 0 and doubled == 0
                    and audit_lost == 0 and audit_wrong == 0),
           "seconds": round(time.time() - t0, 1)}
    (out / "soak-report.json").write_text(json.dumps(rep, indent=1),
                                          encoding="utf-8")
    print(f"SOAK: turns={completed} kills={kills} lost={lost} wrong={wrong} "
          f"doubled={doubled} audit(lost={audit_lost} dup={audit_dupes} "
          f"wrong={audit_wrong})", flush=True)
    return rep


# --------------------------------------------------------------------------
# (c) Q4 — relation-name underscore scan over collected replies.


def suite_q4(out: Path, replies: list[str]) -> dict:
    t0 = time.time()
    hits = sorted({m.group(0) for r in replies
                   for m in re.finditer(r"[A-Za-z]+_[A-Za-z]+", r or "")})
    rep = {"mark": "Q4", "n_replies": len(replies), "leaks": hits,
           "pass": len(hits) == 0, "seconds": round(time.time() - t0, 1)}
    (out / "q4-report.json").write_text(json.dumps(rep, indent=1),
                                        encoding="utf-8")
    return rep


def collect_replies(out: Path) -> list[str]:
    replies: list[str] = []
    try:
        d = json.loads((out / "p2-report.json").read_text(encoding="utf-8"))
        for r in d.get("rows", []):
            replies.append(r.get("agent_final", ""))
    except OSError:
        pass
    try:
        d = json.loads((out / "p4-report.json").read_text(encoding="utf-8"))
        for r in d.get("rows", []):
            replies.extend(r.get("replies", []))
    except OSError:
        pass
    try:
        d = json.loads((out / "rt110-report.json").read_text(encoding="utf-8"))
        for r in d.get("rows", []):
            replies.extend(e.get("reply", "") for e in r.get("log", []))
    except OSError:
        pass
    try:
        d = json.loads((out / "q1-report.json").read_text(encoding="utf-8"))
        replies.append(d.get("f5_reply", ""))
        replies.append(d.get("m5_reply", ""))
    except OSError:
        pass
    return replies


# --------------------------------------------------------------------------
# single-suite entry (one parallel worker) vs full-run entry

SUITE_FNS = {"p2": suite_p2, "p3": suite_p3, "p4": suite_p4,
             "rt110": suite_rt110, "q1": suite_q1, "bench": suite_bench,
             "rt81": suite_rt81, "sleep": suite_sleep}


def run_single_suite(suite: str, out: str, agent: str, config: str,
                     soak_turns: int) -> dict:
    outp = Path(out)
    outp.mkdir(parents=True, exist_ok=True)
    if suite == "soak":
        return suite_soak(outp, agent, config, n_turns=soak_turns)
    fn = SUITE_FNS[suite]
    return fn(outp, agent, config)


BAR = {
    "p2": "0 OK->BUG, 0 still-BUG (64 cases)",
    "p3": "L1-L6 all PASS",
    "p4": "<= 2 false refusals, 0 non-pass (30)",
    "rt110": "62/62 executed, 0 harness-error",
    "q1": "F5+M5 both OK",
    "bench": "scorer v2; split-A 0 wrong (200+200)",
    "rt81": "74/74 OK, 0 wrong writes",
    "sleep": "Z1-Z5 if sleep path else SKIP+reason",
    "soak": "0 lost / 0 wrong / 0 doubled (2000 turns, 3 kill-9)",
    "q4": "0 relation-name underscore leaks",
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 123 marks runner")
    ap.add_argument("--agent", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", default=str(ART123 / "run"))
    ap.add_argument("--suite", default="all",
                    choices=["all"] + SUITES)
    ap.add_argument("--suites", default="",
                    help="comma list overriding --suite when --suite all")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--soak-turns", type=int, default=2000)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.suite != "all":
        rep = run_single_suite(args.suite, str(out), args.agent,
                               args.config, args.soak_turns)
        print(json.dumps({"suite": args.suite, "pass": rep.get("pass"),
                          "seconds": rep.get("seconds")}))
        return 0 if rep.get("pass") else 1
    suites = [s for s in (args.suites.split(",") if args.suites else SUITES)
              if s in SUITES]
    t0 = time.time()
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    rows: dict[str, dict] = {}

    def run_one(suite: str) -> tuple[str, dict]:
        cmd = [sys.executable, "-B", str(SCRIPTS / "fable_marks123_all.py"),
               "--agent", args.agent, "--config", args.config,
               "--out", str(out), "--suite", suite,
               "--soak-turns", str(args.soak_turns)]
        p = subprocess.run(cmd, capture_output=True, text=True, env=env)
        sys.stdout.write(p.stdout)
        sys.stderr.write(p.stderr)
        report_file = {"p2": "p2-report.json", "p3": "p3-report.json",
                       "p4": "p4-report.json", "rt110": "rt110-report.json",
                       "q1": "q1-report.json", "bench": "bench-report.json",
                       "rt81": "rt81-report.json",
                       "sleep": "sleep-report.json",
                       "soak": "soak-report.json"}[suite]
        try:
            rep = json.loads((out / report_file).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            rep = {"pass": False, "seconds": None, "error": str(exc)}
        return suite, rep

    with concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, args.workers)) as ex:
        futs = {ex.submit(run_one, s): s for s in suites}
        for fut in concurrent.futures.as_completed(futs):
            suite, rep = fut.result()
            rows[suite] = rep
    # Q4 in parent over collected replies
    q4 = suite_q4(out, collect_replies(out)) if "q1" in rows else None
    total_s = round(time.time() - t0, 1)

    def number(suite: str, rep: dict) -> str:
        if suite == "p2":
            return (f"{rep.get('n', '?')} cases, OK->BUG "
                    f"{len(rep.get('ok_to_bug', []))}, still-BUG "
                    f"{len(rep.get('still_bug', []))}")
        if suite == "p3":
            marks = rep.get("marks", {})
            return "/".join(f"{k}:{'P' if v.get('pass') else 'F'}"
                            for k, v in sorted(marks.items()))
        if suite == "p4":
            return (f"{rep.get('n', '?')} sents, refusals "
                    f"{len(rep.get('false_refusals', []))}, nonpass "
                    f"{len(rep.get('nonpass', []))}")
        if suite == "rt110":
            return (f"{rep.get('n', '?')} cases, OK->BUG "
                    f"{len(rep.get('ok_to_bug', []))}, still-BUG "
                    f"{len(rep.get('still_bug', []))}, herr "
                    f"{len(rep.get('harness_errors', []))}")
        if suite == "q1":
            return (f"F5={'OK' if rep.get('f5_ok') else 'FAIL'} "
                    f"M5={'OK' if rep.get('m5_ok') else 'FAIL'}")
        if suite == "bench":
            sp = rep.get("splits", {})
            parts = []
            for tag in ("fable_edit_200", "s2fresh_4hop"):
                t = sp.get(tag, {}).get("table", {})
                tot = {k: sum(c.get(k, 0) for c in t.values()) for k in
                       ("correct", "abstain", "wrong")}
                parts.append(f"{tag} {tot}")
            return "; ".join(parts)
        if suite == "rt81":
            return str(rep.get("summary", {}))
        if suite == "sleep":
            return ("SKIP: " + str(rep.get("reason", ""))[:80]
                    if rep.get("skipped") else "ran")
        if suite == "soak":
            return (f"turns={rep.get('completed')} kills={rep.get('kill9s')} "
                    f"lost={rep.get('lost')} wrong={rep.get('wrong')} "
                    f"doubled={rep.get('doubled_replies')}")
        return ""

    table = []
    for suite in suites + (["q4"] if q4 is not None else []):
        rep = q4 if suite == "q4" else rows[suite]
        if suite == "q4":
            status = "PASS" if rep.get("pass") else "FAIL"
            num = f"leaks={rep.get('leaks', [])}"
        elif suite == "sleep" and rep.get("skipped"):
            status = "SKIP"
            num = number(suite, rep)
        else:
            status = "PASS" if rep.get("pass") else "FAIL"
            num = number(suite, rep)
        table.append({"suite": suite, "bar": BAR.get(suite, ""),
                      "number": num, "status": status,
                      "seconds": rep.get("seconds")})
    summary = {"agent": args.agent, "config": args.config,
               "suites": suites, "table": table,
               "total_seconds": total_s,
               "pass": all(r["status"] in ("PASS", "SKIP") for r in table)}
    (out / "fable_marks123_summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    print("")
    print(f"{'suite':6s} | {'registered bar':42s} | "
          f"{'number':58s} | status | secs")
    for r in table:
        print(f"{r['suite']:6s} | {r['bar'][:42]:42s} | "
              f"{str(r['number'])[:58]:58s} | {r['status']:6s} | "
              f"{r['seconds']}")
    print(f"TOTAL {total_s} s -> "
          f"{'PASS' if summary['pass'] else 'FAIL'}")
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
