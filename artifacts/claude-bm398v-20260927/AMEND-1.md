# bm-398v AMEND-1 (benchmarks thread, written 2026-09-27 00:34 UTC)

Made after the Thread manager's review (00:34 UTC), before any bm-398v reply was read. The run started at 00:31
UTC, before the review arrived. Nothing here changes a step of the run: the replies do not depend on any mark. PLAN.md
and the script stay as sealed (7058498ab). Where this file and PLAN.md differ, this file holds.

1. **W3 in words, as coded.** PLAN.md says "3% of the category"; `verdict()` uses max(3, round(3 × n / 100)). The
   coded rule is the mark. On conversations 5-9 that allows a drop of at most 4, 5, 3 and 13 right answers in
   categories 1-4 (140, 164, 45 and 423 questions). A floor instead of rounding would allow 4, 4, 3 and 12, so the
   coded rule is one answer looser in categories 2 and 4.
2. **The K rule was set after the finding counts were seen.** The 90% line and the choices 5, 8 and 10 were written
   after bm-398u's table of reranked any@k on conversations 0-4 (539, 582, 601 against 639) was seen. k = 8 keeps
   91.1%, just over the line; a 92% line would have picked k = 10.
3. **LoCoMo is practice only.** Never train on it.
4. **Scope of a PASS.** Store B's notes come from the rd-378 writer, which is out of every build. So a PASS shows
   that the 1B's own top 8 beats all 20 of store B's lines, and applies to store B only. It does not go into the
   memory path as it stands: the build's store (without that writer's notes) needs its own test first.
