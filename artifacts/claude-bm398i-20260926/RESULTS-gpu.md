# bm-398i RESULTS-gpu: the switch with the real bm-397t adapter (benchmarks thread, written 2026-09-26 16:50 UTC)

**PASS in both runs.** This is the confirmation the PLAN named, with the same marks. The real bm-397t adapter
(~/premonition-models/bm397t-adapter397t.pt, never pushed) ran twice on one RTX 5090 in bf16, in fresh processes
(rent-bm398r part 1). The rental report is on builder-outbox: artifacts/claude-bm398r-20260926/RESULTS-rent.md.
Counts only.

| Mark | Run a | Run b |
|---|---|---|
| I1: off replies equal base; logits diff | 75/75; 0.0 | 75/75; 0.0 |
| I2: mixed-off equal base; mixed-on equal on; off logits after mixing | 75/75; 75/75; 0.0 | 75/75; 75/75; 0.0 |
| I3: replies the adapter changes | 68/75 (GSM8K 15/15, MMLU 33/40, LoCoMo 20/20) | 68/75 |
| Verdict | PASS | PASS |

- **Adapter:** 192 keys; the loaded state's sha256 was 8e370203…029f. The file's own sha was checked on both sides
  before upload: 621edd16…7233.
- **Runs agree:** a and b wrote byte-identical replies (replies398i.jsonl sha256 b6bfdbf3…733d in both). So on
  this GPU the switch is deterministic between runs, not only within one.
- **Largest logit change with the adapter on:** 16.70, against 3.56 for the random adapter in the CPU run.
- **Timing:** each run took about 145 seconds, against 5,674 on the CPU here.
- **Deviation:** run a has no recorded exit code; the wrapper was added from run b onward. Its files and final JSON
  line are complete.
