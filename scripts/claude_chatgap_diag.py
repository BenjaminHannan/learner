#!/usr/bin/env python3
"""Why does sleep's puzzle skill not show when a person asks in plain English? (Fix-sleep thread, 2026-09-26)
DIAGNOSIS ONLY: report, no marks, no training, nothing registered.

0.2c (artifacts/claude-e2e02c-20260926/VERIFY-02c.md) passed sleep's six marks inside the joined assistant: right
guesses on fresh puzzles 74 -> 192. But the same kind of puzzle typed as a chat message was solved 0 of 40, before
and after the nights. The nights practise one fixed puzzle prompt, with a rule-keeper that only lets the 1B write
legal expressions over the given numbers. A chat message goes through the assistant's layers instead.

For the same 40 chat puzzles as 0.2c (CHAT_SEED02C, built exactly as claude_sleep02c.run does), with the trained
adapter ON and OFF (every LoRA scale 0 = the plain base), this records:
  P1 puzzle prompt + rule-keeper, greedy        (what the nights train and TEST measures)
  P2 puzzle prompt, NO rule-keeper, greedy      (does the skill survive without the rule-keeper?)
  C1 chat wording straight to the 1B, greedy    (does the skill carry to English, without the assistant's layers?)
  C2 chat wording through the assistant (agent.turn), fresh agent per ask, as 0.2c's chat measure
Each reply is kept in full, with solved yes/no (claude_panel382_run.puzzle_solved; P1 also claude_blurt1.check),
plus a coarse kind: has-expression / refuses-or-asks / other. The puzzles are code-made, not a TEST-ONLY panel.

  python -B scripts/claude_twinb_wrap.py scripts/claude_chatgap_diag.py --arm claude_e2e02c:build_02c \
      --model READER319 --gen-model BASE --adapter PATH/adapter02c.pt --out OUT
  python -B scripts/claude_chatgap_diag.py --selftest
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

REFUSE = re.compile(r"(not sure|don't know|do not know|can't|cannot|unable|sorry|could you|please provide)", re.I)


def kind(reply: str, solved: bool) -> str:
    if solved:
        return "solved"
    if re.search(r"\d\s*[-+*/x×÷]\s*\(?\s*\d", reply):
        return "wrong-expression"
    if REFUSE.search(reply):
        return "refuses-or-asks"
    return "other"


def chat_puzzles(n_chat=40, nights=3, n_day=150, n_test=100):
    """Exactly claude_sleep02c.run's chat set."""
    import claude_blurt2 as B2
    import claude_sleep02c as SL
    day_keys = {(tuple(p["nums"]), p["target"]) for d in range(1, nights + 1)
                for p in B2.puzzles(SL.DAY_SEED02C + d, n_day)}
    test = [p for p in B2.puzzles(SL.TEST_SEED02C, n_test + 300)
            if (tuple(p["nums"]), p["target"]) not in day_keys][:n_test]
    tkeys = day_keys | {(tuple(p["nums"]), p["target"]) for p in test}
    return [p for p in B2.puzzles(SL.CHAT_SEED02C, n_chat + 300)
            if (tuple(p["nums"]), p["target"]) not in tkeys][:n_chat]


def ask_text(p) -> str:
    import claude_sleep02c as SL
    nums = ", ".join(str(n) for n in p["nums"][:-1]) + " and " + str(p["nums"][-1])
    return SL.CHAT_ASK.format(nums=nums, target=p["target"])


def free_puzzle(s, p, m, max_new=32) -> str:
    """The puzzle prompt, greedy, without the rule-keeper."""
    ids = s.tok(s.prompt(p), return_tensors="pt").to(s.dev)
    with s.torch.no_grad():
        out = m.generate(**ids, max_new_tokens=max_new, do_sample=False, pad_token_id=s.tok.eos_token_id)
    return s.tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def set_scale(m, on: bool, saved):
    mods = [x for x in m.modules() if hasattr(x, "A") and hasattr(x, "scale")]
    for x, sc in zip(mods, saved):
        x.scale = sc if on else 0.0


def run(a) -> None:
    import claude_blurt1 as B1
    import claude_dl1_nights as D1
    import claude_e2e330_arms as A
    import claude_panel382_run as P
    import claude_sleep02c as SL
    os.environ["SLEEP02C_ADAPTER"] = a.adapter            # every build_02c installs and loads it (sidecar-checked)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    mod, fn = a.arm.split(":")
    build = getattr(importlib.import_module(mod), fn)

    def agent():
        return build(tempfile.mkdtemp(prefix="gap-"), a)

    agent()
    one_b = A._GEN[a.gen_model]
    SL.install_sleep02c(one_b)                            # no-op if the build already installed it
    s = SL.solver_shim(one_b)
    m = one_b.model
    saved = [x.scale for x in m.modules() if hasattr(x, "A") and hasattr(x, "scale")]
    puzzles = chat_puzzles(a.n_chat)
    rows, t0 = [], time.time()
    for side in ("off", "on"):
        set_scale(m, side == "on", saved)
        for i, p in enumerate(puzzles):
            r = {"i": i, "side": side, "nums": p["nums"], "target": p["target"]}
            p1 = s.answer(p, m)
            r["P1"] = {"reply": p1, "solved": bool(B1.check(p1, p["nums"], p["target"]))}
            p2 = free_puzzle(s, p, m)
            r["P2"] = {"reply": p2, "solved": bool(P.puzzle_solved(p2, p["nums"], p["target"]))}
            c1 = D1.free_answer(s, ask_text(p), m, a.max_new)
            r["C1"] = {"reply": c1, "solved": bool(P.puzzle_solved(c1, p["nums"], p["target"]))}
            parts = agent().turn(ask_text(p))
            c2 = " ".join(x for x in (parts or []) if x)
            r["C2"] = {"reply": c2, "solved": bool(P.puzzle_solved(c2, p["nums"], p["target"]))}
            for k in ("P1", "P2", "C1", "C2"):
                r[k]["kind"] = kind(r[k]["reply"], r[k]["solved"])
            rows.append(r)
            with open(out / "chatgap_rows.jsonl", "a", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps(r) + "\n")
        print(f"[chatgap] {side} done ({round((time.time() - t0) / 60, 1)} min)", flush=True)
    set_scale(m, True, saved)
    summ = {"n": len(puzzles), "adapter": a.adapter, "minutes": round((time.time() - t0) / 60, 1)}
    for side in ("off", "on"):
        for k in ("P1", "P2", "C1", "C2"):
            rs = [r[k] for r in rows if r["side"] == side]
            kinds = {}
            for x in rs:
                kinds[x["kind"]] = kinds.get(x["kind"], 0) + 1
            summ[f"{k}_{side}"] = {"solved": sum(x["solved"] for x in rs), "kinds": kinds}
    (out / "chatgap_summary.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    print(json.dumps(summ))


def selftest() -> None:
    assert kind("(3 * 8) * 1", True) == "solved"
    assert kind("Try 3 + 8 * 1 = 11", False) == "wrong-expression"
    assert kind("I'm not sure how to solve that.", False) == "refuses-or-asks"
    assert kind("Great question! Puzzles are fun.", False) == "other"
    ps = chat_puzzles(40)
    assert len(ps) == 40 and all("nums" in p and "target" in p for p in ps)
    assert "exactly once" in ask_text(ps[0])
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="claude_e2e02c:build_02c")
    ap.add_argument("--model", default="", help="reader dir")
    ap.add_argument("--gen-model", default="", help="base MiniCPM5-1B dir")
    ap.add_argument("--mouth-model", default="")
    ap.add_argument("--adapter", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--n-chat", type=int, default=40)
    ap.add_argument("--max-new", type=int, default=96)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    if not (a.out and a.gen_model and a.adapter):
        raise SystemExit("chatgap: --out, --gen-model and --adapter are required")
    run(a)


if __name__ == "__main__":
    main()
