# History read (each round may look at its earlier states): pass marks

Written 2026-09-29 (after 02:38 UTC, `date -u`; commit time is in git) by helper "Huginn ideas", on top of main `401a2cb98`, **before any code of this test has been run** (the box has no torch) and before any score of it exists. No mark changes after this file is committed. Design: DESIGN.md. Plug-ins: scripts/claude_dir_hist_net.py (window 8), scripts/claude_dir_hist_net_w1.py (control, window 1). Numbers are "x of N". Labels: shown / suggested / untested.

## The one change
Each round of the loop also reads the last 8 states of the same cell (a learned attention, 98,688 extra weights, +6.0%). Nothing else differs from the loop (prompt re-added every round is already there; stop head, round counts, practice recipe, learner, ladder all the loop's).

## Arms (seeds 0 and 1, the equal-practice ruler, dev panel only, `--init pre`; source practice = the ruler's qualified recipe, ADDENDUM-3)
- **HIST**: window 8, retrained from scratch on the source practice (sums and grids, no maze), then the ladder.
- **CTRL-W1**: same code, window 1 (only the previous state is readable: same extra weights, same compute, no history). Also retrained and laddered.
- **The loop** (`artifacts/claude-fewex-20260927/eq-runs/loop-s{0,1}-pre`, not retrained) and **the plain net** (`plain-s{0,1}-pre`, not retrained).
- The holdout is not opened. Blind panels never touched. Each seed is judged alone, seeds never pooled.

## Reads (from `adapt.json`, computed by `scripts/claude_dir_h12_marks.py f_all` unedited)
F_eq = mean over k = 1,4,16,64,256,1024,4096,16384 of 100 x right/300, 9x9 dev. F_few = same over k = 1,4,16,64. Each net's score is the higher of its learned-stop and fixed-16 reads.
Baseline loop F_eq 51.21 / 51.67, plain 34.04 / 32.62 (recounted by `claude_dir_hist_marks.py selftest`; the loop reads reproduce 51.21 and 51.67).

## Validity (before any mark is read; failure = INVALID)
V1. Source guard, both arms both seeds: at least 190 of 200 on 4-digit sums and 190 of 200 on 5x5 grids after practice, and every 2-D weight matrix has a nonzero fp32 gradient (the harness's own check).
V2. Selftests `scripts/claude_dir_hist_selftest.py` ("SELFTEST ok": the window-8 net equals the loop while the read output weight is zero, the ring never holds more than 8 states, the control holds 1) and `claude_dir_hist_marks.py selftest` ("SELFTEST-marks ok") are logged before any run.
V3. Stored weights: HIST and CTRL-W1 both 1,744,414 (= 1,645,726 + 98,688).

## Marks (all required, in BOTH seeds)
- **H1 (F_eq).** HIST F_eq >= max(loop F_eq, CTRL-W1 F_eq) + **10.0** points.
- **H2 (F_few, its own row).** HIST F_few >= max(loop F_few, CTRL-W1 F_few) + **10.5** points.
- **P (plain-net row).** HIST F_eq >= plain F_eq + **10.0** points (34.04 / 32.62). A same-size plain net gains +0.0 by construction and has no rounds to read, so it cannot pass. Dev layouts are banned from the practice pool, so this is not memorised layouts.
- Report-only: per-rung counts, 7x7 and 11x11 dev, old-kind counts before and after both sleeps, `mean_rounds` and `cap_hits`, the attention weight on the newest state per round (does it use older states at all?), and the same read repeated on the CTRL-W1 arm.

## Verdict words
1. **HISTORY HELPS:** H1, H2 and P pass in both seeds.
2. **HISTORY DOES NOT HELP:** in both seeds HIST F_eq is at least 5.0 points below the higher comparator, or in both seeds HIST F_eq is more than 3.33 points below CTRL-W1 (the noise SD of a two-run difference).
3. **NOT SHOWN:** anything else.
**What would prove the idea wrong (in this form):** HISTORY DOES NOT HELP. A NOT SHOWN with the attention sitting almost all on the newest state (mean newest-state weight above 0.9 on rounds 4 to 48) is read as "the net did not choose to use its history", not as a proof.
If CTRL-W1 alone beats the loop by the H1 bar in both seeds, the page says "the extra read layer helps, not the history"; that never counts toward HISTORY HELPS.

## MARKS SELF-CHECK (thread-helper-common.md), one line each
1. **Bars above noise.** F_eq +10.0 and F_few +10.5 are above 2 x 3.33 = 6.7 and 2 x 4.17 = 8.3 (two-run difference noise from H12's PASSMARKS, reproduced by the lr thread, board 21:50 UTC). This test also retrains the source net, which the H12 noise did not include; the CTRL-W1 run under the same seeds gives a first measure (report-only: HIST-vs-CTRL gap and CTRL-vs-loop gap both printed). Bars are chosen for that extra variance (H3's +10 precedent).
2. **Every-seed reading.** HELPS needs both seeds; DOES NOT HELP needs both seeds clearly below; one seed passing is NOT SHOWN.
3. **Fair comparator.** The higher of the loop and CTRL-W1 (same extra weights and compute) per seed and per score.
4. **Plain-net row.** P.
5. **F_few** is H2, required.
6. **Sleep gates:** none; sleep rows report-only. Any later gate must be the mean of 3 sleep draws with margin max(6, 2 x SE).

## Order (fixed now)
1. Commit this file, DESIGN.md, plug-ins, marks script, selftests (logs when run on a machine with torch). 2. Job `hist-1-practice` (Mac CPU, $0): selftest, then practise HIST and CTRL-W1, seeds 0 and 1; guard V1; stop if it fails. 3. Job `hist-2-dev`: dev ladders of the four. 4. `python -B scripts/claude_dir_hist_marks.py judge --hist ... --ctrl ...` prints the numbers and word; this page wins on disagreement. 5. Blind recount from the raw JSON and this page only. 6. A failed or INVALID run is re-run unchanged, never edited.
