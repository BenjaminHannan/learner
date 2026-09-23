#!/usr/bin/env python3
"""Experiment 207 -- ATOMIC INBOX WRITES in the test harness (driver-only).

Problem: the soak and rt110 suites flake under load ("startup mailbox
race"; e.g. exp 192's registered soak lost a first teach: 41 wrong vs 40
predicted). Hypothesis: the harness writes inbox files with plain
write_text (scripts/fable_marks123_all.py lines 159, 186, 243, 413;
scripts/fable_redteam110_runner.py:178), so the daemon can read a
half-written (0-byte) file and answer "I didn't catch anything." on a
non-empty message.

THE ONE CHANGE (harness side only, additive -- no runner, agent, config,
or case file is edited): at runtime this wrapper monkeypatches
pathlib.Path.write_text / write_bytes so that any write whose target
sits in a directory named "inbox" goes to a temp file the daemon
ignores, then os.replace()s it into place:

  tmp = inbox / ("<final-name>.tmp<pid>.<counter>.207")

Ignored TWO ways (recorded in PASSMARKS.md):
  (1) the pickup glob is inbox/*.txt (D74.run; 141 settle daemon), so a
      name ending ".tmp<pid>...207" never matches;
  (2) Loop138bDaemon.settled_files() (inherited by 138f/138g/138h/138i,
      the loop138i daemon's actual run loop) explicitly excludes any
      name containing ".tmp" (and dotfiles).
This mirrors the daemon's own client rule (D74._atomic_write,
Loop138bDaemon.atomic_write_text: "<name>.tmp<pid>" + os.replace).

Suites run the UNCHANGED marks123 code paths (--workers 2 shape):
  --suite soak  -> fable_marks123_all.run_single_suite("soak", ...)
  --suite rt110 -> fable_marks123_all.run_single_suite("rt110", ...)
--mode patched installs the patch first; --mode control runs identical
code with no patch. The daemon subprocess is a separate process and is
never patched. Agent: scripts/fable_loop138i_agent.py, config
artifacts/fable-agent138i-20260922/loop138i-config.json, idle 3600.

After each run the scorer writes analysis207.json: lost / doubled /
didnt_catch_nonempty (replies containing abstain bits to non-empty
messages) / empty_serves (daemon log turn records with empty turn_text)
plus patched_writes (0 in control).

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_atomic207.py --mode patched --suite soak \\
    --agent scripts/fable_loop138i_agent.py \\
    --config artifacts/fable-agent138i-20260922/loop138i-config.json \\
    --out artifacts/fable-atomic207-20260922/run-soak-p1
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
ART207 = ROOT / "artifacts" / "fable-atomic207-20260922"

ABSTAIN_BITS = ["didn't catch", "didn't understand", "don't know",
                "which one", "another way", "only handle one-word",
                "1 to 3", "wasn't waiting", "left it as it was",
                "not someone i can look up", "could not save"]

_patch_counter = itertools.count()
PATCHED_WRITES = 0

_orig_write_text = Path.write_text
_orig_write_bytes = Path.write_bytes


def _is_inbox_txt(path: Path) -> bool:
    try:
        parts = path.parts
    except Exception:  # noqa: BLE001
        return False
    return "inbox" in parts and path.name.endswith(".txt")


def _atomic_write_text(self: Path, data, encoding="utf-8", errors=None,
                       newline=None) -> int:
    global PATCHED_WRITES
    if not _is_inbox_txt(self):
        return _orig_write_text(self, data, encoding=encoding,
                                errors=errors, newline=newline)
    n = next(_patch_counter)
    tmp = self.parent / f"{self.name}.tmp{os.getpid()}.{n}.207"
    kwargs = {} if newline is None else {"newline": newline}
    with open(tmp, "w", encoding=encoding, errors=errors or "strict",
              **kwargs) as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, self)
    PATCHED_WRITES += 1
    return len(data)


def _atomic_write_bytes(self: Path, data) -> int:
    global PATCHED_WRITES
    if not _is_inbox_txt(self):
        return _orig_write_bytes(self, data)
    n = next(_patch_counter)
    tmp = self.parent / f"{self.name}.tmp{os.getpid()}.{n}.207"
    with open(tmp, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, self)
    PATCHED_WRITES += 1
    return len(data)


def install_atomic_patch() -> None:
    Path.write_text = _atomic_write_text  # type: ignore[method-assign]
    Path.write_bytes = _atomic_write_bytes  # type: ignore[method-assign]


def _reply_is_didnt_catch(reply: str) -> bool:
    low = (reply or "").lower()
    return any(bit in low for bit in ABSTAIN_BITS)


def _scan_daemon_log(root: Path) -> dict:
    empty_serves: list[str] = []
    turn_files: list[str] = []
    log = root / "daemon.log.jsonl"
    try:
        lines = log.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {"empty_serves": [], "turn_count": 0, "log_missing": True}
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("event") == "turn" and rec.get("file"):
            turn_files.append(rec["file"])
            if not str(rec.get("turn_text", "")).strip():
                empty_serves.append(rec["file"])
    return {"empty_serves": empty_serves, "turn_count": len(turn_files),
            "log_missing": False}


def _scan_outbox(root: Path) -> dict:
    hits: list[dict] = []
    outbox = root / "outbox"
    try:
        names = sorted(p.name for p in outbox.glob("*.txt"))
    except OSError:
        return {"didnt_catch_files": [], "outbox_missing": True}
    for name in names:
        try:
            reply = (outbox / name).read_text(encoding="utf-8")
        except OSError:
            continue
        if _reply_is_didnt_catch(reply):
            hits.append({"file": name,
                         "reply": reply.strip()[:160]})
    return {"didnt_catch_files": hits, "outbox_missing": False}


def analyze_soak(out: Path) -> dict:
    rep = json.loads((out / "soak-report.json").read_text(encoding="utf-8"))
    root = out / "soak-tmp" / "daemon"
    log_info = _scan_daemon_log(root)
    box_info = _scan_outbox(root)
    # All soak sends are non-empty by construction (teaches, corrections,
    # questions), so every abstain-bit reply counts as didnt_catch_nonempty.
    return {
        "suite": "soak",
        "lost": rep.get("lost"),
        "wrong": rep.get("wrong"),
        "doubled_replies": rep.get("doubled_replies"),
        "dupes_allowed": rep.get("dupes_allowed"),
        "audit": {k: rep.get(k) for k in
                  ("audit_lost_pairs", "audit_dup_pairs",
                   "audit_wrong_pairs")},
        "didnt_catch_nonempty": len(box_info["didnt_catch_files"]),
        "didnt_catch_detail": box_info["didnt_catch_files"][:20],
        "empty_serves": log_info["empty_serves"][:20],
        "n_empty_serves": len(log_info["empty_serves"]),
        "turn_count": log_info["turn_count"],
        "wrong_detail": rep.get("wrong_detail", [])[:20],
        "pass": rep.get("pass"),
        "seconds": rep.get("seconds"),
    }


def analyze_rt110(out: Path) -> dict:
    rep = json.loads((out / "rt110-report.json").read_text(encoding="utf-8"))
    cases = json.loads(
        (ROOT / "artifacts" / "fable-redteam110-20260921"
         / "fable_redteam110_cases.json").read_text(encoding="utf-8"))
    texts: dict[str, list[str]] = {}
    must_answer: dict[str, set[int]] = {}
    for case in cases:
        texts[case["id"]] = [s.get("text", "") for s in case["steps"]
                             if s["op"] in ("send", "vanish")]
        must_answer[case["id"]] = {
            chk["turn"] for chk in case.get("expect", {}).get("checks", [])
            if chk.get("contains")}
    hits: list[dict] = []
    raw_hits = 0
    for row in rep.get("rows", []):
        step_texts = texts.get(row["id"], [])
        want = must_answer.get(row["id"], set())
        for i, entry in enumerate(row.get("log", [])):
            reply = entry.get("reply", "")
            if not _reply_is_didnt_catch(reply):
                continue
            sent = step_texts[i] if i < len(step_texts) else ""
            if not str(sent or "").strip():
                continue
            raw_hits += 1
            if i in want:
                hits.append({"id": row["id"], "file": entry.get("file"),
                             "sent": str(sent)[:80],
                             "reply": reply.strip()[:120]})
    # Daemon-log evidence: turns served with EMPTY turn_text for a file
    # whose sent text was non-empty (the half-written-read signature).
    # Case roots persist under rt110-tmp/<case-id>_*
    empty_serves: list[dict] = []
    tmp_root = out / "rt110-tmp"
    if tmp_root.exists():
        for case in cases:
            step_texts = [s.get("text", "") for s in case["steps"]
                          if s["op"] in ("send", "vanish")]
            for cdir in sorted(tmp_root.glob(case["id"] + "_*")):
                log = cdir / "daemon.log.jsonl"
                try:
                    lines = log.read_text(
                        encoding="utf-8").splitlines()
                except OSError:
                    continue
                for line in lines:
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    if rec.get("event") != "turn" or not rec.get("file"):
                        continue
                    if str(rec.get("turn_text", "")).strip():
                        continue
                    fname = rec["file"]
                    # sent text for this file: find matching send step
                    sent = ""
                    for j, entry in enumerate(
                            [e for e in case["steps"]
                             if e["op"] in ("send", "vanish")]):
                        exp_name = entry.get("file")
                        if exp_name is None:
                            exp_name = f"msg_{j:02d}.txt"
                        if exp_name == fname:
                            sent = entry.get("text", "")
                            break
                    if str(sent or "").strip():
                        empty_serves.append(
                            {"id": case["id"], "file": fname,
                             "sent": str(sent)[:80]})
    verdicts = {r["id"]: r["agent_verdict"] for r in rep.get("rows", [])}
    return {
        "suite": "rt110",
        "n": rep.get("n"),
        "ok_to_bug": rep.get("ok_to_bug"),
        "still_bug": rep.get("still_bug"),
        "bug_to_ok": rep.get("bug_to_ok"),
        "harness_errors": rep.get("harness_errors"),
        "didnt_catch_nonempty": len(hits),
        "didnt_catch_raw": raw_hits,
        "didnt_catch_detail": hits[:20],
        "n_empty_serves": len(empty_serves),
        "empty_serves": empty_serves[:20],
        "verdicts": verdicts,
        "pass": rep.get("pass"),
        "seconds": rep.get("seconds"),
    }


def run_suite(mode: str, suite: str, out: Path, agent: str, config: str,
              soak_turns: int, rt110_limit: int | None) -> dict:
    import fable_marks123_all as M123  # noqa: E402 (unchanged suites)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if suite == "rt110" and rt110_limit is not None:
        rep = _run_rt110_pilot(M123, out, agent, config, rt110_limit)
    else:
        rep = M123.run_single_suite(suite, str(out), agent, config,
                                    soak_turns)
    wall = round(time.time() - t0, 1)
    if suite == "soak":
        analysis = analyze_soak(out)
    else:
        analysis = analyze_rt110(out)
    analysis["mode"] = mode
    analysis["patched_writes"] = PATCHED_WRITES
    analysis["wall_seconds"] = wall
    (out / "analysis207.json").write_text(
        json.dumps(analysis, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"207 {mode} {suite}: patched_writes={PATCHED_WRITES} "
          f"wall={wall}s", flush=True)
    print(json.dumps({k: analysis.get(k) for k in
                      ("lost", "wrong", "doubled_replies",
                       "didnt_catch_nonempty", "n_empty_serves",
                       "harness_errors", "pass")}, indent=1), flush=True)
    return analysis


def _run_rt110_pilot(M123, out: Path, agent: str, config: str,
                     limit: int) -> dict:
    """Pilot-only: first `limit` rt110 cases through the unchanged R110
    path (same daemon_cmd override marks123 uses). Not a registered run."""
    import fable_redteam110_runner as R110  # noqa: E402
    agent_abs = str(Path(agent).resolve())
    cfg_abs = str(Path(config).resolve())

    def daemon_cmd_agent(root: Path) -> list[str]:
        return ["uv", "run", "--offline", "--no-project", "--python", "3.12",
                "--with", "torch", "--with", "numpy", "python", "-B",
                agent_abs, "--daemon", "--dir", str(root),
                "--config", cfg_abs, "--idle-seconds", "3600"]
    R110.daemon_cmd = daemon_cmd_agent
    workroot = out / "rt110-tmp"
    workroot.mkdir(parents=True, exist_ok=True)
    art110 = (ROOT / "artifacts" / "fable-redteam110-20260921")
    cases = json.loads((art110 / "fable_redteam110_cases.json").read_text(
        encoding="utf-8"))[:limit]
    rows = []
    for case in cases:
        res = R110.run_case(case, workroot)
        verdict = R110.judge(case, res)
        rows.append({"id": case["id"], "agent_verdict": verdict["verdict"],
                     "reason": verdict.get("reason", "")[:200],
                     "log": [{"file": e.get("file"), "reply": e.get("reply"),
                              "statuses": e.get("statuses"),
                              "fact_writes": e.get("fact_writes")}
                             for e in res.get("log", [])],
                     "harness_error": bool(res.get("harness_error"))})
        print(f"RT110-pilot {case['id']}: {verdict['verdict']}", flush=True)
    rep = {"mark": "RT110-PILOT", "n": len(rows), "rows": rows,
           "ok_to_bug": [], "still_bug": [], "bug_to_ok": [],
           "harness_errors": [r["id"] for r in rows if r["harness_error"]],
           "pass": True, "seconds": 0.0}
    (out / "rt110-report.json").write_text(json.dumps(rep, indent=1),
                                           encoding="utf-8")
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 207 atomic-inbox driver")
    ap.add_argument("--mode", required=True, choices=["patched", "control"])
    ap.add_argument("--suite", required=True, choices=["soak", "rt110"])
    ap.add_argument("--agent", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--soak-turns", type=int, default=2000)
    ap.add_argument("--rt110-limit", type=int, default=None,
                    help="pilot only: first N rt110 cases")
    args = ap.parse_args(argv)
    if args.mode == "patched":
        install_atomic_patch()
    run_suite(args.mode, args.suite, Path(args.out), args.agent,
              args.config, args.soak_turns, args.rt110_limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
