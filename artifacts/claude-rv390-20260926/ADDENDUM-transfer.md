# Transfer rows for rv-387 to rv-390 (thought-memory thread; written 2026-09-26 15:43 UTC by date -u, before any rv-387, rv-388 or rv-390 result)

Why: Ben's new goal (15:41 UTC, via the Thread manager at 15:46): the brain should "apply skills learned to other
places". Asked: where cheap, a report-only row on whether going back, built on grids, helps a kind it was not built on.
No new spend. No marks change; these rows decide nothing.

- rv-387 (sealed 2d54b5992, launched on 358i's rental at 14:02): no row can be added. Its code and grids are sealed and
  already on the rental; it runs 7x7 and 6x6 grids only. Nothing changes.
- rv-388 (sealed 53d7a6489, running on CPU here since 15:07): no row can be added mid-run. Its going back and judge are
  built on the 24 game only. Nothing changes.
- rv-389 (not designed yet; going back on Sleep research's one-move-per-round 24-game env): it will reuse rv-385/387's
  go-back bookkeeping, which was built on grids, on a number game. That whole test is a transfer test; its report will
  say so.
- rv-390 (not sealed): one added row, report only. rv-387's BACK, with the same logic and settings (a snapshot before
  each guess, going back when q falls below the snapshot's q, a check every 8 rounds, cut 0.5), applied to the unfinished
  SUMS puzzles (sums6, sums8), a kind it was not built on. On sums the candidates for a guessed cell are blank or a
  digit, and there is no row/column rule. Code: AnyRunner in scripts/claude_rv390.py; on grids it gives exactly rv-387's
  BACK (checked on 2 grids with a smoke-trained 358i net). Reported as "back_transfer_report_only" beside KEEP and
  RESTART on sums, same 480 rounds.
- Caution written now: rv-387's rehearsal (NOTE-rehearsal-before-result.md) found its go-back trigger almost never fires
  on a small net, so a null transfer row may mean "the trigger never fired", not "the skill does not transfer". The
  report will give the number of go-backs next to the solved count.
