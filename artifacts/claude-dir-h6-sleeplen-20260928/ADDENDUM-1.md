# dir-h6 addendum 1: a mid-night curve and a carry-over row (both report only)

Written 2026-09-28 21:10 UTC (`date -u`) by helper H10 (Claude), for the Director, to answer the review that flagged the H6 marks.
**Written before any score of this test was seen.** Checked at 21:07 UTC: this folder holds only DESIGN.md, PASSMARKS.md,
SEAL-code.sha256.txt and queue-h6-sleeplen.md (`ls`); origin/main has no `runs/` folder for it and its last commit for the folder is
5c64fbcee ("H6 sleep-length design (held)"); no `dirh6-seed*.json` exists anywhere in the repo (`grep`). Checked again at 21:12 UTC
after fetching: origin/main and origin/builder-outbox hold no dirh6 result file (only H7's held queue jobs and kit). No arm B has ever run.
The sealed files are unchanged (sha256 as in SEAL-code.sha256.txt): PASSMARKS.md 2568077…, DESIGN.md 9437f2d…,
scripts/claude_dir_h6_sleeplen.py 3185998…. Nothing here edits them.

## 1. What this supersedes, and what it does not
- **No mark, threshold, arm, seed, cap or verdict word of PASSMARKS.md changes.** M0 to M3c, INTEGRITY, PASS (rescue), proved wrong
  and partial read exactly as sealed (lines 26-49). The two rows below can neither create nor rescue a verdict.
- It **adds two report-only rows** after PASSMARKS.md line 59 (the "Report only (decides nothing)" list, lines 51-59):
  R1 the mid-night curve (section 2) and R2 the carry-over row (section 3).
- It **replaces two commands** that name `claude_dir_h6_sleeplen.py`: in queue-h6-sleeplen.md line 11 and, in the kit H7 built since
  (handoff/kit/sleeph6r/box/drive.sh, its `python -B $H6 smoke` and `python -B $H6 run` lines). Neither file is sealed by hash. The new
  commands are in section 4, with a fall-back that keeps the sealed run alive.

## 2. R1: the mid-night curve (report only; built, not run)
**Why (suggested):** L lost the grid gain and B is the "gentler night" fix. The end-of-night marks cannot say whether L moved too far
(rose, then fell back), memorised its own puzzles, or never learned. Scoring inside the night can.

**What is scored** (the sealed judge, 48 rounds, v2 stop rule, no gradient, eval mode):
- *fresh*: the sealed `day_grids` test (400 puzzles the night never sees, the same set the morning marks use);
- *own*: that day's own grid puzzles (the ones half of the night's day batches come from; about 300 after exclusions);
- at night steps **300, 1,000, 2,000 and 6,000** for L and B (S at its own 300), on every night of every seed. N has no night.
Step 0 is not re-scored: it is the arm's previous morning `day_grids` (night 1: the base net) and its "day tries" grids in the sealed JSON.

**How** (`scripts/claude_dir_h6_sleeplen_add1.py`, new file): it imports the sealed script and, for the length of one run, wraps
`N3.train_step` (count steps, score at a milestone) and `N3.night` (say which arm/day/items), then puts them back. The torch and CUDA
random state is saved and restored around every scoring call, so batches, round draws and weights are meant to be exactly those of
an unhooked run. A scoring error is written into the curve file and the night goes on. Output: `dirh6-curve-seed{S}.json`
(rewritten after every night); the marks file `dirh6-seed{S}.json` keeps the sealed layout.
- Its `smoke` runs the tiny CPU config twice, hooks off then on, and asserts every morning / day / lost number is identical, the
  hooks are put back, the milestones are 2, 4, 6, 8 (S: 2, 4, 6), the curve's last point equals the morning score, and `--save-final` files load.
- **Untested with torch** (this box has none): py_compile only. The hook logic was checked with stub `torch` and stub sealed modules
  (milestones for tiny and real settings, restore of the patched names, error path, save-final): passed; that stub file is not shipped.

**Reading rule** (`scripts/claude_dir_h6_curve_read.py`, pure python, selftest ok: 6 cases, 11 edge cases at 39 against 40 and 269 against
270 of 300, 6 file checks). Per seed x night x arm (L, B), the first line that applies. F = fresh score, O = own score, f0/own0 = step 0,
"early" = steps 300, 1,000, 2,000. T = 40 counts: M1's +40 (PASSMARKS line 29) and twice the +-20 wobble in DESIGN.md section 1.

| # | label | when | plain words |
|---|---|---|---|
| 0 | NO-ROOM | own0 is 90% or more of the own puzzles (270 of 300) | the net already solves them; nothing to read |
| 1 | NOT-LEARNING | O(end) - own0 < 40 and max F - f0 < 40 | both low: the night is not learning |
| 2 | MEMORISED | O(end) is 90% or more of own, and max F - f0 < 40 | own puzzles near the top, fresh ones flat |
| 3 | PEAK-THEN-DECAY | max F(early) - F(end) >= 40 and max F(early) - f0 >= 40 | rose, then fell back: moved too far |
| 4 | GAIN-KEPT | F(end) - f0 >= 40 | the fresh-grid gain is still there at the end |
| 5 | UNCLEAR | none of the above | say so |

Output is a table and counts "x of N arm-nights" per label (N = 12 when all 4 seeds x 3 nights finish), the mean fresh change per arm,
night and step, and two integrity lines: the curve's last point equals the morning score (it is the same net on the same 400 puzzles,
so it must; x of N), and on night 1 L at step 300 equals S's morning `day_grids` (L's first 300 steps are S's whole night: same
batches, round draws and rate; equal on CPU, may differ by GPU wobble; x of 4 seeds). A mismatch is shown, never hidden.

**How the pair is read (suggested, untested):** L PEAK-THEN-DECAY with B GAIN-KEPT fits "the rate was too high for that many steps"
(the design's suspect); both PEAK-THEN-DECAY says lowering the rate alone did not stop the fall back; L MEMORISED with B MEMORISED
points at the repeat count / replay mix; B NOT-LEARNING is the "may simply not have learned" case that PASSMARKS line 46-47 already
names. **It says nothing about sums** (not scored mid-night) and MEMORISED is a pattern, not proof of memorising.

**Cost (shown arithmetic, wall clock untested):** added scoring per seed = S 700 + L 2,800 + B 2,800 = 6,300 puzzles a night, 18,900 over
3 nights, on top of the sealed run's 35,800 judged puzzles (2,200 base + 3 nights x 4 arms x (2,200 morning + up to 600 day tries)). By
rounds, a judged puzzle is 48 no-gradient rounds; a trained one is about 8.5 forward rounds plus a backward pass through about 3
(code: `randint(1, 16)`, `randint(1, min(total, 6))`). The seed trains 36,900 steps x 256 puzzles, so the added scoring is about 0.5 to
0.8% of the training work (backward at 1x to 3x a forward). That is small against the queue's $4 cap, but GPU efficiency of a batch of
100 against 256 is not measured. The sealed `night_minutes` now include the scoring; `score_minutes` in the curve file gives it per night.

## 3. R2: the carry-over row (plan only; not built)
**Question (suggested):** does a night on sums and grids change how a net does on a kind it never trains on? **What can be scored
now:** zero-shot accuracy (no example given) on one code-made kind. **What cannot:** whether a slept net *learns* that kind faster; that
needs the few-example ruler (H1) and the slept nets, and is a separate test.
- **Kind and panel:** `rank` from scripts/claude_dir_h1_kinds.py (n = 9 digits, tokens the sums practice already uses), 300 puzzles from a NEW
  seed range (not PANEL_SEED 9402900+n or POOL_SEED 9412900+seed), unique by `rank_key`, disjoint from every H1 dev/holdout/pool key
  (`panels("rank")` and `make_pool("rank", seed, banned)` return the keys in code; nothing scores them), from the sealed H6 tests and
  from the day items. Made by code only.
- **Scorer:** a copy of `N3.judge` (same 48 rounds and stop rule) whose right/wrong is `claude_dir_h1_kinds.check(item, grid)`. Why it
  is not in the wrapper: 358u's `tensors()` calls `E.ENVS.index(items[0].env)` (claude_rsn358u_run.py:41) and ENVS is sums, grids,
  numbers (claude_rsn358a_envs.py:40), so a "rank" item raises there; and `N3.judge` grades with `E.check`, which sends any env other
  than sums or grids to the numbers checker (claude_rsn358a_envs.py:317-322): a rank item would be graded by the wrong rule without
  an error. The adapter hands `R.tensors` the same tokens under a known env label (358u overwrites the env id with FIXED_ENV anyway)
  and grades the original item with the H1 checker. **Untested:** that `R.tensors` accepts a 2 x 9 digit grid. It needs
  a 5-item CPU dry run in a new file before any live use; a wrong adapter inside a live seed could crash it.
- **Where and when:** the base net and every arm's morning net after each night (N, S, L, B): 13 scores of 300 per seed, 3,900
  puzzles, about 0.1% of the training work by the section 2 arithmetic.
- **Reading:** "at floor" if every score on the seed is 15 of 300 or less (5%, an arbitrary marker fixed here); then the row is
  printed as floor and not read. Otherwise "carried over" only if an arm is at least 40 of 300 above the base net on at least 3 of 4 seeds.
  Expect floor (suggested): a net never shown "rank the list" has no reason to do it. Report only.
- **Enabling the real test:** `--save-final` (off by default; the sealed script saves no weights) writes S-, L- and B-final.pt (N is the input
  checkpoint), about 26 MB each (6,438,302 weights x 4 bytes; the 358u loop's weight count, PASSMARKS-draft line 38 of that folder; file
  size not measured), so a later few-example job could start from the slept nets. **The sleeph6r kit never copies .pt files back**
  (section 4.4), so this only works after a kit change.

## 4. Edits for the Director's kit (handoff/kit/sleeph6r, built by H7 at b0d1d74bc; nothing here touches it)
The kit is pinned: vstart.sh:101-103 refuses to go on unless drive.sh on the rental equals the pinned copy, and `git archive "$PIN" scripts ...`
(vstart.sh:21 and :71) ships the whole `scripts` folder of the pinned commit. So the wrapper reaches the rental only if the Director makes a NEW
kit copy (for example `handoff/kit/sleeph6r2`; the existing files stay as they are) and re-points PIN in h7-dirh6-1-start to a commit that holds
that copy, this addendum's scripts and both sealed sets. The seal checks (dir-h6 3 of 3, slp-358n3 18 of 18) are not affected: no sealed file changes.
1. box/drive.sh: keep `python -B $H6 smoke` (must print "smoke ok"). After the `st "SMOKE ok"` line add
```bash
H6A=scripts/claude_dir_h6_sleeplen_add1.py; RUNNER=$H6
python -B $H6A smoke > W/smoke-add1.txt 2>&1
if grep -q '^smoke ok' W/smoke-add1.txt; then RUNNER=$H6A; st "SMOKE-ADD1 ok (curve on)"
else st "CURVE-SKIPPED: add1 smoke failed: $(grep -m1 -E '^[A-Za-z_.]*(Error|Exception)' W/smoke-add1.txt | cut -c1-160)"; fi
```
   and launch with `python -B $RUNNER run ...` in place of `python -B $H6 run ...`. **A failed add1 smoke must not stop the job and must not
   be patched:** the seeds then run with the sealed script exactly as PASSMARKS sealed them, and the curve is simply absent.
2. vcommon.sh: EXPECT stays `dirh6-seed%S.json`; the curve file is optional and never gates a collect.
3. The curve file comes back in the tar of every non-.pt file in W (vcommon.sh:124-127) and lands in the Mac's out/W/s{S}/, but vcollect.sh:35
   copies only `dirh6-seed{S}.json`, `.log` and `.err` into the repo: add `$R/dirh6-curve-seed${R#s}.json` to that list.
4. `--save-final`: the kit never copies .pt files back (vcommon.sh:109 and :124-127, vguard.sh:32), so the slept nets would be destroyed with the
   rental. Leave it off unless the copy-back is also changed (about 77 MB a seed).
5. After collect: `python3 scripts/claude_dir_h6_curve_read.py read --runs artifacts/claude-dir-h6-sleeplen-20260928/runs --out
   artifacts/claude-dir-h6-sleeplen-20260928/curve-reading.json`. The blind recount of the marks still uses only PASSMARKS.md and
   `dirh6-seed*.json`, so R1 cannot shift a mark.
6. Report R1 as its label counts and integrity lines only, after the verdict; R2 only if it was built and smoke-tested.

## 5. Not tested, risks, and the Director's calls
- **Untested (needs torch):** the wrapper's `smoke` and `run`, `--save-final`, the whole R2 plan. **Tested here:** the reader (selftest) and
  the hook logic against stub modules.
- **Risk:** the wrapper touches the sealed night path. If the hooks changed training on a GPU (they should not: no gradient, RNG restored),
  the marks would be affected without any flag; only the tiny CPU smoke checks this (the night-1 "L at step 300 equals S" line checks that the
  two arms train the same 300 steps, not the hook: no scoring happens before step 300). Suggested mitigation: the fall-back in section 4.1.
- **Calls for the Director:** (a) use the wrapper (recommended) or the sealed script alone; (b) `--save-final` (recommended off with the kit as it is; on only together with a copy-back change, if a
  few-example carry-over test is planned); (c) whether R2 is worth a new adapter file (my view: only after R1 has been read).
