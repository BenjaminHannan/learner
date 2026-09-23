# Exp 292t — PASSMARKS (registered before the seal; the panel folder has not been opened item by item)

Arm under test: **292t** = `scripts/claude_loop292t_agent.py` + `artifacts/claude-join292t-20260923/loop292t-config.json`
(SEALED here; no code change to any agent after the seal).
Base arm: **292** = `scripts/claude_loop292_agent.py` + `artifacts/claude-merge292-20260923/loop292-config.json`.
Piece arms (SEALED here, read-only after): **292+280b** (`scripts/claude_292t_280b_agent.py`),
**292+281** (`scripts/claude_292t_281_agent.py`), **292+282b** (`scripts/claude_292t_282b_agent.py`),
all on the 292t config.
Spec: `design/v3/30-modes/280m-talking-join.md`, section "292t: the talking layers on the main base 292"
(director, 2026-09-23 15:01 UTC).
Panel: fresh blind joinpanel292t, same spec as joinpanel280m (90 turns: 25 ability, 8 teach + 12 called,
25 smalltalk, 10 mixed, 10 controls; columns dialog_id, turn_index, user_text, category, gold;
categories ability / called / teach / smalltalk / mixed / control; fictional names only).

The verdict is PASS only if M1–M2–M3 all pass. Any change to a sealed file after the seal = FAIL. No re-seal.
No silent re-runs: each registered command runs once; a driver-only fix after the seal is reported with its diff.
CPU only. At most 4 parallel processes; `uptime` / `df -g /` checked before heavy steps.

## Ownership (mechanical, for EVERY turn)

The owner of each turn is decided mechanically from the single-layer arms' recorded rows:
the single single-layer arm (280b, 281 or 282b) whose reply, writes or store differ from 292's,
or 292 if none differs. If two or more single-layer arms differ from 292 on one turn,
that turn counts as an overlap and fails. Implemented in `scripts/claude_join292t_score.py`
(new, sealed here); no trigger evaluation, no text rules, no per-category fixed owners.

## Commands (from the repo root, uv prefix as in the scripts)

- M1+M3-panel (registered, once): after the panel writer's
  `artifacts/claude-joinpanel292t-20260923/SEAL.sha256.txt` checks OK:
  `bash scripts/claude_292t_panel.sh artifacts/claude-join292t-20260923/run` — panel seal check, schema gate,
  then the panel once on all five arms with the SEALED runner (`scripts/claude_join292t_run.py panel`),
  then the NEW scorer (`scripts/claude_join292t_score.py panel`); then smalltalkpanel234 once on 292 and once
  on 292t (`st234` mode, sealed runner + new scorer).
- M2+probes (registered, once, after the seal): `bash scripts/claude_292t_runall.sh artifacts/claude-join292t-20260923/run`
  (NEW runall: `fable_suitediff218 --only sessions152,bench` vs 292's rows + `--only rt136` + rt143nogate +
  verifier probes vs 292's saved rows; scorer `scripts/claude_292t_regscore.py` writes `run/regscore292t.json`).
  Output lands in this exp's own run dir; the sealed scripts are not modified.
- If the panel is not sealed 120 minutes after this seal: report and stop (poll every 2 min).
- Strict schema (columns dialog_id, turn_index, user_text, category, gold; categories ability / called / teach /
  smalltalk / mixed / control; `user` also accepted for the text): the runner refuses to run on any schema
  violation or empty turn text, and the scorer gates SCHEMA-MISMATCH (exit 3 = VOID). Runner and scorer were run
  end to end on a mock panel in exactly this schema before the seal (mock in /tmp, not sealed), covering all six
  categories, a mock overlap (FAIL exit 1, overlap listed), a writes-only-diff owner, the empty-text refusal
  (exit 4), and the SCHEMA-MISMATCH paths (exit 3).

## M1 — blind joinpanel292t, run once on five arms (292, 280b, 281, 282b, 292t)

Mechanical agreement and counts per category only (new scorer `panel` mode). Truth of claims and grammar are
director-graded, ungraded here; the file path of every 292t reply is listed for the claim check.
The scorer prints ids of misses, never item text.

| bar | pass if |
|---|---|
| every 292t reply, write count and store byte-identical to the mechanical owner arm | 100% of turns (90/90) |
| overlaps (2+ single-layer arms differing from 292 on one turn) | 0 |
| question and small-talk turns with writes on 292t | 0 |
| wrong answers on called and control questions on 292t | 0 (director claim check; scorer lists reply files) |
| unsupported claims anywhere on 292t | 0 (director checks; scorer reports old-sheet scan + reply files) |

Report only (no bar): absolute rates per category, 292 beside 292t; mechanical owner counts.

Predicted: 100% agreement (pilot on 66 own dev dialogs / 111 turns: 292t byte-identical to the mechanical
owner on 111/111, with 0 overlaps, 0 question writes and 0 old-sheet hits; owners there 280b:12 turns,
281:4 turns, 292:95 turns); 0 overlaps; 0 question/smalltalk writes; 0 store diffs 292t vs 292 except
where a single-layer arm differs.

## M2 — frozen suites vs 292's saved rows (GATE identical to 292's)

Suites: rt136, rt143, sessions152, bench. Registered post-seal run with the sealed runall/regscore.

**Predicted moves (exactly this list — every move by id with its owning layer, nothing else):**
- sessions152: exactly 3 reply-only moves, all owned by the **280b** arm (281: 0, 282b: 0 on the pilot),
  verdict UNHELPFUL -> UNHELPFUL, stored identical, 0 write changes:
  S2-casual-friends#1, S3-teachers-correction#0, S4-pets-identity#9 — old reply -> sealed `CAN280`.
  GATE as clean as 292's.
- bench 4x200: 0 moved. rt136 (145 units): 0 field diffs 292t vs 292 (direct row compare);
  vs-138j-base labels identical to 292's; GATE identical to 292's (the NOT-clean string is inherited
  from 292, byte-identical).
- rt143_nogate (124 rows): 0 moved.
- Verifier probes vs 292's saved rows: **exactly 2 changed rows, N06 owned by 281** (name-of + stored ->
  stored answer "Tomas's boss is Mirela.", ev 0, store identical) **and E04 owned by 282b** (whats-up +
  empty store -> head greeting reply, ev 0, store identical); supp 0 changes. The 281 arm moves exactly
  N06, the 282b arm exactly E04, the 280b arm 0 (pilot).
- Any other moved unit, any verdict flip, or any write change fails M2.

## M3 — smalltalkpanel234, run once on 292 and once on 292t

56 items, each run once per arm (sealed `run.py st234`), scored by the new scorer `st234` mode with per-arm
fitting sets from the recorded canonical probes. This panel is NOT run before the seal (its registered run is
its only run; deviation from "pilot everything", forced by the run-once rule).

| bar | pass if |
|---|---|
| wellbeing (expect small_talk): fitting hits on 292t | ≥ 292's hits (292 shown beside) |
| every other item: 292t reply == 292 reply | all equal |
| setup replies and stores 292t vs 292 | 0 diffs |
| turns with writes on 292t | 0 |

Predicted: 292t equal to or better than 292 on every figure (the talking layers only ever substitute the
reply of a turn the head already mishandled and never write; pilot probes on all five arms show 0 writes
and identical stores on the canonical small-talk probes).

## Abstain flips

Any unpredicted flip toward an abstain counts against its mark; that item is then run alone 5 times and
reported, with whether the 228 guard was installed (it is: SrcGuardMixin228 first, asserted in `_check`).
The two predicted verifier moves (N06, E04) move away from broken abstains/mode-status lines, not toward an
abstain, so no 5x follow-up applies to them.

## Mock set (not a mark; scorer-tested, mock in /tmp, never sealed)

Mock panel in exactly the schema {dialog_id, turn_index, user_text, category, gold} covering all six
categories (ability / called / teach / smalltalk / mixed / control, plus the `user` alias): clean 8/8 PASS
exit 0 (owners 280b:1, 281:1, 282b:1, 292:5); mock overlap
(280b + 281 both differing from 292) 7/8 FAIL exit 1 with the overlap id listed; writes-only-diff turn owned
by 281 and PASS exit 0; question-turn writes-only-diff correctly FAILs the 0-question-writes bar;
empty-text refusal exit 4; unexpected-category and missing-key SCHEMA-MISMATCH exit 3.
Sealed runner loader checked on the same mocks (6 dialogs / 8 turns loaded; empty exit 4; bad category exit 3).

## Known limits (predicted, not hidden)

- A turn where 2+ single-layer arms differ from 292 is an overlap and fails by construction; pilot had 0/111.
- Embedded called-wordings that match none of the four sealed 281 shapes keep 292's reply (inherited limit).
- The known flake: about 1 in 800 bench items (rarely rt143) flips between identical runs toward an abstain;
  reported as-is with a 5x follow-up if hit.
- 292's rt136 GATE string is NOT clean (inherited from 291/292: 13 WRONG-WRITE + 1 junk write vs 138j);
  the bar is byte-identical to 292's, which the pilot holds exactly.

## Numbered predictions

- P292t.1 (M1 blind joinpanel292t, once per arm): every 292t reply, write count and store byte-identical to
  the mechanical owner of its turn (100%, 90/90); 0 overlaps; 0 writes on question and small-talk turns;
  0 wrong called/control answers and 0 unsupported claims (director claim check over the listed reply files);
  absolute rates per category reported with 292 beside 292t.
- P292t.2 (M2 frozen suites + verifier probes vs 292's rows, registered post-seal run with sealed
  runall/regscore): exactly the 3 sessions152 reply-only moves owned by 280b, 0 moves everywhere else
  (bench, rt136 with labels identical to 292's, rt143), GATE identical to 292's; verifier vp exactly
  N06(281)+E04(282b), vs 0; 0 write changes.
- P292t.3 (M3 st234): wellbeing 292t ≥ 292, every other item identical, 0 writes, 0 setup/store diffs;
  0 notebook differences 292t vs 292 on suites and panel except where a single-layer arm differs.
- P292t.4 (falsifiers): any 292t reply differing from its mechanical owner arm, any suite/probe move outside
  the predicted list, any write on a question or small-talk turn, or any turn with 2+ single-layer arms
  differing from 292 proves the join wrong.
