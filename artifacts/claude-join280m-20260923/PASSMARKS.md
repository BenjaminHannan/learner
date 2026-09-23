# Exp 280m — PASSMARKS (registered before the seal; the panel folder has not been opened)

Arm under test: **280m** = `scripts/claude_loop280m_agent.py` + `artifacts/claude-join280m-20260923/loop280m-config.json`
(260 + the three piece layers stacked inner to outer — 281, then 280, then 280b, then 282, then 282b;
outermost instance turn stack `turn282b(turn282(turn280b(turn280(turn281(turn260)))))`;
SrcGuardMixin228 first in the daemon MRO, as on 260).
Base arm: **260** = `scripts/claude_loop260_agent.py` + `artifacts/claude-openers260-20260922/loop260-config.json`.
Piece arms: **280b**, **281**, **282b** (their sealed agents + configs, read-only).
Spec: `design/v3/30-modes/280m-talking-join.md` (base 260; no new behaviour; 0 overlaps before the seal).
Predicted moves (machine-readable): `predicted_moves280m.json`.

The verdict is PASS only if M1–M4 all pass. Any change to a sealed file after the seal = FAIL. No re-seal.
No silent re-runs: each registered command runs once; a driver-only fix after the seal is reported with its diff.

## The join (no new behaviour)

Piece files are imported read-only and unchanged (`scripts/claude_fix281_called.py`,
`scripts/claude_fix280_capab.py`, `scripts/claude_fix280b_general.py`, `scripts/claude_fix282_small.py`,
`scripts/claude_fix282b_vocab.py`) and installed on the 260 build in the note's order, inner to outer.
Each layer only ever substitutes the reply of a turn its own head already mishandled (or serves the sealed
CAN280 text), and otherwise passes through byte-identical with identical stores. The builder's own dev turns
(60 dialogs, 85 turns: ability questions, called questions after teaches, small talk, mixed turns, controls)
fire the three triggers 12 / 13 / 14 times with **0 overlaps** (no turn fires 2+ triggers), so every turn has
exactly one owner. Any overlap on the blind panel is listed by the scorer as a deviation.

## Commands (from the repo root, uv prefix as in the scripts)

- M2+probes (registered, once): `bash scripts/claude_280m_runall.sh artifacts/claude-join280m-20260923/run`
  (checks `uptime` before every step; scorer `scripts/claude_join280m_regscore.py` writes `run/regscore280m.json`).
- M1+M3+M4-panel (registered, once): after the panel writer's
  `artifacts/claude-joinpanel280m-20260923/SEAL.sha256.txt` checks OK:
  `bash scripts/claude_280m_panel.sh artifacts/claude-join280m-20260923/run` — panel seal check, schema gate,
  then the panel once on all five arms (`scripts/claude_join280m_run.py panel`), then
  `scripts/claude_join280m_score.py panel`; then smalltalkpanel234 once on 260 and once on 280m (`st234` mode).
- If the panel is not sealed 120 minutes after this seal: report and stop.
- Strict schema (columns dialog_id, turn_index, user_text, category, gold; categories ability / called / teach /
  smalltalk / mixed / control; `user` also accepted for the text): the runner refuses to run on any schema
  violation or empty turn text, and the scorer gates SCHEMA-MISMATCH (exit 3 = VOID). Runner and scorer were run
  end to end on a mock panel in exactly this schema before the seal (mock in /tmp, not sealed), incl. the `user`
  key, the empty-text refusal (exit 4), and the SCHEMA-MISMATCH paths (exit 3).

## M1 — blind joinpanel280m, run once on five arms (260, 280b, 281, 282b, 280m)

Mechanical agreement and counts per category only (scorer `panel` mode). Truth of claims and grammar are
director-graded, ungraded here; the file path of every changed reply shape is the piece file of its owner arm.
The scorer prints ids of misses, never item text.

| bar | pass if |
|---|---|
| every 280m reply, write count and store byte-identical to the owner arm | 100% of turns |
| question and small-talk turns with writes on 280m | 0 |
| wrong answers on called items on 280m | 0 (director claim check; scorer lists reply files) |
| unsupported claims anywhere on 280m | 0 (director checks; scorer reports old-sheet scan + reply files) |

Report only (no bar): absolute rates per category, 260 beside 280m.

Ownership (fixed now; mixed shapes enumerated — the 282/282b classifiers can never fire on a mixed turn with
fact content, since relation and entity words are outside their grammars/vocabulary):

| panel category | owner arm | shape |
|---|---|---|
| ability | 280b | general ability questions |
| called | 281 | called/named/name-of questions after teaches |
| teach | 260 | plain teaches (no layer touches teaches) |
| smalltalk | 282b | greetings, thanks, closings |
| control | 260 | plain teaches and plain questions |
| mixed, smalltalk-opener + plain ask (no called/ability wording) | 260 | fires nothing |
| mixed, smalltalk-opener + trailing-called/named/do-you-call/name-of | 281 | fires only the 281 rewrite |
| mixed, smalltalk + general ability wording | 280b | fires only the 280/280b rule |
| mixed, any other wording | 260, 281 or 280b by the same trigger rule (scorer computes it from the turn text and the live store) | never 282b |

Predicted: 100% agreement (dev pilot: 85/85 turns agree, incl. 9 plain mixes on 260, 1 called-mix on 281,
1 ability-mix on 280b); 0 question/smalltalk writes; 0 overlaps; 0 store diffs 280m vs 260.

## M2 — frozen suites vs 260's saved rows (GATE as clean as 260's)

Suites: rt136, rt143, sessions152, bench (4 files). Method (same deviation 260/281 used): rt136 labels come
from `fable_suitediff218 --base-dir artifacts/fable-agent138j-20260922`; the 280m-vs-260 comparison is a direct
field-by-field row compare except wall-clock timing. rt143 via `scripts/claude_138l_rt143nogate.py` (124 rows)
compared with 260's saved `run/rt143nogate-n.json`. sessions152 + bench use
`--base-dir artifacts/claude-openers260-20260922/run/sd`.

**Predicted moves (exactly this list — the union of the pieces' registered moves, nothing else):**
- sessions152: exactly 280's 3 reply-only moves, verdict UNHELPFUL -> UNHELPFUL, stored identical,
  0 write changes: S2-casual-friends#1 "what can you do", S3-teachers-correction#0 "heyy, what can you do?",
  S4-pets-identity#9 "what can you do?" — old C24 reply -> sealed `CAN280` on all 3. GATE as clean as 260's.
- bench 4x200: 0 moved. rt136 (145 units): 0 field diffs; vs-138j-base labels identical to 260's (16 inherited
  moves, same counts; GATE NOT clean on both arms exactly as on 260 — recorded, not a bar).
- rt143_nogate (124 rows): 0 moved.
- Verifier probes vs 260's saved `run/vp-n.json` / `run/vs-n.json`: **exactly 2 changed rows, N06 (281's:
  "What is the name of Tomas's boss?" with Tomas/boss/Mirela stored -> "Tomas's boss is Mirela.", ev 0,
  stored identical) and E04 (282's: "what's up?" with nothing stored -> the head's greeting reply, ev 0,
  stored identical)**; supp 0 changes.
- Any other moved unit, any verdict flip, or any write change fails M2.

## M3 — smalltalkpanel234, run once on 260 and once on 280m

56 items, each run once per arm (`run.py st234`), scored by `score.py st234` with per-arm fitting sets from the
recorded canonical probes. This panel is NOT run before the seal (its registered run is its only run;
deviation from "pilot everything", forced by the run-once rule).

| bar | pass if |
|---|---|
| wellbeing (expect small_talk): fitting hits on 280m | ≥ 260's hits (260 shown beside) |
| every other item: 280m reply == 260 reply | all equal |
| setup replies and stores 280m vs 260 | 0 diffs |
| turns with writes on 280m | 0 |

Predicted: only all-vocabulary wellbeing turns that 260 errs on move to fitting on 280m (at most E04-shaped
ones); everything else identical; 0 writes; 0 store diffs.

## M4 — notebook-zero

0 notebook differences 280m vs 260 on the suites (M2: 0 write changes, 0 store diffs) and on the panel
(M1 table: 0 store diffs — no layer ever writes on a question or small-talk turn, and teaches pass through
untouched, so stores are identical on every turn; the "except where a piece arm already differs" clause is
vacuous by construction).

## Abstain flips

Any unpredicted flip toward an abstain counts against its mark; that item is then run alone 5 times and
reported, with whether the 228 guard was installed (it is: SrcGuardMixin228 first, asserted in `_check`).
The two predicted verifier moves (N06, E04) move away from broken abstains/mode-status lines, not toward an
abstain, so no 5x follow-up applies to them.

## Dev set (not a mark; tuned on)

`devcases280m.json` (60 dialogs, 85 turns, builder's own wording, fictional names). Pilot with the sealed code:
85/85 turns 280m byte-identical (reply + write count + store) to the owner arm
(ability 12/12 on 280b, called 23 turns on 281 incl. notstored-abstain and ambiguous-unchanged,
smalltalk 14/14 on 282b, mixed 21 turns on 260/281/280b by shape, control 15 turns on 260);
trigger fires 12 called / 13 ability / 14 small with 0 overlaps; 0 question-write violations on 280m.
Suites pilot: sessions152 exactly the 3 predicted moves, bench 0, rt136 0 field diffs with labels identical to
260's, rt143 0, vp exactly N06+E04, vs 0. smalltalkpanel234 never run (run-once rule).
No panel was read item by item at any point.

## Known limits (predicted, not hidden)

- A mixed turn worded so that 2+ triggers fire would break the single-owner rule; none exists in dev (0/85),
  and the scorer lists any such turn as an overlap deviation rather than grading it by hand.
- Embedded called-wordings that match none of the four sealed 281 shapes keep 260's reply (inherited limit).
- Cue-less general wordings, "Can you <specific>?", negations, and pure-tail/how-are-you small talk keep
  their piece-arm routes (inherited limits); 280m adds nothing beyond the pieces.

## Numbered predictions

- P280m.1 (M1 blind joinpanel280m, once per arm): every 280m reply, write count and store byte-identical to
  the owner arm of its category (100%); 0 writes on question and small-talk turns; 0 wrong called answers and
  0 unsupported claims (director claim check over the listed reply files); absolute rates per category reported
  with 260 beside 280m. Mixed turns owned per the table above.
- P280m.2 (M2 frozen suites + verifier probes vs 260's rows): exactly the 3 sessions152 reply-only moves,
  0 moves everywhere else (bench, rt136 with labels identical to 260's, rt143), GATE identical to 260's;
  verifier vp exactly N06+E04, vs 0; 0 write changes anywhere.
- P280m.3 (M3 st234 + M4 notebook-zero): wellbeing 280m ≥ 260, every other item identical, 0 writes,
  0 setup/store diffs; 0 notebook differences 280m vs 260 on suites and panel.
- P280m.4 (falsifiers): any 280m reply differing from its owner arm, any suite/probe move outside the union
  list, any write on a question or small-talk turn, or any overlap of 2+ triggers on one turn proves the join
  wrong.
