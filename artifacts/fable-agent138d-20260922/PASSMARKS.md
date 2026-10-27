# Exp 138d PASSMARKS — morning integration (138b + late fixes), sealed before run

Agent: `scripts/fable_loop138d_agent.py` (Loop138dEars / Loop138dAgentLoop /
Reasoner138d / Loop138dDaemon, build_agent138d, DEFAULT_CONFIG138D).
Config: `artifacts/fable-agent138d-20260922/loop138d-config.json`.
Design: `design/v3/30-modes/138d-stack-muse.md` (hook points file:line,
same-shape pairs with order + why, IN/OUT judgments).
Seeded in this file before any registered run; hashed to SEAL.sha256.txt
together with the config. Ledger P138d.1–P138d.7 appended pre-run.

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`.
Every seed/case reported, never averaged. A registered FAIL stays FAIL
with one diagnosis note. No rule changes after the seal. Soak/rt110 flakes
under heavy load are a known mailbox race: that suite may be re-run ONCE in
the open and both reported.

## In / out of this build

IN (each verified as a mixin on an older base; ported read-only):
142 speed index (IndexedLoopNotebook swap + FastReasoner142 +
patch_chain142 + patch_loop121_teach + _patch_relation; the
FastQuestionMixin142 "?" reroute is OUT, judged below), 138c serving rule
(self serves only grounded answers, else base reply verbatim), 146d doubt
(hearsay-exempt refused-correction doubt), 153 reverse questions, 154
yes/no, 155 inverted frames (x135 variant: officeholder never touched),
156b small talk, 157 fillers (one strip, base-first contract verbatim),
158 question forms, 159 hop through names (one fallback attempt on
untagged non-OK answers only), 150b clause-swallow guard.
OUT: FastQuestionMixin142 "?" reroute only -- it answers "?" turns without
calling the inner ears, bypassing 138b's sealed 148b neg/time screen AND
the 132 rewriter (57+54 bench fixes). Porting it changes two other pieces'
behaviour; honest OUT. M6 is expected to miss because of this (stated).

## Composition (part of the seal)

Ears outer→inner: Qform158 > Filler157 > Smalltalk156b > Doubt146b >
Subject150B > Inverted155 > Reverse153 > Loop138bEars (all super-first
cooperative; each rewrites only its sealed leftover shape). Loop _act:
Doubt146b record/clear > Subject150B > 138b guards. _listening_tick:
YesNo154Mixin. turn(): 138c rule (L134 turn on self = full 138d loop path;
serve self only on non-DECLINE + grounded, else base verbatim).
Reasoner138d: 148b tag logic over FastReasoner142 + one 159 fallback on
untagged non-OK (tagged asks never touch it). Sleep145 wraps reasoner +
ears (taught-first for word episodes only). Daemon: 141 settle + exactly-once.

## Marks

- M1 (per piece, `scripts/fable_loop138d_m1.py`, fresh in-process loops):
  142: 500-turn reply-identity vs 138b, 500/500. 138c: 4 probe cases
  (hi = sealed smalltalk greeting by construction, other 3 base-verbatim).
  146d: H2 24 dialogues -- the 21 that pass on 146c must pass (H13/H17/H18
  reported only; they fail on 146c itself for base reasons). 153: 50/50, 0
  question-turn writes. 154: 54/54 patterns, 0 wrong, 0 writes. 155x135:
  5/5 (office byte-identical). 156b: T1 116/116 + T2 68/68 under the
  unified bar (class reply / strip remainder / base preserved; N02 =
  loop155-identical polluted save, listed). 157: 60/60 (filler==bare where
  the base clarifies, else ==138b filler turn). 158: 59/59. 159: 48/48, 0
  writes. 150b: 49/49 (title-exempt = base preserved).
- M2 (`scripts/fable_loop138d_bench121.py`): bench121 new + old_s2fresh +
  Fable-Edit 200 + bench132 per-item vs sealed 138b rows: 0 new wrong,
  every move listed (wrong->correct allowed, e.g. via the 159 fallback).
- M3 (`scripts/fable_marks123_all.py --agent scripts/fable_loop138d_agent.py
  --config artifacts/fable-agent138d-20260922/loop138d-config.json --out
  artifacts/fable-agent138d-20260922/marks138d --workers 4`): every suite
  per-case vs `artifacts/fable-agent138b-20260922/marks138b`. Predicted
  moves only: rt110 S1 OK->BUG (138c by design: grounded count served),
  rt81 D_q_vs_s-04 OK->UNCLEAR + p3 l5z1 turns 49/58 (154 honest replies,
  inherited); everything else verdict- and reply-identical. Any other move
  is listed, any race flake re-run once in the open with both reported.
- M4 (`scripts/fable_loop138d_junk.py`, `..._redteam143.py`,
  `..._sessions.py`): redteam136 + cases150 + f1 + cases139b + redteam143 +
  sessions152 vs sealed 138b rows: 0 new WRONG, 0 new junk writes.
  Predicted improvements (listed, not new-wrong): sessions S4 turns 7/27
  WRONG->OK (159), S2 eight turns ->OK (157), S5 n5/n6/n9 ->OK (158).
- M5 (`scripts/fable_loop138d_sleepdrive.py --only z104`;
  `scripts/fable_loop138d_soak.py`): z104 (seeds 1-3 + Z4 + Z5) 3/3
  installs, 0 wrong installs, taught wins; kill-9 soak: 3000 turns
  (shorter than 138b's 6000, stated), seed 931, 10 aimed mid-turn kills,
  0 graceful stops: 0 duplicate / 0 lost / 0 wrong, exactly-once receipts.
- M6 (`scripts/fable_loop138d_speed2.py`): doorway-built 15k-fact notebook,
  copied dir, 25 asks/arm: 138d asks p50 < 50 ms (138b measured 4008 ms).
- M7: every registered run < 1500 s wall-clock.

## Predicted fault lines (part of the seal; FAILs stay FAIL)

- F1: M6 misses (composers still scan; index covers store+reasoner only).
- F2: M3/M4 moves beyond the predicted sets (each itemised per-case).
- F3: mailbox-race flakes (empty-read clarifies, lost teaches) under
  parallel-agent load: recorded, re-run once in the open, both reported.
