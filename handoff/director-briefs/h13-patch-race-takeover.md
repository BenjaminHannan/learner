# H13: take over the patch race (brief, 2026-09-28 21:23 UTC)

Serves: item 3 (learns a new kind from fewer examples). The patch race is the test of Ben's clip-on patch on the fair few-example ruler.

Checked at handoff (Director, read-only): nothing scored on a maze; 4 of 4 source nets are only on branch claude/funny-heisenberg-ot316m and their sha256 match checkpoints-sha256.txt; marks say "both seeds" already (X2 fine); the review fixes X1, P1, P2, X3, X4, P3/P4 are NOT applied (no ADDENDUM-2; claude_patch_eq_report.py has no F_few, no higher-of-two-loops, no writes-off arm).

Steps, in order:
1. Write ADDENDUM-2.md (new file) and scripts/claude_patch_eq_report_add2.py (new file) applying the seven fixes from reviews/chat-prompt-patches-review-fixes-2026-09-28.md. Selftest on two fake seeds (gains-and-breaks vs gains-and-passes). Commit to main before any maze rung.
2. Copy the 4 source.pt files from the branch into runs/ (verify sha256); build Mac queue jobs from scripts/claude_patch_eq_dev_queue.sh (CPU, fp32, torch 2.14.0, same as the baseline; jobs idempotent). ~15 h. No GPU.
3. Dev ladders, commit dev records, then holdout once, verdict script, RESULTS.md, blind recount by a separate thread, report.
Rules: rules.md and thread-helper-common.md. Nothing changes after any dev score is seen. Questions for Ben go through the Director.
