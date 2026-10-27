# Exp 164b PASSMARKS — FRESH REGISTRATION of the 164 "about" feature on base loop138h (sealed BEFORE any registered run)

Background: exp 164 (`scripts/fable_fix164_about.py`, read-only about-stage on
loop150) is a registered FAIL because its sealed files were edited after the
seal; the director's probe showed the feature works, but it was never
registered cleanly and never merged. On 138h, "Tell me about Kim." and "What
do you know about Kim?" still reply the long R-CLARIFY verbatim even when Kim
has stored facts (calibrated 2026-09-22: two Kim teaches then both asks reply
R-CLARIFY; users ask this all the time).

Agent: `scripts/fable_loop164b_agent.py` (Loop164bEars / Loop164bAgentLoop /
Loop164bDaemon, build_agent164b, DEFAULT_CONFIG164B). Imports/subclasses the
frozen 138h stack read-only; no 138h or 164 file edited. Ears: About164bMixin
checked FIRST, then the full 138h chain via super(). Act path unchanged
(about-turns are clarify actions: 0 writes). _listening_tick: 138h tick
verbatim (173/166 rendering + 166c display) plus an idempotent raw-USER safety
net on about-claimed turns only (normally a no-op).
Config: `artifacts/fable-about164b-20260922/loop164b-config.json`.
Design: `design/v3/30-modes/164b-about-muse.md` (written after the runs).
Drivers (new, sealed with the agent): `scripts/fable_fix164b_probe.py` (A1),
`scripts/fable_fix164b_suites.py` (A2 + bench), `scripts/fable_fix164b_marksdiff.py` (A3).
Ledger P164b.1–P164b.7 appended pre-run. Sealed files hashed to
SEAL.sha256.txt: this file, the agent file, the config, cases164b.json, the 3
drivers.

## THE ONE CHANGE (port of the current 164 about-stage, read-only, onto 138h)

P0–P4 full-turn shapes (case-insensitive, collapsed whitespace, optional
trailing `./?/!`), X validation (charset `[A-Za-z0-9 \-']`, no possessive
`'s` chains, no whole-word `and`/`or` compounds, no pronouns), read of every
active taught fact with X as subject (fact_id order) then every active taught
fact with X as value (fact_id order), max 8 sentences then `"and N more."`,
unknown X -> the existing contract unknown-entity reply
(`"I don't know anyone called {X}."`, X as typed), known-X-zero-facts /
AMBIGUOUS / internal error -> delegate byte-identical, clarify-only (0
writes, 0 web, 0 inference). Rule body reused read-only from
`scripts/fable_fix164_about.py` (`match_about`, `fact_sentences`,
`summary_reply`, `unknown_reply`); 164 files never edited.

Two disclosed deltas vs 164 (required by the 138h base, part of the seal):
(a) 138h reply templates for fact sentences: USER-subject facts render
`"Your sister is Ada."` (138h me-rendering, stored casing), USER-as-value
renders `"you"` (138h last resort); all other sentences are 164's `"Tom's
boss is Ann."` verbatim.
(b) `"me"` as X: P1–P4 shapes with X == "me" (any case) read the reserved
USER entity ("What do you know about me?" -> the user's facts). Bare "me" is
the only pronoun claimed; reflexives and all other pronouns still delegate
exactly like 164. Zero USER facts (or no USER entity yet) delegates to the
base chain: no new strings invented.

## Sealed inputs

- A1 probe: `artifacts/fable-about164b-20260922/cases164b.json` (50
  dialogues, frozen pre-pilot, fictional names only: A 25 about-X incl. P1–P4
  shapes, all-caps/lowercase/no-punct variants, value-side-only, subject-then-
  value order, 8-exact, 10 with `and 2 more`, literal value as X, retraction
  absent, overwrite absent, word-like name Will, 3 USER-fact cases rendering
  Your/you, USER-fact-on-value-side; B 8 unknown-X incl. cooking x2, as-typed
  ZELDA, prefix Jona, my-sister phrase; C 5 bare summary incl. empty notebook
  and USER-fact counting; D 12 near-misses: reflexives, pronoun, compound,
  possessive chain, yes/no frame, story frame, statement, teaches containing
  "about" x2, trailing extra text, me-compound).
- A2 reference: sealed loop138h rows (`artifacts/fable-agent138h-20260922/`:
  redteam136-loop138h.json, probe150-loop138h.json, f1-loop138h.json,
  probe139b-loop138h.json, redteam143-loop138h.json, sessions152-loop138h.json).
- A3 reference: sealed loop138h marks (`artifacts/fable-agent138h-20260922/marks138h`)
  via stock `scripts/fable_marks123_all.py --agent
  scripts/fable_loop164b_agent.py --config
  artifacts/fable-about164b-20260922/loop164b-config.json --out
  artifacts/fable-about164b-20260922/marks164b --workers 4`, diffed by
  `scripts/fable_fix164b_marksdiff.py` (volatile `seconds` exempt; sleep SKIP
  reason exempt but must name the new agent file, verdict identical; log/reason
  transport text is diag-only, never a mark move).
- Bench reference: sealed loop138h bench rows (4 splits) via the base agent's
  driver (`scripts/fable_bench121_run.py` run_item/summarize, read-only).
- Benches, suites, scorer v2, sessions: sealed in their own exps, read-only.

## Marks (integer counts, every seed/case reported, never averaged)

- A1 (`scripts/fable_fix164b_probe.py`): all 50 dialogues OK — 38 must-cases
  exact (frozen reply literal + 0 FACT-event delta on every about/summary turn
  + frozen triple set), 12 near-misses byte-identical loop164b vs loop138h
  (replies + FACT writes). 0 writes on every about-turn.
- A2 (`scripts/fable_fix164b_suites.py` --only junk,rt143,sessions): every
  suite verdict AND reply byte-identical to the sealed 138h rows
  (redteam136 145, cases150 57, f1 46, cases139b 101, redteam143 124,
  sessions152 180 turns); 0 new WRONG / WRONG-WRITE / junk writes, 0 new
  writes anywhere. Predicted move set: EMPTY (listed here before the seal).
- A3 (marksdiff): every marks123 suite per-case identical to sealed marks138h
  after the stated exemptions (11 reports); suite FAILs inherited
  byte-identical (p3 l5z1, p4-1-nonpass, rt81 14 unclear + 1 bug). Predicted
  move set: EMPTY (listed here before the seal).
- Bench (suites driver --only bench, base driver): 4 splits x 200 items,
  0 verdict moves, 0 reply moves, 0 new wrong vs sealed 138h rows. Predicted
  move set: EMPTY (listed here before the seal).
- G4: every registered run < 1500 s wall-clock (< 25 min) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrappers
  take idle_seconds=3600.0; heavy suites one at a time.

## Pre-seal evidence (dev only, NOT registered runs)

- Pilot A1 50/50 OK (4.1 s) on the final code.
- Pilot junk: redteam136 136 OK/6 WRONG-WRITE/3 MISSED, cases150 57/57,
  f1 46/46, cases139b 101/101 — 0 moves vs 138h everywhere (13.0 s).
- Pilot rt143: 107 OK / 10 WRONG-ANSWER / 7 MISSED — 0 moves vs 138h.
- Pilot sessions152: 0 reply/verdict moves, 0 new writes vs 138h.
- Pilot bench 4x200: 0 verdict moves, 0 reply moves, 0 new wrong (107.9 s).
- Pilot marks123 + marksdiff: TOTAL case-moves=0 (only 1 diag-only log race
  in rt110 U4; sleep reason names the new agent; summary identical modulo
  agent+seconds).
- Pre-seal literal scan: no about/summary full-turn shape (incl. the about-me
  variant) appears in any bench turn text (6175), session152 turn (180), or
  suite case literal (473) outside this experiment's own files — hence the
  EMPTY move predictions.
- Base calibration (loop138h only): "Tell me about Kim." / "What do you know
  about Kim?" with stored Kim facts -> long R-CLARIFY verbatim.

## Predictions (ledger P164b.1–P164b.7 appended BEFORE any registered run)

- P164b.1: A1 probe 50/50 OK; 0 writes on every about/summary turn. 0.85.
- P164b.2: A2 junk + rt143 + sessions: 0 moves, 0 new WRONG/WRONG-WRITE, 0 new writes vs sealed 138h rows. 0.80.
- P164b.3: bench 4 splits x 200: 0 verdict moves, 0 reply moves, 0 new wrong. 0.85.
- P164b.4: A3 marks123 per-case identical to sealed marks138h after exemptions; 0 case-moves. 0.70.
- P164b.5: every registered run < 1500 s wall-clock Mac CPU, OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; daemon wrappers take idle_seconds=3600.0. 0.95.
- P164b.6: no post-seal edits to sealed files (shasum -c SEAL.sha256.txt all OK post-run); any edit reported with affected marks re-run in the open. 0.95.
- P164b.7: frozen suites + marks123 + bench: 0 moves except rows listed here — the listed set is EMPTY. 0.80.

A registered FAIL is recorded as FAIL with one diagnosis note, never re-run
into a pass. Claims never exceed evidence.

## Registered reproduce (run from worktree root, after sealing, one suite at a time)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix164b_probe.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix164b_suites.py --only junk
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix164b_suites.py --only rt143
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix164b_suites.py --only sessions
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix164b_suites.py --only bench
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop164b_agent.py --config artifacts/fable-about164b-20260922/loop164b-config.json --out artifacts/fable-about164b-20260922/marks164b --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix164b_marksdiff.py
