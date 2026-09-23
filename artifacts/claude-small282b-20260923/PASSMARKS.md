# Exp 282b — PASSMARKS (registered before the seal; the panel folder has not been opened)

Arm under test: **282b** = `scripts/claude_loop282b_agent.py` + `artifacts/claude-small282b-20260923/loop282b-config.json`
(282 + `scripts/claude_fix282b_vocab.py`, outermost instance turn layer `turn282b` over `turn282`; SrcGuardMixin228 first in the daemon MRO, as on 282).
Base arm: **282** = `scripts/claude_loop282_agent.py` + `artifacts/claude-small282-20260923/loop282-config.json`.
Spec: the "282 ruling and the 282b follow-up" section of `design/v3/30-modes/280-282-chat-fixes.md`. Predicted moves (machine-readable): `predicted_moves282b.json`.

The verdict is PASS only if M1–M3 all pass. Any change to a sealed file after the seal = FAIL. No re-seal.
No silent re-runs: each registered command runs once; a driver-only fix after the seal is reported with its diff.

## The one change

A whole turn is small talk when every word, after lowercasing and stripping punctuation and emoji
(`normalize_282b`: lower-case, fold curly quotes, drop apostrophes, collapse letter runs of 3+,
split on non-letters), belongs to the sealed vocabulary `VOCAB282B` (131 words: greetings, thanks,
closings, "how are you" words, fillers such as "so", "ok", "lol", "man", "again", "all", "for",
"now", "much", "a", "lot", joiners, and the assistant's own name "premonition"), it holds at least
one greeting, thanks or closing word, and it names no stored entity (notebook subject or value,
incl. apostrophe-less possessive stems of known subjects) and no relation word (single or
adjacent-pair surfaces from `fable_listening_english.RELATION_MAP`; verified disjoint from the
vocabulary). Class = the first greeting/thanks/closing word. The original turn runs first through
the whole head: if it wrote, or its reply is already not an error reply, its reply stands. Else the
canonical probe runs with the pre-turn state restored (greet -> "Hello.", thanks -> "Thanks!",
close -> "Bye."); its reply is used only if it is not an error reply and the run wrote nothing.
Otherwise the original reply stands with its state restored. A turn with any fact or question
content fails the vocabulary test (entity/relation words are outside it), so mixed turns keep 282's
route byte-identical. Teaches are untouched; questions never write.

## Commands (from the repo root, uv prefix as in the scripts)

- M2+probes: `bash scripts/claude_282b_runall.sh artifacts/claude-small282b-20260923/run` (checks `uptime` before
  every step; scorer `scripts/claude_small282b_regscore.py` writes `run/regscore282b.json`).
- M1+M3: after the panel writer's `artifacts/claude-smallpanel282b-20260923/SEAL.sha256.txt` checks OK:
  `bash scripts/claude_282b_panelrun.sh artifacts/claude-small282b-20260923/run` — panel seal check, then the
  panel once on 282 and once on 282b (`scripts/claude_small282b_run.py panel`, per-arm canonical probes
  recorded), then `scripts/claude_small282b_score.py panel`; then smalltalkpanel234 once on each arm
  (`st234` mode) and `score.py st234`.
- If the panel is not sealed 120 minutes after this seal: report and stop.
- Strict schema (deviation from 282's flexible loader, required by the brief): the runner loads only rows
  shaped `{dialog_id, turn_index, user_text, category, gold}` with category in
  {greeting, closing, mixed, control}; a key named `user` is also accepted for the text; any missing key,
  unexpected category, or empty turn text stops the run with an error. The scorer re-gates the same schema
  (SCHEMA-MISMATCH exit 3 = VOID). Runner and scorer were run end to end on a mock panel in exactly this
  schema before the seal (mock in /tmp, not sealed), incl. the `user` key, the empty-text refusal (exit 4),
  and the SCHEMA-MISMATCH paths (exit 3).

## M1 — blind smallpanel282b, 282's number reported next to every figure

Mechanical counts per WRITER category only (scorer `panel` mode). Fitting = the arm's own canonical reply
set (greeting items: its reply to "Hello.", plain or "Hi! "-prefixed; closing items: its replies to
"Thanks!" or "Bye.", plain or "Hi! "-prefixed), with 0 writes. The denominator is the writer's greeting
and closing categories (spec: 20 + 15 = 35 turns; the scorer enforces at least 90% of the actual count).

| bar | pass if |
|---|---|
| writer greeting+closing: fitting replies on 282b | ≥ 90% (282 arm shown beside) |
| writer greeting+closing turns with writes on 282b | 0 |
| question turns with writes on 282b (whole panel) | 0 |
| mixed turns: 282b keeps 282's reply, write delta and store | 0 moves vs 282 |
| control turns: 282b keeps 282's reply, write delta and store | 0 moves vs 282 |
| M3-notebook: panel store diffs 282b vs 282 (every turn) | 0 diffs |

Report-only (no bar): wrong vs abstain split on each arm; per-category counts; 282's fitting count.

## M2 — frozen suites vs 282's saved rows (0 moves)

Suites: rt136, rt143, sessions152, bench. sessions152+bench via `fable_suitediff218 --base-dir
artifacts/claude-small282-20260923/run/sd`; rt136 via `--base-dir artifacts/fable-agent138j-20260922` for the
vs-base labels plus a direct field-by-field row compare against 282's saved `run/sd136/rt136-rows.json`
(timing ignored); rt143 via `scripts/claude_138l_rt143nogate.py` compared directly with 282's saved
`run/rt143nogate-282.json`.

**Predicted moves (exactly this list): none.** 0 moved units on sessions152 (180 units), bench 4×200,
rt136 (145 units, 0 field diffs; the vs-138j-base labels identical to 282's on both arms), rt143_nogate
(124 rows). Any moved unit, verdict flip, write change, or abstain-ward flip fails M2.

## Verifier probes + notebook-zero (registered, in the same runall)

- `artifacts/claude-verify-20260922/138m/probes.json` (98 rows) and `probes-supp.json` (12 rows), run with the
  probes runner on 282b and compared with 282's saved `run/vp-282.json` / `run/vs-282.json`: **predicted 0
  changes on both.** Any change fails.
- Notebook-zero: 0 store changes on the suites (M2) and on the panel (M1 table); 0 question writes on 282b
  anywhere.

## M3 — smalltalkpanel234 rerun once per arm (registered, in the same panel script)

56 items, each run once on 282 and once on 282b (`run.py st234`), scored by `score.py st234` with per-arm
fitting sets from the recorded canonical probes. This panel was NOT run before the seal (its registered run
is its only run; deviation from "pilot everything", forced by the run-once rule).

| bar | pass if |
|---|---|
| wellbeing (expect small_talk): fitting hits on 282b | ≥ 282's hits (282 shown beside) |
| every other item: 282b reply == 282 reply | all equal |
| setup replies and stores 282b vs 282 | 0 diffs |
| turns with writes on 282b | 0 |

Predicted: only all-vocabulary wellbeing turns that 282 errs on move to fitting on 282b; everything else
identical; 0 writes; 0 store diffs.

## Abstain flips

Any unpredicted flip toward an abstain counts against its mark; that item is then run alone 5 times and
reported, with whether the 228 guard was installed (it is: SrcGuardMixin228 first, asserted in `_check`).

## Dev set (not a mark; tuned on)

`devcases282b.json` (65 dialogs, 79 turns, builder's own wording, fictional names; from
`scripts/claude_small282b_devcases.py`), scored by `claude_small282b_score.py dev`. Pilot: **282b 65/65**
(`pilot/dev-score.json`); exactly 18 moves 282→282b (d282b-002, d282b-007, d282b-009, d282b-010, d282b-011,
d282b-013, d282b-014, d282b-015, d282b-016, d282b-017, d282b-018, d282b-021, d282b-026, d282b-036, d282b-037,
d282b-038, d282b-039, d282b-040 turn 0, all toward the head's canonical reply for their class); mixed 15/15
+ control 10/10 byte-identical; 0 question-write violations on either arm; exact stores.
Families: greet 20, thanks_close 20, mixed 15, control 10.
282-arm dev failure modes (dev info only): filler mid-turn, opener words, extra words, emoji tails and
typo variants → clarify, save-failure, or the mode-status line; pure tails and "how are you" shapes keep
their (already fitting or abstaining) route.

## Known limits (predicted, not hidden)

- Pure-tail closings with no class word ("that's all" alone) and "how are you"-shaped turns keep 282's
  route (the vocabulary test has no class word for them; 282's grammar or 234 owns them).
- Bare emoji-only turns never match (no words at all).
- Foreign greetings are outside the sealed vocabulary.
- A whole-turn word that is also a stored name ("Cheers" taught as a name, then "cheers" alone) keeps
  282's route via the stored-entity gate (conservative: 0 moves vs 282).
- "Class = the first such word": "bye, thanks!" counts as thanks ("Thanks!" reply — still fitting for a
  closing item).

## Numbered predictions

- P282b.1 (M1 blind smallpanel282b, once per arm): writer greeting+closing fitting on 282b ≥ 90% (bar
  32/35 at spec counts; 282 shown beside); 0 writes on them; mixed and control 0 moves vs 282; 0 store
  diffs; 0 question writes. Panel moves: exactly the writer-smalltalk turns where 282 errs and the
  vocabulary test fires (dev proxy: 18/40 smalltalk dev turns move, the rest keep 282's already-fitting
  reply; blind-panel ids not predictable).
- P282b.2 (M2 frozen suites + verifier probes vs 282's rows; dev): 0 moves everywhere (sessions152,
  bench GATE clean; rt136 0 field diffs with labels identical to 282's; rt143 0 diffs; vp/vs 0 diffs);
  dev 65/65 with exactly the 18 listed moves, 0 question writes, exact stores.
- P282b.3 (M3 st234 + falsifiers): wellbeing 282b ≥ 282, other items all identical, 0 writes, 0 diffs.
  Falsifiers: any 282b reply change on a mixed/control turn, any question-turn write, any suite/probe
  move vs 282's rows, or any store diff proves the change wrong.
