#!/usr/bin/env python3
"""0.2c: the joined agent with every fix that passed its own registered test by the cutoff (month-end line,
2026-09-26; marks artifacts/claude-e2e02c-20260926/PASSMARKS-02c.md). New file only.

The switches below are set once, at the 07:30 UTC cutoff, from the verified verdicts (the PASSMARKS addendum names
each), and then the code is sealed. A switch is on only when its fix's own registered test is a PASS.
  MEM02C     ep-382 episodic memory, k = 20 (382b)
  ROUTE02C   route383: plain questions go to the 1B (383, with its 512-token / 350-word route cap)
  SLEEP02C   the shared 1B carries the copy-practice adapter (scripts/claude_sleep02c.py); with
             SLEEP02C_ADAPTER=<adapter02c.pt> the agent starts with the weights its nights trained
  READER02C  "r319" = the lis-319 history reader at 0.995 (claude_lis319_arms, registered PASS), "r319c" = the
             same at 0.98 (only if lis-319c passes), "" = 0.1's reader; with r319/r319c, --model is the lis-319
             merged reader (sha256 e688e1b2...6a76), not lis-301
Layer order as claude_e2e383._build: 330a_334 -> rec360 -> cre333d -> think299b -> chat338b -> [answer382] ->
[route383] -> vary330c -> gram360 -> [heard382] -> turnlog323.
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

MEM02C = 20        # 0 = off
ROUTE02C = True
SLEEP02C = True
READER02C = "r319"


def build_02c(state_dir, args):
    import importlib
    import claude_chat338_agent as C38
    import claude_chat338b_agent as C38B
    import claude_cre333b_agent as C333B
    import claude_cre333d_agent as C333D
    import claude_e2e330_arms as A
    import claude_e2e330c as E330C
    import claude_e2e382 as E382
    import claude_e2e383 as E383
    import claude_gram360 as GR
    import claude_nb323_turnlog as NB
    import claude_sleep02c as SL
    import claude_think299b_agent as T299B
    import claude_vary330c as VARY
    if args.gen_model not in A._GEN:
        A._GEN[args.gen_model] = C333B.Gen333b(args.gen_model)
    one_b = A._GEN[args.gen_model]
    if SLEEP02C:
        SL.install_sleep02c(one_b)                    # once per process; loads SLEEP02C_ADAPTER if set
    if args.gen_model not in E330C._G338B:
        E330C._G338B[args.gen_model] = C38.Gen338(share=one_b)
    gen = E330C._G338B[args.gen_model]
    store = importlib.import_module(E382.STORE382).MemoryStore(state_dir) if MEM02C else None
    if READER02C:
        import claude_lis319_arms as L319
        loop = {"r319": L319.build_330a_334_r319, "r319c": L319.build_330a_334_r319c}[READER02C](state_dir, args)
    else:
        loop = A.build_330a_334(state_dir, args)
    GR.record_inner360(loop)
    C333D.install_creative333d(loop, gen)
    T299B.install_think299b(loop, one_b)
    C38B.install_chat338b(loop, gen)
    layers = ["330a_334", "rec360", "cre333d", "think299b", "chat338b"]
    if store is not None:
        E382.install_answer382(loop, gen, store, k=MEM02C)
        layers.append("answer382")
    if ROUTE02C:
        E383.install_route383(loop, C38.Gen338(share=one_b, max_new=E383.MAXNEW383))
        layers.append("route383")
    VARY.install_vary330c(loop)
    GR.install_gram360(loop)
    layers += ["vary330c", "gram360"]
    if store is not None:
        E382.install_heard382(loop, store)
        loop.store382 = store
        layers.append("heard382")
    NB.install_turnlog323(loop, str(Path(state_dir) / E330C.TURNLOG330C))
    loop.layers330c = layers + ["turnlog323"]
    loop.sleep02c = getattr(one_b, "sleep02c_loaded", None)
    return loop
