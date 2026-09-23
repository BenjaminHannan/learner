#!/usr/bin/env python3
"""Exp 293 dev repro: run the 111 dev dialogs (D61 DIAG + N50 new) on ONE arm.

New file only. CPU only. Fresh temp state_dir per dialog outside the repo,
sleep_threshold 100000. Records reply, kind, outer/inner stage, acts,
event counts (writes). Never opens any panel folder.

Usage:
  uv run ... python -B scripts/claude_293_repro.py <agent_py> <config> <out_rows> [label]
"""
from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_293_devdialogs as DEV  # noqa: E402 (dev dialogs, read-only)


def load_agent(agent_py: str):
    spec = importlib.util.spec_from_file_location(
        "ag_repro_293", str(Path(agent_py).resolve()))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ag_repro_293"] = mod
    spec.loader.exec_module(mod)
    return mod


def kind_of(reply: str) -> str:
    low = reply.lower()
    if "didn't understand that question" in low:
        return "didnt-understand"
    if reply.startswith("Yes,") or reply.startswith("Yes "):
        return "yes"
    if reply.startswith("No,") or reply.startswith("No "):
        return "no"
    if low.startswith("not that i know of"):
        return "not-that-i-know"
    if "couldn't save" in low or "could not store" in low or "don't know that shape" in low:
        return "nosave-clarify"
    if "i don't know" in low or "i do not know" in low or "no record" in low:
        return "decline-targeted"
    return "answer-or-other"


def evcount(loop) -> int:
    try:
        return len(getattr(loop.nb, "nb", loop.nb).events)
    except Exception:
        return -1


def main() -> int:
    agent_py, config, out = sys.argv[1:4]
    label = sys.argv[4] if len(sys.argv) > 4 else ""
    mod = load_agent(agent_py)
    build = None
    for name in ("build_agent293", "build_agent138nb"):
        if hasattr(mod, name):
            build = getattr(mod, name)
            break
    if build is None:
        raise SystemExit("no known build_* in agent module")
    base = copy.deepcopy(json.loads(Path(config).read_text(encoding="utf-8")))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    if Path(out).exists():
        Path(out).unlink()
    n = 0
    for did, setup, q, arm, shape in DEV.D:
        sd = Path(tempfile.mkdtemp(prefix="nb293-"))
        cfg = copy.deepcopy(base)
        cfg["state_dir"] = str(sd)
        cfg["sleep_threshold"] = 100000
        loop = build(cfg)
        seen: list = []
        outer = loop.ears.hear

        def hear_wrap(turn, _o=outer):
            a = _o(turn)
            seen.append([dict(x) if isinstance(x, dict) else x for x in (a or [])])
            return a

        loop.ears.hear = hear_wrap
        setup_replies = []
        for t in setup:
            seen.clear()
            setup_replies.append(" ".join(loop.turn(t)))
        seen.clear()
        e0 = evcount(loop)
        reply = " ".join(loop.turn(q))
        e1 = evcount(loop)
        acts = seen[-1] if seen else []
        inner = getattr(loop, "_inner138j_ears", None)
        row = {"id": did, "arm": arm, "shape": shape, "setup": setup,
               "setup_replies": setup_replies, "question": q, "reply": reply,
               "kind": kind_of(reply),
               "stage": str(getattr(loop.ears, "last_stage", "")),
               "inner_stage": str(getattr(inner, "last_stage", "")) if inner is not None else None,
               "acts": acts,
               "has_ask": any(isinstance(a, dict) and a.get("act") == "ask" for a in acts),
               "ev0": e0, "ev1": e1, "label": label}
        with open(out, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        n += 1
        print(f"{did} [{arm}/{shape}] kind={row['kind']} stage={row['stage']!r} "
              f"ev={e0}->{e1} reply={reply[:70]!r}", flush=True)
        shutil.rmtree(sd, ignore_errors=True)
    print(f"WROTE {n} rows to {out}")


if __name__ == "__main__":
    assert len(DEV.D) == 111, len(DEV.D)
    main()
