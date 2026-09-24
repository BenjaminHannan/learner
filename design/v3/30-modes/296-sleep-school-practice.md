# 296: sleep-school practice (idea #16): varied practice notebooks

Reasoning line, 2026-09-24. Follow-up to 294 (registered FAIL). Ben said yes (01:11) to checking
ideas #5, #14 and #16 and then writing the best one up as a single-change test. The check is in
294-idea-check-5-14-16.md.

## Why

294's main finding (VERIFY-director.md, D1): the learned reasoners scored 100/100 on fresh
practice-style notebooks but only 6–11/30 on blind two-step questions and 5–8/15 on blind big
notebooks, where the hand-written code gets full marks. They learned the practice generator's
style, not reasoning. The MLC recipe (Lake & Baroni 2023) says systematic generalization comes
from practising across many differently built episodes, not only fresh symbols. 294 already had
fresh symbols; this adds the varied structure.

## The one change

Practice and dev episodes come from scripts/claude_rsn296_gen.py instead of 294's generator.
Each episode draws its own style:
- 3–40 rows;
- extra facts about the asked person, sometimes several values for one relation;
- extra facts about the people along a chain;
- 0–10 other people, often sharing the question's relations;
- people reused as values;
- shuffled "when" stamps.
The question kinds, frames and answers are 294's. Three-step chains are still never practised.
Each episode is re-solved by an independent solver and thrown away if its answer isn't exactly
the gold (checked: 0 mismatches against the code arm on 21,000 episodes).

Everything else is identical to 294:
- the arms: loop 2×1024 and plain 6×640, about 30.8M each;
- copy 6,000 and practice 6,000 steps, batch sizes, learning rate, reward, fact-check, seeds 1 and 2;
- the eval code (claude_rsn296_run.py runs 294's runner with the new generator).
294's loop training problem (D2) and comparing at chance (D3) are deliberately NOT fixed here.

## Tests

- **reasonpanel296** (new, blind, sealed). It was written by a fresh Opus agent that never saw
  either generator or the 294 panel items, and it was asked for realistic, messy notebooks of
  3–40 rows. It has 30 three-step items, which are never practised.
- **reasonpanel294 v3** (items never read; its category results are known from 294, so it is a
  transfer check).
- The code arm on both panels.

Pass marks: artifacts/claude-rsn296-20260924/PASSMARKS.md (sealed before any run).

## Cost

This is the same compute as 294: one rented 5090 for about 2.8 h, about $1.3–1.5. It sits under
Ben's $4 combined cap per job, which the guard enforces.
