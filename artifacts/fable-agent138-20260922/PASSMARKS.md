# Exp 138 PASSMARKS — "tonight's agent" (loop138 integration), sealed before run

Agent: `scripts/fable_loop138_agent.py` (Loop138Daemon / build_agent138 /
DEFAULT_CONFIG138). Config: `artifacts/fable-agent138-20260922/loop138-config.json`.
Seeded in this file before any registered run; hashed to SEAL.sha256.txt.

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`.
Every seed/case reported, never averaged. A registered FAIL stays FAIL.

## In / out of this build

IN (all verified tonight by the director): loop134 base (= loop121 teach +
loop117 F5/M5/underscore fixes); exp-129 punct mixin; exp-113c partial-frame
composer gate (ported onto the 134 question side); exp-127 self router
(route127 frozen + Self99Agent.answer_self over live loop138 state);
exp-131 live sleep (Sleep131Reasoner/Sleep131Daemon retrofit);
exp-108 exactly-once daemon (receipts + boot_reconcile).
OUT (no RESULTS.md saying PASS existed when layer 1 closed, 2026-09-22
~02:00 EDT): 113e fallback gate with inverse cues, 135 officeholder guard,
137 multi-word possessive subjects. No 113e/135/137 artifact folders exist.

## Interpretation notes (part of the seal)

- L2 rule: notebook answers always win. A notebook-missed turn (empty
  records, or every record a clarify containing "didn't understand";
  hearsay clarifies and MISSING_FACT abstains never route) is handled by
  the self path: non-DECLINE serves the self content answer; DECLINE serves
  the loop138 decline (frozen HONEST_DECLINE + " Could you say it another
  way?", zero names/numbers). No content is ever served on DECLINE.
- "Routed to the self answerer" (A3 bench count) = non-DECLINE content
  answers served. DECLINE servings are counted separately (abstain-shaped,
  verdict-neutral).
- A3 panel scoring: each answer is checked against the LIVE post-turn
  snapshot with fable_self100_runner.score (turn-count answers must match
  the state that produced them, not the pre-panel state).

## Marks

- A1: `scripts/fable_marks123_all.py --agent scripts/fable_loop138_agent.py
  --config artifacts/fable-agent138-20260922/loop138-config.json --out
  artifacts/fable-agent138-20260922/marks138 --workers 4`.
  Bars: q1 F5+M5 OK; q4 0 underscore leaks; P2 0 OK->BUG and 0 still-BUG
  (113c fixes B7/C2/C5/D8; G8 reply "Albany." single period); p3 L1-L6 all
  PASS; p4 0 false refusals 0 nonpass; rt110 62 run 0 harness-error,
  still-BUG exactly N6/R4/S3/S6 with F5+M5 BUG->OK; bench fable_edit_200
  n=200 wrong=0 and s2fresh_4hop n=200 (counts equal to loop134:
  150/50/0 and 157/43/0); rt81 0 wrong writes; sleep SKIP; soak 2000 turns
  3 kill-9 with 0 lost/0 wrong/0 doubled. Every other suite verdict-equal
  to sealed loop134 (artifacts/fable-loop134-20260922/marks134/).
- A2: `artifacts/fable-agent138-20260922/fable_loop138_bench121.py`
  (bench121-new + bench103-old-fresh + bench65-edit200 by import, class
  swapped). Bar: 0 new wrong vs sealed loop134 rows on every split;
  correct/abstain moves reported item by item (tolerance: <=3 moved items
  per split, all abstain<->correct or wrong->abstain, none abstain->wrong).
- A3: `artifacts/fable-agent138-20260922/fable_loop138_selfcheck.py`.
  Bar: blind panel through loop138 turn path <= 1 wrong; bench121-new
  200 questions 0 content-routed to the self answerer.
- A4: `artifacts/fable-agent138-20260922/fable_loop138_sleepdrive.py`
  (D104.PY swap; e116 + z104). Bar: installs happen, 0 wrong installs,
  E2/E3/E4 answer Z01/Z02/Z03 with source taught (taught wins), all other
  sealed 116/104 verdicts unchanged.
- A5: `artifacts/fable-agent138-20260922/fable_loop138_soak.py` (G2:
  6000 turns seed 931, 10 aimed mid-turn kill-9). Bar: 0 duplicate /
  0 lost / 0 wrong replies.
- A6: every registered run above < 30 min wall-clock Mac CPU
  (OMP_NUM_THREADS=1; parallel processes allowed).

## Frozen dependency hashes (referenced, never rewritten)

- Router/bank/deltas: see artifacts/fable-self127-20260922/PASSMARKS.md
  (router 6b835c77…, bank 293d9b04…, deltas 8803034b…).
- Blind panel seal: artifacts/fable-self127panel-20260922/SEAL.sha256.txt.
- Sealed loop134 rows for A1/A2 diffs:
  artifacts/fable-loop134-20260922/ (SEAL.sha256.txt).
