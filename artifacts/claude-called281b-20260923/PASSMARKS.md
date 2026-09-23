# Exp 281b — PASSMARKS (registered before the seal; the panel folder has not been opened)

Arm under test: **281b** = `scripts/claude_loop281b_agent.py` + `artifacts/claude-called281b-20260923/loop281b-config.json`
(281 + `scripts/claude_fix281b_casual.py`, outermost instance turn layer `turn281b` over `turn281`; SrcGuardMixin228 first in the daemon MRO, as on 281).
Base arm: **281** = `scripts/claude_loop281_agent.py` + `artifacts/claude-called281-20260923/loop281-config.json`.
Spec: the "281 result and the 281b follow-up" section of `design/v3/30-modes/280-282-chat-fixes.md`. Predicted moves (machine-readable): `predicted_moves281b.json`.
Ledger predictions: P281b.1 (M1), P281b.2 (M2 + probes + dev), P281b.3 (falsifiers and known limits).

The verdict is PASS only if M1–M3 all pass. Any change to a sealed file after the seal = FAIL. No re-seal.
No silent re-runs: each registered command runs once; a driver-only fix after the seal is reported with its diff.

## The one change

On top of 281, a casual called/named question turn is normalised to the formal called-wording and run through
281's own turn: leading "whats"/"what's" (any case) reads as "What is"; a possessive written without its
apostrophe ("anas") is restored to the known entity's form ("Ana's") only when its stem names a subject already
in the notebook (s-final subjects restore to the teach form, e.g. "nils" for known "Nils" reads as "Nils's");
a missing "?" is appended only when the turn (or its opener-stripped core) starts with a question word. The
original turn runs first through the whole head: if it already answers, its reply stands. Else the formal turn
runs as if typed alone; its reply is used only if it answers with 0 writes (a written run is undone and the
original stands). Otherwise the original reply stands with its state restored. Formal turns 281 already
rewrites, turns with no called cue, "called <Name>" value-questions, and plain teaches (never question-shaped)
always take the 281 path byte-identical. Teach turns and writes are untouched. Nothing else moves.

## Commands (from the repo root, uv prefix as in the scripts)

- M2+probes: `bash scripts/claude_281b_runall.sh artifacts/claude-called281b-20260923/run` (checks `uptime` before
  every step; scorer `scripts/claude_called281b_regscore.py` writes `run/regscore281b.json`).
- M1: after the panel writer's `artifacts/claude-calledpanel281b-20260923/SEAL.sha256.txt` checks OK:
  `bash scripts/claude_281b_panel.sh artifacts/claude-called281b-20260923/run` — panel seal check, then the panel
  once on 281 and once on 281b (`scripts/claude_called281b_panelrun.py panelrun`), then
  `scripts/claude_called281b_panelscore.py`. Each arm runs exactly once.
- If the panel is not sealed 120 minutes after this seal: report and stop.
- Schema gate (panel-schema contract): per-turn rows `{dialog_id, turn_index, user_text, category, gold}`; the
  runner also accepts the key `user` for the text (same string; both present with different values mismatches).
  Required categories: teach_setup / stored_called / nostore_called / ambiguous_called / control_plain. Teach gold
  is `Subject|relation|Object`; stored/control gold is the exact value; nostore/ambiguous gold is `abstain`.
  Any missing file, field, family or label prints SCHEMA-MISMATCH and exits 3: VOID, never scored by hand.
  The gate was run end to end on a 10-row mock panel in this exact schema before the seal: both key variants run
  clean on both arms with identical scores (teach 4/4 both arms; stored denominator 2/3 with the never-taught row
  excluded; 0 writes; 0 store diffs), and missing-gold / bad-category mocks exit 3.

## M1 — blind calledpanel281b, 281's number reported next to every figure

Mechanical counts per category only (scorer `panelscore`). Truth of claims and grammar are director-graded,
ungraded here; every changed reply is the head's own answer to the formal called question, via the normaliser in
`scripts/claude_fix281b_casual.py` plus 281's sealed rewrite.

| bar | pass if |
|---|---|
| stored: denominator items answered exactly on 281b (denominator = stored_called rows whose dialog teach triple is stored on the 281 arm; the note's M1 denominator) | ≥ 90% (281 arm shown beside) |
| stored: wrong answers on 281b (over the denominator) | 0 |
| notstored: items where the fact was never taught still abstain on 281b | all abstain (0 new guesses) |
| ambiguous ("called" belongs to the value): 281b keeps 281's reply | 0 moves vs 281 |
| control: 281b keeps 281's reply | 0 moves vs 281 |
| teach: teach_setup gold triples stored (per arm; the 281-arm fail count is the note's teach-fail count) | at most 2 fail on 281, else the panel is VOID |
| M3: panel store diffs 281b vs 281 (every turn) | 0 diffs |
| M3: question turns with writes on 281b | 0 |

On the denominator: the note counts stored items "only over items whose teach turn the 260 arm stores". The
registered arms are 281 and 281b, so the scorer reads teach stores off the 281 arm: 281 is sealed to keep
teaches byte-identical to 260 (its rewrite needs "?", its classes never touch teaches; 281's registered M3
shows 0 teach/store diffs vs 260), and 281b provably takes the no-op path on plain teach forms (no question
word start, no called shape), mechanically checked by teach store_same 281b vs 281 on every teach row.
Predicted: stored moves are exactly the casual-wording + stored-fact items (dev: 21 stored-shape moves incl.
3 "What's" formal items); ?-terminated lowercase/doyoucall/whats-nameof shapes 281 already answers stay
identical; ambiguous/control/notstored 0 moves; M3 0/0; teach fails 0.
Report-only (no bar): "I don't know X's R called/named." style broken abstains remaining on each arm.

## M2 — frozen suites vs 281's saved rows (0 flips toward an abstain)

Suites: rt136, rt143, sessions152, bench (4 files), via `fable_suitediff218 --only rt136,rt143,sessions152,bench`
as in 281. sessions152 + bench use `--base-dir artifacts/claude-called281-20260923/run/sd` (281's saved rows);
rt136 labels come from `--base-dir artifacts/fable-agent138j-20260922` with a direct field-by-field row compare
against 281's `run/sd136/rt136-rows.json`; rt143 (`scripts/claude_138l_rt143nogate.py`, 124 rows) is compared
directly with 281's saved `run/rt143nogate-281.json`.

**Predicted moves (exactly this list): none.** 0 moved units on sessions152 (180 units), bench 4×200,
rt136 (145 units, 0 field diffs; vs-138j labels identical to 281's, gate string NOT-clean on both arms from the
13 inherited 222 WRONG-WRITE + 1 junk), rt143_nogate (124 rows). Every suite and probe turn is formal text, so
the casual normaliser returns None and the 281 path runs byte-identical.
Any moved unit, verdict flip, write change, or abstain-ward flip fails M2.

## Verifier probes + M3 notebook-zero (registered, in the same runall)

- `artifacts/claude-verify-20260922/138m/probes.json` (98 rows) and `probes-supp.json` (12 rows), run with the
  probes runner on 281b and compared with 281's saved `run/vp-281.json` / `run/vs-281.json`: **predicted 0
  changes on both files.** Any change fails.
- M3 (spec): 0 notebook changes on the panel (M1 table: 0 store diffs) and suites (M2: 0 write changes,
  0 write diffs); 0 question writes on 281b; ambiguous and control items identical to 281.

## Abstain flips

Any unpredicted flip toward an abstain counts against its mark; that item is then run alone 5 times and reported,
with whether the 228 guard was installed (it is: SrcGuardMixin228 first, asserted in `_check`).

## Dev set (not a mark; tuned on)

`devcases281b.json` (56 dialogs, builder's own wording, fictional names; from
`scripts/claude_called281b_devcases.py`), scored by `claude_called281b_score.py dev`. Pilot: **281b 56/56**
(`pilot/dev-score.json`); exactly 21 moves 281→281b (d281b-003, d281b-009, d281b-010, d281b-012…d281b-019,
d281b-021, d281b-022, d281b-023, d281b-027…d281b-033 turn 1, all toward the stored value); all other 91 dev turns
byte-identical 281b vs 281; notstored 8/8 abstain on both arms; ambiguous 8/8 + control 6/6 identical; 0
question-write violations on either arm; exact stores.
Families: stored_formal 10, stored_casual 20, opener_casual 4, notstored 8, ambiguous 8, control 6.
281-arm dev failure modes (dev info only): "whats"-led turns clarify; ?-less called turns give the broken
"I don't know X's R called/named." or clarify; all-casual ?-less turns get a save-shape error; "What's X
called?" (stored, never taught) abstains honestly.

## Known limits (predicted, not hidden)

- A no-apostrophe possessive of a multi-word subject ("mary anns cat") is not restored (single-token stems
  only); such turns keep 281's reply.
- Formal text 281 already mishandles stays mishandled (e.g. a no-apostrophe plain question with "?" that the
  head itself cannot answer keeps 281's reply byte-identical).
- ?-less turns that do not start with a question word, or carry no called cue, never normalise (small talk,
  tag-checks and teaches keep 281's route exactly).
- If the rewritten formal question clarifies or abstains, the original reply stands, including 281's malformed
  abstains and save-shape errors (report-only count).
- Not-stored and ambiguous items keep 281's reply byte-identical by construction (substitution needs the head's
  own answer to the formal question).
