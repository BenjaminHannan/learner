---
name: exp43i-learned-addressing
description: 2026-09-21 — step 1 PASS 6/6: callable skills + router with LEARNED relative addressing (4 distance clues) runs to length 16 and learns CARDFOLD from 20 episodes
metadata:
  type: project
---

scripts/fable_learnedaddr43i.py, artifacts/fable-learnedaddr43i-20260921/. Replaces 43G's six hand-given places with a learned score table [skill, parity case, 4 clues, 9 buckets] over all n places; clues = j−t, j−mirror(t), 2j−t, 2(n−1−j)−t, clipped ±4. 1,464 parameters; base 22 s, sleep 15 s on CPU.

All marks pass: old skills 1.00 at lengths 4–16, CARDFOLD from 20 episodes fresh/long 1.00, old skills untouched, weights-only reload.

**Why:** shows length-free addressing can be learned, not only given, once skills are callable modules on a tape ([[exp43g-transport-router-control]], [[router-sleep-approved]]).
**How to apply:** caveats — zero init so seeds differ only in data; clues chosen knowing the skills; parity facts + output length still given; read probability sags to 0.97 at length 16 (dilution) so find the breaking length next; toy only. Next rungs: stress length (32/64), learn parity instead of giving it, then step 2 (notebook lookups as skills).

Length stress (same day): soft reads break only on ROTL1's wrap-around place (0.77–0.88 at 64 digits, ~0.4 at 256); hardening each read to its best place at TEST time (no retraining) gives 1.00 for all skills + CARDFOLD to 256 digits, 6/6 seeds. Step 4 glue loop also built: scripts/fable_agent_loop.py (+ _selftest.py, 8/8 pass, save–kill–resume OK).
