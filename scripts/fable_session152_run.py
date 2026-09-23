#!/usr/bin/env python3
"""Experiment 152 -- registered runner: realistic-user sessions red team.

Drives BOTH targets through the mailbox, one file per turn, fresh daemon
dir per session (12 daemons total: 6 sessions x 2 targets), in-process
`process_file` exactly like scripts/fable_marks123_all.py `_p2_process_pending`.

Targets:
  T-Q = scripts/fable_loop149_agent.py:Qrewrite149Daemon
        + artifacts/fable-wordmatch149-20260922/loop149-qrewrite-config.json
  T-T = scripts/fable_loop139b_agent.py:Loop139bDaemon
        + artifacts/fable-fix139b-20260922/loop139b-config.json

Run (Mac CPU, offline; only AFTER PASSMARKS.md + sessions dump are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_session152_run.py

Reads: scripts/fable_session152_sessions.py (this exp's sessions, read-only).
Writes: only artifacts/fable-session152-20260922/ (this exp's folder).
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-session152-20260922"

import fable_session152_sessions as S152  # noqa: E402 (this exp's sessions)


def load_mod(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def fact_count(daemon) -> int:
    return sum(1 for e in daemon.loop.nb.events if e.get("kind") == "FACT")


def run_session(daemon, root: Path, session: dict) -> list[dict]:
    out = []
    for i, turn in enumerate(session["turns"]):
        name = f"turn_{i:02d}.txt"
        (root / "inbox" / name).write_text(turn["text"], encoding="utf-8")
        before = fact_count(daemon)
        try:
            daemon.process_file(root / "inbox" / name)
            writes = fact_count(daemon) - before
            reply = (root / "outbox" / name).read_text(encoding="utf-8")
            statuses = [r.get("status", r.get("kind", "?"))
                        for r in daemon.loop.last_records]
            err = None
        except Exception as exc:  # noqa: BLE001 -- observed, never raised
            reply = f"HARNESS-CAUGHT {type(exc).__name__}: {exc}"
            statuses = ["EXCEPTION"]
            writes = 0
            err = f"{type(exc).__name__}: {exc}"
            try:
                (root / "inbox" / name).rename(root / "done" / name)
            except OSError:
                pass
        out.append({"n": i, "text": turn["text"], "expect": turn["expect"],
                    "want": turn.get("want"), "clear": turn.get("clear", True),
                    "known": turn.get("known"), "reply": reply,
                    "statuses": statuses, "fact_writes": writes,
                    "harness_error": err})
    return out


CLARIFY_BITS = ["didn't understand", "another way", "only handle one-word",
                "please say it like", "didn't catch", "don't know",
                "which one", "do not know", "unknown", "unsure",
                "missing", "1 to 3"]


def is_clarify(reply: str) -> bool:
    low = reply.lower()
    return any(b in low for b in CLARIFY_BITS)


def judge(turn: dict) -> dict:
    """Mechanical candidate verdict per turn (reviewed by hand afterwards)."""
    e, want, reply = turn["expect"], turn.get("want"), turn["reply"]
    w = turn["fact_writes"]
    if turn["harness_error"]:
        return {"verdict": "HARNESS-ERROR", "why": turn["harness_error"]}
    if e in ("smalltalk", "self"):
        if w > 0:
            return {"verdict": "WRONG", "why": "write from small talk/self (critical)"}
        if is_clarify(reply):
            return {"verdict": "UNHELPFUL",
                    "why": f"honest clarify but user stuck: {reply.strip()[:80]}"}
        return {"verdict": "OK", "why": "no write, non-confused reply"}
    if e in ("teach", "correct"):
        if w <= 0:
            if is_clarify(reply):
                if turn["clear"]:
                    return {"verdict": "UNHELPFUL",
                            "why": f"clear teach got clarify: {reply.strip()[:80]}"}
                return {"verdict": "OK",
                        "why": "garbled input honestly clarified, no write"}
            return {"verdict": "UNHELPFUL",
                    "why": f"no write, reply: {reply.strip()[:80]}"}
        if want and want.lower() not in reply.lower():
            return {"verdict": "WRONG",
                    "why": f"wrote but reply misses {want!r}: {reply.strip()[:80]}"}
        return {"verdict": "OK", "why": f"wrote {w}, confirmed"}
    if e in ("ask", "reask"):
        if want and want.lower() in reply.lower():
            if w > 0:
                return {"verdict": "WRONG", "why": "right answer but also wrote"}
            return {"verdict": "OK", "why": "exact answer, no write"}
        if w > 0:
            return {"verdict": "WRONG",
                    "why": f"question wrote {w}: {reply.strip()[:80]}"}
        if is_clarify(reply):
            if turn["clear"]:
                return {"verdict": "UNHELPFUL",
                        "why": f"clear question clarified: {reply.strip()[:80]}"}
            return {"verdict": "OK", "why": "unclear input clarified, no write"}
        return {"verdict": "WRONG",
                "why": f"wrong answer, want {want!r}: {reply.strip()[:100]}"}
    if e == "abstain":
        if w > 0:
            return {"verdict": "WRONG", "why": "abstain case wrote"}
        if is_clarify(reply):
            return {"verdict": "OK", "why": "honest abstain/clarify, no write"}
        if want and want.lower() in reply.lower():
            return {"verdict": "OK", "why": "answered as expected"}
        return {"verdict": "WRONG",
                "why": f"answered untaught: {reply.strip()[:100]}"}
    if e == "clarify":
        if w > 0:
            return {"verdict": "WRONG", "why": "clarify case wrote"}
        if is_clarify(reply):
            return {"verdict": "OK", "why": "ambiguous input clarified, no write"}
        return {"verdict": "OK" if (want is None or want.lower() in reply.lower())
                else "WRONG",
                "why": f"non-clarify reply: {reply.strip()[:100]}"}
    if e == "known":
        base = dict(turn)
        base["expect"] = "ask" if (want and turn["clear"]) else "clarify"
        if base["expect"] == "clarify":
            base["expect"] = "abstain" if want is None else "ask"
        # known turns: judge leniently, verdict recorded but excluded
        j = judge({**turn, "expect": "ask" if want else "abstain"})
        j["why"] = "KNOWN-" + (turn.get("known") or "?") + ": " + j["why"]
        return j
    return {"verdict": "HARNESS-ERROR", "why": f"bad expect {e!r}"}


def main() -> int:
    t0 = time.time()
    ART.mkdir(parents=True, exist_ok=True)
    # dump sessions (must match sealed hash; runner refuses on mismatch)
    dump = [{"id": s["id"], "note": s["note"], "turns": s["turns"]}
            for s in S152.SESSIONS]
    (ART / "sessions152.json").write_text(
        json.dumps(dump, indent=1, ensure_ascii=False), encoding="utf-8")
    m149 = load_mod(str(SCRIPTS / "fable_loop149_agent.py"), "s152_149")
    m139 = load_mod(str(SCRIPTS / "fable_loop139b_agent.py"), "s152_139b")
    cfgQ = json.loads((ROOT / "artifacts" / "fable-wordmatch149-20260922"
                       / "loop149-qrewrite-config.json").read_text(encoding="utf-8"))
    cfgT = json.loads((ROOT / "artifacts" / "fable-fix139b-20260922"
                       / "loop139b-config.json").read_text(encoding="utf-8"))
    targets = [("T-Q", m149.Qrewrite149Daemon, cfgQ),
               ("T-T", m139.Loop139bDaemon, cfgT)]
    summary = {}
    for tag, cls, base in targets:
        summary[tag] = {}
        for s in S152.SESSIONS:
            root = ART / "work" / tag / s["id"]
            if root.exists():
                import shutil
                shutil.rmtree(root)
            root.mkdir(parents=True)
            cfg = copy.deepcopy(base)
            cfg["state_dir"] = str(root)
            cfg["sleep_threshold"] = 100000
            daemon = cls(root, cfg=cfg, idle_seconds=3600.0)
            turns = run_session(daemon, root, s)
            for t in turns:
                t.update(judge(t))
            (ART / f"turns152-{tag}-{s['id']}.json").write_text(
                json.dumps(turns, indent=1, ensure_ascii=False), encoding="utf-8")
            counts = {}
            for t in turns:
                counts[t["verdict"]] = counts.get(t["verdict"], 0) + 1
            summary[tag][s["id"]] = counts
            print(f"{tag} {s['id']}: {counts}", flush=True)
    total = round(time.time() - t0, 1)
    (ART / "run152-summary.json").write_text(
        json.dumps({"summary": summary, "seconds": total}, indent=1),
        encoding="utf-8")
    print(f"TOTAL {total} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
