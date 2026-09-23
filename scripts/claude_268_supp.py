#!/usr/bin/env python3
"""Exp 268 supplemental dialogs: possessive-phrased founder chains (the
o11-o14/o25 teaches used "The founder of X is Y.", which the teach side
does not parse -- empty notebook, RECORD). Plus one B73-shape control.

New file only. CPU only. Fictional names. Fresh agent + isolated temp
state dir per dialog, never the repo-root notebook.

Usage:
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/claude_268_supp.py <agent_py> <config> <out_json> [label]
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

import fable_loop90_agent as L90  # noqa: E402 (read-only triples)

SUPP: list[tuple[str, list[str], str, str]] = [
    ("p01-founder-whatfound",
     ["Copperfield's founder is Liora Sen.",
      "Liora Sen's founder is Marek Doyle.",
      "What did Liora Sen found?"],
     "Copperfield's founder is Liora Sen.", "WRONG-nhop"),
    ("p02-founder-whose",
     ["Copperfield's founder is Liora Sen.",
      "Liora Sen's founder is Marek Doyle.",
      "Whose founder is Liora Sen?"],
     "Copperfield's founder is Liora Sen.", "WRONG-nhop"),
    ("p03-founder-who-founded-value",
     ["Copperfield's founder is Liora Sen.",
      "Liora Sen's founder is Marek Doyle.",
      "Who founded Liora Sen?"],
     "Liora Sen's founder is Marek Doyle.", "CORRECT"),
    ("p04-founder-what-has-founded",
     ["Copperfield's founder is Liora Sen.",
      "Liora Sen's founder is Marek Doyle.",
      "What has Liora Sen founded?"],
     "Copperfield's founder is Liora Sen.", "WRONG-nhop"),
    ("p05-founder-nochain-whatfound",
     ["Copperfield's founder is Liora Sen.",
      "What did Liora Sen found?"],
     "", "RECORD"),
    ("p06-founder-fwd-possessive",
     ["Copperfield's founder is Liora Sen.",
      "Liora Sen's founder is Marek Doyle.",
      "Who is Liora Sen's founder?"],
     "Liora Sen's founder is Marek Doyle.", "CORRECT"),
    ("p07-spouse-who-is-the-spouse-of",
     ["Talia Wren's spouse is Bex Marlowe.",
      "Bex Marlowe's spouse is Cato Fenn.",
      "Who is the spouse of Bex Marlowe?"],
     "Bex Marlowe's spouse is Cato Fenn.", "CORRECT"),
]


def load_agent(agent_py: str):
    spec = importlib.util.spec_from_file_location(
        "ag_under_test_supp", str(SCRIPTS / Path(agent_py).name))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ag_under_test_supp"] = mod
    spec.loader.exec_module(mod)
    return mod


def stage_of(loop) -> str:
    for obj in (getattr(loop, "_inner138j_ears", None),
                getattr(loop, "ears", None)):
        st = getattr(obj, "last_stage", "")
        if st:
            return str(st)
    return ""


def main() -> int:
    agent_py, config, out = sys.argv[1:4]
    label = sys.argv[4] if len(sys.argv) > 4 else ""
    mod = load_agent(agent_py)
    build = None
    for name in ("build_agent268", "build_agent138m", "build_agent138n",
                 "build_agent138l"):
        if hasattr(mod, name):
            build = getattr(mod, name)
            break
    if build is None:
        raise SystemExit("no known build_* found in agent module")
    base = copy.deepcopy(json.loads(Path(config).read_text(encoding="utf-8")))
    rows: list[dict] = []
    for did, turns, gold, expect in SUPP:
        sd = Path(tempfile.mkdtemp(prefix="nhop268supp-"))
        try:
            cfg = copy.deepcopy(base)
            cfg["state_dir"] = str(sd)
            cfg["sleep_threshold"] = 100000
            loop = build(cfg)
            for j, t in enumerate(turns):
                rep = " ".join(loop.turn(t))
                st = stage_of(loop)
                try:
                    tr = [list(x) for x in L90.notebook_triples(loop.nb)]
                except Exception as e:  # noqa: BLE001
                    tr = [["ERR", str(e), ""]]
                last = (j == len(turns) - 1)
                verdict = ""
                if last and expect in ("WRONG-nhop", "CORRECT") and gold:
                    verdict = ("GOLD" if rep == gold
                               else ("WRONG-AS-PREDICTED"
                                     if expect == "WRONG-nhop" else "MISMATCH"))
                rows.append({"dialog": did, "turn": j, "input": t,
                             "stage": st, "reply": rep,
                             "triples_after": tr,
                             "gold_final": gold if last else "",
                             "expect": expect if last else "",
                             "verdict": verdict})
                if last:
                    print(f"[{label}] {did}: stage={st} reply={rep!r} "
                          f"verdict={verdict}", flush=True)
        finally:
            shutil.rmtree(sd, ignore_errors=True)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"WROTE {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
