# 352: plan for Ben's goal "the 3x model beats the 1x, genuinely"

Ben, 00:04 UTC 2026-09-25: "Have the 3x model outperform the 1x model as much as possible. You shouldn't
let it reward hack for false numbers. You should make sure that all improvement is genuine intelligence,
not targeted practice and improvement."

## Rules for this line
1. **Fair tuning.** Every knob tried on the 3x (91.6M) is tried on the 1x (30.9M) with the same budget.
   A win must come from size, not from extra tuning. (351 = 3x at lr 1e-4; 351b = 1x at lr 1e-4.)
2. **Choose on dev only.** Settings are picked on generated dev items (seed 777), never on a panel.
   Dev numbers are never quoted as results.
3. **No targeted practice.** The practice generator stays 296's. Nothing is added to practice because a
   test category is weak. Gains must show on held-out kinds: three-step (never practised), the transfer
   panel, and new relation names and notebook styles in the fresh panel.
4. **No reward hacking.** Scores are "checked right" after the code fact-check. Raw and checked are
   both reported. Invented answers must stay ≤ 2 per panel. A gain made of more "I don't know"s on
   answerable items doesn't count.
5. **The final comparison uses a FRESH blind panel (reasonpanel353), written after the recipe is
   frozen** by an Opus agent that never sees the generators or older panels, audited blind, then run
   once on both frozen recipes (2 seeds each). A second blind Opus agent recounts before anything is
   reported.
6. One change per run, registered and sealed first. $4 per run. Check the director's total before each
   rental and stop before $30. A registered FAIL stays FAIL.

## Steps
- S1 (running): learning rate. 351 (3x, 1e-4) and 351b (1x, 1e-4); 350 and 296 already cover 3e-4.
  Each size keeps its better lr on dev.
- S2 (only if the 3x still gains less in practice than the 1x): more practice steps (2x) for BOTH sizes,
  as one registered change.
- S3: freeze both recipes, write and audit reasonpanel353, score once, blind recount, report.

What would show size does not help here: on reasonpanel353 the frozen 3x is within ±5 of the frozen 1x
on both seeds.
