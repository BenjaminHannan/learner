#!/usr/bin/env python3
"""290 probe: which shapes reach the glue decline on 138k; which corrections take.
New file only. Fictional names only."""
from __future__ import annotations
import copy, shutil, sys, tempfile
from pathlib import Path
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import claude_loop138k_agent as K

D = [
    ("s1-empty-what", [], "What is Bex's mother?"),
    ("s2-empty-where", [], "Where does Bex live?"),
    ("s3-empty-who", [], "Who is Bex's mother?"),
    ("s4-empty-does", [], "Does Bex have a dog?"),
    ("s5-taught-other-what", ["Bex's mother is Talia."], "What is Bex's father?"),
    ("s6-taught-other-where", ["Bex's mother is Talia."], "Where does Bex live?"),
    ("s7-taught-other-who", ["Bex's mother is Talia."], "Who is Bex's father?"),
    ("s8-taught-other-does", ["Bex's mother is Talia."], "Does Bex have a dog?"),
    ("s9-city-what", ["Bex's city is Oslo."], "What is Bex's city?"),
    ("s10-city-where", ["Bex's city is Oslo."], "Where does Bex live?"),
    ("s11-city-where-never", ["Bex's mother is Talia."], "Where does Rin live?"),
    ("s12-dog-does-taught", ["Bex's dog is Biscuit."], "Does Bex have a dog?"),
    ("s13-dog-does-never", ["Bex's mother is Talia."], "Does Bex have a dog?"),
    ("s14-boss-who", ["Bex's mother is Talia."], "Who is Bex's boss?"),
    ("s15-unknown-entity", ["Bex's mother is Talia."], "What is Zane's mother?"),
    ("s16-unknown-where", ["Bex's mother is Talia."], "Where does Zane live?"),
    ("c1-forget", ["Bex's mother is Talia.", "Forget Bex's mother."], "What is Bex's mother?"),
    ("c2-confirm-yes", ["Bex's mother is Talia.", "Actually Bex's mother is Zara.", "Yes."], "What is Bex's mother?"),
    ("c3-not", ["Bex's mother is Talia.", "Bex's mother is not Talia."], "What is Bex's mother?"),
    ("c4-wrong", ["Bex's mother is Talia.", "You are wrong, Bex's mother is Zara."], "What is Bex's mother?"),
    ("c5-never-was", ["Bex's mother is Talia.", "Bex's mother was never Talia."], "What is Bex's mother?"),
]

def run():
    base = copy.deepcopy(K.DEFAULT_CONFIG138K)
    for did, setup, q in D:
        sd = Path(tempfile.mkdtemp(prefix="nb290s-"))
        cfg = copy.deepcopy(base); cfg["state_dir"] = str(sd); cfg["sleep_threshold"] = 100000
        loop = K.build_agent138k(cfg)
        for t in setup:
            r = " ".join(loop.turn(t))
            print(f"138k {did} setup: {t!r} -> {r}", flush=True)
        h0 = len(getattr(loop.nb, "nb", loop.nb).events)
        r = " ".join(loop.turn(q))
        h1 = len(getattr(loop.nb, "nb", loop.nb).events)
        oe = getattr(loop.ears, "last_stage", "")
        inw = getattr(getattr(loop, "_inner138j_ears", None), "last_stage", "")
        lr = getattr(loop, "last_routed", None)
        intent = lr.get("intent") if isinstance(lr, dict) else None
        print(f"138k {did} Q: {q!r} -> {r} [outer={oe} inner={inw} intent={intent} ev={h0}->{h1}]", flush=True)
        shutil.rmtree(sd, ignore_errors=True)

if __name__ == "__main__":
    run()
