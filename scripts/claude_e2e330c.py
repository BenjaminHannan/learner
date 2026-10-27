#!/usr/bin/env python3
"""330c: the joined Premonition 0.1 agent for the registered run 336 (month-end line, 2026-09-24).

Layer order, inner to outer (every piece imported read-only, none edited):
  330a_334 = 292t -> 298 -> 274 listen-first -> listener stack G b (313b/315/314b/316)
             -> 274 reply-first -> 334 sleep agenda                          (claude_e2e330_arms)
  -> 333d creative: 333c's request detector, replies generated the way 338 chat does (333, 333b, 333c =
                registered FAILs: thinking mode, then a pick rule that chose the shortest reply; VERIFY-333.md)
  -> think299b  think-then-answer with an exact calculator and a 3-of-5 vote; registered FAIL on its bar,
                joined for safety (it says "I'm not sure" instead of guessing; it routes 0/194 DEV turns)
  -> 338b       open conversation from the base 1B when the agent gives up, with the person-question
                guard (338 = registered FAIL on grammar and helpfulness, 0 invented facts; 338b = its fix)
  -> vary330c   wording variety for two fixed lines (338b's honest "not sure" and lis-314's "Okay."), same meaning
  -> nb-323     durable hash-chained turn log, installed LAST so it records the final reply (replies unchanged)
Not joined: 339 style preferences (registered FAIL, 2/20 false saves) and the own-line mouth (own-M1v has
no verdict yet; if it passes, a 330d adds it and 336b uses it).

One 1B (a Gen333b) is loaded once and shared by 333, think299b and 338b. The lis-301 reader
is the only other model.

  python -B scripts/claude_twinb_wrap.py scripts/claude_e2e336_run.py --bank BANK \
      --arm claude_e2e330c:build_330c --name P --model <lis-301 dir> --gen-model <MiniCPM5-1B dir> --out OUT
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

TURNLOG330C = "turns323.jsonl"
_G338B: dict = {}


def build_330c(state_dir, args):
    import claude_chat338_agent as C38
    import claude_chat338b_agent as C38B
    import claude_cre333b_agent as C333B
    import claude_cre333d_agent as C333D
    import claude_e2e330_arms as A
    import claude_nb323_turnlog as NB
    import claude_think299b_agent as T299B
    import claude_vary330c as VARY
    if args.gen_model not in A._GEN:
        A._GEN[args.gen_model] = C333B.Gen333b(args.gen_model)
    one_b = A._GEN[args.gen_model]
    if args.gen_model not in _G338B:
        _G338B[args.gen_model] = C38.Gen338(share=one_b)
    loop = A.build_330a_334(state_dir, args)
    C333D.install_creative333d(loop, _G338B[args.gen_model])
    T299B.install_think299b(loop, one_b)
    C38B.install_chat338b(loop, _G338B[args.gen_model])
    VARY.install_vary330c(loop)
    NB.install_turnlog323(loop, str(Path(state_dir) / TURNLOG330C))
    loop.layers330c = ["330a_334", "cre333d", "think299b", "chat338b", "vary330c", "turnlog323"]
    return loop
