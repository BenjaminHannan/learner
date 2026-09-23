# Exp 280b — PASSMARKS (registered before the seal; the panel folder has not been opened)

Arm under test: **280b** = `scripts/claude_loop280b_agent.py` + `artifacts/claude-capab280b-20260923/loop280b-config.json`
(280 + `scripts/claude_fix280b_general.py`, outermost instance turn layer `turn280b` over `turn280`; SrcGuardMixin228 first in the daemon MRO, as on 280).
Base arm: **280** = `scripts/claude_loop280_agent.py` + `artifacts/claude-capab280-20260923/loop280-config.json`.
Spec: the "280b" section of `design/v3/30-modes/280-282-chat-fixes.md`. Predicted moves (machine-readable): `predicted_moves280b.json`.
capabilpanel280 is burned for 280b (director's correction): no 280b mark uses it; M1 is graded only on the fresh capabilpanel280b.

The verdict is PASS only if M1–M3 all pass. Any change to a sealed file after the seal = FAIL. No re-seal.
No silent re-runs: each registered command runs once; a driver-only fix after the seal is reported with its diff.

## The one change

A turn is a general ability question when it is question-shaped (or starts with "tell me"/"list", or opens
with "i want to know"/"i wonder"), addresses the assistant (you/u/your/yourself), contains an ability cue
(can, able, good at, capable, help, abilities, skills, purpose, what...for, what...you...do in order), and
names no stored or new entity (no possessive, no capitalised name, no notebook-stored word) and no relation
word, and is not negated. "Can you <specific thing>?" turns are NOT in scope: a can/could + you/u led turn
is general only when the remainder after that prefix is itself general. Such turns get 280's sealed CAN280
text with 0 writes. Everything else — can-you specifics, near-misses, teaches, asks, notebook — passes
through byte-identical to 280. Slang/typo tolerance: small slang map + edit-distance-1 on cue words.

## Commands (from the repo root, uv prefix as in the scripts)

- M2+probes: `bash scripts/claude_280b_runall.sh artifacts/claude-capab280b-20260923/run` (checks `uptime` before
  every step; scorer `scripts/claude_capab280b_regscore.py` writes `run/regscore280b.json`).
- M1: after the panel writer's `artifacts/claude-capabilpanel280b-20260923/SEAL.sha256.txt` checks OK:
  `bash scripts/claude_280b_panel.sh artifacts/claude-capab280b-20260923/run` — panel seal check, schema gate,
  then the panel once on 280 and once on 280b (`scripts/claude_capab280b_run.py panel`), then
  `scripts/claude_capab280b_score.py panel`.
- If the panel is not sealed 120 minutes after this seal: report and stop.
- Schema gate (brief gives dialog_id, turn_index, last turn scored): every row must carry dialog_id,
  turn_index, user_text; (dialog_id, turn_index) unique; scored turn = last row per dialog. Violations print
  SCHEMA-MISMATCH and exit 3: VOID, not FAIL. Gold never read. Category/family labels are hints only
  (general/canyou/nearmiss/control by keyword, else by turn text). Counts only; ids of misses listed, item
  text never quoted.

## M1 — blind capabilpanel280b, 280's number reported next to every figure

Mechanical counts per category only (scorer `panel` mode). Truth of claims and grammar are director-graded,
ungraded here; the file path of every changed reply shape is `scripts/claude_fix280b_general.py` (one fixed
text: 280's sealed CAN280).

| bar | pass if |
|---|---|
| M1gen: every general item's 280b reply == CAN280 exactly | 25/25 |
| M1a: replies claiming an ability the table does not support (old-sheet scan over every 280b reply) | 0 on 280b |
| M1xy: canyou / nearmiss / control items changed 280b vs 280 | 0 / 0 / 0 |
| M3: panel write diffs 280b vs 280 | 0 diffs |
| M3: question/self turns with writes on 280b | 0 |

Predicted: M1gen 25/25 canon; M1a 0 (280 arm: misses only where 280 emits the old sheet, if any);
M1xy 0/0/0; M3 0/0.

## M2 — frozen suites vs 280's saved rows (GATE clean)

Suites: rt136, rt143, sessions152, bench (4 files). Method (same deviation 260/280 used): rt136 labels come
from `fable_suitediff218 --base-dir artifacts/fable-agent138j-20260922`; the 280b-vs-280 comparison is a
direct field-by-field row compare except wall-clock timing. rt143 via `scripts/claude_138l_rt143nogate.py`
(124 rows) compared with 280's saved `run/rt143nogate-280.json`. sessions152 + bench use
`--base-dir artifacts/claude-capab280-20260923/run/sd`.

**Predicted moves (exactly this list): none anywhere.**
- sessions152: 0 moves (the 3 known general-wording turns already get CAN280 on 280; no other suite turn is
  a general ability question under the 280b rule — verified by scan in pilot). GATE clean.
- rt136 (145 units): 0 field diffs; vs-138j-base labels identical to 280's (16 inherited moves, same counts).
- rt143_nogate (124 rows): 0 moved. sessions152 otherwise 0 moved. bench 4x200: 0 moved.
- Any moved unit, any verdict flip, or any write change fails M2.

## Verifier probes + M3 notebook-zero (registered, in the same runall)

- `artifacts/claude-verify-20260922/138m/probes.json` (98 rows) and `probes-supp.json` (12 rows), run with the
  probes runner on 280b and compared with 280's saved `run/vp-280.json` / `run/vs-280.json`: **predicted 0
  changes**. Any change fails.
- M3 (spec): 0 notebook changes on the panel (M1 table) and suites (M2: 0 write changes, 0 write diffs).

## Abstain flips

Any unpredicted flip toward an abstain counts against its mark; that item is then run alone 5 times and
reported, with whether the 228 guard was installed (it is: SrcGuardMixin228 first, asserted in `_check`).

## Dev set (not a mark; tuned on)

`devcases280b.json` (68 dialogs, builder's own wording, fictional names; from
`scripts/claude_capab280b_devcases.py`), scored by `claude_capab280b_score.py dev`. Pilot with the sealed
code: general 28/28 replies byte-equal to sealed CAN280 (13 of them already CAN280 on 280, 13 moved);
canyou 12/12, nearmiss 12/12, control 10/10, ability sanity 6/6 byte-identical 280b vs 280 (0 diffs);
writes identical per family; 0 question-write violations on either arm.
Pilot also found and fixed one over-fire before the seal: "What do you know about me?" (verifier probe
B17) caught the unordered what+do+you cue; the cue is now ordered (what...you...do) and B17 is 0-diff.
No panel was read item by item at any point.

## Known limits (predicted, not hidden)

- "Can you tell me about yourself?" (no ability cue in the remainder) and "What can't you do?" / "What can
  you not do?" (negation) keep 280's replies by construction. A panel general item worded with no cue from
  the rule's list would miss M1gen by staying clarify (claims nothing).
- Near-misses that name no person, no relation and carry a cue while addressing the assistant would be the
  falsifier (none found in dev; the rule's gates were built for exactly the listed near-miss shapes).
