# lf-sz run plan and price (written 2026-09-28 by the lf-sz helper; nothing has been run)

What runs: 6 runs at once on ONE vast card (loop8, loop2w, loop4w x seeds 9 and 10), by the lf-8 kit copy at
handoff/kit/lfszv (torch 2.11.0+cu128 pin, seal check 16/16, selftest that asserts the three weight counts, Stage 0, then
the runs). Marks: PASSMARKS.md (sealed before any run). Recount: `python -B scripts/claude_lfsz_recount.py <runs dir>`.

## Price (an estimate, not measured)
- lf-8's rental: $0.47/h for 967 s (16.1 min) = $0.13, 4 runs (artifacts/claude-lf8-20260927/run-vast/rentals.txt; the four runs
  took 3.8 to 6.7 min each, all at once, drive-state.txt 19:55-20:02 UTC; the rest of the 16 min was start-up and copy-back).
- These 6 runs have about the same compute per round as loop8 (2 x 512^2 = 8 x 256^2 = 4 x 360^2, within 1%), so the runs are 6 loop8-sized jobs instead of
  2 loop8-sized plus 2 small. If the card is compute-bound they take about 1.5 to 2 times as long: 10 to 14 min, plus about 9 min start-up and copy-back.
- So about 19 to 23 min at $0.47/h = **$0.15 to $0.18 expected**. Worst case the guard allows: time cap 45 min (1.5 x the 0.5 h
  estimate) at the $0.65/h ceiling = $0.49, but the money stop is set at **$0.45**, so the job cannot reach $0.50.
  The kit refuses any offer whose estimate x price exceeds 0.8 x $0.45 = $0.36.
- Under $0.50, so the standing rule says just go; no OK from Ben is needed. (Ben's rule 21:34 UTC 09-28.)

## Cheaper options, if the Director wants them (each loses something)
- Drop loop4w (4 runs): about $0.13, keeps the main question (depth vs size), loses the "does 4 layers sit in between?" row.
- Reuse lf-8's loop8 numbers instead of re-running (loop2w and loop4w only, 4 runs): about $0.13, but the comparator is then from another box, which PASSMARKS avoids on purpose.
- Only loop2w x 2 seeds (2 runs): about $0.08, weakest: no same-box loop8, no 4-layer row.

## Untested (this box has no torch)
- The three weight counts (formula only; matches lf-8's two known counts exactly). The rental's selftest asserts them first; on a mismatch nothing runs.
- Speed of d512 x 2 layers and d360 x 4 layers on a GPU (compute per round is equal to loop8's, so the estimate above is a guess).
- d360 has head size 45 (360 / 8 heads); attention with an additive bias mask should accept it, but it has not been run.
  If loop4w dies, the drive marks it DIED and the other five runs still finish; a d368 arm (head size 46) would be the fix.
- The kit copy passed `bash -n` only; it is a text-substitution copy of lf-8's kit, which ran end to end.
