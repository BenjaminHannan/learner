# Exp 280n — PASSMARKS (registered before the seal; the panel folder has not been opened)

Arm under test: **280m sealed, unchanged** = `scripts/claude_loop280m_agent.py` + `artifacts/claude-join280m-20260923/loop280m-config.json`
(260 + 281, then 280/280b, then 282/282b; 280m SEAL 12/12 OK checked from the worktree root before writing this file).
Base arm: **260** = `scripts/claude_loop260_agent.py` + `artifacts/claude-openers260-20260922/loop260-config.json`.
Piece arms: **280b**, **281**, **282b** (their sealed agents + configs, read-only).
Spec: `design/v3/30-modes/280m-talking-join.md`, section "280m result and 280n" (director, 2026-09-23 11:54 UTC):
re-test of the same sealed 280m agent with no code change on a fresh panel joinpanel280n (same spec as joinpanel280m:
90 turns; 25 ability, 8 teach + 12 called, 25 smalltalk, 10 mixed, 10 controls).
No agent file is new in 280n. The one new file with logic is the scorer `scripts/claude_join280n_score.py`
(mechanical mixed ownership from the piece arms' replies); the panel driver `scripts/claude_280n_panel.sh` is a thin
wrapper that calls the SEALED 280m runner read-only plus the new scorer.

The verdict is PASS only if M1–M4 all pass. Any change to a sealed file after the seal = FAIL. No re-seal.
No silent re-runs: each registered command runs once; a driver-only fix after the seal is reported with its diff.

## Commands (from the repo root, uv prefix as in the scripts)

- M2+probes (registered, once): `bash scripts/claude_280m_runall.sh artifacts/claude-join280n-20260923/run`
  (the SEALED 280m runall, reused read-only; checks `uptime` before every step;
  scorer `scripts/claude_join280m_regscore.py` writes `run/regscore280m.json`).
  Method: fable_suitediff218 --only rt136,rt143,sessions152,bench vs 260's rows, plus verifier probes vs 260's rows.
- M1+M3+M4-panel (registered, once): after the panel writer's
  `artifacts/claude-joinpanel280n-20260923/SEAL.sha256.txt` checks OK:
  `bash scripts/claude_280n_panel.sh artifacts/claude-join280n-20260923/run` — panel seal check, schema gate,
  then the fresh panel once on all five arms via the SEALED `scripts/claude_join280m_run.py panel`, then
  `scripts/claude_join280n_score.py panel`; then smalltalkpanel234 once on 260 and once on 280m (`st234` mode).
- If the panel is not sealed 120 minutes after this seal: report and stop (poll every 2 minutes).
- Strict schema (columns dialog_id, turn_index, user_text, category, gold; categories ability / called / teach /
  smalltalk / mixed / control; `user` also accepted for the text): the runner refuses to run on any schema
  violation or empty turn text, and the scorer gates SCHEMA-MISMATCH (exit 3 = VOID). Runner and scorer were run
  end to end on a mock panel in exactly this schema before the seal (mock in /tmp, not sealed), incl. a mock
  overlap (FAIL, exit 1, overlap id listed), the empty-text refusal (exit 4), and the SCHEMA-MISMATCH path (exit 3).

## M1 — blind joinpanel280n, run once on five arms (260, 280b, 281, 282b, 280m)

Mechanical agreement and counts per category only (scorer `panel` mode). Truth of claims and grammar are
director-graded, ungraded here; the file path of every changed reply shape is the piece file of its owner arm.
The scorer prints ids of misses, never item text.

| bar | pass if |
|---|---|
| every 280m reply, write count and store byte-identical to the owner arm | 100% of turns |
| overlaps (2+ piece arms differing from 260 on one mixed turn) | 0 |
| question and small-talk turns with writes on 280m | 0 |
| wrong answers on called items on 280m | 0 (director claim check; scorer lists reply files) |
| unsupported claims anywhere on 280m | 0 (director checks; scorer reports old-sheet scan + reply files) |

Report only (no bar): absolute rates per category, 260 beside 280m.

Ownership (fixed now, per the director note; mixed ownership uses NO trigger logic):

| panel category | owner arm | rule |
|---|---|---|
| ability | 280b | fixed |
| called | 281 | fixed |
| teach | 260 | fixed (no layer touches teaches) |
| smalltalk | 282b | fixed |
| control | 260 | fixed |
| mixed | 260 if no piece arm's reply differs from 260's | mechanical reply compare |
| mixed | the single piece arm (280b, 281 or 282b) whose reply differs from 260's | mechanical reply compare |
| mixed | OVERLAP: 2+ piece arms differ from 260 on one turn | fail, agree=False |

Predicted: 100% agreement (280m's 3 ability-led mixed misses from 280m are now owned by 280b under this rule,
since only 280b's reply differs from 260 there; dev basis 0 overlaps on 85 builder turns, and no turn ever showed
2+ piece replies differing); 0 question/smalltalk writes; 0 overlaps; 0 store diffs 280m vs 260.

## M2 — frozen suites vs 260's saved rows (GATE identical to 260's)

Suites: rt136, rt143, sessions152, bench (4 files) via the sealed runall, scored by the sealed regscore.
Same allowed union as 280m (the pieces' registered moves, nothing else):

**Predicted moves (exactly this list, nothing else):**
- sessions152: exactly 280's 3 reply-only moves, verdict UNHELPFUL -> UNHELPFUL, stored identical,
  0 write changes: S2-casual-friends#1, S3-teachers-correction#0, S4-pets-identity#9 — old reply -> sealed `CAN280`
  on all 3. GATE as clean as 260's.
- bench 4x200: 0 moved. rt136 (145 units): 0 field diffs; vs-138j-base labels identical to 260's
  (GATE identical to 260's).
- rt143_nogate (124 rows): 0 moved.
- Verifier probes vs 260's saved rows: **exactly 2 changed rows, N06 (281) and E04 (282)**; supp 0 changes.
- Any other moved unit, any verdict flip, or any write change fails M2.
- Deviation note: the 280m builder ran the suites only as a pre-seal pilot, not as a registered run after the seal;
  this 280n run performs the registered after-seal run the note requires.

## M3 — smalltalkpanel234, run once on 260 and once on 280m

56 items, each run once per arm, scored by the new scorer `st234` mode (same logic as the sealed 280m scorer).
This panel is NOT run before the seal (its registered run is its only run; deviation from "pilot everything",
forced by the run-once rule).

| bar | pass if |
|---|---|
| wellbeing (expect small_talk): fitting hits on 280m | ≥ 260's hits (260 shown beside) |
| every other item: 280m reply == 260 reply | all equal |
| setup replies and stores 280m vs 260 | 0 diffs |
| turns with writes on 280m | 0 |

Predicted: repeat of the 280m observation (wellbeing 17/20 vs 16/20, other 36/36, 0 writes/diffs; the 1 move the
same row 282 moved), barring the known ~1-in-800 bench-class flake toward an abstain (counts against the mark if
it appears; that item is then run alone 5 times and reported).

## M4 — notebook-zero

0 notebook differences 280m vs 260 on the suites (M2: 0 write changes, 0 store diffs) and on the panel
(0 store diffs — no layer ever writes on a question or small-talk turn, and teaches pass through untouched).

## Abstain flips

Any unpredicted flip toward an abstain counts against its mark; that item is then run alone 5 times and
reported, with whether the 228 guard was installed (it is, inside the sealed 280m agent, unchanged).
The two predicted verifier moves (N06, E04) move away from broken abstains/mode-status lines, not toward an
abstain, so no 5x follow-up applies to them.

## Mock end-to-end (not a mark; scorer tested, panel never opened)

Mock panel in /tmp (not sealed) in exactly the panel schema, all six categories: 7 dialogs / 8 turns incl.
mixed with owners 260, 280b and 281 -> scorer PASS 8/8, exit 0, mixed_owners {260:1, 280b:1, 281:1}.
Same mock plus one mixed turn where 280b AND 281 both differ from 260 -> scorer FAIL 8/9, exit 1,
moved=[d_over#0(mixed->OVERLAP)], overlaps=[d_over#0]. Empty-text mock -> EMPTY-TURN refusal, exit 4.
Bad-category mock -> SCHEMA-MISMATCH, exit 3. Sealed runner loader on the mock: 7 dialogs, 8 turns.
No blind panel was read item by item at any point.

## Known limits (predicted, not hidden)

- A mixed turn where 2+ piece arms' replies differ from 260's is an overlap and fails by construction; none is
  predicted (dev 0/85; 280m blind run 0/90 by the trigger count, and every 280m blind turn equalled some piece arm).
- Embedded called-wordings outside the four sealed 281 shapes keep 260's reply (inherited limit).
- The scorer compares replies for ownership but requires reply + write count + store identity for agreement.
- No panel was read item by item; TEST-ONLY panels are never tuned on.

## Numbered predictions

- P280n.1 (M1 blind joinpanel280n, once per arm): every 280m reply, write count and store byte-identical to
  the owner arm of its category (100%) with mixed owners decided mechanically from the piece arms' replies
  (single differing piece arm, else 260; 2+ differing = overlap = fail); 0 overlaps; 0 writes on question and
  small-talk turns; 0 wrong called answers and 0 unsupported claims (director claim check over the listed reply
  files); absolute rates per category reported with 260 beside 280m.
- P280n.2 (M2 frozen suites + verifier probes vs 260's rows, registered after-seal run): exactly the 3
  sessions152 reply-only moves, 0 moves everywhere else (bench, rt136 with labels identical to 260's, rt143),
  GATE identical to 260's; verifier vp exactly N06+E04, vs 0; 0 write changes anywhere.
- P280n.3 (M3 st234 + M4 notebook-zero): wellbeing 280m ≥ 260, every other item identical, 0 writes,
  0 setup/store diffs; 0 notebook differences 280m vs 260 on suites and panel.
- P280n.4 (falsifiers): any 280m reply differing from its mechanical owner arm, any suite/probe move outside
  the union list, any write on a question or small-talk turn, or any mixed turn with 2+ piece arms differing
  from 260 proves the re-test wrong.
