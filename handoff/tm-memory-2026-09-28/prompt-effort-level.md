---
name: prompt-effort-level
description: Ben 01:29 UTC 09-28: every chat prompt the TM writes states the Opus 5.5 effort level to run it at (medium = set steps, high = design/diagnosis; skip xhigh/max for usage)
metadata:
  type: feedback
  modified: 2026-09-28T01:29:42.142Z
---
Ben, 2026-09-28 01:29:24 UTC (cmsg_01FuvegZXjMmeUzStiEFVnEWPbDp9WXMjGgtzpawDfo96v): "for each prompt, give me the effort level I should have the prompts have for opus 5.5".

TM's rule (judgment, not measured), given 01:30:
- **medium:** jobs that mostly follow set steps (rental driving, sealed tests, data finishing). Examples: the sleep test, the lis-320 reader, the blank-count replay pilot.
- **high:** jobs that need design or careful reasoning (new architecture arms, fairness-sensitive races, diagnosis). Examples: fewex, patches, relnet, the Astra backref diagnosis, a sparse (Looped-MoE) race entry.
- Skip xhigh and max: Ben is usage-sensitive.

**Why:** Ben runs each prompt in his own cloud chat and picks the effort level there.
**How to apply:** put "Effort: <level> (Opus 5.5)" as the first line of every new chat or Astra prompt, both in the reviews/ file and in the card. Related: [[ben-eli5-style]] (an explainer artifact follows every prompt).
