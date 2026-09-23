#!/usr/bin/env python3
"""Exp 268b dev runner: 268's dev36+own34 (70) + supp7 + 46 new 268b dialogs.

New file only. CPU only. Fictional names. Never the repo-root notebook:
every dialog runs on a FRESH agent with an isolated temp state dir.

268's dialog definitions are imported read-only from
scripts/claude_268_devrepro.py (DEV36, OWN34) and
scripts/claude_268_supp.py (SUPP); the 46 new dialogs come from
scripts/claude_268b_newdev.py (NEW268B). Nothing is read item by item
from any TEST-ONLY panel; nhoppanel268 is never dev material.

Usage:
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/claude_268b_devrepro.py <agent_py> <config> <out_json> [label]

agent_py: scripts/claude_loop138nb_agent.py | scripts/claude_loop268b_agent.py
config:   artifacts/claude-merge138nb-20260923/loop138nb-config.json |
          artifacts/claude-nhop268b-20260923/loop268b-config.json
Writes one JSON row per turn: dialog, turn, input, stage, reply,
triples_after, gold_final, expect, verdict. Prints a summary.
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


def _load_lists():
    import claude_268_devrepro as D268  # noqa: E402 (read-only dialog defs)
    import claude_268_supp as S268  # noqa: E402 (read-only dialog defs)
    import claude_268b_newdev as N268B  # noqa: E402 (own new dialogs)
    dev = [("dev", d) for d in D268.DEV36] + [("own", d) for d in D268.OWN34]
    supp = [("supp", d) for d in S268.SUPP]
    new = [("new268b", d) for d in N268B.NEW268B]
    return dev, supp, new


def load_agent(agent_py: str):
    spec = importlib.util.spec_from_file_location(
        "ag_under_test_268b", str(SCRIPTS / Path(agent_py).name))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ag_under_test_268b"] = mod
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
    dev, supp, new = _load_lists()
    ALL = dev + supp + new
    mod = load_agent(agent_py)
    build = None
    for name in ("build_agent268b", "build_agent138nb", "build_agent268",
                 "build_agent138m", "build_agent138n"):
        if hasattr(mod, name):
            build = getattr(mod, name)
            break
    if build is None:
        raise SystemExit("no known build_* found in agent module")
    default_cfg = None
    for name in ("DEFAULT_CONFIG268B", "DEFAULT_CONFIG138NB",
                 "DEFAULT_CONFIG268", "DEFAULT_CONFIG138M",
                 "DEFAULT_CONFIG138N"):
        if hasattr(mod, name):
            default_cfg = getattr(mod, name)
            break
    base = copy.deepcopy(json.loads(Path(config).read_text(encoding="utf-8"))
                         if config != "-" else default_cfg)
    rows: list[dict] = []
    n_exp: dict[str, int] = {}
    n_gold = 0
    n_wrongpred_ok = 0
    for _src, (did, turns, gold, expect) in ALL:
        sd = Path(tempfile.mkdtemp(prefix="nhop268b-"))
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
                if last:
                    n_exp[expect] = n_exp.get(expect, 0) + 1
                    if expect in ("WRONG-nhop", "CORRECT") and gold:
                        if rep == gold:
                            verdict = "GOLD"
                            n_gold += 1
                        elif expect == "WRONG-nhop":
                            verdict = "WRONG-AS-PREDICTED"
                            n_wrongpred_ok += 1
                        else:
                            verdict = "MISMATCH"
                rows.append({"src": _src, "dialog": did, "turn": j,
                             "input": t, "stage": st, "reply": rep,
                             "triples_after": tr,
                             "gold_final": gold if last else "",
                             "expect": expect if last else "",
                             "verdict": verdict})
        finally:
            shutil.rmtree(sd, ignore_errors=True)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"[{label}] dialogs={len(ALL)} turns={len(rows)} "
          f"gold={n_gold} wrong_as_predicted={n_wrongpred_ok} "
          f"n_exp={n_exp}", flush=True)
    for r in rows:
        if r["turn"] == 2 or (r["gold_final"] and r["verdict"]):
            pass
    for r in rows:
        if r["verdict"] in ("MISMATCH", "WRONG-AS-PREDICTED") or (
                r["gold_final"] and r["verdict"] == "GOLD"):
            print(f"[{label}] {r['dialog']}: stage={r['stage']} "
                  f"reply={r['reply']!r} verdict={r['verdict']}",
                  flush=True)
    print(f"WROTE {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
