# Probe-6 plan (draft, not sealed): "should I ask first?" fix for trick jobs

Evidence (shown, K2 Probe-4 pools): trap wins end with a question 122/137; non-trap asking tries lose 112/122.
Test writers (K2-tuned, Haiku+state, Haiku+checklist) all pick 14-20% on Guess-1 traps of a possible 51%.

Pick rule: a judge says ask / act for the request (+ start state). If "ask", pick among tries that end with a
question (ties by TEST-T); else TEST-T as in Probe-5.

Judge arms (each scored first on the frozen Probe-4/Guess-1 pools, no new tries):
- J-LFM3: LFM3 prompted P(ask) from logprobs.
- J-D1 (Ben's idea 00:16Z Oct 28): a LiquidAI one-pass decision model (coordinator names LFM3 d1-2B / d1-Omni-2B;
  to verify it exists and what input it takes) as the ask/act judge, and separately as a scorer of the 12 tries.
- J-DISTIL: LFM3 LoRA trained on Haiku ask/act labels from the 372 non-target tasks (trap flag is known there).
Pass marks to fix before any run: trap pick >= TEST-T trap + 15 points, non-trap pick >= TEST-T non-trap - 3.
