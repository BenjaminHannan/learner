# Premonition (beautiful-model)

## Outside opinions on hard problems

Ben will relay research or diagnosis prompts to other models and bring the answers back. Offer one when a hard question has more than one plausible answer (a surprising failure, a result with two explanations, a design choice). Don't use it for routine steps. You cannot message them yourself: write the prompt, save it under `reviews/`, and give it to Ben.

- **Astra** (the lead agent) can read this repo. Point it at files and results. For diagnosis tasks, forbid edits, training, tests and GPU use.
- **GPT (web)** cannot see the repo. The prompt must stand alone: paste the result tables and describe the relevant mechanism in words. Example: `reviews/gpt-diagnose-second-request-2026-09-19.md`.

In every such prompt:
- ask for claims labelled shown / suggested / untested;
- keep the small card experiments and the village model separate;
- ask for one change at a time, with pass marks fixed in advance and the result that would prove it wrong;
- ask for a plain-language summary for Ben (a high-school senior).

Check factual claims in the reply against the code before acting on them.

## Subagent context cap

SUBAGENT CONTEXT CAP: every subagent must finish under 100k tokens of context. Never read a whole file over 300 lines; use grep, head/tail or line ranges (max 300 lines per read). Never print full logs or jsonl; use tail -n 50, wc, or python one-liners that print summaries. If you think you are past ~60k tokens, stop immediately and return a short HANDOFF (what's done, what's left, file:line pointers) instead of continuing.
