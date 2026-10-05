# Fix screen v3: result (BensPC, run by the Mac session; see PC-RUN-NOTE.md)

## Shown
- **A (rank-8 LoRA on every LM Linear, lr 1e-3):** fit 13.4 / 11.2 / 11.2 vs baseline 50.6 / 52.5 / 46.3 = mean -37.8 -> **HURTS**. Held-out 27.8 -> ~9.5%. The LM's answers collapse.
- **S is not a lesion (code bug, found by the ultracode thread and checked here):** with `--copy-path`, the wrapper patches both `project_training` and `forward`, and `StatePrefix.forward` calls the patched `project_training`. So at generation the prompt embeddings were appended twice ([pool][prompt][prompt][BOS], vs [pool][prompt][BOS] in training). With `--shuffle-pool` the inner call stores the row's own pool and the outer call swaps it back, so S scored each row with its own vectors and a single prompt copy, i.e. the training layout.
- So S = **main2 scored in its training layout: 74.6%** (1,014 / 1,360) vs 68.5% in the doubled layout. The doubling bug costs about 6 points on every copy-path generation score (all skills scores, both screens, the plateau diagnosis).
- `--zero-pool` (v2 Z, 0%) zeroed the pool and the first prompt copy, so it is not a clean lesion either.

## What still stands
All screen arms were scored in the same doubled layout, so the relative verdicts (five NO EFFECT changes, LoRA at 1e-3 HURTS) stand as comparisons; absolute fit/held-out levels are about 6 points low.

## Untested
LoRA at a lower lr (e.g. 1e-4) or with a KL guard; whether fit is still capped near 50% under the fixed layout. The fix (`--gen-fix`) and further work are owned by the "Ultracode: solve the learning blocker" thread (branch claude/ultracode-learning-blocker-gh011t).
