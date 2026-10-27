# Exp 138f PASSMARKS — stack clean (138d minus 155, 154, 138c), sealed before run

Agent: `scripts/fable_loop138f_agent.py` (Loop138fEars / Loop138fAgentLoop /
Reasoner138d reused / Loop138fDaemon, build_agent138f, DEFAULT_CONFIG138F).
Config: `artifacts/fable-agent138f-20260922/loop138f-config.json`.
Design: `design/v3/30-modes/138f-stack-clean-muse.md` (Step-1 attribution
table + removal set {155, 154, 138c} + per-piece capability/cost).
Step-1 evidence (diagnosis, pre-seal):
`artifacts/fable-agent138f-20260922/attribution-138f.json`.
Seeded in this file before any registered run; hashed to SEAL.sha256.txt
together with the config, the agent file and the five
`scripts/fable_fix138f_*.py` drivers. Ledger P138f.1–P138f.7 appended
pre-run.

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`.
Every seed/case reported, never averaged. A registered FAIL stays FAIL
with one diagnosis note. No rule changes after the seal. Soak/rt110 flakes
under heavy load are a known mailbox race: that suite may be re-run ONCE in
the open and both reported. Open pilot runs (same drivers, same paths)
were used to enumerate the predicted moves below; the registered runs
re-run everything after the seal.

## In / out of this build

IN (8, ported read-only from 138d): 142 speed index (IndexedLoopNotebook
swap + FastReasoner142 + patch_chain142 + patch_loop121_teach +
_patch_relation; the FastQuestionMixin142 "?" reroute stays OUT as in
138d), 146d doubt, 153 reverse questions, 156b small talk, 157 fillers,
158 question forms, 159 hop fallback, 150b clause guard.
OUT (3, by Step-1 attribution): 155 inverted frames (6 wrong writes),
154 yes/no (1 wrong answer), 138c serving rule (reply-text cause on 5 of
the 7 cases; no wrong of its own).

## Marks

- M1 (`scripts/fable_fix138f_m1.py`, fresh in-process loops): each
  REMAINING piece at its own 138d bar — 142: 500-turn reply-identity vs
  138b, 500/500. 146d: H2 21/21 must-pass (H13 ok, H17/H18 fail exactly
  as on 146c, reported only). 153: 50/50, 0 question-turn writes. 156b:
  T1 116/116 + T2 68/68 with N02 = base-identical no-write (155
  interaction gone by design). 157: 60/60. 158: 59/59. 159: 48/48,
  0 writes. 150b: 49/49.
- M4 (`scripts/fable_fix138f_junk.py`, `…_rt143.py`, `…_sessions.py`):
  the 7 cases byte-identical (verdict + reply + stored) to loop138b:
  C124/C127/C129/C142/C10/C21/M3. 0 new WRONG / WRONG-WRITE / junk
  writes vs loop138b on redteam136 (0 verdict moves; 135 OK / 7 WW /
  3 MISSED as on 138b), cases150 (0 moves), f1 (only f144-t14
  WRONG-WRITE→OK, inherited 138d improvement), cases139b (0 moves),
  redteam143 (only S4 WRONG-ANSWER→OK abstain, inherited 138d
  improvement), sessions152 (exactly 138d's 36-move set: 165 OK /
  15 UNHELPFUL / 0 WRONG, 0 down-moves, the same 3 correct S2
  filler-teach writes n=4/6/12; enumerated: S1-family10 #0/24/27/29,
  S2-casual-friends #0/4/6/7/12/13/14/15/20/25/28/29, S3 #20/27,
  S4-pets-identity #0/7/15/18/24/27/28 (incl. #7/#27 WRONG→OK),
  S5-robustness #0/5/6/9/15/20/29, S6 #0/22/26/29 — all UNHELPFUL→OK
  except the two noted WRONG→OK).
- G1 (`scripts/fable_fix138f_bench.py`): bench121 new + old_s2fresh +
  Fable-Edit 200 + bench132 per-item vs sealed 138b rows: 0 new wrong;
  the only move is bench132-152 wrong→abstain (inherited 138d listing).
- G2 (`scripts/fable_marks123_all.py --agent
  scripts/fable_loop138f_agent.py --config
  artifacts/fable-agent138f-20260922/loop138f-config.json --out
  artifacts/fable-agent138f-20260922/marks138f --workers 4`): every suite
  per-case vs `artifacts/fable-agent138d-20260922/marks138d` —
  verdict-identical EXCEPT: p3 l5z1 turns 49 + 58 observed CLARIFY with
  status_match true (154-off revert of the 138d honest replies;
  status_match 58/60); rt81 D_q_vs_s-04 UNCLEAR→OK and I_edges-03
  OK→UNCLEAR (both byte-identical to the 138b rows); sleep SKIP reason
  naming fable_loop138f_agent.py. Reply-only (verdict-identical)
  EXCEPT: p2 agent_final B7/C1/C2/C5; rt110 one clarify log line in each
  of D2/N5/P1/P2/P3/P4/P5/P6/S4/S6/T1/T2/T3; rt81 observed in
  B_corrections-04/D_q_vs_s-05/F_pronoun-03/K_json-01/K_json-02/
  N_yesno-02/O_user-02/O_user-03/Q_quote-01/Q_quote-02; p3 l2
  loop96_reply in B_corrections-04/D_q_vs_s-04/D_q_vs_s-05/
  F_pronoun-03/I_edges-03/K_json-01/K_json-02/N_yesno-02/O_user-02/
  O_user-03/Q_quote-01/Q_quote-02 (changed flags true there);
  p3 l5z1 turns 49–60 ears_stage tags (no loop154-yesno prefix; turn 53
  loop151-qmark+none, turn 57 fake). All are 138c-revert clarify texts
  (short L134 clarify → long 138b clarify) or 154-off stage tags.
  p3 l5z1 FAIL (turns 42/43 stale expectation) and rt81 FAIL labels
  inherited from 138b/138d per-case identical. l6: pass true per seed
  with correct 200/200/200, wrong 0, unanswered 0, dupes 0, chain_ok
  true (replied_before_kill is timing-volatile: pilot 6/13/11,
  reported not predicted). rt110: OK→BUG 1 + still-BUG 5, 0 verdict
  moves vs 138b. 0 new WRONG anywhere vs 138b (rt81's only verdict move
  vs 138b is the inherited D_q_vs_s-03 OK→UNCLEAR).
- G4: every registered run < 1500 s wall-clock (pilot: m1 12 s, junk
  3 s, rt143 4 s, sessions 3 s, bench 40 s, marks wave 268 s).

## Predicted fault lines (part of the seal; FAILs stay FAIL)

- F1: any move beyond the enumerated sets (each itemised per-case).
- F2: any new WRONG / WRONG-WRITE / junk write vs loop138b on any suite.
- F3: mailbox-race flakes (empty-read clarifies, lost teaches) under
  parallel-agent load: recorded, re-run once in the open, both reported.
