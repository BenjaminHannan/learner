# Fix screen v3: is the frozen LM the ceiling?

Written 2026-10-05 00:07 UTC, before any run. Fast lane. Follows screens v1 and v2: five changes on the core side and the exit width all leave fit at ~50%. The remaining fixed part on the path is the frozen 1.2B LM that speaks the answer. Outside hint (abstract only, untested here): "Transformers Stop Thinking Too Early, and a Tiny LoRA Fixes It" (arXiv 2609.36585), where a rank-8 LoRA on a frozen LM lifts reference-chain following.

## Runs (Ben's PC, sequential; same setup as screens v1/v2)
1. **S (lesion, eval only):** main2 with each question's 8 pooled core vectors replaced by the previous question's (`--shuffle-pool`). All 1,360 in_dist rows. Intact = 68.5%.
2. **A1-A3 (LM LoRA):** `--lm-lora 8`: rank-8 LoRA on every Linear inside the LM (not lm_head), active only when the LM talks (reader features unchanged). B starts at 0, so the start is exactly main2. Same 2,000 fixed rows x 3 passes, seeds 1-3. Baseline = diagnosis F1-F3 at 6,000: fit 50.6 / 52.5 / 46.3.

## Marks (fixed now)
- **S:** "core carries question-specific information" if shuffled <= 48.5% (20+ points below intact); "core carries little" if >= 58.5%; between: report.
- **A:** FIXES FIT if mean fit gain >= +15 and all 3 seeds positive; HELPS if +5 to +15 with all positive; else NO EFFECT (HURTS if <= -5). Held-out gain reported; flag MEMORISES if fit is fixed but held-out drops 5+.
- If A fixes fit, the LM-side adapter is the lever and the 6-seed confirmation (own marks, written before it runs) follows. If A also fails, the ceiling is in the training signal itself (answer-only CE, batch 1), the next screen.
- Note for Ben: a LoRA changes the borrowed LM a little (about 0.5% extra weights). Size comparisons already count the LM.

## Clarifications added 00:16 UTC, before any v3 result was seen
- dev/in_dist.jsonl is grouped by family (1,326 of 1,359 neighbours share a family), so S swaps in the core vectors of another question **of the same family** for nearly every row. S therefore tests question-specific content, not the family/task mode.
- A has no guard on the LM's general behaviour. If A passes, it is not kept until a plain-English check (the R4 English set or plain-text perplexity) shows the LM's other talking is not damaged.
