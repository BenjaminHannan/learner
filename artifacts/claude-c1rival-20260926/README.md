# 0.2d row C1: everyday chat against same-size rivals (everyday-chat thread; written 2026-09-26 16:17 UTC, before any run)

Asked by Month-end (0.2d owner) after Ben's Redirect (goals page 328b97c78): the joined build is judged against plain
same-size models. This folder fixes how C1 is scored. The bar itself is Month-end's, in the 0.2d marks file.

- Panel: chatpanel404, artifacts/claude-panel404-20260926 (sealed 81bd131db; 60 blind conversations; never read or
  run). Spare: chatpanel403 (sealed 78fc677bd, never run).
- Arms, each run ONCE with ch-403's runner (same per-turn seeds, fresh agent per conversation): the joined build, and
  three rivals on the plain twin recipe (claude_e2e336_twinb.py: its fair system line, the whole chat, thinking off,
  greedy, at most 160 new tokens): T MiniCPM5-1B, Q Qwen3.5-2B, L LFM2.5-1.2B, each at Benchmarks' pinned snapshot.
- Scoring: scripts/claude_c1rival_run.py (selftest 5/5). One blind pair set per rival over all 60 conversations, order
  shuffled per conversation with a fixed seed (4061, 4062, 4063), packets of 15, keys kept apart.
- Judging: one blind Opus judge per packet with artifacts/claude-ch403-20260926/JUDGE-BRIEF.md (winner 1/2/tie, and
  replies that state or assume something about the user they never said).
- Marks: per rival, margin = build wins - rival wins; the mark passes when margin >= the bar Month-end fixes and no
  judgement is missing. The row passes when all three pass. Made-up counts, median words, stock lines, "don't know"
  and ms per turn are reported beside it.

## What the numbers can tell apart (for choosing the bar; exact binomial, 60 decisive pairs)
If the build and a rival are equally good, build wins ~ Binomial(60, 1/2):
- "wins >= losses" (margin >= 0) passes 55% of the time and fails 45%, so it cannot separate equal from worse.
- margin <= -14 happens 4.6% of the time; margin >= +14 happens 4.6% of the time.
The design's talker is MiniCPM5-1B itself, so against T parity is what the design predicts on everyday chat.
Recommendation (the everyday-chat thread's; Month-end decides): a no-harm bar of margin >= -12 against each rival
(an equal build fails it 4.6% of the time), with "ahead" (margin >= +14) reported as the stronger claim. marks prints
"behind / level / ahead" at -14 / +14 for every rival whatever the bar.
