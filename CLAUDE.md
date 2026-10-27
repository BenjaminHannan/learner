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
