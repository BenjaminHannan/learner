---
name: exp43j-learned-parity
description: 2026-09-21 Experiment 43J — removing the given odd/even facts; counters discover parity 5/6 seeds but SWAP fails at unseen lengths 6/6
metadata:
  type: project
---

43J = 43I with the two hand-given parity facts replaced by 4+4 learned 2-state counters (additive score tables). Registered 6 seeds: J1 fit FAIL 5/6, J2 length FAIL 0/6 (only SWAP breaks, e.g. 0.11 at length 12), J3 flip-counter found 5/6 (FAIL as a 6/6 mark), J4 CARDFOLD sleep PASS 6/6. FOLD, which needs parity, worked at all lengths.

**Why:** the clue scores are under-determined by training lengths 4–8; early memorisation leaves junk clue weights. Weight decay, L1 pull and clue dropout did not help (seed 9999 exploration, disclosed in PASSMARKS).

**How to apply:** next step per the sealed reading rule is wider training lengths (a data change), not more regularisers. Until then the honest statement is "parity facts are still given by hand" for [[exp43i-learned-addressing]]. Files: scripts/fable_learnedparity43j.py, artifacts/fable-learnedparity43j-20260921/.

**43K follow-up (2026-09-21):** practising lengths 4–12 instead of 4–8 fixed SWAP completely: 5/6 seeds perfect on all skills to 64 digits with random-start counters (registered FAIL 5/6; seed 4111 had no counter start near "flip"). 43K-v2 = balanced start (2 counters lean flip, 2 lean stay per direction): K1–K4 PASS 9/9 incl. fresh seeds 4121–4123, all 1.00 to length 64, sleep 9/9. Caveat: v2 flip counters start ~98% flip, so v2 = "uses an offered odd/even signal", discovery from random = 5/6. Files: scripts/fable_widelengths43k*.py, artifacts/fable-widelengths43k-20260921/.
