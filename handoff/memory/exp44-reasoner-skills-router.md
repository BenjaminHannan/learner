---
name: exp44-reasoner-skills-router
description: 2026-09-21 Experiment 44 — reasoner rebuilt as notebook-lookup skills + learned router; R1–R7 PASS 3/3; caveats and the noisy-teacher brittleness
metadata:
  type: project
---

Experiment 44 (step 2 of the end-to-end roadmap, built by an Opus agent, re-scored by me): village N=60, 8 relations, lookup matrices built from the notebook at run time, UNKNOWN sink, hard-coded hop loop, only final answers supervised. R1–R7 all PASS on seeds 4102–4104: 1–3 hops 1.00, depth 4–10 1.00 (stress to 32 hops 1.00), N=200 new names 1.00, 400 missing chains → "unknown" 400/400 with 0 confident-wrong, 3 new composite words slept in from 20/50 episodes 6/6 per seed, reusable inside longer chains. 64 learned numbers for the base, 27 per word; wave 51 s.

**Why:** shows the 43H/43I design (frozen skills + router + automatic sleep gate) carries over to the reasoner's job — see [[exp43i-learned-addressing]], [[router-sleep-approved]].

**How to apply:** claims stay small: new-names and honesty are true by construction (wiring, not learning); no baseline run; no language; zero-init means seeds differ only in data. Known brittleness: 2 wrong episodes out of 20 → word rejected 9/9 (safe but a 10%-noisy teacher cannot teach) — this is where GPT's robust corruption likelihood should be tested. Files: scripts/fable_reasoner44*.py, artifacts/fable-reasoner44-20260921/.
