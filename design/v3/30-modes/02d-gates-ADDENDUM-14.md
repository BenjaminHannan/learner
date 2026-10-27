# 0.2d gates, ADDENDUM-14: C1 everyday-chat row fixed. Written 2026-09-26 16:17 UTC, before any run

Panel: chatpanel404 (artifacts/claude-panel404-20260926, sealed 81bd131db, TEST-ONLY, never read); spare chatpanel403.
Scorer: scripts/claude_c1rival_run.py (Everyday chat, sealed 6f6a6e17d). Rivals T = MiniCPM5-1B, Q = Qwen3.5-2B,
L = LFM2.5-1.2B under the twin recipe; one blind pair set per rival (seeds 4061-4063, packets of 15).
Mark C1 (per rival): margin = conversations won minus lost by the joined build.
- PASS (no harm): margin >= -12 against every rival. An equal build fails this 4.6% of the time over 60 decisive
  pairs (binomial checked by Month-end, P(wins <= 23 of 60) = 0.046).
- Reported as the stronger claim: margin >= +14 ("ahead"), 4.6% by chance. Not a mark.
Talker rule from Everyday chat's DIAG: no stock lines, no 1-to-4-sentence rule, no 90-word cap on everyday turns.
