#!/usr/bin/env python3
"""Exp 268 dev repro: 36 nhopdiag dev dialogs + 34 own dialogs, fresh agent.

New file only. CPU only. Fictional names. Never the repo-root notebook:
every dialog runs on a FRESH agent with an isolated temp state dir.

Usage:
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/claude_268_devrepro.py <agent_py> <config> <out_json> [label]

agent_py: e.g. scripts/claude_loop138m_agent.py
config:   e.g. artifacts/claude-merge138m-20260922/loop138m-config.json
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

# (dialog id, turns, gold final reply, expect class)
# expect: WRONG-nhop | CORRECT | RECORD
DEV36: list[tuple[str, list[str], str, str]] = [
    ("d01-anchor-spouse-whose",
     ["Kim Varro's spouse is Dana Holt.",
      "Dana Holt's spouse is Ravi Stone.",
      "Whose spouse is Dana Holt?"],
     "Kim Varro's spouse is Dana Holt.", "WRONG-nhop"),
    ("d02-anchor-spouse-married",
     ["Kim Varro's spouse is Dana Holt.",
      "Dana Holt's spouse is Ravi Stone.",
      "Who is married to Dana Holt?"],
     "Kim Varro's spouse is Dana Holt.", "WRONG-nhop"),
    ("d03-spouse-whose",
     ["Talia Wren's spouse is Bex Marlowe.",
      "Bex Marlowe's spouse is Cato Fenn.",
      "Whose spouse is Bex Marlowe?"],
     "Talia Wren's spouse is Bex Marlowe.", "WRONG-nhop"),
    ("d04-spouse-married",
     ["Talia Wren's spouse is Bex Marlowe.",
      "Bex Marlowe's spouse is Cato Fenn.",
      "Who is married to Bex Marlowe?"],
     "Talia Wren's spouse is Bex Marlowe.", "WRONG-nhop"),
    ("d05-spouse-husband",
     ["Talia Wren's spouse is Bex Marlowe.",
      "Bex Marlowe's spouse is Cato Fenn.",
      "Whose husband is Bex Marlowe?"],
     "Talia Wren's spouse is Bex Marlowe.", "WRONG-nhop"),
    ("d06-spouse-wife",
     ["Talia Wren's spouse is Bex Marlowe.",
      "Bex Marlowe's spouse is Cato Fenn.",
      "Whose wife is Bex Marlowe?"],
     "Talia Wren's spouse is Bex Marlowe.", "WRONG-nhop"),
    ("d07-spouse-nochain",
     ["Talia Wren's spouse is Bex Marlowe.",
      "Whose spouse is Bex Marlowe?"],
     "Talia Wren's spouse is Bex Marlowe.", "CORRECT"),
    ("d08-spouse-2subj-yn1",
     ["Talia Wren's spouse is Bex Marlowe.",
      "Bex Marlowe's spouse is Cato Fenn.",
      "Is Bex Marlowe Talia Wren's spouse?"],
     "", "RECORD"),
    ("d09-spouse-2subj-yn2",
     ["Talia Wren's spouse is Bex Marlowe.",
      "Bex Marlowe's spouse is Cato Fenn.",
      "Is Cato Fenn Bex Marlowe's spouse?"],
     "", "RECORD"),
    ("d10-spouse-forward",
     ["Talia Wren's spouse is Bex Marlowe.",
      "Bex Marlowe's spouse is Cato Fenn.",
      "Who is Bex Marlowe's spouse?"],
     "Bex Marlowe's spouse is Cato Fenn.", "CORRECT"),
    ("d11-anchor-author-whatwritten",
     ["Harbor Lights's author is Dana Holt.",
      "Dana Holt's author is Ravi Stone.",
      "What has Dana Holt written?"],
     "Harbor Lights's author is Dana Holt.", "WRONG-nhop"),
    ("d12-author-whatwritten",
     ["The author of Salt Harbor is Petra Quinn.",
      "The author of Petra Quinn is Milo Hart.",
      "What has Petra Quinn written?"],
     "Salt Harbor's author is Petra Quinn.", "WRONG-nhop"),
    ("d13-author-forward",
     ["The author of Salt Harbor is Petra Quinn.",
      "The author of Petra Quinn is Milo Hart.",
      "Who wrote Salt Harbor?"],
     "Salt Harbor's author is Petra Quinn.", "CORRECT"),
    ("d14-author-nochain",
     ["The author of Salt Harbor is Petra Quinn.",
      "What has Petra Quinn written?"],
     "", "RECORD"),
    ("d15-author-2subj",
     ["The author of Salt Harbor is Petra Quinn.",
      "The author of Petra Quinn is Milo Hart.",
      "Did Petra Quinn write Salt Harbor?"],
     "", "RECORD"),
    ("d16-founder-whatfound",
     ["Ember Bay's founder is Sela Voss.",
      "Sela Voss's founder is Daro Venn.",
      "What did Sela Voss found?"],
     "Ember Bay's founder is Sela Voss.", "WRONG-nhop"),
    ("d17-founder-forward",
     ["Ember Bay's founder is Sela Voss.",
      "Sela Voss's founder is Daro Venn.",
      "Who founded Ember Bay?"],
     "Ember Bay's founder is Sela Voss.", "CORRECT"),
    ("d18-founder-nochain",
     ["Ember Bay's founder is Sela Voss.",
      "What did Sela Voss found?"],
     "", "RECORD"),
    ("d19-founder-2subj",
     ["Ember Bay's founder is Sela Voss.",
      "Sela Voss's founder is Daro Venn.",
      "Did Sela Voss found Ember Bay?"],
     "", "RECORD"),
    ("d20-boss-chain",
     ["Juno Pike's boss is Wren Talbot.",
      "Wren Talbot's boss is Ash Moreno.",
      "Whose boss is Wren Talbot?"],
     "Juno Pike's boss is Wren Talbot.", "CORRECT"),
    ("d21-boss-nochain",
     ["Juno Pike's boss is Wren Talbot.",
      "Whose boss is Wren Talbot?"],
     "Juno Pike's boss is Wren Talbot.", "CORRECT"),
    ("d22-boss-forward",
     ["Juno Pike's boss is Wren Talbot.",
      "Wren Talbot's boss is Ash Moreno.",
      "Who is Wren Talbot's boss?"],
     "Wren Talbot's boss is Ash Moreno.", "CORRECT"),
    ("d23-mother-chain",
     ["Lark Ohm's mother is Tess Ibarra.",
      "Tess Ibarra's mother is Nia Sol.",
      "Whose mother is Tess Ibarra?"],
     "Lark Ohm's mother is Tess Ibarra.", "CORRECT"),
    ("d24-mother-nochain",
     ["Lark Ohm's mother is Tess Ibarra.",
      "Whose mother is Tess Ibarra?"],
     "Lark Ohm's mother is Tess Ibarra.", "CORRECT"),
    ("d25-mother-forward",
     ["Lark Ohm's mother is Tess Ibarra.",
      "Tess Ibarra's mother is Nia Sol.",
      "Who is Tess Ibarra's mother?"],
     "Tess Ibarra's mother is Nia Sol.", "CORRECT"),
    ("d26-friend-chain",
     ["Pell Dray's friend is Moss Kline.",
      "Moss Kline's friend is Vera Jost.",
      "Whose friend is Moss Kline?"],
     "Pell Dray's friend is Moss Kline.", "CORRECT"),
    ("d27-friend-nochain",
     ["Pell Dray's friend is Moss Kline.",
      "Whose friend is Moss Kline?"],
     "Pell Dray's friend is Moss Kline.", "CORRECT"),
    ("d28-friend-forward",
     ["Pell Dray's friend is Moss Kline.",
      "Moss Kline's friend is Vera Jost.",
      "Who is Moss Kline's friend?"],
     "Moss Kline's friend is Vera Jost.", "CORRECT"),
    ("d29-spouse-3link",
     ["Aldo Rehn's spouse is Bram Colt.",
      "Bram Colt's spouse is Cleo Drane.",
      "Cleo Drane's spouse is Dov Elkin.",
      "Whose spouse is Cleo Drane?"],
     "Bram Colt's spouse is Cleo Drane.", "WRONG-nhop"),
    ("d30-spouse-fwd-wording",
     ["Talia Wren's spouse is Bex Marlowe.",
      "Bex Marlowe's spouse is Cato Fenn.",
      "Who is Bex Marlowe married to?"],
     "Bex Marlowe's spouse is Cato Fenn.", "CORRECT"),
    ("d31-spouse-sink",
     ["Talia Wren's spouse is Bex Marlowe.",
      "Bex Marlowe's spouse is Cato Fenn.",
      "Whose spouse is Cato Fenn?"],
     "Bex Marlowe's spouse is Cato Fenn.", "CORRECT"),
    ("d32-spouse-2subj-choice",
     ["Talia Wren's spouse is Bex Marlowe.",
      "Bex Marlowe's spouse is Cato Fenn.",
      "Who is married to Bex Marlowe, Talia Wren or Cato Fenn?"],
     "", "RECORD"),
    ("d33-author-whose",
     ["The author of Salt Harbor is Petra Quinn.",
      "The author of Petra Quinn is Milo Hart.",
      "Whose author is Petra Quinn?"],
     "Salt Harbor's author is Petra Quinn.", "WRONG-nhop"),
    ("d34-founder-whose",
     ["Ember Bay's founder is Sela Voss.",
      "Sela Voss's founder is Daro Venn.",
      "Whose founder is Sela Voss?"],
     "Ember Bay's founder is Sela Voss.", "WRONG-nhop"),
    ("d35-boss-2subj",
     ["Juno Pike's boss is Wren Talbot.",
      "Wren Talbot's boss is Ash Moreno.",
      "Is Wren Talbot Juno Pike's boss?"],
     "", "RECORD"),
    ("d36-friend-nochain-fwd",
     ["Pell Dray's friend is Moss Kline.",
      "Who is Moss Kline's friend?"],
     "", "RECORD"),
]

# 34 own dialogs (o-prefix), fictional names.
OWN34: list[tuple[str, list[str], str, str]] = [
    ("o01-spouse-was-married",
     ["Alba Reyes's spouse is Bram Kolb.",
      "Bram Kolb's spouse is Cleo Drane.",
      "Who was married to Bram Kolb?"],
     "Alba Reyes's spouse is Bram Kolb.", "WRONG-nhop"),
    ("o02-spouse-who-has-as",
     ["Alba Reyes's spouse is Bram Kolb.",
      "Bram Kolb's spouse is Cleo Drane.",
      "Who has Bram Kolb as their spouse?"],
     "Alba Reyes's spouse is Bram Kolb.", "WRONG-nhop"),
    ("o03-spouse-fwd-married-to",
     ["Alba Reyes's spouse is Bram Kolb.",
      "Bram Kolb's spouse is Cleo Drane.",
      "Who is Bram Kolb married to?"],
     "Bram Kolb's spouse is Cleo Drane.", "CORRECT"),
    ("o04-spouse-partner",
     ["Alba Reyes's spouse is Bram Kolb.",
      "Bram Kolb's spouse is Cleo Drane.",
      "Whose partner is Bram Kolb?"],
     "Alba Reyes's spouse is Bram Kolb.", "WRONG-nhop"),
    ("o05-spouse-2subj-choice",
     ["Alba Reyes's spouse is Bram Kolb.",
      "Bram Kolb's spouse is Cleo Drane.",
      "Is Bram Kolb married to Alba Reyes or Cleo Drane?"],
     "", "RECORD"),
    ("o06-spouse-sink-whose",
     ["Alba Reyes's spouse is Bram Kolb.",
      "Bram Kolb's spouse is Cleo Drane.",
      "Whose spouse is Cleo Drane?"],
     "Bram Kolb's spouse is Cleo Drane.", "CORRECT"),
    ("o07-author-what-did-write",
     ["The author of Grayport is Ines Halvors.",
      "The author of Ines Halvors is Jorah Bell.",
      "What did Ines Halvors write?"],
     "", "RECORD"),
    ("o08-author-who-wrote-value",
     ["The author of Grayport is Ines Halvors.",
      "The author of Ines Halvors is Jorah Bell.",
      "Who wrote Ines Halvors?"],
     "", "RECORD"),
    ("o09-author-whose",
     ["The author of Grayport is Ines Halvors.",
      "The author of Ines Halvors is Jorah Bell.",
      "Whose author is Ines Halvors?"],
     "Grayport's author is Ines Halvors.", "WRONG-nhop"),
    ("o10-author-fwd-possessive",
     ["The author of Grayport is Ines Halvors.",
      "The author of Ines Halvors is Jorah Bell.",
      "Who is Ines Halvors's author?"],
     "Ines Halvors's author is Jorah Bell.", "CORRECT"),
    ("o11-founder-who-founded-value",
     ["The founder of Copperfield is Liora Sen.",
      "The founder of Liora Sen is Marek Doyle.",
      "Who founded Liora Sen?"],
     "Liora Sen's founder is Marek Doyle.", "CORRECT"),
    ("o12-founder-whose",
     ["The founder of Copperfield is Liora Sen.",
      "The founder of Liora Sen is Marek Doyle.",
      "Whose founder is Liora Sen?"],
     "Copperfield's founder is Liora Sen.", "WRONG-nhop"),
    ("o13-founder-what-has-founded",
     ["The founder of Copperfield is Liora Sen.",
      "The founder of Liora Sen is Marek Doyle.",
      "What has Liora Sen founded?"],
     "Copperfield's founder is Liora Sen.", "WRONG-nhop"),
    ("o14-founder-what-was-founded-by",
     ["The founder of Copperfield is Liora Sen.",
      "The founder of Liora Sen is Marek Doyle.",
      "What was founded by Liora Sen?"],
     "", "RECORD"),
    ("o15-employer-whose",
     ["Theo Marsh's employer is Priya Nair.",
      "Priya Nair's employer is Oren Hale.",
      "Whose employer is Priya Nair?"],
     "Theo Marsh's employer is Priya Nair.", "WRONG-nhop"),
    ("o16-employer-fwd",
     ["Theo Marsh's employer is Priya Nair.",
      "Priya Nair's employer is Oren Hale.",
      "Who is Priya Nair's employer?"],
     "Priya Nair's employer is Oren Hale.", "CORRECT"),
    ("o17-employer-who-employs",
     ["Theo Marsh's employer is Priya Nair.",
      "Priya Nair's employer is Oren Hale.",
      "Who employs Priya Nair?"],
     "", "RECORD"),
    ("o18-child-whose",
     ["Rosa Lind's child is Tomas Rey.",
      "Tomas Rey's child is Uma Frost.",
      "Whose child is Tomas Rey?"],
     "Rosa Lind's child is Tomas Rey.", "WRONG-nhop"),
    ("o19-child-fwd",
     ["Rosa Lind's child is Tomas Rey.",
      "Tomas Rey's child is Uma Frost.",
      "Who is Tomas Rey's child?"],
     "Tomas Rey's child is Uma Frost.", "CORRECT"),
    ("o20-author-3link-whatwritten",
     ["The author of Dunmere is Elif Aydin.",
      "The author of Elif Aydin is Felix Marsh.",
      "The author of Felix Marsh is Greta Lund.",
      "What has Felix Marsh written?"],
     "Elif Aydin's author is Felix Marsh.", "WRONG-nhop"),
    ("o21-spouse-sink-who-has-as",
     ["Alba Reyes's spouse is Bram Kolb.",
      "Bram Kolb's spouse is Cleo Drane.",
      "Who has Cleo Drane as her spouse?"],
     "Bram Kolb's spouse is Cleo Drane.", "CORRECT"),
    ("o22-spouse-fwd-husband",
     ["Alba Reyes's spouse is Bram Kolb.",
      "Bram Kolb's spouse is Cleo Drane.",
      "Who is Bram Kolb's husband?"],
     "Bram Kolb's spouse is Cleo Drane.", "CORRECT"),
    ("o23-author-nochain-whatwritten",
     ["The author of Grayport is Ines Halvors.",
      "What has Ines Halvors written?"],
     "", "RECORD"),
    ("o24-spouse-sink-whose-wife",
     ["Alba Reyes's spouse is Bram Kolb.",
      "Bram Kolb's spouse is Cleo Drane.",
      "Whose wife is Cleo Drane?"],
     "", "RECORD"),
    ("o25-founder-fwd-possessive",
     ["The founder of Copperfield is Liora Sen.",
      "The founder of Liora Sen is Marek Doyle.",
      "Who is Liora Sen's founder?"],
     "Liora Sen's founder is Marek Doyle.", "CORRECT"),
    ("o26-mother-chain",
     ["Ivy Sloane's mother is Nadia Fer.",
      "Nadia Fer's mother is Opal Gray.",
      "Whose mother is Nadia Fer?"],
     "Ivy Sloane's mother is Nadia Fer.", "CORRECT"),
    ("o27-spouse-fwd-short",
     ["Alba Reyes's spouse is Bram Kolb.",
      "Bram Kolb's spouse is Cleo Drane.",
      "Who is Bram Kolb's spouse?"],
     "Bram Kolb's spouse is Cleo Drane.", "CORRECT"),
    ("o28-spouse-whose-was",
     ["Alba Reyes's spouse is Bram Kolb.",
      "Bram Kolb's spouse is Cleo Drane.",
      "Whose spouse was Bram Kolb?"],
     "Alba Reyes's spouse is Bram Kolb.", "WRONG-nhop"),
    ("o29-author-past-perfect",
     ["The author of Grayport is Ines Halvors.",
      "The author of Ines Halvors is Jorah Bell.",
      "What had Ines Halvors written?"],
     "Grayport's author is Ines Halvors.", "WRONG-nhop"),
    ("o30-boss-fwd",
     ["Quinn Avery's boss is Rory Tan.",
      "Rory Tan's boss is Skye Lind.",
      "Who is Rory Tan's boss?"],
     "Rory Tan's boss is Skye Lind.", "CORRECT"),
    ("o31-friend-chain",
     ["Pax Ford's friend is Quin Harper.",
      "Quin Harper's friend is Remy Cook.",
      "Whose friend is Quin Harper?"],
     "Pax Ford's friend is Quin Harper.", "CORRECT"),
    ("o32-spouse-sink-3link",
     ["Alba Reyes's spouse is Bram Kolb.",
      "Bram Kolb's spouse is Cleo Drane.",
      "Cleo Drane's spouse is Dov Elkin.",
      "Whose spouse is Dov Elkin?"],
     "Cleo Drane's spouse is Dov Elkin.", "CORRECT"),
    ("o33-author-who-wrote-sink",
     ["The author of Grayport is Ines Halvors.",
      "The author of Ines Halvors is Jorah Bell.",
      "Who wrote Jorah Bell?"],
     "", "RECORD"),
    ("o34-founder-2subj",
     ["The founder of Copperfield is Liora Sen.",
      "The founder of Liora Sen is Marek Doyle.",
      "Did Liora Sen found Copperfield?"],
     "", "RECORD"),
]

ALL = [("dev", d) for d in DEV36] + [("own", d) for d in OWN34]


def load_agent(agent_py: str):
    spec = importlib.util.spec_from_file_location(
        "ag_under_test", str(SCRIPTS / Path(agent_py).name))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ag_under_test"] = mod
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
    default_cfg = None
    for name in ("DEFAULT_CONFIG268", "DEFAULT_CONFIG138M",
                 "DEFAULT_CONFIG138N", "DEFAULT_CONFIG138L"):
        if hasattr(mod, name):
            default_cfg = getattr(mod, name)
            break
    base = copy.deepcopy(json.loads(Path(config).read_text(encoding="utf-8"))
                         if config != "-" else default_cfg)
    rows: list[dict] = []
    n_exp = {"WRONG-nhop": 0, "CORRECT": 0, "RECORD": 0}
    n_gold = 0
    n_wrongpred_ok = 0
    for _src, (did, turns, gold, expect) in ALL:
        sd = Path(tempfile.mkdtemp(prefix="nhop268-"))
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
                    n_exp[expect] += 1
                    if expect in ("WRONG-nhop", "CORRECT") and gold:
                        if rep == gold:
                            verdict = "GOLD"
                            n_gold += 1
                        elif expect == "WRONG-nhop":
                            verdict = "WRONG-AS-PREDICTED"
                            n_wrongpred_ok += 1
                        else:
                            verdict = "MISMATCH"
                rows.append({"dialog": did, "turn": j, "input": t,
                             "stage": st, "reply": rep,
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
        if r["verdict"] in ("MISMATCH", "WRONG-AS-PREDICTED") or (
                r["gold_final"] and r["verdict"] == "GOLD"):
            print(f"[{label}] {r['dialog']}: stage={r['stage']} "
                  f"reply={r['reply']!r} verdict={r['verdict']}",
                  flush=True)
    print(f"WROTE {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
