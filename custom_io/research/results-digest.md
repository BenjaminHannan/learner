# results-digest (Sonnet reader, 2026-10-05)

DIGEST: what has been tried on the reader, talker, core contribution and LLM-free alternatives

Labels: [S]=shown (measured in a repo file), [G]=suggested (reasoning or literature), [U]=untested. All results are fast-lane, mostly 6 paired seeds, exact match, with test sets written by Claude helpers. Path prefixes:
- RTC=/mnt/project-files/reader-talker-compare
- N=/mnt/project-files/notes
- AJO=origin/claude/project-thread-ajo58u:reasoner_ptr
- UC=origin/claude/ultracode-learning-blocker-gh011t:artifacts/ultracode-v4
- AYA=origin/claude/project-thread-aya9pk
- BO=origin/builder-outbox

Sandwich = frozen 1,170M LM + ~9.3M trained parameters (0.8%).

A) WHAT WAS TRIED (tried | setup | result | source)

Talker / exit (English QA, 192-question sets)
1. Pool-only exit (8 averaged vectors) | story toy and 48-question English | 0.0% on unseen answer words; all 1152/1152 wrong answers were training words; seen 16.8%; English 4.3% [S] | AJO/real/RESULTS-R2.md, english/RESULTS-R3.md
2. +8 pointer vectors (ptr) / +all prompt-word embeddings (allptr) | same | unseen words 56.7% / 87.2%; English bank-only allptr 34.7% [S] | same
3. allptr + 8000 generated rows | 6 practised kinds | fresh 92.6% (89-96) vs bare 1.2B 8-shot 75.0%; generated held-out 99.7% [S] | english/RESULTS-R4.md
4. New question kinds | R5/R6 | six new kinds 79.9% vs 67.7% bare; leave-two-kinds-out 80.2 vs 76.6 (CI -7..+14); 12 practised kinds 83.0 vs 6 kinds 81.1; second unseen set 78.2 (12) / 75.3 (6) vs bare 77.6 = tie [S] | RESULTS-R5, R6
5. Question first + reused cache | qfirst | -7.6 pooled (CI -8.7..-6.5); first token still 2.96x bare time, so no speed gain [S] | RESULTS-R7
6. Talker sees only 16 core vectors, no question words | ptr arm | 18.9% pooled (fresh 37.9, new kinds 11.1 / 7.7) vs allptr 82.9 [S] | RESULTS-R7
7. Copy-and-gate talker (~2M, no second LM pass) | pointer + word head + gate on core states | unseen kinds 13.6% vs 78.2% (-64.5, CI -69.5..-59.6); practised kinds, generated wording 97.4%; human wording 58.7 vs 92.2; yes/no 46.6, one-word span 5.6, multi-word 11.3; talk stage 0.15 vs 25.1 ms [S] | RTC/RESULTS-CT.md
8. Same head on reader output, core skipped | copytalk_nocore | unseen 12.9% (core adds +0.7, CI -2.0..+3.4); practised generated 41.6 vs 97.4 [S] | RESULTS-CT.md
9. Lesions | zero core / shuffled core | zero = 0-5% in every round (crude: LM sees an alien prefix) [S]. Shuffled core, unseen kinds: 73.2% -> 73.2%, 334/384 answers identical (1 seed, read only) [S] | RESULTS-CT.md

Reader and LM size
10. 350M LM as reader and talker | allptr recipe | fresh 66.1% (60.9-72.0) vs 92.6; bare 350M 33.9 / 50.0 (0/8-shot); trained parts add +16.1 (350M) / +17.6 (1.2B) over the bare LM [S] | N/hearer-talker/RESULTS-SMALL-LM.md
11. Core 4x bigger (2->8 blocks, 9.0->35.8M) | scaling | new-kinds 64.4 / 65.3 / 66.3 vs bare 62.5; +1.9 (CI -0.95..+4.77); training fit does not rise [S] | origin/claude/project-thread-6qsyg1:scaling_test/RESULTS-SCALE.md
12. Contextual LM reader (last layer) vs word embeddings | arithmetic, 6 seeds | new-wording calculator call 59.2 -> 91.0 [S]; ordered per-loop read hurts chain 54.9 -> 43.1 [S] | origin/claude/project-thread-u9uvmq:pipeline/recipe_test/RESULTS-2,3.md
13. Truncated LM reader (layers 4-12 of 16) | speed only, 5090 | 8 layers 2.0x faster, 659M counted; quality never measured [S speed / U quality] | RTC/armB/speed-probe.md
14. Smaller pretrained readers (LFM2-350M/700M, SmolLM2, Qwen3-0.6B) | speed only | 30-layer models slower than the 1.2B at batch 1 [S] | speed-probe.md

Skills line (34 families; worst 8 = chain_ops, state_update, cipher_map, chain_story2, var_chain, seq_cycle, fewshot_number_rule, group_induct)
15. Fit-screen knobs | reader 32->256, 8 rounds, lr x0.3, pointer exit, exit hidden 32->256 | fit gain +0.2, -0.2, -1.2, -2.5, +0.7: all stay ~47-50% on 2000 practice rows [S] | AYA/artifacts/fix-screen-v1,v2 RESULT
16. Rank-8 LoRA on all LM linears | lr 1e-3 | fit -37.8: LM collapses [S] | AYA/fix-screen-v3
17. Reader+core with direct answer-class head, no LM in loss | 6000 updates | fit 46, 49, 43 of 320 (13-15%), held-out ~10%; nearly all group_induct (475-class head; unseen held-out answers count wrong) [S] | UC/results/03,04,05
18. 8 free vectors optimised per row | main2-wrong rows | solves 64/64 in front, after the question, or alone with no question [S]; optimising core output h through the exit 53/64, exit hidden 64/64 [S] | UC/results/02,10
19. Worked-step targets (LM writes steps then answer) | arm S | fit 66.6 -> 78.3 (+11.8, 3/3 seeds), held-out 48.1 -> 69.8; chain families gain most [S] | UC/SCREEN-v4.md, results/11,12
20. Skills curriculum, copy path | 50k updates | in_dist 72/100 (no copy path 3-6); lr decay 65; steps 71; fresh English afterward 2-3/48 [S] | AYA/docs/premonition-status/LIVE.md

Chat-assistant line (not the sandwich)
21. Thinker reads frozen 1B vectors, writes pointer cards | 9.3M trained | 1,098 of 1,230 right saves vs LoRA 924; wrong-save turns 4 vs 1 (missed by 1); backref 81 vs 88 of 136; 17.7 vs 1129 ms; stop head quit after round 1 always [S] | artifacts/claude-vread-20260927/RESULTS.md
22. Tiny looped reasoners, no language | 1.6M-6.4M, code puzzles | 6-digit sums ~298/300 vs plain twin ~154; 6x6 grids 291 vs 250 [S] | artifacts/claude-rsn358u-20260927, claude-relnet-20260927
23. From-scratch ears (tape / BiGRU, 0.24M) vs borrowed SciBERT (110M) | frames from sentences | seen 1,867 / 1,847 vs 1,954 of 2,000; new 2,149 / 2,290 vs 2,682 of 3,000; SciBERT executes 0 of 46 real sentences and made 2 silent wrong writes (tape/BiGRU 0) [S] | BO:artifacts/fable-ears47-20260921/RESULTS.md
24. From-scratch talker101 (28.85M, 617M tokens) + record fine-tune | SimpleStories | val loss 1.57; grammar test 67.4% vs 70% bar FAIL; raw unfaithful 313 -> 172 of 500 (cut-off names), 0/500 after a word brake [S] | BO:fable-talker101/120/120b RESULTS; AYA:design/v3/30-modes/240
25. Designed, not built: 33M ears/thought/mouth with 416-number typed thought | design 24 | no result [U] | AYA:design/v3/24-talker-from-scratch-fable-design.md. Own small ear shelved 09-23 and talker swapped to LFM 09-27 by Ben's ruling (AYA:design/v3/50-own-model/01-own-ear-mouth-plan.md; git e4a5ee891).

Speed [S]: sandwich 19 q/s at batch 1, 325 at batch 64 (5090); bare decode 70 tok/s; each of the two LM passes costs ~one fixed-overhead forward (N/speed-5090-2026-10-04.txt, RESULTS-R7).

B) STRONGEST SHOWN REASONS THE LM DOES THE REASONING
1. [S] Swapping in another question's core output changes nothing. Unseen kinds go 73.2 -> 73.2 (334/384 identical). Skills go 74.6 -> 74.4 (1014 vs 1012 of 1360). Replacing every prefix with its family mean gives 160 -> 161 of 320 (UC job 06, 09). The core carries a family "mode", not the question.
2. [S] Core-only talkers fail where the LM must read (rows 6-8). The core adds +0.7 on unseen kinds, so little content reaches a talker that cannot re-read the question. Pool-only / pointer / all-words give 0 / 56.7 / 87.2 on unseen words; the more raw words the LM gets, the higher.
3. [S] The core and reader cannot compute these skills alone (row 17, 13-15% with a clean head). The bare LM answers them with written steps (43.1% fit rows, 45.0% held-out; chain families 77-87%) but only 1.6-2.8% without steps (UC results/01).
4. [S] More core never helps. 8 vs 4 rounds give identical answers (loop relative change ~0.6% per round), 4x core gives +1.9, widths give +0.2/+0.7 (rows 11, 15).
5. [S] LM size sets the ceiling: 350M system 66.1 vs 92.6. The trained parts add the same +16-18 over either bare LM (row 10).
6. [S] The channel is not the limit: 8 free vectors make the frozen LM say any of 64 answers with no question visible (row 18). Learning from core state is the failure. [G] The LM's own loss lets it ignore the core when raw words are present.
7. [S] Pointer vectors alone reached 56.7% (story toy) but 18.9% on English. Handing the LM every prompt word reached 87-92%, so the LM is the reader (rows 1-2, 6).
8. [S] The worked-steps gain (row 19) is the LM's own chain of thought; do not credit it to the core.

Caveat [S]: skills copy-path generation fed the prompt twice (bug in skills_pretrain_v1.py; not reported for the English runner [G]). The fixed layout raises main2 from 68.5 to 74.6, so old absolute skills numbers are ~6 low (AYA fix-screen-v3 RESULT; UC DIAG-v4.md).

C) PROPOSED, NEVER TESTED
- [U] Reader quality:
  - a truncated LM reader (layers 6-8), or LFM2-350M/SmolLM2 as reader only
  - a distilled 20-60M reader, a BERT-class encoder
  - an embeddings-only reader + small 2-4 layer encoder, a byte/Perceiver reader
  - (lit-reader.md, lit-efficiency.md, lit-small-reasoners.md)
- [U] Talkers:
  - 2-layer cross-attending decoder (5-7M), program head (op + operand pointers + calculator), Perceiver-IO query decoder
  - fixed answer slots + stop, Flan-T5 hear-and-talk, shared reader/talker embedding table
  - talker-to-reader round-trip self-check (lit-talker.md, brain-talking.md)
  - Copytalk was tested only as one regularisation-free linear head.
- [U] Structured interface: reader emits slots/ops, deterministic executor, template talker (lit-small-reasoners ranking 1); SVAMP-style perturbation tests.
- [U] Core-forcing:
  - vectors after the question, a two-path loss with a prompt-free pass
  - shrinking LoRA to a one-layer residual edit, random round count, batch-16 accumulation
  - (papers/blocker-ideas.md; flags only smoke-tested, UC results/07, 08)
  - Arms SR, SP, P and queue jobs 13-15 have no results on the branch (last commit 02:56Z).
- [U] Deep exit into LM attention layers; learned Perceiver pooling; middle-layer features (design/info-paths).
- [U] Latent-supervision papers: CODI 2502.21074, implicit-CoT distillation 2311.01460, stepwise internalization 2405.14838, LRT 2609.01117, progressive mask against bypass 2605.07106 (papers/ultracode-blocker-papers.md).
- [U] Pipeline: PC arms S vs M (core init from skills checkpoint) queued, no results (AYA PASS-MARKS-PTR-PC.md).
- Citation warnings (armB/citation-check.md):
  - The MWP-BERT id is 2107.13435.
  - The step-by-step SVAMP claim and the single-digit tokenization claim were overstated.
  - Two lit files were written from memory.

D) NUMBERS A NEW DESIGN MUST BEAT

Skills [S] (worst-8 rows; 320 train-fit, 320 held-out in_dist; UC results/01, 06, 11, 12):
- Bare 1.2B:
  - Direct: 5/320 (1.6%) fit, 9/320 (2.8%) held-out.
  - With worked steps: 138/320 (43.1%) fit, 144/320 (45.0%) held-out. Raw copy-path format scores 0%.
  - Steps held-out by family: chain_story2 32/40, state_update 29, var_chain 28, chain_ops 25, fewshot 22, seq_cycle 7, cipher_map 1, group_induct 0.
  - No bare number exists for all 34 families.
- Sandwich main2 (1 seed, 50k updates, fixed layout):
  - All 1360 in_dist rows: 74.6%.
  - Worst-8: fit 161/320 (50.3%), held-out 123/320 (38.4%).
  - Per family of 40: chain_ops 7, state_update 4, var_chain 12, chain_story2 13, cipher_map 15, seq_cycle 18, fewshot 24, group_induct 30; copy_word 39, passage_qa 39, syllogism 40.
  - Strong families are near 100% and are the ones the bare LM already does.
- After 6000 more updates on 2000 rows: baseline fit 66.6%, held-out 48.1%; with steps 78.3 / 69.8. Project marks: 85% fit, 80% in_dist.
- Shifts (100 rows each; in_dist 72): answer 63, frame 65, vocab 78, variant 50, held-out family 13 (LIVE.md). The 1360-row plateau run reports family shift 24.4% on 160 rows (doubled-prompt layout), and the two figures are unreconciled.

English [S] (192-question sets):
- Fresh: 92.6 (bare 8-shot 75.0; zero-shot 29.7 exact, 76.0 contains). Generated held-out: 99.7.
- Per kind: negation 99, giver 98, comparison 95, two relations 95, which-one 87, event order 82 (bare 81, 88, 84, 72, 75, 50).
- New kinds R5: 79.9-81.1 vs 67.7 (counting 43.8; cause 81.8 vs 34.4).
- Second unseen set: 75.3-78.2 vs 77.6. NEW-KINDS-S: 64.4-66.3 vs 62.5.
- The same-size bar on FRESH is bare LFM2.5-350M 8-shot 50.0 (zero-shot 33.9). No bare number exists for ~30M models on these sets.

Arithmetic (real pipeline) [S]: two-step chain 81.4 own wording, 73-79 blind set 1, 62-66 blind set 2, long questions 66.6, with distractor numbers 50.2.

Lesion marks already fixed:
- A shuffled core must cost >= 20 points (UC DIAG-v4).
- The core must beat core-skipped by >= 10 (RTC copytalk).
- The sandwich scores 0.2 and 0 points, and copytalk +0.7.

Speed to beat: 19 q/s at batch 1, 325 at batch 64.
