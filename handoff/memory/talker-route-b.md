---
name: talker-route-b
description: "2026-09-20 Ben chose route B — train his own small talking model from scratch (simple English), wired to the notebook + reasoner; rental OK to speed up; fine if not smart"
metadata: 
  node_type: memory
  type: project
  originSessionId: 76c622f5-1395-42cc-b432-71b65f256cf4
  modified: 2026-09-20T23:15:11.332Z
---

After trying the M0 notebook demo Ben said "That's not that cool. It should be able to talk to me." He chose route B (2026-09-20): train a small conversational language model FROM SCRATCH on simple-English text (no pretrained weights, not Qwen as the mouth), and wire it to the persistent notebook and learned reasoner. "It's ok if it's not that smart." He allows a GPU rental to speed it up (still within the ~$27 budget; quote first, Ben presses Run — see [[rental-create-blocked-by-classifier]], [[gpu-budget-cap]]) and a one-off multi-hour run despite [[test-time-limit-30min]]. Design is in design/v3/24-talker-from-scratch-fable-design.md (Fable reviewer).

CORRECTION from Ben the same day: NOT a plain next-word chat transformer. "I moreso wanted it to be a numeric representation of a thought that gets translated into english" — i.e. English → encoder → numeric THOUGHT → reasoner + memory work on thoughts → decoder translates the thought into English (the original Contract A shape). Encoder/decoder may use attention or GRU layers inside; what must be his is the thought bottleneck with the learned reasoner + notebook in the middle. A plain small chat LM is only a baseline/fallback.

**Why:** a template calculator with memory is not what he means by an assistant; talking is the visible milestone for [[teachable-assistant-goal]].
**How to apply:** prioritise the talker pipeline alongside the reasoning experiments; demos should be conversational; keep the honest-claims box (language distilled from data vs. his learned reasoner/notebook); don't present template/CLI demos as exciting.

DECISIONS 2026-09-20 (design/v3/24b-talker-decisions-ben.md): Ben said "Just choose your recommendations for each" → all of D1–D9 as recommended: 416-number typed thought; ≈33M transformer encoder/decoder (85–100M is the registered scale-up step, no 1B); full ≈5–6 GB reading list; typed fields feed the frozen operator; thinker for chit-chat; ≈29M plain chat LM as yardstick; free on BensPC, NO rental; exception of ≤3 unattended runs ≤6 h each. Still needs Ben later: Qwen generation nights, his 100 sealed L3 sentences, any rental.

2026-09-20 late: Ben said run the talker training overnight on BensPC (free, no rental) and "have an opus subagent manage it" — an Opus night-manager agent runs data prep → copy to BensPC → S0 smoke test → long resumable runs → morning report. Launch it once the three talker builders have handed over.

2026-09-20 night: Ben said "don't worry actually about making a talker if it's not ready yet" — no rush on the overnight BensPC run. Let the three builders finish, check their work properly, and only then start the smoke test / long runs (Opus-medium manager). Don't push unaudited training code into a multi-hour run just to hit tonight.

**2026-09-21 — "trained on a ton of stuff":** Ben wants the model trained on far more data. Agreed position: more text for LANGUAGE is good, specific FACTS stay out of the weights (name masking continues); data must match size (~20 tokens/param: 33M≈0.7B have 1.2B; 200M≈4B; 1B≈20B = not feasible). Plan: keep 33M first rung unchanged; at the 200M step widen the reading list to real-world English (Simple English Wikipedia + filtered educational web text, names masked), which also helps [[web-search-tool-idea]]; claim then becomes "knows English + common sense, facts from notebook/web", not "knows nothing". Data survey for ~4B tokens to be prepared when 33M results are in.
