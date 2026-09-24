# rsn-296 pass marks (fixed before any registered run; 2026-09-24)

Design: design/v3/30-modes/296-sleep-school-practice.md.
Code: scripts/claude_rsn296_{gen,run}.py plus rsn-294's sealed core/run/codearm (unchanged).
Panels:
- reasonpanel296: fresh and blind, artifacts/claude-reasonpanel296-20260924/items.jsonl.
- reasonpanel294 v3: items never read; its category results are known from 294.
Both are TEST-ONLY and reported as category-level counts only.

**One change from 294:** practice and dev episodes come from the varied "sleep school" generator.
Arms, sizes, steps, batches, learning rate, reward, fact-check, seeds (1 and 2) and eval are
identical to 294. The plain arm is the primary arm. 294's loop never learned to copy on seed 1
(D2), which is not fixed here, so the loop is reported with the same numbers but has no pass mark.

Scoring: "checked right", after the fact-check. "Code-doable" means one_step, two_step, backwards,
yes_no, newest_correction and missing_fact (178 items on reasonpanel296 v2).

| mark | what (plain arm, each seed) | pass |
|---|---|---|
| P296.1 | invented answers (answered without a fact), each panel | ≤ 2 / 300 |
| P296.2 | transfer: right on reasonpanel294 | ≥ same-seed 294 plain + 20 (seed 1 ≥ 204, seed 2 ≥ 209) |
| P296.3 | fresh panel, code-doable categories | ≥ code arm on those − 10 |
| P296.4 | fresh panel, total right | ≥ code arm total + 20 |

Registered fresh panel: reasonpanel296 **items-v2.jsonl** (298 items). The blind Opus audit flagged 2
newest_correction items as ambiguous, with no wrong gold, and they were dropped by id (FIX-v2.md).
Code arm, run before any learned run:
- reasonpanel296 v2: 208/298, which is 178/178 on the code-doable categories plus 30/30 three-step,
  and 0 on counting, comparing and before/after;
- reasonpanel294 v3: 210/300.
The bars are therefore **P296.3 ≥ 168/178** and **P296.4 ≥ 228/298**.

PASS = P296.1 to P296.4 on both plain seeds. **What proves the idea wrong:** P296.2 fails on both
seeds, meaning varied practice does not carry over to differently written notebooks.

Predictions (logged before the run):
- P296.1 pass.
- P296.2 likely pass.
- P296.3 uncertain; two-step on varied notebooks is the hard part.
- P296.4 uncertain; comparing sits at chance (D3) and counting was only partly learned.

Dev evidence (CPU, tiny plain model of about 0.2M numbers, NOT the registered size; 40 per kind,
12 kinds):
- trained on 294-style practice: 312/480 on 294-style dev, 202/480 on varied dev;
- trained on varied practice: 345/480 on 294-style dev, 312/480 on varied dev.
Two-step on varied dev stayed low (9/40). Three-step stayed 0 in both.
