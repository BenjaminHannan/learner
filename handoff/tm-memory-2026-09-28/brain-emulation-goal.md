---
name: brain-emulation-goal
description: Ben 2026-09-23 19:07 UTC: the project's purpose is to emulate a brain and make it better; the hand-coded reasoner is "annoying", reasoner must be a learned neural network
metadata:
  type: feedback
  modified: 2026-09-23T19:07:54.237Z
---
Ben (19:06-19:07 UTC, notebook thread): "wtf? the reasoner should be a neural network?" then "No, that's annoying. The purpose of this model was to emulate a brain but make it better in all the ways we can". Earlier (19:03): the reasoner should be the bulk of the model, trained mostly by RL "since it should learn as a person does" (under $50; current rental cap $30).

Context he didn't know: 292's reasoner is hand-written code (doc 50: "Nothing is trained; the notebook is the index", scripts/fable_reasoner50.py:18-22); the ear/mouth are a borrowed Llama-style MiniCPM5-1B.

**Why:** Ben's core vision is brain emulation plus improvements, not a rules engine around a store.
**How to apply:** don't present hand-coded reasoning as the plan; design toward a learned reasoner (cortex) that queries the notebook (exact hippocampus), with sleep replay training it. Framing offered to Ben: keep "answers must trace to stored facts" as the better-than-brain part (no confabulation). Reasoning thread (rsn) owns the plan. Related: [[notebook-line]], [[listener-line]].
- Ben 19:13 UTC: "I really want this model to be unique/innovative. Right now it really feels like we're piggybacking off of already made ideas that are pretty well understood and just slapping a notebook on it. The goal of this model is just to replicate the strengths of the brain in the form of a helpful assistant, but to excel in every way we can, with the priority being reasoning." He then chose a self-relayed concise prompt over a workflow (reviews/novel-mechanisms-prompt-2026-09-23.md): 8 unpublished mechanisms ranked by reasoning gain.
