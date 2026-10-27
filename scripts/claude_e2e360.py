#!/usr/bin/env python3
"""gram-360 arm: 330c (scripts/claude_e2e330c.py, unchanged) with one change, the gram-360 slot finisher.

Layer order is 330c's, with two additions:
  330a_334 -> record_inner360 (remembers the rule agent's own parts; changes nothing)
  -> cre333d -> think299b -> chat338b -> vary330c -> gram360 (renders slots in rule-agent parts only) -> nb-323
build_330c itself is not edited; this file repeats its body with the two installs added.

  python -B scripts/claude_twinb_wrap.py scripts/claude_e2e336_run.py --bank BANK \
      --arm claude_e2e360:build_360 --name P360 --model <lis-301 dir> --gen-model <MiniCPM5-1B dir> --out OUT
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def build_360(state_dir, args):
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
    loop = A.build_330a_334(state_dir, args)
    GR.record_inner360(loop)
    C333D.install_creative333d(loop, E330C._G338B[args.gen_model])
    T299B.install_think299b(loop, one_b)
    C38B.install_chat338b(loop, E330C._G338B[args.gen_model])
    VARY.install_vary330c(loop)
    GR.install_gram360(loop)
    NB.install_turnlog323(loop, str(Path(state_dir) / E330C.TURNLOG330C))
    loop.layers330c = ["330a_334", "rec360", "cre333d", "think299b", "chat338b", "vary330c", "gram360",
                       "turnlog323"]
    return loop
