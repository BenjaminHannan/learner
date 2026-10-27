# rsn-294 pass marks (fixed before any registered run; 2026-09-23 ~20:15 UTC)

Plan: design/v3/30-modes/294-learned-reasoner-plan.md. Code: scripts/claude_rsn294_{core,run,codearm}.py
(sealed in SEAL-code.sha256.txt). Panel: artifacts/claude-reasonpanel294-20260923/items-v3.jsonl
(SEAL-v3), 300 items, never trained or tuned on; results are category-level counts only.

**One change:** the brain-style loop reasoner ("loop": 2 layers of width 1024, re-applied; trained
with 2-12 passes, scored with 12) versus the equal-size plain transformer ("plain": 6 layers of
width 640). The loop has 30,771,221 learned numbers and the plain has 30,938,261. Both use the
same generator, copy phase (6,000 steps, batch 256), practice phase (6,000 steps, batch 128 x 8
tries), reward, learning rate and seeds (1 and 2). Comparison arm: the code arm (292's abilities,
re-implemented on frames).

Scoring: "checked" answers, meaning after the fact-check on the way out (an unchecked answer
becomes "I don't know"). "Answered without a fact" means an answer given when the gold is
UNKNOWN.

| mark | what | pass |
|---|---|---|
| P294.1 | invented answers (answered without a fact), per loop seed | ≤ 2 / 300 |
| P294.2 | loop right overall, per seed | ≥ code arm right + 30 |
| P294.3 | missing_fact honest "I don't know", per loop seed | ≥ 25 / 30 |
| P294.4 | held-out (three-step + big notebook, 30 items): loop right − plain right, same seed | ≥ +10 |
| P294.5 | no regression on one_step, backwards, yes_no, newest_correction: loop right per category, per seed | ≥ code arm − 3 |
| P294.6 | practice teaches: loop final right − loop copy-only right, per seed | ≥ +10 |

PASS = every mark for both loop seeds. What proves the loop idea wrong: P294.4 fails (a plain
model of the same size reasons over the notebook as well as the loop). What proves practice
wrong: P294.6 fails.

My predictions (logged before the run): P294.1 likely pass (the fact-check); P294.2 likely pass
(counting, comparing and before/after are 0 for the code arm); P294.3 likely pass; **P294.4 likely
FAIL** (a three-step chain is hard to reach from two-step practice, and big notebooks look the
same to both arms); P294.5 uncertain on newest_correction; P294.6 likely pass.

Dev evidence so far (CPU smoke, tiny plain model with about 0.2M numbers, NOT the registered
sizes): after practice, counting went from 0/40 to 12/40, comparing from 0/40 to 17/40 (about
chance for a two-way pick), before from 4/40 to 27/40 and after from 0/40 to 17/40. Three-step
was 0/40. Changes made on dev evidence before sealing:
- a wrong try costs −0.1, not −1 (with −1 the model gave up on counting and comparing);
- the fact-check now verifies the cited chain and that the kind of answer fits the question;
- a generator bug that sometimes put a "missing" fact back was fixed. On 50,000 generated
  episodes checked independently, 1 gold was wrong (an "after" episode with two rows sharing
  the same invented value).
