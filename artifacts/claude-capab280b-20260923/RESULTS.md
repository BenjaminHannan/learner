# Exp 280b — RESULTS: VOID on M1 (panel schema mismatch); M2 PASS

Registered M2 + probes ran once with the sealed code (`bash scripts/claude_280b_runall.sh
artifacts/claude-capab280b-20260923/run`, VERDICT PASS). Registered M1 ran once per the sealed
panel script and exited SCHEMA-MISMATCH code 3 before either arm ran a single dialog: no verdict,
VOID, not FAIL. No sealed file was changed after the seal (15/15 OK re-verified). No item text was
read at any point; only keys/counts/labels were inspected for this diagnosis.

## M1 — blind capabilpanel280b: VOID (no arm ran)

Panel file: `artifacts/claude-capabilpanel280b-20260923/panel.jsonl` (panel seal OK: panel.jsonl +
SPEC-COPY.md check out). Schema gate requires every row to carry dialog_id, turn_index, user_text.
Row 0 carries `user`, not `user_text`. All three sealed steps (280 arm, 280b arm, scorer) exited 3
with `SCHEMA-MISMATCH: row 0 missing field user_text` in 1 s total; no `panel-280.json` /
`panel-280b.json` was produced, so 0 of 50 rows ran on either arm and nothing was scored by hand.

Keys/counts/labels only (no text read):
- 50 rows, 45 dialogs (40 single-row, 5 two-row with turn_index starting at 0; scored turn = last row).
- Every row has dialog_id + turn_index + category + gold; the turn-text field on all 50 rows is `user`.
- Categories: general 25, specific 10, nearmiss 10, control 5 — exactly the spec's 25/10/10/5 split.
- The category labels in use (`specific` vs the scorer's `canyou` keyword) would have classified
  correctly by the scorer's text fallback; the field name is the sole blocker.

## M2 — frozen suites vs 280's saved rows: PASS (registered, once)

| check | 280b | 280 | verdict |
|---|---|---|---|
| sessions152 moves (reply-only, 0 write changes) | 0 | 0 | PASS |
| bench 4x200 moves | 0 | 0 | PASS |
| sessions152/bench GATE | clean | clean | PASS |
| rt136 direct field diffs (145 units) | 0 | — | PASS |
| rt136 vs-138j labels vs 280's | identical | — | PASS (16 inherited, same counts) |
| rt143_nogate moves (124 rows) | 0 | — | PASS |
| verifier probes vp (98) / vs (12) diffs | 0 / 0 | — | PASS |
| write changes anywhere | 0 | — | PASS |

Moves 280b vs 280: none. Misses: none. Abstain-ward flips: 0 (no 5x follow-ups needed).

## Dev + mock (pilot, with the sealed code)

- `devcases280b.json` (68 dialogs, builder's own wording, fictional names): general 28/28 replies
  byte-equal to sealed CAN280 on 280b (13 already CAN280 on 280, 13 moved); canyou 12/12, nearmiss
  12/12, control 10/10, ability sanity 6/6 byte-identical 280b vs 280; writes identical per family;
  0 question-write violations either arm.
- Mock panel (8 dialogs, exact registered schema incl. `user_text`): runner + scorer end to end on both
  arms: 3/3 generals canon, 0 canyou/nearmiss/control moves, 0 writes; broken-schema probe exits 3.
- Pre-seal pilot fix (disclosed, code sealed after): verifier probe B17 "What do you know about me?"
  over-fired the unordered what+do+you cue; cue ordered (what...you...do) before the seal; B17 0-diff
  in the registered run.

## Deviations

1. Panel schema: the brief's schema "(dialog_id, turn_index, last turn scored)" names no text field; the
   builder registered `user_text` (280's convention, proven on the mock) and the writer used `user`.
   Per the panel-schema contract this is VOID, not FAIL. No re-seal, no hand scoring.
2. PUSH (file list in the brief) is reported as deliverables in place; no git commit/push was made
   (OPUS-RULES hard rule: no commits, PRs or pushes).

## What it means (plain high-school English)

The new rule works on everything we built ourselves: all 28 test wordings of "what can you do" get the
honest answer, and nothing else the agent does changed at all — all frozen tests and probes match the
old version exactly. But the final blind test could not run because the test file calls its question
column `user` while our sealed test-taker demands `user_text`, so there is no grade yet.

## What it doesn't mean

It doesn't mean the agent passed or failed: a VOID run proves nothing about the 25 blind general items.
It also doesn't mean the agent learned new skills — the change only affects how it describes what it can
do, and only on wordings the rule recognizes.
