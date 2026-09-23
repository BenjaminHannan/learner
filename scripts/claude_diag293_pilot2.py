#!/usr/bin/env python3
"""Pilot2 for exp 293-diag: edge shapes on 138nb."""
from __future__ import annotations
import copy, shutil, sys, tempfile
from pathlib import Path
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import claude_loop138nb_agent as NB

base = copy.deepcopy(NB.DEFAULT_CONFIG138NB)
tests = [
    (["Bex's mother is Talia."], "Is Talia Bex's mother?", "is-inv-true"),
    (["Bex's mother is Talia."], "Is Wren Bex's mother?", "is-inv-false"),
    (["Bex's mother is Talia."], "Is Bex's father Talia?", "is-unknown-rel"),
    (["Bex's mother is Talia."], "Is Zane's mother Talia?", "is-unknown-subj"),
    (["Bex's city is Oslo."], "Does Bex live in Bergen?", "does-live-false"),
    (["Bex's mother is Talia."], "Where does Bex live?", "does-live-unknown"),
    (["Sela ben Tamsin's mother is Wren."], "Is Sela ben Tamsin's mother Wren?", "is-2word"),
    (["Sela ben Tamsin's mother is Wren."], "Does Sela ben Tamsin have a mother?", "does-2word"),
    (["Bex's mother is Talia."], "Has Bex a mother?", "has-shape"),
    (["Bex's mother is Talia."], "Does Bex have mother?", "does-noart"),
    ([], "Bex does judo on Tuesdays.", "stmt-does"),
    ([], "Ana is happy.", "stmt-is"),
    (["Bex's mother is Talia."], "What is Bex's mother?", "wh-control"),
    (["Bex's mother is Talia."], "Is Talia the mother of Bex?", "is-ofform"),
    (["Rin's city is Bergen."], "Does Rin come from Bergen?", "does-come-true"),
    (["Rin's boss is Lee."], "Does Rin work at Halden?", "does-work-unknown"),
]
for setup, q, tag in tests:
    sd = Path(tempfile.mkdtemp(prefix="nb293p2-"))
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
    seen.clear()
    e0 = len(getattr(loop.nb, "nb", loop.nb).events)
    reply = " ".join(loop.turn(q))
    e1 = len(getattr(loop.nb, "nb", loop.nb).events)
    acts = seen[-1] if seen else []
    print(f"{tag} Q={q!r} -> {reply!r} stage={getattr(loop.ears,'last_stage','')!r} acts={str(acts)[:120]} ev={e0}->{e1}", flush=True)
    shutil.rmtree(sd, ignore_errors=True)
print("PILOT2 DONE", flush=True)
