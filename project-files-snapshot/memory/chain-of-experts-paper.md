---
name: chain-of-experts-paper
description: Ben's arXiv 2506.18945 (Chain-of-Experts) read 10-05; our looped core reuses one router per round; per-round-router planner test proposed (not run)
metadata:
  type: project
  modified: 2026-10-05T11:37:07.001Z
---

Ben posted arXiv 2506.18945 (Chain-of-Experts) on 2026-10-05 with no comment. Thread "cmsg_01GSLCHTCnZxn7DhV19qcDvM1sCBajcZ7UwFnENTm58gqJ" answered at 7:40 AM ET. Note: /mnt/project-files/papers/chain-of-experts-2506.18945.md.

Paper: sequential expert picks within a layer. Its key ablation: sharing one router across iterations plateaus worse than plain MoE. Evidence is weak (loss only, 544M model, ~65M tokens, benchmarks at chance).

Checked in code: our core (UpcycledMLP, 8 experts top-2) reuses the same router on all 4 loop rounds. In main2-based cores the router is zero-init and never learns, so about 1.6M of 9M params are live. In `--fresh-core` planner runs (PLS/PLCD) the MoE is alive but the router is still shared across rounds.

Proposed test (ultracode thread, NOT run as of 7:40 AM ET): per-round routers in PLS. Pass = 6-seed mean >= 137.3/160 and ahead on 5/6 seeds vs PLS (132.5). Fail = gain < 1.6 rows or ahead on <= 3 seeds. Run it on the PC or Mac only.

**Why:** shows Ben's paper drops were acted on, and records that the core's honest live size is ~1.6M.
**How to apply:** if the ultracode thread runs it, read marks from the note; related [[ultracode-blocker-findings]].
