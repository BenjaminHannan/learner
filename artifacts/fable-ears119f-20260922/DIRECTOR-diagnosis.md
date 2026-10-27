# 119f director diagnosis (2026-09-22 10:25; inference only, no training, no tuning)

Script: scratchpad diag119f.py, run on BensPC over the three 119f checkpoints. Per-sentence output kept outside the repo (director held-out probe).

1. **The occupation rows were learned.** 40 of the 5,000 synthetic occupation training rows (every 125th): exact 40/40 on all 3 seeds (STATE, occupation, right person, right profession; conf 0.92-0.98).
2. **reading94b occupation sentences (51 sentences, 94 occupation golds), aggregate only:** the model says STATE on 50-51/51 but picks relation *date of birth* 22-27 times, *country of citizenship* 6-12, located-in 5-6, date of death 3-6, UNSURE 2-5, occupation 1 (every seed). Broken spans (bad_obj/bad_subj) 7-13 per seed.
3. **24 fresh encyclopedia-style sentences written by the director (fictional names; held out):** occupation is read when the sentence is "NAME was a/an NATIONALITY JOB." (the training template); a birth-date bracket makes it pick *date of birth* (and the date span swallows the whole "4 March 1901 - 9 June 1966" range); "NAME is a/an NATIONALITY JOB" mostly gives *country of citizenship* -> the nationality word.

**Cause.** The model can only output ONE fact per sentence: its four span pointers (subject start/end, object start/end) are fixed vectors, not tied to the chosen relation (scripts/fable_ears47_model.py, `ptr_q`). Real encyclopedia sentences state 2-3 facts at once (reading94b: 378 golds over 165 fact sentences), and the single slot goes to the date or nationality. More occupation-shaped data can only move which fact wins the slot (zero-sum); it cannot read all of them.

**Follow-up (one change): 119g relation-conditioned pointers + multi-fact decoding** — the span pointers are conditioned on the relation, and at decode time each confident relation gets its own subject/object. Same data (119f pool), seeds, recipe and scorer marks.
