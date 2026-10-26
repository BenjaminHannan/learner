# Completeness critic (2026-10-05)

**(1) Contradictions and suspect claims**

- **The baselines "Context" paragraph uses superseded numbers.** 121/320 (37.8%), 68.5% and 24.4% were all measured with the prompt fed twice. The fixed figures are trainfit 161/320, held-out 123/320 and in_dist 74.6% (SCREEN-v4.md:6). The claim "reached 48.1% on its 2,000 practised rows" is wrong: 48.1% is held-out, and fit was 66.6% (SCREEN-v4.md:25). So "bare LM with steps is in the same range as the sandwich" needs recomputing.
- **The digest says "SR, SP, P … no results".** That is out of date. Branch commit e9e99d567 (04:00Z) has these results:
  - P: 72.4 fit / 49.4 held-out.
  - SR: 83.3 / 80.5.
  - SP: 86.8 / 78.9, with every seed at or above 85%.
  - MX and SL/BL (lesions) are pending. Read SCREEN-v4.md:44-75 and PANEL-v4.md.

  All of these gains come from the LM writing the steps. The current main line moves reasoning further into the LM, which is the opposite of Ben's goal.
- **custom-readers #2 ("reads the question once… the structural difference") is wrong.** The core already re-injects the input every round: `z = h + e` (claude_fewex_net.py:77-81). The real faults are two. First, |e|/|h| = 44 and ln_state rescales h, so the input swamps the state. Second, e is a 32-dim-per-token feature computed once. What the core lacks is attention that re-reads the raw tokens and changes from round to round.
- **Steps vs answer-only.** looped-reasoners says answer-only supervision extrapolated better (2603.21676). The repo measured steps at +11.8 fit and +21.7 held-out. The two can fit together if the step targets supervise the core, not the talker. That is untested.
- **LPN figures differ between reports:** "7.75 → 15.5% OOD" vs "0% vs 88%". Check 2411.08706 before quoting either.
- **The intact score is 160 in one place and 161 in another.** 160 is job 09 (answers fed in, not generated); 161 is job 06 (generated). The reports mix the two.
- **custom-readers cites 1909.07940 for "a raw scalar is weak".** That paper is Wallace et al.'s char-CNN numeracy probe. Verify the attribution.
- **looped-reasoners says "no paper shows NL QA at tens of M from scratch".** It overlooks Saxton et al. 1904.01557 (character-level, about 30M parameters, text math questions, interpolation and extrapolation splits).

**(2) Missing facts for a designer**

- **The key bar is missing.** No from-scratch plain transformer has been trained on the skills curriculum. I searched all branches; the Fable baseline was a different task and under-trained. This should be experiment 1.
- **Compute (estimate, untested).**
  - Character-level gives about 17-20M characters per epoch (200k rows × about 85 characters).
  - The core has about 2.6M live parameters × 4 rounds. That is about 1e15 FLOPs per epoch: minutes on a 5090, roughly hours on CPU.
  - The existing batch-1 harness (500 updates/min) needs about 6.7 h per epoch, so batching is mandatory.
  - The generator gives unlimited rows. Keep the hash-pinned seed-1 build for comparisons.
- **Sequence length at character level.**
  - Train prompts reach 204 characters, so the position cap of 64 and the N≤64 token skip must change.
  - Local heads (±1 position) and relative bias clipped at ±4 would see only neighbouring characters.
  - The share of training rows dropped by the 64-token skip is unreported. Compare the new model and the sandwich on the same rows.
- **Symbols that appear only in dev.** Capital O appears only in dev/vocab, and # @ & $ only in dev/family. op_define depends on the never-trained `@`. Use a byte vocabulary or symbol-agnostic handling.
- **Word tokenisation fails.**
  - Train has 13k made-up words; OOV rate is 10% on vocab and 29% on family.
  - cipher_map and string_transform need brand-new strings.
  - Answers are at most 8 characters in train and 12 in dev; 61% are numbers up to 4800.
  - So the output should be character-level with copying, possibly fixed slots read out in one pass.
- **Scope of "beats same-size models".** The English 192-question sets cannot be reached with nothing pretrained, so claims must use the skills curriculum.
  - Report live and stored parameters separately: 9.0M stored vs about 2.6M live, because the dead MoE experts inflate the count.
  - clock_date needs world knowledge, so exclude it or treat it as a floor (weekday chance is 1/7).
  - Shortcuts (syllogism, object_track) and the 82% template overlap inflate in_dist.
- **Lesion design without an LM.** An LSTM or GRU reader, or an autoregressive talker, can take over the reasoning.
  - Add a core-skipped arm with the same reader and talker trained.
  - Fix the talker's access to the input in advance.
  - Use the donor-swap check from the data report.

**(3) Missing research angles**

- **Character-level from-scratch math QA:** Saxton 1904.01557, the TP-Transformer 1910.06611.
- **Executing code and exact arithmetic:** Learning to Execute 1410.4615 (it looks like var_chain), Neural GPU 1511.08228, NALU 1808.00508 and NAU/NMU 2001.05016.
- **State tracking and why a loop is needed:** Merrill, "Illusion of State" 2404.08819 (relevant to state_update, var_chain and object_track).
- **Shortcut precedent:** math word-problem solvers trained from scratch (seq2tree, GTS, Graph2Tree) and SVAMP 2103.07191, which shows those solvers answer without reading the question.
- **Per-family matches:** RobustFill 1703.07469 for string_transform and fewshot_number_rule; CLUTRR 1908.06177 for kin_chain.
- **Adaptive halting:** ACT 1603.08983 and PonderNet 2107.05407. The halt head exists but is never used, and the chain families need varying numbers of steps.
- **Digit tokenisation:** Singh & Strouse 2402.14903 (right-to-left digit grouping).
- **Supervising the core directly:** 11 families already store worked equations in `steps`. They could supervise intermediate values on the core's rounds, or the alignment test from fair-eval could be used as a training loss.
- **Task diversity:** the generator could add sub-rules to get closer to the many-task threshold that fair-eval cites (Raventos). With 38 families, the induction families will probably only identify the task.
