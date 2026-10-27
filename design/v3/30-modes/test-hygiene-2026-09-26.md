# Test hygiene lessons (Thread manager, 2026-09-26 18:12 UTC)

Three lessons from today's verdicts. They apply to every thread that trains a model or seals a test. They add to the
goals page (ben-goals-2026-09-26.md); they don't replace anything in it.

1. **No fixed sentence frame in a training target, whoever wrote it (Claude, GLM or code).** After dl-5's grid nights,
   the 1B answered 299-300 of 300 general questions in the grid target's shape ("The X of Y is V"). Every lost item was
   a wrong fact inside that shape (f808ee39c, CARRY.md). Targets are the bare, code-checked answer. A fixed
   instruction in the prompt, masked from the loss and the same in every arm, is still allowed in tests (Ben 16:50).
2. **A label taken from what a writer was asked to write is not a label of what the text does.** In rt-02h, 77 of 144
   practice drafts labelled "asks for a puzzle" didn't ask anything (ec47b79d9). Before training, check a blind sample
   of any label that comes from the prompt, or label from the text itself (code or GLM).
3. **Try-outs and smokes never use test items, and output-format compliance is counted on DEV before sealing.**
   bm-398c's only smoke used its first 3 test questions and missed a format break that caused 32 of its 58 misses
   (f0ec5dfc3, 9e82034e6).
