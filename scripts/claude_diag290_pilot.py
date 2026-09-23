#!/usr/bin/env python3
"""290 pilot: 4 dialogs on 138k vs 138m. Confirms phenomenon + attr paths.
New file only. Fictional names only."""
from __future__ import annotations
import copy, shutil, sys, tempfile
from pathlib import Path
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import claude_loop138k_agent as K
import claude_loop138m_agent as M

D = [
    ("p1-taught", ["Bex's mother is Talia.", "What is Bex's mother?"]),
    ("p2-never", ["Bex's mother is Talia.", "What is Bex's father?"]),
    ("p3-retract", ["Bex's mother is Talia.", "No, Bex's mother isn't Talia.", "What is Bex's mother?"]),
    ("p4-replace", ["Bex's mother is Talia.", "Actually Bex's mother is Zara.", "What is Bex's mother?"]),
]

def stage_of(loop):
    for o in (getattr(loop, "_inner138j_ears", None), getattr(loop, "ears", None)):
        s = getattr(o, "last_stage", "")
        if s:
            return s
    return ""

def evcount(loop):
    try:
        inner = getattr(loop.nb, "nb", loop.nb)
        return len(inner.events)
    except Exception as e:
        return f"ERR:{e}"

def run_one(mod, tag):
    base = copy.deepcopy(mod.DEFAULT_CONFIG138K if tag == "138k" else mod.DEFAULT_CONFIG138M)
    for did, turns in D:
        sd = Path(tempfile.mkdtemp(prefix="nb290p-"))
        cfg = copy.deepcopy(base); cfg["state_dir"] = str(sd); cfg["sleep_threshold"] = 100000
        build = mod.build_agent138k if tag == "138k" else mod.build_agent138m
        loop = build(cfg)
        for j, t in enumerate(turns):
            n0 = evcount(loop)
            rep = " ".join(loop.turn(t))
            n1 = evcount(loop)
            st = stage_of(loop)
            lr = getattr(loop, "last_routed", None)
            intent = lr.get("intent") if isinstance(lr, dict) else None
            extra = ""
            if hasattr(loop, "decline224_log") and loop.decline224_log:
                extra += f" d224={loop.decline224_log[-1]}"
            if hasattr(loop, "q1honest224c_log") and loop.q1honest224c_log:
                extra += f" q1c={loop.q1honest224c_log[-1]}"
            print(f"{tag} {did} t{j}: stage={st} intent={intent} ev={n0}->{n1} reply={rep}{extra}", flush=True)
        shutil.rmtree(sd, ignore_errors=True)

if __name__ == "__main__":
    run_one(K, "138k")
    run_one(M, "138m")
