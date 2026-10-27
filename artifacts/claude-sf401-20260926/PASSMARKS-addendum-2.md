# PASSMARKS sf-401, addendum 2 (2026-09-26 ~14:20 UTC, after the panel's audit, before the seal and any run)

PASSMARKS.md and addendum 1 are unchanged: marks M1-M6, the INCONCLUSIVE rule and the judging are as registered.

1. Machine. Ben, 13:30 UTC: no test waits for BensPC. The run moves from a BensPC job (never queued) to a vast
   rental, handoff/queue/rent-sf401.md (label claude-wrongfact-sf401, $1.50 of this thread's $2 line). Same code,
   same commands, same arms: A = build_02c with the lis-319 reader (sha e688e1b2..., through claude_readersha_wrap)
   and the 0.2c sleep adapter (sha a33211dc...); B = A + the guard. Tree paths from Month-end (0.2c's SEAL-code).
2. Panel choice, fixed at 13:51 UTC before any panel content was read or any run: use the four-part panel if all
   four parts pass the checker and the blind audit, else a single-writer 24-life panel written in parallel. The
   four parts passed (checker, then 231/231 blind audit), so panel/ is the merged four parts. The single-writer
   panel (24 lives, 628 turns, also passing the checker) stays unread in the shared folder as a spare for a later
   test; it is not part of this one.
3. Diagnosis log (report only; added before the seal, replies unchanged, CPU test s14): with SF401_EVENTS=<path>
   the guard appends one line per turn with no words (state dir, sha1 of the user's words, reader act, live
   doubts, live doubts the reply names, counters that moved). Arm B runs with it. scripts/claude_sf401_diag.py
   joins it to the panel and splits B's (and A's) judged-wrong edit asks into W1 reader never saw the change,
   W2 doubt raised then cleared, W3 live doubt but the reply names another value, W4 named but not fired,
   W5 fired and still wrong, W0 join failure; plus correction turns framed and doubted per style and every guard
   firing on a non-edit ask. It never changes the verdict.
4. Next step by outcome (plans, not marks; each gets its own sealed marks before it runs):
   - PASS: Month-end decides whether the guard joins the build. Replication on the spare panel with the guard on
     top of Reading facts' lis-319k (save corrections at 0.95) if 319k passes, testing that the two combine.
   - M1 fails, W1 largest: the reader misses the corrections; the answer-side guard cannot help. Next = hand the
     per-style counts to Reading facts (save-side, lis-319k/319f) rather than widen the guard.
   - M1 fails, W3 largest: the wrong values do not come from a doubted note (another layer states them). Next =
     trace which layer wrote those replies (layer tags in the run rows), one change there.
   - M1 fails, W4 or W5 largest: the guard sees the doubt but its reply check misses. Next = one change to the
     naming/explained rule, DEV first.
   - M2, M4 or M5 fail (harm): list guard firings on non-edit asks by decoy style (diag); next = narrow the rule that
     fired (e.g. rule a to CORRECT mode only), DEV first.
