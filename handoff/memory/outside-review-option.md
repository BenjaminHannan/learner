---
name: outside-review-option
description: Ben will relay research/diagnosis prompts to Astra (has repo access) or GPT web (no access) when a hard problem would benefit from a second opinion
metadata:
  type: feedback
---

On 2026-09-19 Ben said I can give more research prompts to Astra "if diversity of opinion at hard problems would help. Just an option to keep in mind." He pastes the prompt and brings the answer back; I cannot message them myself.

**Why:** the first GPT review that day caught three over-claims of mine (what "both cards given" proves, the ASK loss being the marginal form, "every run still rising") and proposed the relation shortcut that fixed the held-out relation error. Outside eyes were worth it.

**How to apply:** offer a prompt when stuck on a genuinely hard question (a result with two plausible explanations, a design choice, a surprising failure), not for routine steps. Astra: point at files, forbid edits/runs for diagnosis tasks. GPT web: fully self-contained, paste tables and the relevant mechanism in words. In both: label claims shown / suggested / untested, keep toy and village tracks separate, ask for one change at a time with pass marks and a falsifier, and a plain-language summary for Ben (see [[explain-each-step]], [[focused-priorities-and-claims]]). Save prompts under `reviews/`. Verify any factual claims in the reply against the code before acting on them.

**2026-09-22 ~20:00 update:** Ben: "if you come across any really hard problems, give them to me as a prompt in gpt 6 pro". GPT-6 Pro (web, no repo access) is now the target for really hard problems: a fully self-contained prompt in one copy box ([[handoff-copy-box-format]]); Ben pastes it and brings the answer back. Use it only for genuinely hard research or design blockers, not routine steps.
