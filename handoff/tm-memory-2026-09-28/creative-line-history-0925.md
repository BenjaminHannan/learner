---
name: creative-line-history-0925
description: Creative thread history 09-24/25: 333e router/writer results, blurt engine plan, Ben's creative reframing
metadata:
  type: project
---
Creative research thread (session_01SsmkQ3qUuVpWRn8kK25kGx), goal from Ben 00:31 UTC 2026-09-25: get creative to PASS.
- Research note: design/v3/30-modes/research-creative-2026-09-24.md (main a561d5d9c).
- 333e (Ben 19:13 09-24: "shouldn't be keyword ... call the creative model as a tool ... give it the conversation"):
  the 1B decides the write_creative tool call via a trained logistic head on its layer-12 hidden state
  (artifacts/claude-cre333e-20260924/head333e.json; train data artifacts/claude-cre333e-train-20260924; DEV set
  artifacts/claude-cre333e-dev-20260924, names S-Z). Zero-shot the 1B couldn't make the call; a head trained only on
  tidy data fired on 104/174 real chat turns, so rambling examples were added (lesson: train routers on realistic chat).
- Registered run ($0.10): routing 40/40, controls 0/30, P333.2 30/30 (first PASS in the 333 series). Writer: useful
  7/40 (e1) and 6/40 with chat (e2) vs twin b 10/40; bar 32. E.2 proved wrong. VERIFY-333e.md (main 88658dfdf).
- The writer (base 1B) is now the limit. Decision card posted 00:4x UTC 09-25: train the 1B writer (LoRA on ~1,500
  Claude-written replies, ~$1, recommended) vs a bigger 4B-8B writer (new download, unequal size). Nothing runs before
  Ben chooses. A LoRA must not change the router's base features: load the writer as a separate model or disable the
  adapter for routing; train it on the rental (no weights through Muse).
Related: [[month-end-results-log2]].
- 00:39 UTC 09-25 Ben REFRAMED creative: emulate the brain part that "says random stuff then gets filtered out";
  the generator may make wrong assumptions; "maximize the number of times it gets lucky". He called the safety filters
  stupid (they don't judge quality). Chose "Both" (ideas + checkable puzzles). Kept: assumptions shown to Ben stay
  labelled as guesses, never stated as facts about his people.
- Engine plan: wild blurts (N~30) -> judge picks (exact checker for puzzles, learned/self judge for ideas) -> sleep
  practice on lucky hits (RFT). blurt-1 baseline queued (rent-blurt1, main 2d37b0b5a). CPU: 0/180 on 4-number
  puzzles, so the DEV set is two-thirds 3-number. Terms caution (reasoning research): Claude outputs as TRAINING data
  for the 1B may break provider terms; puzzles give code-made labels, prefer those.
- 02:50 UTC 09-25: blurt-2 (constrained decoding: only legal formulas over the given numbers; built-in LoRA, no peft)
  and registered loop PASSMARKS (artifacts/claude-blurt2-20260925/PASSMARKS-blurt2.md, main adc6e5d97/62f8df010):
  L1 W-S0 >= +8/150, L2 W-C >= +5 and each W seed > each C seed; INCONCLUSIVE if < 20 wins. Running on the thread's
  CPU ($0, out artifacts/claude-blurt2-20260925/cpu); GPU repeat queued handoff/queue/blurt2-loop.md (BensPC, asked
  director). Idea self-judge rule: pick@1 >= 6/10 -> 333g uses it. Road map: design/v3/30-modes/creative-roadmap-2026-09-25.md.
- 05:35 UTC 09-25 RESULTS: blurt-2 learning loop CPU passed, but OVERALL = registered FAIL (GPU repeat W 13,11 vs S0 6 = +6, bar +8; W>C both runs; VERIFY-blurt2.md f1b93900a). CPU (fresh puzzles S0 6/127 -> W 15,19; C 6,6;
  173 wins of 379 misses; RESULTS-cpu.md main ee265a833). GPU repeat still queued. Ideas: self-judge 2/10, GLM 5.3
  labels 256/300 agree (label source OK), trained head top pick 3/10 (not a pass), top-3 has good 7/10. Placebo run
  blurt-2p (wrong guesses, new seeds 3/778) registered 8813be47c, running on CPU. Next: transfer family, raise luck,
  333g with top-3 ideas. wins.jsonl sent to the Fix sleep thread.
- 06:50: blurt-2b registered (--all-hits, seeds 4/779, one BensPC GPU run = registered; handoff/queue/blurt2b-loop.md).
(trimmed; full record in git: design/v3/30-modes/research-creative-2026-09-24.md and artifacts VERIFY files)
