# 353: the loop reasoner without the per-pass step embedding

Sleep research thread, 2026-09-25. Ben (00:00 UTC): "Why didn't the loop learn? Can you see if you can
detect the issue?" CPU diagnosis: artifacts/claude-loopdiag-20260925/DIAG.md (width 256, 3 seeds): the
loop without the step embedding trained like the plain net (copy ce 0.52/0.54 vs plain 0.47); as built it
stayed at 1.10/1.30.

## The one change
rsn-296's loop arm exactly (2 layers x width 1024, random 2-12 passes in training, 12 at eval, same
generator, steps, batches, lr 3e-4, reward, fact-check, seeds 1 and 2, eval), except that
LoopThinker.forward no longer adds `self.step.weight[t]` to the state. Runner: scripts/claude_rsn353_run.py.

**Twin:** 296's loop seeds 1 and 2 (recount): copy loss at the end 1.85 and 1.97; fresh panel296 v2
106 and 101; transfer panel294 v3 89 and 87. The plain 296 arm (225/217 fresh) is the reference.

This is the prerequisite for Ben's thinking stop token (memory: reasoner-thinks-until-done): the loop has
to train before learned halting can mean anything. The dev runner's 6/12/20-pass scores show whether
extra passes help once it trains.
