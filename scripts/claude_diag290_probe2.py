#!/usr/bin/env python3
"""290 probe2: same + extra shapes on 138k/138l/138m with act capture.
New file only. Fictional names only."""
from __future__ import annotations
import copy, shutil, sys, tempfile
from pathlib import Path
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import claude_loop138k_agent as K
import claude_loop138l_agent as L
import claude_loop138m_agent as M

D = [
    ("does-taught-dog", ["Bex's dog is Biscuit."], "Does Bex have a dog?"),
    ("does-never-dog", ["Bex's mother is Talia."], "Does Bex have a dog?"),
    ("does-taught-mother", ["Bex's mother is Talia."], "Does Bex have a mother?"),
    ("does-unknown-ent", ["Bex's mother is Talia."], "Does Zane have a dog?"),
    ("does-after-forget", ["Bex's dog is Biscuit.", "Forget Bex's dog."], "Does Bex have a dog?"),
    ("does-after-isnot", ["Bex's dog is Biscuit.", "Bex's dog is not Biscuit."], "Does Bex have a dog?"),
    ("newrel-what", ["Bex's mother is Talia."], "What is Bex's hobby?"),
    ("newrel-who", ["Bex's mother is Talia."], "Who is Bex's hobby?"),
    ("newrel-where", ["Bex's mother is Talia."], "Where does Bex work?"),
    ("newrel-does", ["Bex's mother is Talia."], "Does Bex have a hobby?"),
    ("never-what", ["Bex's mother is Talia."], "What is Bex's father?"),
    ("never-where", ["Bex's mother is Talia."], "Where does Bex live?"),
    ("never-who", ["Bex's mother is Talia."], "Who is Bex's father?"),
    ("taught-what", ["Bex's mother is Talia."], "What is Bex's mother?"),
    ("taught-where", ["Bex's city is Oslo."], "Where does Bex live?"),
    ("taught-who", ["Bex's mother is Talia."], "Who is Bex's mother?"),
    ("forget-what", ["Bex's mother is Talia.", "Forget Bex's mother."], "What is Bex's mother?"),
    ("forget-where", ["Bex's city is Oslo.", "Forget Bex's city."], "Where does Bex live?"),
    ("forget-who", ["Bex's mother is Talia.", "Forget Bex's mother."], "Who is Bex's mother?"),
    ("isnot-what", ["Bex's mother is Talia.", "Bex's mother is not Talia."], "What is Bex's mother?"),
    ("isnot-does", ["Bex's mother is Talia.", "Bex's mother is not Talia."], "Does Bex have a mother?"),
]

MODS = {"138k": (K, "build_agent138k", "DEFAULT_CONFIG138K"),
        "138l": (L, "build_agent138l", "DEFAULT_CONFIG138L"),
        "138m": (M, "build_agent138m", "DEFAULT_CONFIG138M")}

def run():
    for tag, (mod, bname, cname) in MODS.items():
        base = copy.deepcopy(getattr(mod, cname))
        for did, setup, q in D:
            sd = Path(tempfile.mkdtemp(prefix="nb290t-"))
            cfg = copy.deepcopy(base); cfg["state_dir"] = str(sd); cfg["sleep_threshold"] = 100000
            loop = getattr(mod, bname)(cfg)
            acts_seen = []
            outer = loop.ears.hear
            def hear_wrap(turn, _o=outer):
                a = _o(turn)
                acts_seen.append([dict(x) if isinstance(x, dict) else x for x in (a or [])])
                return a
            loop.ears.hear = hear_wrap
            for t in setup:
                acts_seen.clear()
                r = " ".join(loop.turn(t))
            acts_seen.clear()
            h0 = len(getattr(loop.nb, "nb", loop.nb).events)
            r = " ".join(loop.turn(q))
            h1 = len(getattr(loop.nb, "nb", loop.nb).events)
            acts = acts_seen[-1] if acts_seen else []
            ask = [a for a in acts if isinstance(a, dict) and a.get("act") == "ask"]
            lr = getattr(loop, "last_routed", None)
            intent = lr.get("intent") if isinstance(lr, dict) else None
            extra = ""
            if getattr(loop, "decline224_log", None):
                extra += f" d224={loop.decline224_log[-1]}"
            if getattr(loop, "q1honest224c_log", None):
                extra += f" q1c={loop.q1honest224c_log[-1]}"
            print(f"{tag} {did}: Q={q!r}\n  reply={r}\n  acts={acts} intent={intent} ev={h0}->{h1}{extra}", flush=True)
            shutil.rmtree(sd, ignore_errors=True)

if __name__ == "__main__":
    run()
