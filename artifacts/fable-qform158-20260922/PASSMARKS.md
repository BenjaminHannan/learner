# Exp 158 PASSMARKS — question-surface normalisation (sealed BEFORE any registered run)

Base: loop150 (scripts/fable_loop150_agent.py,
artifacts/fable-fix150-20260922/loop150-config.json; loop150 = loop129b +
139b value guard + 150 subject guard, imported read-only, no file edited).
Exp-152 red team (both targets byte-identical) found N5
(`what's tess's city?` / `tell me tess's city` refused although the fact
is known) and N7 (`Who is Rosa's mother's city???` ->
`I don't know Vera's city??.`). Exp 151 (separate, running) owns bare
`What is X's R` with NO `?`; this experiment never touches that case.

Responsible code (read-only): scripts/fable_agent_loop.py:94
(`_QUESTION` accepts `who|what|where + is|are` only and its trailing
`[?.]?` strips exactly one mark); scripts/fable_loop121_agent.py:175
(`?`-final turns take the question side, all else the teach path);
scripts/fable_loop113b_agent.py:70 (`?` turns run the N-hop router with
loop102-chain fallback).

THE ONE CHANGE (scripts/fable_fix158_qform.py, `Qform158Mixin`;
thin loop158 = loop150 + mixin in scripts/fable_loop158_agent.py with
--daemon entry incl. idle_seconds): question-surface normalisation
BEFORE the question parser at the outermost ears hear(), in order:
(1) `tell me|show me|give me X's R` -> `What is X's R?` and
`tell me who/what ...` -> the bare question (fires only when the
remainder starts with a question word/auxiliary or holds a possessive
`'s`; `tell me more` / `show me the money` do not fire);
(2) leading `what's|who's|where's|when's` (straight or curly) ->
`what|who|where|when is` (leading position only);
(3) trailing `[?.!]+` collapsed to one `?`.
The rewrite is RETURNED only when the candidate differs, the original
holds `?`/`!` OR rule 1 fired (bare statements, `.`-teaches and 151's
no-`?` territory never eligible), NO interior `?`/`!` precedes the
terminal run (glued multi-sentence turns such as red-team
`Who is Mira's city? also Mira's pet is a cat.` are never spliced into
one garbage ask), and the candidate through the UNCHANGED loop yields an
`ask` action. Otherwise the original turn is heard untouched, so a
rewrite can only turn a clarify-miss into the canonical-question reply.
Question actions never write: 0 new writes by construction.

Sealed lists: none (no word lists; three closed mechanical rules above).

Sealed inputs:
- Q1 probe: artifacts/fable-qform158-20260922/cases158.json (59 cases:
  43 pairs P01-P43 each with teaches + variant + canonical
  `What/Who/Where is X's R?` + want; 16 non-questions N01-N16).
- loop158-config.json (loop150 config + 2 renamed plug strings).
- G1 reference: sealed loop150 bench rows
  (artifacts/fable-fix150-20260922/fable_bench150_loop150_*_rows.jsonl).
- G2 reference: sealed loop150 marks123 run
  (artifacts/fable-fix150-20260922/marks150).
- G3/Q2 reference: sealed 152 sessions dump + T-T turns
  (artifacts/fable-session152-20260922/sessions152.json,
  turns152-T-T-*.json).
- Bench splits + scorer v2, marks123 suites, session runner: sealed in
  their own exps, read-only, used by import only.

## Marks (integer counts, every seed/case reported, never averaged)

- Q1 (scripts/fable_fix158_probe.py): 43/43 pairs byte-identical replies
  (variant == canonical, want contained, 0 FACT writes on both sides);
  16/16 non-questions byte-identical replies to loop150 with identical
  FACT deltas and 0 writes on loop158; 0 writes from any question.
- Q2/G3 (scripts/fable_fix158_session.py, 6 sessions x 30 turns through
  Loop158Daemon): every reply byte-identical to the sealed T-T run
  EXCEPT exactly S5-robustness n5 (`what's tess's city?` ->
  `tess's city is Omaha.`, UNHELPFUL->OK), n6 (`tell me tess's city` ->
  `tess's city is Omaha.`, UNHELPFUL->OK), n9
  (`Who is Rosa's mother's city???` -> `Rosa's mother's city is lima.`,
  UNHELPFUL->OK); 0 new WRONG verdicts; 0 new FACT writes (all three
  moves write 0).
- G1 (scripts/fable_fix158_bench.py, edit200 + old_s2fresh_4hop +
  new_121_4hop): per-item verdicts AND replies identical to the sealed
  loop150 rows, 0 verdict moves, 0 reply moves, 0 new wrong.
- G2 (scripts/fable_marks123_all.py --agent
  scripts/fable_loop158_agent.py --config
  artifacts/fable-qform158-20260922/loop158-config.json --out
  artifacts/fable-qform158-20260922/marks158 --workers 4): every suite
  per-case identical to marks150 EXCEPT exactly rt81 D_q_vs_s-03
  (`Tell me Mira's city.` now answered `Mira's city is Lisbon.`,
  OK->UNCLEAR: suite `must` = `another way` missing, taught_delta 0,
  not BUG, no underscore leak); sleep SKIP verdict identical (reason
  text names fable_loop158_agent.py, as in 139b/150); Q4 0 leaks.
- G4: each registered run (probe, bench, marks123, session) < 25 min
  wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
  --no-project --python 3.12 --with torch --with numpy python -B ...);
  daemon wrapper takes idle_seconds.

## Pre-seal evidence (dev only, NOT registered runs; no registered
## runner ran before sealing)

- Pure-function scan of 5524 sealed inputs (bench teaches+questions,
  sessions152 turns, redteam98/p4/rt110/rt81 inputs, redteam136 JSONs):
  30 eligible candidates; base ask-checks on every unique one: only the
  S5 n5/n6/n9 shapes and rt81 `Tell me Mira's city.` yield `ask`
  (predicted moves); bench 098/158 `B.C.?`/`Beatles!?` candidates
  clarify on base (gate blocks, identical); all teaches/smalltalk
  multi-mark candidates clarify on base (identical); rt110 S2/S4/S6
  glued turns return None via the interior-mark guard (byte-identical;
  S2's garbage `city?_also_mira` reply pre-exists on loop150).
- Dev pair matrix (scripts/scratchpad/dev158_calib.py): all 43 sealed
  pair shapes + 16 non-question shapes behave as predicted (pairs
  answer-or-abstain identically with 0 writes; non-questions identical
  to loop150 with 0 writes).
- `When's Tess's city?` clarifies on both loops (no `when` question
  path in the base); `when's` mapping implemented per spec but excluded
  from the probe pairs.

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence.

## Registered reproduce (run from worktree root, after sealing)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix158_probe.py --out artifacts/fable-qform158-20260922/probe158-loop158.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix158_session.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix158_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop158_agent.py --config artifacts/fable-qform158-20260922/loop158-config.json --out artifacts/fable-qform158-20260922/marks158 --workers 4
