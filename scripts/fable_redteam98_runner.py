#!/usr/bin/env python3
"""Experiment 98 — mailbox harness driving the integrated exp-90 agent.

Public interface only: each case gets a fresh temp dir (under the exp-98
artifact dir, never a live state dir); messages go in as inbox/*.txt files
and are processed in sorted name order exactly like Loop90Daemon.run() does;
replies are read back from outbox/*.txt. In-process Loop90Daemon instances
are file-boundary users only: we never call loop.turn() or touch the
notebook except to COUNT new FACT events for the zero-write checks.
Ops: send | send_bytes | restart | tear_tail | kill9_burst.
Run: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project \
  --python 3.12 --with torch --with numpy python -B \
  scripts/fable_redteam98_runner.py --export   # before seal
  scripts/fable_redteam98_runner.py --run      # registered run
"""

from __future__ import annotations

import argparse
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

import fable_redteam98_cases as RC  # noqa: E402 (our own cases file)
from fable_loop90_agent import Loop90Daemon  # noqa: E402 (read-only import)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-redteam98-20260921"
ABSTAIN_BITS = ["don't know", "which one", "didn't understand",
                "didn't catch", "another way", "only handle one-word",
                "1 to 3", "wasn't waiting", "left it as it was",
                "not someone i can look up", "could not save"]


def is_abstain(reply: str) -> bool:
    low = reply.lower()
    return any(bit in low for bit in ABSTAIN_BITS)


def fact_count(daemon) -> int:
    return sum(1 for e in daemon.loop.nb.events if e.get("kind") == "FACT")


def new_daemon(root: Path) -> Loop90Daemon:
    cfg = {"sleep_threshold": 100000}
    return Loop90Daemon(root, cfg=cfg, idle_seconds=3600.0)


def process_pending(daemon, root: Path, log: list) -> None:
    for path in sorted((root / "inbox").glob("*.txt")):
        before = fact_count(daemon)
        try:
            daemon.process_file(path)
            writes = fact_count(daemon) - before
            reply = (root / "outbox" / path.name).read_text(encoding="utf-8")
            statuses = [r.get("status", r.get("kind", "?"))
                        for r in daemon.loop.last_records]
        except Exception as exc:  # noqa: BLE001 -- observed, never raised
            reply = f"HARNESS-CAUGHT {type(exc).__name__}: {exc}"
            statuses = ["EXCEPTION"]
            writes = 0
            try:  # quarantine the poison file so later turns still run
                os.replace(path, root / "done" / path.name)
            except OSError:
                pass
        log.append({"file": path.name, "reply": reply, "statuses": statuses,
                    "fact_writes": writes})


def do_kill9_burst(root: Path, log: list) -> dict:
    """Real subprocess daemon + SIGKILL mid-burst, then in-process restart."""
    out: dict = {"phase": "kill9"}
    cmd = [sys.executable, "-B", str(SCRIPTS / "fable_loop90_agent.py"),
           "--daemon", "--dir", str(root), "--idle-seconds", "3600"]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    try:
        for _ in range(900):  # wait for boot (imports), ≤90 s
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
        time.sleep(0.5)  # kill while the burst is (probably) in flight
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
    # restart in the same root: chain verify + seal discipline under test
    try:
        daemon = new_daemon(root)
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


def run_case(case: dict, workroot: Path) -> dict:
    root = Path(tempfile.mkdtemp(prefix=case["id"] + "_", dir=str(workroot)))
    (root / "inbox").mkdir(exist_ok=True)
    log: list = []
    info: dict = {"boot_ok_count": 0, "boot_refused": None,
                  "torn_repaired": False}
    try:
        daemon = new_daemon(root)
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
        if batch:  # same-second stamp: ordering must come from names alone
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
                daemon = new_daemon(root)
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
            info["kill9"] = do_kill9_burst(root, log)
        else:
            raise ValueError(f"unknown op {op!r}")
    flush_batch()
    return {"id": case["id"], "group": case["group"], "root": str(root),
            "log": log, "info": info}


def judge(case: dict, res: dict) -> dict:
    exp = case.get("expect", {})
    fails: list[str] = []
    replies = [e["reply"] for e in res["log"]
               if e["file"] not in ("RESTART", "TEAR-TAIL", "KILL9-SUMMARY")]
    if any(e["reply"].startswith("HARNESS-CAUGHT") for e in res["log"]
           ) and case["id"] != "E7":
        fails.append("turn raised inside process_file")
    for chk in exp.get("checks", []):
        i = chk["turn"]
        if i >= len(replies):
            fails.append(f"turn {i} missing from transcript")
            continue
        for sub in chk.get("contains", []):
            if sub not in replies[i]:
                fails.append(f"turn {i} lacks {sub!r} (got {replies[i][:120]!r})")
        for sub in chk.get("absent", []):
            if sub in replies[i]:
                fails.append(f"turn {i} leaks {sub!r}")
    for i in exp.get("abstain_on", []):
        if i >= len(replies):
            fails.append(f"turn {i} missing from transcript")
        elif not is_abstain(replies[i]):
            fails.append(f"turn {i} should abstain (got {replies[i][:120]!r})")
    blob = "\n".join(replies)
    for sub in exp.get("absent_everywhere", []):
        if sub in blob:
            fails.append(f"{sub!r} appears somewhere in the transcript")
    for i in exp.get("zero_fact_writes_on", []):
        turns = [e for e in res["log"]
                 if e["file"] not in ("RESTART", "TEAR-TAIL", "KILL9-SUMMARY")]
        if i < len(turns) and turns[i]["fact_writes"] != 0:
            fails.append(f"turn {i} wrote {turns[i]['fact_writes']} FACT events")
    if exp.get("boot_ok") and not (res["info"].get("boot_ok_count")
            or (res["info"].get("kill9") or {}).get("boot_ok")):
        fails.append("restart did not boot")
    if exp.get("torn_repaired") and not res["info"].get("torn_repaired"):
        fails.append("torn tail was not repaired on restart")
    if exp.get("boot_refused"):
        err = res["info"].get("boot_refused") or ""
        if not err:
            fails.append("restart booted but tamper must refuse")
        elif not any(s in err for s in ["last line edited", "log truncated",
                                        "tail", "seal", "chain", "truncat"]):
            fails.append(f"refusal reason off-doctrine: {err[:120]!r}")
    st = exp.get("stats")
    if st:
        k9 = res["info"].get("kill9", {})
        if not k9.get("boot_ok"):
            fails.append(f"post-kill boot failed: {k9.get('boot_error')}")
        else:
            if k9.get("correct", 0) < st["min_correct"]:
                fails.append(f"only {k9.get('correct')} correct (< {st['min_correct']})")
            if k9.get("wrong", 0) > st["max_wrong"]:
                fails.append(f"{k9.get('wrong')} WRONG answers after restart")
    if case["id"] == "E7" or exp.get("no_exception"):
        if any(e["reply"].startswith("HARNESS-CAUGHT") for e in res["log"]):
            fails.append("inbox bytes raised out of process_file "
                         "(a production daemon would die here)")
    if fails:
        return {"verdict": "BUG", "severity": case["severity_if_fail"],
                "reason": "; ".join(fails)}
    # UNCLEAR only when the transcript is too thin to call safe
    if not replies:
        return {"verdict": "UNCLEAR", "reason": "empty transcript"}
    return {"verdict": "OK", "reason": "all sealed checks held"}


REPRO_HEAD = ("import sys, tempfile\nfrom pathlib import Path\n"
              "sys.path.insert(0, 'scripts')\n"
              "from fable_loop90_agent import Loop90Daemon\n\n"
              "root = Path(tempfile.mkdtemp())\n"
              "(root / 'inbox').mkdir()\n"
              "d = Loop90Daemon(root, cfg={'sleep_threshold': 100000}, idle_seconds=3600.0)\n"
              "def say(text, name):\n"
              "    (root / 'inbox' / name).write_text(text)\n"
              "    for p in sorted((root / 'inbox').glob('*.txt')):\n"
              "        d.process_file(p)\n"
              "    print(name, '->', (root / 'outbox' / name).read_text().strip()[:150])\n")


def make_repro(case: dict, res: dict) -> str:
    lines = [REPRO_HEAD]
    n = 0
    for step in case["steps"]:
        if step["op"] == "send":
            lines.append(f"say({step['text']!r}, 'm{n}.txt')")
            n += 1
        elif step["op"] == "send_bytes":
            lines.append(f"(root/'inbox'/m{n}.txt).write_bytes(bytes.fromhex({step['data_hex']!r}))")
            n += 1
        elif step["op"] == "restart":
            lines.append("d = Loop90Daemon(root, cfg={'sleep_threshold': 100000}, idle_seconds=3600.0)"
                         "  # restart: rebuild on the same root")
        elif step["op"] == "tear_tail":
            lines.append("# F5: truncate the last events.jsonl line, then rebuild (see wave log)")
    exp = case.get("expect", {})
    tail = []
    for chk in exp.get("checks", []):
        for sub in chk.get("contains", []):
            tail.append(f"final must contain {sub!r}")
    if exp.get("abstain_on") is not None:
        tail.append("flagged turns must abstain")
    lines.append(f"# EXPECTED (sealed pre-run): {'; '.join(tail) or exp}")
    lines.append(f"# OBSERVED: {res.get('verdict')} -- {res.get('reason','')[:200]}")
    return "\n".join(lines) + "\n"


def cmd_export(_args) -> int:
    ART.mkdir(parents=True, exist_ok=True)
    payload = [{"id": c["id"], "group": c["group"],
               "severity_if_fail": c["severity_if_fail"], "note": c["note"],
               "steps": c["steps"], "expect": c["expect"]} for c in RC.CASES]
    (ART / "fable_redteam98_cases.json").write_text(
        json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"exported {len(payload)} cases -> {ART / 'fable_redteam98_cases.json'}")
    return 0


def cmd_run(_args) -> int:
    t0 = time.time()
    workroot = ART / "tmp"
    workroot.mkdir(parents=True, exist_ok=True)
    reprodir = ART / "repro"
    reprodir.mkdir(parents=True, exist_ok=True)
    results = []
    for case in RC.CASES:
        res = run_case(case, workroot)
        verdict = judge(case, res)
        res.update(verdict)
        res["observed_final"] = next(
            (e["reply"] for e in reversed(res["log"])
             if e["file"] not in ("RESTART", "TEAR-TAIL", "KILL9-SUMMARY")),
            res["log"][-1]["reply"] if res["log"] else "")
        if verdict["verdict"] in ("BUG", "UNCLEAR"):
            rp = reprodir / f"fable_redteam98_repro_{case['id']}.py"
            rp.write_text(make_repro(case, res), encoding="utf-8")
            res["reproducer"] = str(rp.relative_to(ROOT))
        results.append(res)
        print(f"{case['id']:>3} {verdict['verdict']:7} {verdict.get('severity',''):8} "
              f"{verdict['reason'][:100]}", flush=True)
    ok = sum(1 for r in results if r["verdict"] == "OK")
    bugs = [r for r in results if r["verdict"] == "BUG"]
    unc = [r for r in results if r["verdict"] == "UNCLEAR"]
    sev: dict[str, int] = {}
    for r in bugs:
        sev[r.get("severity", "?")] = sev.get(r.get("severity", "?"), 0) + 1
    summary = {"cases": len(results), "OK": ok,
               "BUG": len(bugs), "by_severity": sev,
               "UNCLEAR": len(unc),
               "bug_ids": [r["id"] for r in bugs],
               "unclear_ids": [r["id"] for r in unc],
               "seconds": round(time.time() - t0, 1)}
    (ART / "fable_redteam98_results.json").write_text(
        json.dumps({"summary": summary, "cases": results}, indent=1,
                   ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 98 mailbox red-team harness")
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args(argv)
    if args.export:
        return cmd_export(args)
    if args.run:
        return cmd_run(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
