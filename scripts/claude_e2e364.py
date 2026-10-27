#!/usr/bin/env python3
"""gram-364 arm: 330c with the fill-in finisher v2 (scripts/claude_gram364.py) where gram-360 had v1.

Layer order is build_360's (scripts/claude_e2e360.py): 330a_334 -> record_inner364 -> cre333d -> think299b
-> chat338b -> vary330c -> gram364 -> nb-323. build_330c and build_360 are not edited.

  GRAM360_LOG=RUN/gram364_parts.jsonl python -B scripts/claude_twinb_wrap.py scripts/claude_e2e336_run.py \
      --bank BANK --arm claude_e2e364:build_364 --name P364 --model <lis-301 dir> --gen-model <MiniCPM5-1B dir> --out RUN
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def build_364(state_dir, args):
    import claude_chat338_agent as C38
    import claude_chat338b_agent as C38B
    import claude_cre333b_agent as C333B
    import claude_cre333d_agent as C333D
    import claude_e2e330_arms as A
    import claude_e2e330c as E330C
    import claude_gram364 as GR
    import claude_nb323_turnlog as NB
    import claude_think299b_agent as T299B
    import claude_vary330c as VARY
    if args.gen_model not in A._GEN:
        A._GEN[args.gen_model] = C333B.Gen333b(args.gen_model)
    one_b = A._GEN[args.gen_model]
    if args.gen_model not in E330C._G338B:
        E330C._G338B[args.gen_model] = C38.Gen338(share=one_b)
    loop = A.build_330a_334(state_dir, args)
    GR.record_inner364(loop)
    C333D.install_creative333d(loop, E330C._G338B[args.gen_model])
    T299B.install_think299b(loop, one_b)
    C38B.install_chat338b(loop, E330C._G338B[args.gen_model])
    VARY.install_vary330c(loop)
    GR.install_gram364(loop)
    NB.install_turnlog323(loop, str(Path(state_dir) / E330C.TURNLOG330C))
    loop.layers330c = ["330a_334", "rec364", "cre333d", "think299b", "chat338b", "vary330c", "gram364",
                       "turnlog323"]
    return loop
