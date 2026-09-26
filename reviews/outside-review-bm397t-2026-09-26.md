# Outside review of bm-397t (pasted by Ben in the Benchmarks thread, 2026-09-26 11:50 UTC)

Source: an outside reviewer that could read the repo (it cites repo files and Ben's Mac paths). Pasted verbatim below
by the benchmarks thread for the record. Every factual claim was checked against the code and saved results; see
artifacts/claude-bm397t-20260926/RESULTS-score.md, "Outside review, checked against the code". All checked claims
held. What was taken is in design/v3/30-modes/398-benchmarks-followups-2026-09-26.md ("Revised after the outside
review").

---

**My recommendation is to preserve the original model's reasoning path, make short answers an explicit output mode, and train the memory reader to select complete evidence.** Mixing in math practice is worth testing, but it should supplement that separation.

I inspected the training code, scorers, saved predictions, and judge labels. I ran read-only analyses and small in-memory checks. **I changed no files, weights, configuration, or Git state.** The proposed fixes below remain untested.

**The overnight result contains more than a length problem.**

- **The trained model changes which answers are correct.** Of the original model's 112 fully correct answers in the judged sample, only 71 stayed fully correct. It lost 41 and gained 36 elsewhere. Of those 41 losses, 33 were single-hop questions. This means the next training run must protect basic fact extraction as well as improve reasoning.
- **The net correctness difference is inconclusive.** My conversation-level bootstrap puts the change of −1.7 percentage points at roughly **−8.2 to +5.4 points**. The experiment demonstrated a reliable F1 improvement; it did not demonstrate improved correctness or establish that correctness was preserved.
- **The math failure is substantive.** Every trained-model GSM8K reply contains a number. It lost 156 previously correct problems and gained seven. The stricter answer extractor also shows a collapse, so a parsing fix cannot explain away the failure.

I would also soften the conclusion that shortening has exhausted its value. The existing optimistic, gold-guided "best substring" diagnostic still reaches **45.14** on the trained model's answers, versus its actual **37.07**. That is not an achievable score prediction—the diagnostic knows the answer and can select misleading fragments—but it means the remaining gap cannot yet be assigned entirely to correctness. There is also no equivalent blind correctness audit of Qwen in this experiment.

**1. Protect math by keeping the adapter separate from the base model.**

Keep the original weights frozen and the short-answer adapter unmerged. Enable it only at a clearly defined memory-answering stage. When disabled, execution should bypass the adapter and reproduce the original model under the same prompt and decoding settings.

Use two separate decisions:

- Does this question require remembered information?
- Does answering it require calculation or reasoning?

A question such as "How much did I spend across those three trips?" requires both memory and math. Simply routing every question about past chats into the existing short-answer adapter would still suppress useful reasoning.

The intended flow should be:

**Retrieve evidence → extract relevant facts → reason or calculate when needed → produce the final answer.**

Keep intermediate work separate from the final response. For LoCoMo, return the short final answer in the position the unchanged scorer expects. For math, preserve the requested working.

The current adapter is suitable for a routing experiment, **not deployment yet**, because its memory correctness and abstention checks failed. Adapter disabling is an established mechanism, although this repository's custom LoRA implementation would need its own explicit bypass. (PEFT documentation: disable_adapter.)

**2. Replace "learn to be short" with "learn to give a complete, supported answer."**

The existing training set makes the undesirable shortcut easy to learn:

- All 1,800 targets are short, answerable responses.
- There are no unanswerable examples or worked solutions.
- Lists contain two items; there are no genuine chains of reasoning.
- Training prompts are approximately 1.6k tokens, compared with a median near 24k in the recorded LoCoMo runs.
- Validation uses the same templates with another random seed.

More seriously, I tested the synthetic validation function: it accepts both "Not Varnholt" and "Varnholt or Eskbridge" when the answer is "Varnholt." Consequently, **199/200 on this validation set is not evidence of 99.5% semantic accuracy**.

For the next candidate, start from the original base and train on independently generated conversations containing:

- Similar facts belonging to different people.
- Corrections, negations, former versus current facts, and ambiguous references.
- Lists of varying lengths that require complete answers.
- Relative dates, multi-step questions, and arithmetic over remembered facts.
- Missing evidence, partial evidence, and conflicting evidence.
- Longer histories with relevant information at different positions.

Where construction allows it, record the supporting turn IDs, the required facts, any derivation, and the final answer. Supervise evidence selection and derivation as well as the final wording.

The target should be **the shortest complete supported answer**, without a universal word cap. Hold out templates, entities, and reasoning patterns—not just random seeds. Research on long-context models supports testing evidence position explicitly; merely fitting a long context does not establish reliable use of it. (Lost in the Middle, arXiv 2307.03172.)

**3. Diagnose retrieval and reading separately before spending more on either.**

The existing retrieval results expose a substantial bottleneck: the fused top-20 retrieval finds **some** annotated evidence for 75.3% of questions, but **all** annotated evidence for only 61.8%. For multi-hop questions, complete-evidence retrieval is just **18.1%**. "An evidence line was found" is therefore too weak a success criterion.

Run the same reader on four conditions using a fresh, independently authored development bank:

| Context supplied | What the comparison reveals |
|---|---|
| Complete supporting passages | Whether the reader can answer when evidence is available |
| Those passages plus controlled distractors | Whether irrelevant context causes failures |
| Actual retrieved passages | How much retrieval limits the reader |
| Full conversation | Whether retrieval helps compared with reading everything |

Use identical answer formatting across conditions. Include Qwen on the same questions and in the blind correctness audit.

If complete supporting passages fix most errors, improve retrieval: expand neighboring turns, preserve speaker and date, and retrieve missing links for multi-part questions. If the model still fails with complete evidence, prioritize reader training.

This distinction matters because retrieval misses cannot explain the entire original result: the plain-model baseline already receives the full conversation.

**4. Treat math replay as a separate preservation experiment.**

For a model that must support both styles within one adapter, mix short memory answers with verified worked math solutions and general instruction-following examples. Make the requested output mode explicit during training.

Two details matter:

- A correct final number does not guarantee correct working. Prefer generated arithmetic with executable intermediate checks, or verify the intermediate steps in accepted model solutions.
- Select checkpoints using both memory correctness and reasoning preservation. The lowest short-answer training loss is not the selection criterion.

Use explicit task weighting and report the supervised-token allocation. The current trainer averages each example's token loss before combining examples; adding long math responses does not automatically give reasoning proportionately more training weight.

I would test math replay and unanswerable-memory training separately before combining them. The queued proposal changes both together, which would make its result harder to interpret.

**The copy-only finalizer should not be pursued in its present form.**

Its constraint checks vocabulary, not meaning. My constructed tests confirmed that it accepts deleting a negation, selecting another person's fact, and dropping a required list item. This explains why copying only existing words failed to preserve correctness. A future finalizer needs structured facts or evidence-aware verification; another shortening prompt does not address that defect.

**I would run the next experiments in this order:**

| Experiment | Advance only if |
|---|---|
| Adapter isolation and mixed memory/math routing | Disabling the adapter reproduces the base; switching between requests does not alter later general answers |
| Complete-evidence reader diagnostic | It identifies whether retrieval, distraction, or reading contributes most to incorrect answers |
| Evidence-trained memory adapter | Blind complete-answer accuracy improves, unsupported answers do not rise, and list/date completeness is preserved |
| Mixed-task replay, if needed | It preserves the memory improvement and meets the existing GSM8K floor of 182/300, followed by a fresh reasoning check |

Keep official F1 as a compatibility metric, alongside blind correctness, complete-evidence recall, unsupported-answer rate, and abstention on genuinely unanswerable questions. Include supporting context in the next semantic audit; the current judges see the question, key, and response, which limits their ability to assess factual support.

Use LoCoMo as development data from here onward, preserve the historical scores, and reserve LongMemEval for the final frozen candidate. Also replace the weak MMLU preservation baseline in a separately registered evaluation: the original **50/300** largely reflects failure to emit option letters, so preserving that number is not meaningful protection of general capability.
