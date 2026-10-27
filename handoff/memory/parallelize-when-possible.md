---
name: parallelize-when-possible
description: Standing rule from Ben — run independent work streams at the same time (agents, Astra handoffs, machines) instead of queueing them
metadata:
  type: feedback
---

Whenever pieces of work don't depend on each other, start them together: Opus builder + auditor agents side by side, Astra ruling questions sent while builds are still running, jobs spread over the Mac / BensPC / a cheap rental box.

**Why:** Ben said (2026-09-20) "I don't care about the queue… parallelize (assuming it's cheap)" and later "keep this as a rule. Parallelize when possible" after I offered to send Astra's questions only once the builders finished.

**How to apply:** before waiting on anything, ask "what else could start now?" — especially Astra handoffs (hand Ben the copy box early, see [[handoff-copy-box-format]]). Limits still hold: rentals need a price quote and Ben's yes ([[rented-cpu-standing-ok]], [[gpu-budget-cap]]), benchmark under load first ([[rented-cpu-slow-for-this-workload]]), waves < 30 min ([[test-time-limit-30min]]), and never run registered seeds before the prereg is frozen.
