# ADDENDUM-1 to PASSMARKS.md (held-out kinds: graph and rank): two review fixes, H1-a and H1-b

Written 2026-09-28 20:51 UTC (`date -u`) by Director helper H10, on the Director's decision, from the adversarial review
`artifacts/claude-dir-h8-review-20260928/REVIEW.md` section 3.4 (items H1-a and H1-b). New file; PASSMARKS.md, DESIGN.md, the seal and
the sealed scripts are not edited.

**Order (checked 20:51 UTC):** written before any score of this test was seen. On origin/main (commit d0a10db78) this folder holds only
DESIGN.md, PASSMARKS.md, SEAL-code.sha256.txt, SELFTEST-kinds.log, SELFTEST-marks.log and queue-h1-heldout.md: no adapt.json, holdout.json,
DEV-GATE-*.json, SCORE-*.json or SOURCE-CHECK.json. origin/builder-outbox has no file under this folder. The job `dir-h1-heldout` is running on
the Mac; I cannot see its local files (untested), and I have seen no score of it.

## How this is applied
The running job uses the sealed code, so its `DEV-GATE-<kind>.json` still applies the sealed V3 and it may open a kind's holdout. These two
additions are computed afterwards, from the same raw dev files (`runs/<kind>/<arm>-s<seed>-<init>/adapt.json`), by the new script
`scripts/claude_dir_h1_marks_add1.py` (pure python; `selftest` passes here, `check --kind <kind>` writes `ADDENDUM1-CHECK-<kind>.json`,
`rollup` prints the sentence). The blind recount runs it. `scripts/claude_dir_h1_marks.py` is imported, not edited.

## (a) Supersedes PASSMARKS.md line 16 (V3 usable ladder)
Sealed line: "at least one of the four arms in at least one seed has accuracy strictly above 10% and strictly below 90% (31 to 269 of 300) on
at least three of the eight positive rungs."

Replaced by **V3-add1**: on the dev graded panel, in at least one seed, the practised loop **and** the fresh loop are both strictly above
10% and strictly below 90% (31 to 269 of 300) on the **same** at least three of the eight positive rungs (a rung counts only when both arms
are in the band on it). Not met: the kind is INCONCLUSIVE, exactly as V3 says.
- Why (H1-a, shown as a possibility from the code, `scripts/claude_dir_h1_marks.py:67-74`): the sealed V3 passes if any one arm is in the band,
  so a ladder where only the fresh plain net is in the band and the practised loop is at 0 or at 300 passes it. M2 compares the practised loop
  with the fresh loop; both need rungs where they can still move.
- If the running job already opened a kind's holdout because the sealed V3 passed but V3-add1 fails: the holdout numbers are reported as they
  stand, the kind's verdict is **INCONCLUSIVE**, and it gets no roll-up credit. Nothing is re-scored and nothing is hidden.
- The sealed V0, V1, V2 and V2k are unchanged.

## (b) Adds one validity row (after PASSMARKS.md line 15): V4, practised plain accuracy at k = 16,384 on dev
Per kind, per seed, on the dev graded panel: the practised plain net's right answers out of 300 at k = 16,384.
- **Label rule:** if it is below 90% (fewer than 270 of 300) in **either** seed, the kind's plain comparisons (M1 and M2b) are labelled
  **"expressivity"** (the plain net, one pass through 8 layers, may be unable to do the job at any number of examples), and **M2 (practised
  loop against the fresh loop) carries the claim** on that kind. At 270 of 300 or more in both seeds the label is "few-example".
- This changes no mark and no threshold, and it is not a validity failure (no INCONCLUSIVE). It changes only what the roll-up may say.
- **Roll-up qualifier (supersedes the wording of PASSMARKS.md lines 35-37 for a labelled kind):** a kind that is PASS and labelled
  "expressivity" may be quoted only as "the practised loop learns from fewer examples than a fresh looped net (M2, two seeds); the same-size
  plain net comparison there is labelled expressivity and is not quoted". The sealed sentence "shown on mazes and on two further held-out
  kinds, in two seeds each" needs both kinds PASS **and** labelled "few-example". REFUTED and NOT-SHOWN rules are unchanged. The exact strings
  are in `sentence()` in the script (selftested).

## (c) Calibration on the published maze dev ladders (shown, arithmetic on raw files; not evidence about the new kinds)
Recounted from `artifacts/claude-fewex-20260927/eq-runs/*/adapt.json` (8 of 8 arm-seeds equal the copy inside the sealed marks script).
- V3-add1 shared rungs, seed 0: k = 64, 256, 4,096 (3 rungs: met). Seed 1: k = 64 only (1 rung). Seed 1 is short because the fresh loop's
  rung k = 1,024 collapsed (0 of 300) and the practised loop sits above the band at k = 256 (277) and k = 4,096 (292).
  So the maze dev ladder meets V3-add1 in one seed of two.
- V4 on mazes: practised plain at k = 16,384 on dev is 210 of 300 (70.0%) in seed 0 and 215 of 300 (71.7%) in seed 1. **Under this row the maze
  plain comparison would be labelled "expressivity" too.** No published maze verdict is changed; but the M1 / M2b margins on mazes carry that
  label if the row is applied to them (suggested reading: the plain net may partly be limited by what one pass can express).

**Director decision point (one line):** V3-add1 as written keeps the sealed "at least one seed" (constant `NEED_SEEDS = 1` in the script).
Requiring it in **both** seeds would make the maze dev ladder itself fail (seed 1: 1 shared rung). The script reports the both-seeds result
next to the sealed-structure result (`V3_add1_both_seeds_report_only`); it does not gate on it. If the Director wants both seeds, this
addendum and the constant change together, before any dev score is read.

## Not changed
M1 to M4, C1, their thresholds (5.0, 5 of 8 rungs, 20.0, 5.0), the ruler, the sources, the holdout-once rule, the never-pooled-seeds rule,
the "result that would prove the claim wrong" list, and everything reported-only.

## What I could not test
Only pure-python parts were run: `scripts/claude_dir_h1_marks_add1.py selftest` prints "selftest ok" (log:
`artifacts/claude-dir-h10-addenda-20260928/h1-add1-selftest.log`), and `check` / `rollup` were run once on fake files in a scratch folder.
The real `adapt.json` files of graph and rank do not exist on main; their layout is the one the sealed `load_counts` reads.
