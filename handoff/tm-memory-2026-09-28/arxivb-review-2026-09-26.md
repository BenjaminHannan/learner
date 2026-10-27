---
name: arxivb-review-2026-09-26
description: 09-26 review of Ben's arxivb.org list (30 papers), BDM X post, 2609.28654; verdicts, the one plan-changing paper (looped flows), queued test ideas
metadata:
  type: reference
  modified: 2026-09-26T02:34:34.518Z
---
Reviewed 02:15-02:40 UTC 09-26 in thread cmsg_01FuvegZXjMmeUzStiEFVnEW2VXUgGbqcLbVMyQweRdsaS. Page: https://claude.ai/artifact/DkY9CCYjCU4zM2ieQipAfo. Repo copy (page source, notes, abstracts, handoff): main 9ab716bbe reviews/arxivb-papers-2026-09-26/. Paper texts: /mnt/project-files/research-2026-09-26/papers/ (12 full texts, abstracts.md for all 30, BDM README/appendix).
- arxivb.org = "arXivBangers": independent of arXiv; Gemini 3.7 Flash scores title/authors/abstract only and posts 2 arXiv papers/day to X. "Certified banger" is not a review. arXiv API export gives 406 after ~10 rapid calls; arxiv.org/abs + /pdf pages still work.
- X post (p0rc314in, Block Delta Memory): repo only (github.com/p0rc314in/bdm), 15-17M, 3 seeds; recall ~= attention on 1-hop/span/overwrite, but 2/4/8-hop pointer chasing fails for all (suite exact BDM 58.7 vs attention 59.0). No bearing.
- CHANGES A PLAN (handed to Sleep research 02:36 UTC under Ben's 02:17 overnight go-ahead; they register it for AFTER 11:00 UTC, after 358a): Looped Flows 2609.11801: same shape as 358a loop (2 layers w512, 5-7M); noisy-answer + time input, falling noise, loss every step; Sudoku-Extreme 97.9±0.4 (3 seeds, 1,000 practice puzzles) vs TRM 87.4, FPRM 94.2. Baselines copied; no bigger-than-practised test; 8 steps = 74.5. My pick for next reasoner change after 358a, before 3x scale-up. Idea A marks: flow-minus-plain >= +20/300 on 2 of 3 bigger tests (sums6/grids6/numbers5) both seeds, <=10/300 loss practised; proved wrong <= +5/300 on all three.
- EXPLAINS: 2609.19107 App B.4: tied loops worsen past trained pass count; random-count training only flattens (358a trains 1-16 rounds, grades last 1-6, tests 48).
- Confirms dl-3 (NGU 2609.13443 Fig 14: unpractised items decay). Nothing measures general-answer forgetting.
- Queued ideas (not registered): B stop vs matched-random-stop + per-round fix/break counts (Sleep research, eval only); C adaptive blurt budget (Fix sleep); D code-made hints for zero-hit puzzles, PSP 2609.29051 (Creative); E swap retrieved chat lines for another conversation's (Benchmarks; only if notebook beats no-notes by >=3 F1).
- PSD 2609.23449 trains on LoCoMo chats (breaks rule), ~123 test questions. Reader problems 1-4: nothing useful.
See [[self-play-zero-data-paper]], [[reasoner-roadmap-state]], [[fix-sleep-line]].
