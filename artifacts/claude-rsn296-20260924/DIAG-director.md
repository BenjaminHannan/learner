# rsn-296 diagnosis: counting, comparing and before/after (reasoning thread, 2026-09-24)

Source: diag-cpu/ on builder-outbox, from scripts/claude_rsn296_diag.py on both plain final checkpoints. It uses generated practice-style episodes only; no panel was touched. Counts are after the fact-check.

**Shown: the plain models do not count or compare. Each has settled on a few fixed answers.**
- **Counting.** The two seeds settled on different numbers:
  - Seed 1 is right only when the true count is 1, 2 or 7 (82/83) and gets 0/117 on counts 3–6.
  - Seed 2 gets 0/59 on counts 1–2, 34/34 on count 3, and partly 4–7.
  - Counts 8–12 (never practised) are 0/200 on both seeds.
  - The fresh panel's 12/30 counting is these fixed numbers happening to match, not counting.
- **Comparing.** 88/200 on both seeds, identical bucket for bucket. That's one fixed pick, which is chance.
- **Before/after.** Always right with 2 dated facts: 134/134 on both seeds. With 3 or 4 dated facts it's about half: seed 1 131/266, seed 2 157/266.
- **Mechanism (suggested).** Practice gives a reward only for the exact answer, on a 13-way (count) or 2-way (compare) choice. Once the 8 tries agree, the group baseline cancels and there is no signal left. This is 294's D3, and it holds for counting too.

The follow-up is 296b: "told the answer after a miss". See design/v3/30-modes/296b-told-after-miss.md.
