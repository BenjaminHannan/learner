# Exp 138b PASSMARKS — "the stack" (loop138 + tonight's fixes), sealed before run

Agent: `scripts/fable_loop138b_agent.py` (Loop138bEars / Loop138bAgentLoop /
Loop138bMouth / Loop138bDaemon, build_agent138b, DEFAULT_CONFIG138B).
Config: `artifacts/fable-agent138b-20260922/loop138b-config.json`.
Seeded in this file before any registered run; hashed to SEAL.sha256.txt
together with the config. Ledger P138b.1–P138b.8 appended pre-run.

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`.
Every seed/case reported, never averaged. A registered FAIL stays FAIL.
No code edit after the seal except as reported in RESULTS.md (affected
marks re-run in the open).

## In / out of this build

IN (all with PASS RESULTS.md, ported as mixins in brief order, L2 frozen):
135 officeholder guard, 137 multi-word possessive subjects, 139b value
guard (rule + UN table), 140 tail cleaner, 144 two-"of" names, 150 subject
guard, 149 whole-word names, 132 relative-clause rewriter (149-qrewrite
shape: rewriter + whole-word match), 151 no-"?" twin, 148+148b
negation/time screen as abstentions (148b status-preserving record path),
sleep145 in place of sleep131 in L3, 141 settle gate + atomic-write
client rule (tmp + rename; daemon serves settled *.txt only, skips
tmp/dot files). L2 = loop138's turn() inherited verbatim (127 router +
Self99 live answers + decline rule); no self-layer file touched.
OUT: 113e fallback gate (registered FAIL on its own bars E2/L5-Z1/L5-Z2;
replacing the frozen 113c gate to fix the single A2-174 item risks new
wrongs on unseen phrasing) and 142 speed index (needs an
IndexedLoopNotebook lower-layer swap, barred by the brief); B7 reports
wall-clock ask times instead.

## Composition vetoes (part of the seal, by design)

- A 137-upgraded teach is additionally vetoed by the 139b value screen
  and the 150 subject screen (else a compound value / polluted subject
  would bypass the stacked guards through the upgrade path).
- A 144-upgraded teach is additionally vetoed by the 139b value screen
  and the 150 subject screen (144's screen is narrower than 139b's).
- The 148b screen runs before the 132 rewriter; a rewritten question is
  re-screened (second pass re-enters the screened path), so a neg/time
  question is never answered around.

## Interpretation notes (part of the seal)

- L2 rule unchanged from loop138: notebook answers always win;
  notebook-missed turns go to the self path (non-DECLINE: routed intent's
  canonical answer; DECLINE: HONEST_DECLINE + suffix). No content on DECLINE.
- 148b adds one status: UNSUPPORTED_QUESTION (well-formed question whose
  negation/time qualifier the notebook cannot represent; refused before
  answering; never a confident answer, never a write). Never-taught
  relations keep the reasoner's own MISSING_FACT.
- The 135 guard turns officeholder-shaped non-office teaches into the
  base clarify path; under the frozen L2 rule a declined clarify is
  served as the loop138 decline (still no write).

## Marks

- B1: `… python -B scripts/fable_marks123_all.py --agent
  scripts/fable_loop138b_agent.py --config
  artifacts/fable-agent138b-20260922/loop138b-config.json --out
  artifacts/fable-agent138b-20260922/marks138b --workers 4`.
  Bar: every suite per-case verdict EQUAL to sealed loop138 marks138
  EXCEPT exactly two predicted per-case moves: p3 L5-Z1 turns 42/43
  ("What is Mira's city in 2019?", "What is Jon's job in 2019?")
  observe UNSUPPORTED_QUESTION where loop138 observes OK (the sealed
  expectation encodes the qualifier-blind answer; 148b R3 precedent).
  Verdicts on L5-Z2's 37 never-items stay MISSING_FACT (identical).
  Bench-edit200/s2fresh reply texts may differ ONLY on never-taught
  items (verdicts identical; 148b deviation precedent). rt81: 0 wrong
  writes. Sleep SKIP; soak 0/0/0.
- B2: `artifacts/fable-agent138b-20260922/fable_loop138b_bench121.py
  --agent loop138b` (bench121-new + bench103-old-fresh + bench65-edit200
  + bench132-4hop, scorer v2, class swapped). Bar: 0 new wrong vs
  loop138 rows on every split (bench132 baseline = fresh loop138 rows
  from the same driver, `--agent loop138 --only bench132_4hop`);
  predicted moves: bench121-new 069 wrong->correct (144 Canberra fix);
  every other correct/abstain move listed item by item, none
  abstain->wrong.
- B3: `… python -B scripts/fable_loop138b_junk.py` (redteam136 145
  cases; cases150 57; f1 46; cases139b 101; each case fresh
  in-process loop138b, own sealed judge). Bar: redteam136 keeps all 5
  tail fixes exact (C117 C118 C119 C126 C140) and all 7 and-focus
  no-writes with 0 new wrong writes; cases150 57/57 verdict- and
  reply-identical to probe150-loop150.json; f1 26/26 must-write exact
  with the single known t14 subject-side write (144 diagnosis, also on
  loop129b) and 19/20 two-fact; cases139b 101/101 OK.
- B4: `… fable_loop138b_redteam143.py` (124 cases, 138b vs 138) and
  `… fable_loop138b_sessions.py` (sessions152.json, 138b vs 138, atomic
  inbox writes). Bar: 0 new WRONG vs loop138 on both; every move listed.
- B5: `… fable_loop138b_sleepdrive.py --only e116|z104` (loop138's A4
  Z1-Z5 + E1-E4 checks, daemon swapped to Loop138bDaemon). Bar:
  installs happen, 0 wrong installs, E2/E3/E4 answer with source taught.
- B6: `artifacts/fable-agent138b-20260922/fable_loop138b_soak.py` (G2:
  6000 turns seed 931, 10 aimed mid-turn kill-9). Bar: 0 duplicate /
  0 lost / 0 wrong replies.
- B7: `… fable_loop138b_speed.py` (15k-fact notebook taught once,
  copied, both arms time 25 asks). Bar: both p50 ask times reported.
- B8: every registered run above < 25 min wall-clock Mac CPU
  (OMP_NUM_THREADS=1; parallel processes allowed).

## Frozen references (read-only, never rewritten)

- Sealed loop138 rows: artifacts/fable-agent138-20260922/ (SEAL.sha256.txt).
- Sealed loop134 rows: artifacts/fable-loop134-20260922/ (SEAL.sha256.txt).
- Junk cases + seals: artifacts/fable-redteam136-20260922/,
  fable-fix139b-20260922/ (SEAL.sha256.txt), fable-fix150-20260922/
  (SEAL.sha256.txt), fable-fix144-20260922/ (SEAL.sha256.txt).
- 143 cases: artifacts/fable-redteam143-20260922/;
  sessions: artifacts/fable-session152-20260922/sessions152.json
  (via scripts/fable_session152_run.py + scripts/fable_session152_sessions.py).
- Router/bank/deltas: artifacts/fable-self127-20260922/PASSMARKS.md.
