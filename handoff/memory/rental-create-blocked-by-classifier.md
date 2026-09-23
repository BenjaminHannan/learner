---
name: rental-create-blocked-by-classifier
description: "In the desktop app's auto mode, the vast.ai instance-create call (PUT /asks/{id}/) is denied as a \"Real-World Transaction\" even after Ben approves; Ben must run it himself or add a Bash permission rule"
metadata: 
  node_type: memory
  type: project
  originSessionId: 76c622f5-1395-42cc-b432-71b65f256cf4
  modified: 2026-09-20T00:57:59.064Z
---

2026-09-19: Ben approved renting two 4x RTX 5060 Ti boxes (option A, $2.50 hard stop) for A3-teacher-delay-v2. Read-only vast.ai calls worked (offer search without a key; GET /instances/ and /users/current/ with the key via header substitution), but the instance-create PUT was denied by the Claude Code auto-mode classifier ("Real-World Transactions"). Do not try to work around it.

**Why:** spending money is gated by the harness regardless of chat approval.

**How to apply:** prepare everything first (bundle, scripts, quote, image digest), then hand Ben a ready-to-run `bash` block (one command per block, key only via `$(cat ~/.config/vastai/vast_api_key)`) or ask him to rent the named offer ids in the vast.ai console; take over by ssh once the instances exist. He can also add a Bash permission rule for it. See [[compute-availability]] for the rental recipe and [[gpu-budget-cap]].
