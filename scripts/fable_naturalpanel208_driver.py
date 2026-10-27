#!/usr/bin/env python3
"""Experiment 208 — reusable natural-panel driver (Muse).

Runs ANY loop agent + config over the sealed natural panel
(artifacts/fable-naturalpanel208-20260922/panel208.json): one fresh
isolated scratch notebook per dialog, each turn through the mailbox
(daemon.process_file) exactly like the registered suites.

Pattern copied from scripts/fable_marks123_all.py:
load_agent / load_base_cfg / make_daemon / process_file.

G1 (automatic) per turn, G2 left to the reader of the run log:
  SAVE    -> OK if fact_writes >= min_writes and reply not abstaining
  ANSWER  -> OK if expected substring in reply (case-insensitive)
  ABSTAIN -> OK if abstain-bit match and 0 writes
  ASK     -> OK if reply asks (has '?') and 0 writes
  CHAT    -> OK if 0 writes

Output: one JSONL row per turn (id, dlg, cat, exp, text, reply, statuses,
fact_writes, new_triples, triples_now, g1, g1_reason, seconds).

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_naturalpanel208_driver.py \
    --agent scripts/fable_loop138i_agent.py \
    --config artifacts/fable-agent138i-20260922/loop138i-config.json \
    --panel artifacts/fable-naturalpanel208-20260922/panel208.json \
    --out artifacts/fable-naturalpanel208-20260922/run138i.jsonl
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
ROOT = SCRIPTS.parent


def load_agent(agent_script: str):
    spec = importlib.util.spec_from_file_location(
        "fable_naturalpanel208_agent_under_test", agent_script)
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
    return mod, daemon_cls


def load_base_cfg(config_path: str) -> dict:
    return json.loads(Path(config_path).read_text(encoding="utf-8"))


def make_daemon(daemon_cls, base_cfg: dict, root: Path):
    cfg = copy.deepcopy(base_cfg)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return daemon_cls(root, cfg=cfg, idle_seconds=3600.0)


def triples_now(daemon) -> list[list[str]]:
    try:
        import fable_loop90_agent as L90  # noqa: E402 (read-only)
        return [[str(a), str(b), str(c)]
                for a, b, c in L90.notebook_triples(daemon.loop.nb)]
    except Exception:  # noqa: BLE001 -- fall back to event scan
        out = []
        for e in getattr(daemon.loop.nb, "events", []):
            if e.get("kind") == "FACT":
                out.append([str(e.get("subject", "?")),
                            str(e.get("relation", "?")),
                            str(e.get("object", "?"))])
        return out


def g1_grade(turn: dict, reply: str, writes: int, is_abstain) -> tuple[str, str]:
    exp = turn["exp"]
    if exp == "SAVE":
        if writes < int(turn.get("min_writes", 1)):
            return "NOT-OK", f"writes {writes} < min {turn.get('min_writes', 1)}"
        if is_abstain(reply):
            return "NOT-OK", "reply abstains on a teach"
        return "OK", f"writes {writes}"
    if exp == "ANSWER":
        want = str(turn.get("ans", ""))
        if want.lower() in reply.lower():
            return "OK", f"contains {want!r}"
        return "NOT-OK", f"missing {want!r}"
    if exp == "ABSTAIN":
        if writes != 0:
            return "NOT-OK", f"wrote {writes} on abstain turn"
        if is_abstain(reply):
            return "OK", "abstain bit + 0 writes"
        return "NOT-OK", "no abstain bit"
    if exp == "ASK":
        if writes != 0:
            return "NOT-OK", f"wrote {writes} on ask turn"
        if "?" in reply:
            return "OK", "asks + 0 writes"
        return "NOT-OK", "no question + 0 writes"
    if exp == "CHAT":
        if writes != 0:
            return "NOT-OK", f"wrote {writes} on chat turn"
        return "OK", "0 writes"
    return "NOT-OK", f"unknown exp {exp}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 208 natural-panel driver")
    ap.add_argument("--agent", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--panel", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--keep-scratch", action="store_true", default=False)
    args = ap.parse_args(argv)

    panel = json.loads(Path(args.panel).read_text(encoding="utf-8"))
    turns = panel["turns"]
    _, daemon_cls = load_agent(args.agent)
    base_cfg = load_base_cfg(args.config)
    import fable_redteam98_runner as R98  # noqa: E402 (sealed abstain judge)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    scratch = out_path.parent / "scratch208"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    n_ok = 0
    daemon_holder: dict = {}
    with out_path.open("w", encoding="utf-8") as fh:
        for turn in turns:
            dlg = turn["dlg"]
            droot = scratch / dlg
            # one daemon per dialog, built lazily and cached
            if dlg not in daemon_holder:
                daemon_holder[dlg] = make_daemon(
                    daemon_cls, base_cfg, droot)
            daemon = daemon_holder[dlg]
            before = set(map(tuple, triples_now(daemon)))
            name = f"{turn['id']}.txt"
            (droot / "inbox" / name).write_text(turn["text"],
                                               encoding="utf-8")
            t1 = time.time()
            try:
                daemon.process_file(droot / "inbox" / name)
                reply = (droot / "outbox" / name).read_text(
                    encoding="utf-8")
                statuses = [r.get("status", r.get("kind", "?"))
                            for r in daemon.loop.last_records]
            except Exception as exc:  # noqa: BLE001 -- observed, never raised
                reply = f"HARNESS-CAUGHT {type(exc).__name__}: {exc}"
                statuses = ["EXCEPTION"]
            dt = time.time() - t1
            now = triples_now(daemon)
            new = [list(t) for t in map(list, now)
                   if tuple(t) not in before]
            writes = len(new)
            g1, reason = g1_grade(turn, reply, writes, R98.is_abstain)
            if g1 == "OK":
                n_ok += 1
            fh.write(json.dumps({
                "id": turn["id"], "dlg": dlg, "cat": turn["cat"],
                "exp": turn["exp"], "text": turn["text"],
                "expect_ans": turn.get("ans"),
                "expect_fact": turn.get("fact"),
                "expect_fact2": turn.get("fact2"),
                "reply": reply, "statuses": statuses,
                "fact_writes": writes, "new_triples": new,
                "triples_now": now, "g1": g1, "g1_reason": reason,
                "seconds": round(dt, 3),
            }, ensure_ascii=False) + "\n")
            # free per-dialog daemon after its 5th turn (T5)
            if turn["id"].endswith("-T5"):
                del daemon_holder[dlg]
    total = time.time() - t0
    if not args.keep_scratch:
        shutil.rmtree(scratch, ignore_errors=True)
    print(f"turns={len(turns)} g1_ok={n_ok} seconds={total:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
