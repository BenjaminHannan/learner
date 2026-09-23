---
name: exp27-newnames-result
description: 2026-09-21 experiment 27 new names with name scale 1.2 — registered PARTIAL 2/3 (no claim); binding works 92–99%/step; seed 2103 reserved_gap on p12-2
metadata: 
  node_type: memory
  type: project
  originSessionId: 76c622f5-1395-42cc-b432-71b65f256cf4
  modified: 2026-09-21T02:26:50.525Z
---

Experiment 27 (M1-F): name loudness `code_scale` fixed at 1.2 (arm F, gated) or learned from 1.2 (arm L, descriptive), fresh seeds 2103–2105. Verdict PARTIAL: F 2/3, L 2/3, control 3/3. Seed 2103 missed p12-2 (479 and 485 vs cutoff 487) and F-2103 broke the paired mark (−15, −19) → `reserved_gap`. All other cells 469–512/512 vs experiment 21's 0–149. Learned scale settles 0.82–0.93, no collapse. Open-set pick among all 4,096 codes only 0.55–0.64.

**Why:** confirms the [[exp21-newnames-result]] diagnosis (zero-scale trap from a too-small start value 0.139); the fix is the start value, hand-fixing isn't needed. Not a pass under the 3/3 rule.

**How to apply:** never say "new names work" — say "partial, 2/3, 16-candidate cells". Follow-up = fresh registration via a Fable reviewer targeting the reserved-name gap on 12-person chained cells; pointer head (M1c) was NOT triggered. Both forecasters put reserved_gap at ≤0.12 and it happened — weight "generalisation gap" failures higher next time. Results: artifacts/fable-newnames27-20260921/RESULTS.md. Part of [[teachable-roadmap-fable-review]] M1.
