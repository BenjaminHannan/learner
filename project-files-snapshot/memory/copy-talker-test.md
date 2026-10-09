---
name: copy-talker-test
description: Copy-talker test (10-04, PR #37): core-only talker 13.6% on unseen kinds vs allptr 78.2%; allptr's LM ignores the core on new kinds
metadata:
  type: project
  modified: 2026-10-04T21:09:03.507Z
---

Thread "Arm B" (cmsg_01GSLCHTCnZxn7DhV19qcDvM2a2f8tv6iFSuFDc6ZSr1Ek), PR #37 (branch claude/project-thread-utxkpw, base claude/project-thread-ajo58u), reasoner_ptr/real/english/RESULTS-CT.md. Finished 21:10 UTC 10-04.

- The test: an ~8k-param span-pointer + gate head on the core states replaces the LM talker (allptr). 6 seeds; the control was round 6's six arm.
- A FAILS: on unseen kinds the copy talker scored 13.6% vs 78.2%. Practised kinds with generated wording: 97.4% vs 99.7%. Human-written practised kinds (FRESH): 58.7% vs 92.2%.
- B NOT SHOWN: skipping the core makes no difference on unseen kinds (+0.7). On practised kinds the core matters: 97.4 vs 41.6.
- Shuffled-core lesion on allptr (seed 0): unseen kinds 73.2 -> 73.2, with 334 of 384 answers identical. So on new kinds the 1.2B LM answers by itself, and the earlier "beats bare LM on new kinds" results came mostly from the LM. The zero-pool lesion was a shock to the LM, not evidence that the core matters.
- Reproduction miss: the allptr seed-0 rerun scored 73.2 vs round 6's 82.3.
- Cost ~$0.75.

**Why:** shrinking the talker or reader can't come before the core generalizes past its practised templates.
**How to apply:** test any "core beats LM" claim with a shuffled-core lesion or a core-only exit. See [[two-doors-pointer-exit]].
