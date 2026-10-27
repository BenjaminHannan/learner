---
name: autocast-cache-bug
description: torch 2.8 bf16 autocast cache stops loop-net layer gradients when no-grad rounds precede graded ones; 358d/358i/358x/358t possibly hit; fix = cache_enabled=False (rsn-358i2)
metadata:
  type: project
  modified: 2026-09-26T20:08:00.000Z
---
Found 2026-09-26 by the Thread manager's audit (/mnt/project-files/thread-manager/loop-training-audit-2026-09-26.md). Confirmed on CPU by Sleep research at 14dc0c013 (artifacts/claude-stage0-autocast-20260926/CPU-RESULT.md).

**The bug.** In scripts/claude_rsn358a_run.py, loop_train runs its free rounds under torch.no_grad() inside the same `with amp:` block as the graded rounds. On torch 2.8 (the rent-kit image is pytorch/pytorch:2.8.0), autocast caches the bf16 copy of each weight. A copy made under no_grad has no gradient link. So the Linear weights in every block get no gradient on each step that has a free round, about 85% of steps.
- torch 2.11 (BensPC) and 2.14 are fine.
- Plain nets are fine: they never run free rounds.
- CPU runs are fine: this code disables autocast on CPU.

**Possibly hit** (loop trained on a rental; no run recorded its torch version):
- 358d, 358i and 358x;
- 358t, which was running at 17:05, when I asked the Director to check and stop it;
- nets trained from 358i's checkpoints.

Verdicts stay registered and get addenda only.

**Fix:** cache_enabled=False. scripts/claude_rsn358i2_run.py patches torch.autocast and logs torch version, steps_block_nograd and per-block gradient norms. rsn-358i2 (358i loop, seeds 1-4, audit Test A marks) was sealed and HELD at 0a0b50b7f, waiting on Ben's yes for $0.90.

**Why:** the loop-vs-plain grid loss on rentals may be this bug, not the design. 358a on BensPC had the loop ahead on grids6 by about +70.
**How to apply:** every future loop training uses the patched autocast or no autocast, and records torch.__version__. See [[rsn-358i-result]], [[reasoner-exit-rule]].

**20:02 UTC 09-26: CONFIRMED on the real loop.** rsn-358i2 (BensPC, torch 2.11, cache off) = SUSPECT CONFIRMED, recount at c761f8717: dev grids5 at 10k 195/198/197/200 (was 0/1/2/1); gaps vs 358i's rental plain sums6 +100.50, grids6 +51.75 (suggested only, two machines). 358x RESULTS shows torch 2.8.0 on the rental, so its loops were hit (addendum). Addenda for 358d/358i/358x at c761f8717. Same-machine test rsn-358i3 (loop + plain seeds 5-8 on BensPC, G0-G3, prediction 70%) sealed and queued T1 at f35b1b09f. Kit note: tag pytorch/pytorch:2.8.0 doesn't exist; use torch 2.11.
