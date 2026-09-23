#!/usr/bin/env python3
"""Pilot for exp 293-diag: build 138nb once, run 4 probe turns, print reply + stage + acts."""
from __future__ import annotations
import copy, shutil, sys, tempfile
from pathlib import Path
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import claude_loop138nb_agent as NB

base = copy.deepcopy(NB.DEFAULT_CONFIG138NB)
tests = [
    (["Bex's mother is Talia."], "Does Bex have a mother?"),
    (["Bex's mother is Talia."], "Is Bex's mother Talia?"),
    (["Bex's mother is Talia."], "Is Bex's mother Wren?"),
    (["Bex's city is Oslo."], "Does Bex live in Oslo?"),
]
for setup, q in tests:
    sd = Path(tempfile.mkdtemp(prefix="nb293pilot-"))
    cfg = copy.deepcopy(base); cfg["state_dir"] = str(sd); cfg["sleep_threshold"] = 100000
    loop = NB.build_agent138nb(cfg)
    seen = []
    outer = loop.ears.hear
    def wrap(turn, _o=outer):
        a = _o(turn)
        seen.append([dict(x) if isinstance(x, dict) else x for x in (a or [])])
        return a
    loop.ears.hear = wrap
    for t in setup:
        seen.clear(); r = " ".join(loop.turn(t))
        print(f"SETUP {t!r} -> {r!r}", flush=True)
    seen.clear()
    e0 = len(getattr(loop.nb, "nb", loop.nb).events)
    reply = " ".join(loop.turn(q))
    e1 = len(getattr(loop.nb, "nb", loop.nb).events)
    acts = seen[-1] if seen else []
    inner = getattr(loop, "_inner138j_ears", None)
    print(f"Q {q!r}\n  reply={reply!r}\n  outer_stage={getattr(loop.ears,'last_stage','')!r} inner_stage={getattr(inner,'last_stage','') if inner is not None else None!r}\n  acts={acts} ev={e0}->{e1} intent={(loop.last_routed or {}).get('intent') if getattr(loop,'last_routed',None) else None}", flush=True)
    shutil.rmtree(sd, ignore_errors=True)
print("PILOT DONE", flush=True)
