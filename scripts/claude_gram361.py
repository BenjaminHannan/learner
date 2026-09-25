#!/usr/bin/env python3
"""gram-361: the 1B's chat replies sampled at temperature 0.3 instead of 0.7 (grammar thread, 2026-09-25).

Why: after gram-360 the 1B's own replies are the largest source of grammar misses (VERIFY-360.md: ~14% of
non-rule replies flagged). DEV probe (54 DEV smalltalk/creative/nosave turns, SYSTEM338, one sample each, two
blind graders): temperature 0.7 44/54 and 41/54 clean, 0.3 54/54 and 53/54, greedy 47/54 and 45/54. Sampling noise
at 0.7 produces garbled phrases and odd word choices.

What (one change): chat338b gets its own Gen338 sharing the loaded 1B but with temperature 0.3 (top_p 0.9, n 4,
max_new 200 unchanged). 333d creative keeps 338's Gen338 at 0.7. Nothing else changes.

  build_361(state_dir, args): 330c + gram-360 (build_360's layer order) with the chat temperature at 0.3.
  run_chat_component(...): the component test used for the registered marks (CPU, no reader): 338b's chat layer
  on a stub agent that always gives up, so every turn is answered by the 1B under 338/338b's guards and history.
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

CHAT_T361 = 0.3
_G361: dict = {}


def build_361(state_dir, args):
    import claude_chat338_agent as C38
    import claude_chat338b_agent as C38B
    import claude_cre333b_agent as C333B
    import claude_cre333d_agent as C333D
    import claude_e2e330_arms as A
    import claude_e2e330c as E330C
    import claude_gram360 as GR
    import claude_nb323_turnlog as NB
    import claude_think299b_agent as T299B
    import claude_vary330c as VARY
    if args.gen_model not in A._GEN:
        A._GEN[args.gen_model] = C333B.Gen333b(args.gen_model)
    one_b = A._GEN[args.gen_model]
    if args.gen_model not in E330C._G338B:
        E330C._G338B[args.gen_model] = C38.Gen338(share=one_b)
    if args.gen_model not in _G361:
        _G361[args.gen_model] = C38.Gen338(share=one_b, temperature=CHAT_T361)
    loop = A.build_330a_334(state_dir, args)
    GR.record_inner360(loop)
    C333D.install_creative333d(loop, E330C._G338B[args.gen_model])
    T299B.install_think299b(loop, one_b)
    C38B.install_chat338b(loop, _G361[args.gen_model])          # the one change: chat at 0.3
    VARY.install_vary330c(loop)
    GR.install_gram360(loop)
    NB.install_turnlog323(loop, str(Path(state_dir) / E330C.TURNLOG330C))
    loop.layers330c = ["330a_334", "rec360", "cre333d", "think299b", "chat338b@0.3", "vary330c", "gram360",
                       "turnlog323"]
    return loop


class _NB:
    events: list = []


class _GiveUp:
    """Stub agent for the component test: always gives 292t's clarify line, never writes, no notebook facts."""
    LINE = "I didn't understand that well enough to save it — could you say it another way?"

    def __init__(self, d: str):
        self.dir, self.nb, self.lis314_store, self.lis314_confirming = d, _NB(), None, None

    def turn(self, text: str) -> list[str]:
        return [self.LINE]


def run_chat_component(model_dir: str, turns: list[dict], temperature: float, seed: int, tmp: str) -> list[dict]:
    """One arm of the component test: 338b's chat layer at `temperature` over every conversation."""
    import random

    import torch

    import claude_chat338_agent as C38
    import claude_chat338b_agent as C38B
    import claude_cre333_agent as C
    import claude_cre333b_agent as C333B
    C._facts = lambda loop: []                     # the stub agent has an empty notebook
    one_b = C333B.Gen333b(model_dir)
    gen = C38.Gen338(share=one_b, temperature=temperature)
    out = []
    convs: dict[str, list[dict]] = {}
    for t in turns:
        convs.setdefault(t["conv_id"], []).append(t)
    for ci, cid in enumerate(sorted(convs)):
        d = Path(tmp) / f"{cid}-{temperature}"
        d.mkdir(parents=True, exist_ok=True)
        loop = _GiveUp(str(d))
        C38B.install_chat338b(loop, gen)
        for t in sorted(convs[cid], key=lambda x: x["turn_index"]):
            torch.manual_seed(seed + ci * 100 + t["turn_index"])
            random.seed(seed + ci * 100 + t["turn_index"])
            reply = " ".join(p for p in loop.turn(t["user_text"]) if p)
            out.append({"conv_id": cid, "turn_index": t["turn_index"], "kind": t["kind"], "reply": reply})
        out[-1]["stats"] = dict(loop.chat338_stats, **loop.chat338b_stats)
    return out


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--gen-model", required=True)
    ap.add_argument("--temperature", type=float, required=True)
    ap.add_argument("--seed", type=int, default=3610)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tmp", required=True)
    a = ap.parse_args()
    turns = [json.loads(x) for x in Path(a.panel).read_text(encoding="utf-8").splitlines() if x.strip()]
    rows = run_chat_component(a.gen_model, turns, a.temperature, a.seed, a.tmp)
    Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps({"rows": len(rows), "temperature": a.temperature}))
