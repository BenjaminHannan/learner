# Construction checks

Written 2026-09-27T22:27:15Z, from raw checks.json. **Shown** means these construction tests only.

| Part | Patch | Loop | Plain |
|---|---:|---:|---:|
| Token embedding | 32,000 | 32,000 | 16,000 |
| Slot embedding | 512 | 512 | 256 |
| Relative-position biases | 288 | 288 | 1,152 |
| Block norms | 2,048 | 2,048 | 4,096 |
| Attention matrices and biases | 526,336 | 526,336 | 528,384 |
| Block MLPs | 919,808 | 1,051,136 | 1,080,424 |
| Recurrent state norm | 512 | 512 | 0 |
| Readout norm | 512 | 512 | 256 |
| Answer head | 32,125 | 32,125 | 16,125 |
| Stop head | 257 | 257 | 0 |
| Patch gate | 513 | 0 | 0 |
| Writer rank slots | 2,048 | 0 | 0 |
| Writer MLP | 131,712 | 0 | 0 |
| Persistent A and B | 4,096 | 0 | 0 |
| **Total** | **1,652,767** | **1,645,726** | **1,646,693** |

**Shown:** all eight numerical checks passed on MPS, PyTorch 2.14.0, fp32, no autocast.
All 20 trainable patch-model matrices received finite nonzero gradients from a different query after two support writes.
No artificial parameter loss was used. Ordinary weights stayed unchanged during support writes.
Zero patch exactly matched this net's reduced ordinary core with the patch disabled.
Three maximum-coefficient patterns stayed finite through 48 rounds on synthetic 11-by-11 inputs.
Each factor has Frobenius norm at most one, so the patch operator norm is at most 0.25.
The query interface takes no answers and preserves the patch across calls.

The reference dense loop's 1,646,750 coefficients include 1,024 kind-embedding coefficients
(four kinds times width 256). Our no-label loop removes those; neither rival sees a kind label.
Plain uses eight width-128 blocks with MLP width 525 to match the total budget.
The patch uses two width-256 blocks with MLP width 896, plus the writer and gate.

**Shown:** a separate runner smoke check completed four functional support updates,
differentiating the final two, and produced finite outer gradients. It applied no optimizer step.

**Untested:** practice eligibility, few-example maze learning, retention after adaptation,
sleep absorption, and trained-model inference cost. No race was run for this construction report.
See BLIND-RECOUNT.json when available for the separate recount.
