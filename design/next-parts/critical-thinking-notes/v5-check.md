# PR #23 vs integrated design v5: edits

Sources: v5.txt (line numbers ≈ location), and CURRENT.json on `claude/premonition-launch-recovery-96c708` (C.json). v5's own text still lists the terminal panel as preparation. Its results appear only in C.json `current_science`.

## Contradictions

1. **§0 rulers, §2 "Assistant panel".** *Now:* "128 calculator questions, Mac only, not readable here." *Change to:* one 16-question panel (8 matched ADD/SUB pairs) run through 8 fixed checkpoints (2 seeds × static/contextual × 2 LRs), giving 128 answers, consumed once. 86/128 calls right, 15/128 finals right, 71 right call but wrong final, 38 wrong operation, 0/64 pairs. Readable in C.json. *v5 l.413:* "identical panel across all eight fixed terminal5120 checkpoints, both seeds, both input modes and both LRs." **shown**

2. **§2 Reader, §9.2, §5, Appendix "Brief".** *Now:* static only, and "settled". *Change to:* v6 code is static. The pipeline behind the 128 answers has two arms: frozen lexical embeddings, or frozen causal states, each feeding a thin adapter. Neither arm gives fresh pairs (0/8 in every endpoint; finals 6/64 static, 9/64 contextual). Seed 1/contextual never fit TRAIN stably (24/32, 29/32). The reader choice belongs to the execution owner, so PR #23 sets no default. Limit the "Brief" correction to v6. *v5 l.71:* "frozen lexical embeddings or the same borrowed output transformer's frozen final causal token states → thin trainable adapter." **shown**

3. **§2 Training and stop rows, C4 rationale.** *Now:* 4 rounds in training, up to 48 at inference, 500 SQuAD updates. *Change to:* the panel pipeline runs a fixed four loops in both training and decoding (512 advances for 128 answers), after 5120 updates on TRAIN32. The 48-round stop exists only in v6 code. Delete C4's "inference runs up to 48". *v5 l.413:* "ordinary fixed-four-loop decoding." **shown**

4. **§2 Key gap, F0.** *Change to:* three gaps are closed. Rounds: 4. Tool return: four reserved value-and-status pairs, one call per loop, with the result written before the next advance (*v5 l.83*). Reader: both arms. Every call fired at loop 0, before any core advance (C.json). Native runs are on the Windows PC. Only the output path (is it v6's 8-vector pool?) is still unknown. **shown**

5. **§5 forbidden list, §8 "not fast weights".** *Change to:* the ban covers only the maze race. *v5 l.97:* "An error-correcting fast-weight matrix is a lower-ranked alternative if binding or temporary-memory errors dominate." It needs transfer and clean-restart evidence. **shown**

6. **§7 compute.** *Now:* "the vast budget the execution owner holds." *Change to:* one 5070 Ti with 16 GB, and GPU dispatch is on hold. The budget is a one-time $10 cap with about $6.55 of headroom; storage drains about $0.83 a day (C.json). There is no overnight cloud budget. S needs its own budget decision. *v5 l.428.* **shown**

7. **§2 Core.** *Change to:* 9,007,790 total and 2,700,974 active parameters, from CPU construction, not "my arithmetic" (*v5 l.117-124*). **shown**

## Duplicates

8. **C3.** *Change to:* v5 already ran more coverage: the 8-vs-32 test scored 0/8 pairs in all four endpoints (fresh 1/16 and 1/16 vs controls 1/16 and 0/16), and an older broader-data test scored 0/32 fresh (*l.42, l.47*). Ben has also approved a two-arm, 1024-example curriculum on the existing architecture, to run after the terminal eval (*l.417*). C3 should read that result and propose a generator only if it fails. Any generator follows v5's rules: a canonical form, semantic siblings kept in one split, and an oracle that is never deployed (*l.66*). Pass marks are counted in pairs, not "/128". **shown**

9. **C1.** *Change to:* this overlaps the English pilot's source-reconstruction arm (*l.420*). Request exact-number reproduction from that arm. A standalone probe waits until after the pilot and stays within "supported two-digit, single-token results" (*l.77*), not 1-6 digits. **suggested**

10. **§1 example, F1.** *Change to:* answers are two-digit single tokens, so score numeric distance and carry/borrow category, not "4,827 vs 4,872" or failure by length. Cite what is already measured. On TRAIN residuals, 10/12 errors were within 5, with no operand copies (*l.358*). 63/64 depth-panel finals and 28/32 earlier-pilot finals matched training targets (*l.171*), which is above PR #23's 25% line. Run F1 only on the 128 terminal outputs. Facts **shown**; applying the line is **suggested**.

11. **F2.** *Change to:* probe TRAIN rows first, where the correct result reaches the task signal but the final is wrong (3 low-LR rows, *l.408*). The probe needs forward passes, so it is CPU-only during the hold. Coordinate with Derek's readout successor (*l.365*) and with the diagnostics A and B named in C.json (contents not readable here). **suggested**

12. **C4.** *Change to:* v5's depth test (64 vs 8 block visits at about the same parameter count) scored 0/8 pairs everywhere and took 1.98× the training time (*l.9, l.131*). Looped rounds are not distinct depth, so C4 is not a duplicate, but its prior is lower (**suggested**). The round count also sets the call budget, and calls fire at loop 0, so extra rounds cannot fix the 38 operation errors without a change in call timing (*l.85*). Gate C4 on a recipe that already scores some fresh pairs. Pass: 16 rounds beat 4 in fresh pairs on both seeds. Falsifier: 16 ≈ 4. **shown**

13. **C5, §1 "examples in the notebook".** *Change to:* in v5 the notebook holds facts and corrections, and the experience store holds examples (*l.54-56*). Context learning is v5's planned first rapid-learning step (not yet run). It uses no oracle method labels, a fresh query, cleared context and a revisit after intervening learning, and it reports contextual and persistent gains separately (*l.89-90*). *l.12:* a persistent skill must "improve unseen instances after context reset and survive intervening learning." Cite the earlier notebook result (24/32 and 20/32 vs inline 32/32; *l.47*) as support for the bag-notebook idea (**suggested**). **shown**

## Order

14. **Header, §1, §8.** *Now:* reads as a run order. *Change to:* "A menu of proposals for separate decisions, after v5 step 1. Asks for no GPU time during the hold; F-checks are CPU-only. C-rows come after the terminal eval, the English pilot and the curriculum have reported, and each needs approval. C2a/C2b/C4/C5 are architecture changes. S follows a recipe that already produces fresh pairs at current size, and C5 moves after S." *l.8:* "New architectural or reasoning-method changes remain separate decisions." **shown**

15. **C2a/C2b.** *Add:* v5 rejected forced copying, lists digit heads as an unimplemented fallback, and treats pointer selection as literature only (*l.172*). C2 must argue why it beats those. Facts **shown**; merit **untested**.

## Missing facts

16. **§4 Rules.** *Add:* panels are parent-supplied and checked, built as matched ADD/SUB pairs with siblings grouped. A pair counts only if both answers are right. Generation sees only the question. Raw answers are frozen before gold is opened, and each panel is consumed once. Consumed panels never enter positive replay, and reserved panels are never inspected. Score call, operand order (ADD commutative, SUB strict) and final-given-right-call separately for each seed and arm, and report ties and negative results. *l.19, l.65, l.175, l.414.* **shown**

17. **Free checks.** *Add an optional F5 (needs approval):* compare canonical and English inputs to separate operation errors from semantic loss. *l.68.* **suggested**

18. **Citations.** Cite SCAN, CFQ and COGS for C3's splits, SVAMP for contrast pairs, and MQuAKE for C5. Repeat v5's caveat on Huginn: "a scale far beyond the proposed local setup" (*l.249*). **shown**
