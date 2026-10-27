# 235 -- SmolLM2-360M as the ear (Opus design note, 2026-09-22)

**Result:** registered FAIL on M2 only (3 wrong saves, bar 2). Full numbers are in
artifacts/claude-smolear235-20260922/RESULTS.md.
After the brake: statement recall 87/92 (94.6%) vs the 138i rules 29/92 (31.5%); questions + chains 40/40
(needs the disclosed chain-gold loader fix); no_save 1/25; GPU 55.8 ms median; Mac CPU 579 ms.

## Design
- Reader = SmolLM2-360M-Instruct, fully fine-tuned (bf16 autocast, AdamW 4e-5, 2 epochs, 36k self-made rows, 10 min on the 5070 Ti).
  Plain-torch Llama re-implementation, because BensPC transformers is broken. Parity with HF is exact.
- Output = frame lines only (`TEACH | s | r | v`, `ASK | s | r1 > r2`, `NONE`), decoded greedily with a CUDA graph.
- Brake (plain software): subject/value must be word-boundary spans of the turn; the relation must be in table v1 (or an alias).
  Anything else is dropped.

## What the failures say (next steps, cheapest first)
1. The wrong saves are meaning errors that pass the span brake: a pronoun bound to the speaker, a "so X does Y?" echo-question,
   and teaches-at -> school. Add data families for "X ... and she/he ..." co-reference, echo-questions ending in "?", and job-verb -> workplace.
2. A second plain-software check: if the turn ends in "?", TEACH frames are not allowed; a first-person subject needs I/my/me in the
   same clause as the value. Both are cheap and fit the "mathematical, not model-judged" rule.
3. Grow the table's alias lists (best_mate, little_sister, parrot...) or map unknown relations to their nearest table name before the brake.
   Right now the brake throws away 2 correct frames.
4. Re-run on a fresh blind panel (never this one again) with the same marks.

## Caveats
One panel, one writer, borrowed weights (a placeholder ear). The loader bug was a gap in schema tolerance that my
pilot fixtures did not cover. Future panel loaders should be piloted on a schema sample the panel writer provides.
