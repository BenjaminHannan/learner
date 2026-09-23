# Exp 280p — PASSMARKS (registered before the seal; the panel folder has not been opened item by item)

Arm under test: **280m** = `scripts/claude_loop280m_agent.py` + `artifacts/claude-join280m-20260923/loop280m-config.json`
(SEALED, unchanged — 280m seal 12/12 OK checked from the worktree root before writing this file; no code change to any agent).
Base arm: **260** = `scripts/claude_loop260_agent.py` + `artifacts/claude-openers260-20260922/loop260-config.json`.
Piece arms: **280b**, **281**, **282b** (their sealed agents + configs, read-only).
Spec: `design/v3/30-modes/280m-talking-join.md`, section "280n result and 280p, the last attempt" (director, 2026-09-23 13:28 UTC).
Panel: fresh blind joinpanel280p, same spec as joinpanel280m (90 turns: 25 ability, 8 teach + 12 called, 25 smalltalk, 10 mixed, 10 controls; columns dialog_id, turn_index, user_text, category, gold; categories ability / called / teach / smalltalk / mixed / control; fictional names only).

The verdict is PASS only if M1–M4 all pass. Any change to a sealed file after the seal = FAIL. No re-seal.
No silent re-runs: each registered command runs once; a driver-only fix after the seal is reported with its diff.
CPU only. At most 4 parallel processes; `uptime` / `df -g /` checked before heavy steps.

## Ownership (the rule that should have been used from the start, for EVERY turn)

The owner of each turn is decided mechanically from the piece arms' recorded rows:
the single piece arm (280b, 281 or 282b) whose reply, writes or store differ from 260's,
or 260 if none differs. If two or more piece arms differ from 260 on one turn,
that turn counts as an overlap and fails. Implemented in `scripts/claude_join280p_score.py`
(new, sealed here); no trigger evaluation, no text rules, no per-category fixed owners.

## Commands (from the repo root, uv prefix as in the scripts)

- Seal check first: 280m `artifacts/claude-join280m-20260923/SEAL.sha256.txt` 12/12 OK (done pre-seal).
- M1+M3-panel (registered, once): after the panel writer's
  `artifacts/claude-joinpanel280p-20260923/SEAL.sha256.txt` checks OK:
  `bash scripts/claude_280p_panel.sh artifacts/claude-join280p-20260923/run` — panel seal check, schema gate,
  then the panel once on all five arms with 280m's SEALED runner (`scripts/claude_join280m_run.py panel`),
  then the NEW scorer (`scripts/claude_join280p_score.py panel`); then smalltalkpanel234 once on 260 and once
  on 280m (`st234` mode, sealed runner + new scorer).
- M2+probes (registered, once, after the seal): `bash scripts/claude_280m_runall.sh artifacts/claude-join280p-20260923/run`
  (280m's SEALED runall: `fable_suitediff218 --only sessions152,bench` + `--only rt136` + rt143nogate + verifier
  probes vs 260's saved rows; scorer `scripts/claude_join280m_regscore.py` writes `run/regscore280m.json`).
  Output lands in this exp's own run dir; the sealed scripts are not modified.
- If the panel is not sealed 120 minutes after this seal: report and stop (poll every 2 min).
- Strict schema (columns dialog_id, turn_index, user_text, category, gold; categories ability / called / teach /
  smalltalk / mixed / control; `user` also accepted for the text): the runner refuses to run on any schema
  violation or empty turn text, and the scorer gates SCHEMA-MISMATCH (exit 3 = VOID). Runner and scorer were run
  end to end on a mock panel in exactly this schema before the seal (mock in /tmp, not sealed), covering all six
  categories, a mock overlap (FAIL exit 1, overlap listed), a writes-only-diff owner, the empty-text refusal
  (exit 4), and the SCHEMA-MISMATCH paths (exit 3).

## M1 — blind joinpanel280p, run once on five arms (260, 280b, 281, 282b, 280m)

Mechanical agreement and counts per category only (new scorer `panel` mode). Truth of claims and grammar are
director-graded, ungraded here; the file path of every 280m reply is listed for the claim check.
The scorer prints ids of misses, never item text.

| bar | pass if |
|---|---|
| every 280m reply, write count and store byte-identical to the mechanical owner arm | 100% of turns (90/90) |
| overlaps (2+ piece arms differing from 260 on one turn) | 0 |
| question and small-talk turns with writes on 280m | 0 |
| wrong answers on called and control questions on 280m | 0 (director claim check; scorer lists reply files) |
| unsupported claims anywhere on 280m | 0 (director checks; scorer reports old-sheet scan + reply files) |

Report only (no bar): absolute rates per category, 260 beside 280m; mechanical owner counts.

Predicted: 100% agreement (across 180 fresh turns in two panels every 280m turn equalled a piece arm with
0 overlaps and 0 wrong answers; the mechanical rule applied to every turn gives 90/90 on both prior panels);
0 overlaps; 0 question/smalltalk writes; 0 store diffs 280m vs 260 except where a piece arm differs.

## M2 — frozen suites vs 260's saved rows (GATE identical to 260's)

Suites: rt136, rt143, sessions152, bench. Registered post-seal run with 280m's sealed runall/regscore.

**Predicted moves (exactly this list — the same union as 280m/280n, nothing else):**
- sessions152: exactly 280's 3 reply-only moves, verdict UNHELPFUL -> UNHELPFUL, stored identical,
  0 write changes: S2-casual-friends#1, S3-teachers-correction#0, S4-pets-identity#9 — old reply -> sealed `CAN280`.
  GATE identical to 260's.
- bench 4x200: 0 moved. rt136 (145 units): 0 field diffs; vs-138j-base labels identical to 260's; GATE identical.
- rt143_nogate (124 rows): 0 moved.
- Verifier probes vs 260's saved `run/vp-n.json` / `run/vs-n.json`: **exactly 2 changed rows, N06 (281) and E04 (282)**;
  supp 0 changes.
- Any other moved unit, any verdict flip, or any write change fails M2.

## M3 — smalltalkpanel234, run once on 260 and once on 280m

56 items, each run once per arm (sealed `run.py st234`), scored by the new scorer `st234` mode with per-arm
fitting sets from the recorded canonical probes. This panel is NOT run before the seal (its registered run is
its only run; deviation from "pilot everything", forced by the run-once rule).

| bar | pass if |
|---|---|
| wellbeing (expect small_talk): fitting hits on 280m | ≥ 260's hits (260 shown beside) |
| every other item: 280m reply == 260 reply | all equal |
| setup replies and stores 280m vs 260 | 0 diffs |
| turns with writes on 280m | 0 |

Predicted: repeat of the 280m/280n observation (wellbeing 17/20 vs 16/20, other 36/36, 0 writes/diffs; the one
move the same row 282 moved), barring the known 1-in-800 flake.

## M4 — notebook-zero

0 notebook differences 280m vs 260 on the suites (M2: 0 write changes, 0 store diffs outside the piece moves)
and on the panel (M1 table: 0 store diffs except where a piece arm already differs).

## Abstain flips

Any unpredicted flip toward an abstain counts against its mark; that item is then run alone 5 times and
reported, with whether the 228 guard was installed (it is: SrcGuardMixin228 first, asserted in `_check`).
The two predicted verifier moves (N06, E04) move away from broken abstains/mode-status lines, not toward an
abstain, so no 5x follow-up applies to them.

## Mock set (not a mark; scorer-tested, mock in /tmp, never sealed)

Mock panel in exactly the schema {dialog_id, turn_index, user_text, category, gold} covering all six
categories (ability / called / teach / smalltalk / mixed / control): clean 6/6 PASS exit 0; mock overlap
(280b + 281 both differing from 260) 6/7 FAIL exit 1 with the overlap id listed; writes-only-diff turn owned
by 281 and PASS; empty-text refusal exit 4; unexpected-category and missing-key SCHEMA-MISMATCH exit 3.
Sealed runner loader checked on the same mocks (6 dialogs / 6 turns loaded; empty exit 4; bad category exit 3).

## Known limits (predicted, not hidden)

- A turn where 2+ piece arms differ from 260 is an overlap and fails by construction; prior panels had 0/180.
- Embedded called-wordings that match none of the four sealed 281 shapes keep 260's reply (inherited limit).
- The known flake: about 1 in 800 bench items (rarely rt143) flips between identical runs toward an abstain;
  reported as-is with a 5x follow-up if hit.
- This is the join's last attempt per the director: if 280p fails, the join closes.

## Numbered predictions

- P280p.1 (M1 blind joinpanel280p, once per arm): every 280m reply, write count and store byte-identical to
  the mechanical owner of its turn (100%, 90/90); 0 overlaps; 0 writes on question and small-talk turns;
  0 wrong called/control answers and 0 unsupported claims (director claim check over the listed reply files);
  absolute rates per category reported with 260 beside 280m.
- P280p.2 (M2 frozen suites + verifier probes vs 260's rows, registered post-seal run with sealed
  runall/regscore): exactly the 3 sessions152 reply-only moves, 0 moves everywhere else (bench, rt136 with
  labels identical to 260's, rt143), GATE identical to 260's; verifier vp exactly N06+E04, vs 0; 0 write changes.
- P280p.3 (M3 st234 + M4 notebook-zero): wellbeing 280m ≥ 260, every other item identical, 0 writes,
  0 setup/store diffs; 0 notebook differences 280m vs 260 on suites and panel except where a piece arm differs.
- P280p.4 (falsifiers): any 280m reply differing from its mechanical owner arm, any suite/probe move outside
  the union list, any write on a question or small-talk turn, or any turn with 2+ piece arms differing from 260
  proves the join wrong.
