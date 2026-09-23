# GPT-6 Pro answers, batch 2 (2026-09-23)

17 of 18 answers, pasted by Ben 10:21-10:23 UTC; question 18 (web mode) not answered yet. Verbatim except citation markers removed. Verification notes: batch2-answers-check.md.

## Answer to question 1: A gate that still works on wording it has never seen
(message cmsg_01FuvegZXjMmeUzStiEFVnEWW7YZCA5kW4X5ugdHDiH5hP, 2026-09-23T10:22:33Z)

**UNTESTED — recommendation:** Run a **frozen-score threshold experiment before building another checker**. It should answer: *Does the current gate already give enough information to separate good writes from bad ones, or does it misunderstand the message?* My leading hypothesis is that you have **both a reader problem and a cutoff-transfer problem**, not merely a poorly chosen number.

**UNTESTED — architectural recommendation:** The most promising eventual gate is **joint, evidence-based verification with checks targeted at different error kinds**, plus explicit user confirmation when the text does not resolve an ambiguity. I do **not** know of evidence establishing nearly independent errors for that design in your setting.

I use **SHOWN** for supplied measurements or published results, **SUGGESTED** for transferring published findings to Premonition, and **UNTESTED** for my proposed procedures and case-specific reasoning. A tag applies to its paragraph or explicitly introduced table.

## 1. Diagnosis

### Your measurements establish failure, but not a single cause

**SHOWN:** Using your revised wrong-frame counts, the YES/NO gate accepted **23 of 25 genuinely wrong ear frames** on the fresh development set. On the original development set, it accepted **13 of 103 scored-wrong frames**. You also measured substantial score changes when only the prompt wording changed. Those results establish that the original development performance did not transfer; they do not isolate whether the cause was threshold selection, different error types, different language, or different labels. 

**UNTESTED:** Your “overfit threshold” explanation is therefore plausible but incomplete. Distinguish these possibilities:

| Explanation | What is happening | Can a new scalar threshold fix it? |
|---|---|---|
| **Cutoff mismatch** | Good frames generally score above bad ones, but the useful cutoff moved. | Potentially. |
| **Poor separation** | Bad frames score as highly as good frames you need to retain. | Not without sacrificing those good frames. |
| **Missing proposals** | The ear never proposes the correct fact. | No. |
| **Incorrect evaluation target** | The key omits asserted facts or applies an unclear spelling policy. | No; the evaluation must be repaired. |

**UNTESTED:** A monotone remapping of the existing score—changing what “0.8” means without changing the ordering—cannot solve poor separation. It preserves the same possible accepted sets. Your three operating thresholds are not enough to determine whether a useful operating point exists between or beyond them.

### Correcting the key changes more than the wrong count

**SHOWN:** The fresh-set table reports 155 ear proposals, including 65 initially scored wrong, later revised to 25 wrong. Under that revised binary grading, **130 proposals are correct**, not 90. The corrected gold-fact denominator is not supplied. Therefore, the raw \(90/117\) figure cannot be treated as corrected recall. 

**SHOWN:** The separate registered panel reports ear recall of **95/125 = 76%**, YES/NO recall of **94/125 = 75.2%**, and QA recall of **81/125 = 64.8%**. 

**UNTESTED — mathematical consequence:** On that registered panel, a gate that only deletes proposals cannot reach 85% end-to-end recall, even if it perfectly identifies every wrong proposal. Its ceiling is 76%. A successful gate experiment must not be presented as fixing the assistant’s overall recall.

### “Nearly independent errors” is not the right acceptance criterion

**SUGGESTED:** Choosing different model families or training data is not sufficient evidence of independent mistakes. *Correlated Errors in Large Language Models*, **arXiv:2506.07962**, found correlated wrong answers across models, including models with different architectures and providers. That is not your extraction task, but it argues against treating model diversity as an independence guarantee. 

**UNTESTED:** Measure the quantities that directly determine safety instead:

\[
a=P(\text{gate accepts}\mid\text{ear proposal correct}),
\qquad
b=P(\text{gate accepts}\mid\text{ear proposal wrong}).
\]

You need high \(a\) and very low \(b\), especially **within each error kind and each held-out writer**. A low overall correlation statistic would not substitute for those measurements.

**UNTESTED — calculation from the registered counts:** With 95 correct and 30 wrong incoming proposals, retaining 88% of correct proposals would produce an expected wrong-save fraction

\[
\frac{30b}{95(0.88)+30b}.
\]

Keeping that below 1% requires \(b<0.0282\): **the gate must reject more than 97% of incoming wrong proposals under that particular mixture**. This is not a performance forecast; it illustrates how demanding the target is. The reported YES/NO and QA gates accepted 6/30 and 5/30 wrong proposals, respectively. 

### The typo failures expose a target-definition problem

**SHOWN:** Two real wrong saves involved typos copied into values, despite high YES scores. Your existing brake already checks whether a value occurs in the turn.  

**UNTESTED:** Copying text exactly prevents invented text; it does not establish that the spelling represents the user’s intended entity. An unfamiliar fictional name and a misspelled familiar name can look identical without additional context.

**UNTESTED — recommendation:** Freeze the spelling policy before another test. Distinguish an unsupported value, a literal spelling the user actually supplied, and an uncertain match to a previously confirmed entity. Do not silently autocorrect an uncertain name. When intent cannot be determined, confirmation adds information that neither the ear nor the gate currently possesses.

### The QA explanation needs a more precise diagnosis

**SHOWN:** On the registered counts, QA retains \(81/95=85.3\%\) of the facts the ear correctly proposed. Its reported **30.4% held-back rate** does not equal either \(1-81/125\) or \(1-81/95\). I do not know its denominator from the supplied material. The registered FAIL should remain FAIL. 

**UNTESTED:** “Three chances to say no” explains a possible mechanism, not the measured cause. Log which check rejects each correct proposal and why: wrong interpretation, multiple valid answers, answer-format mismatch, or failure to understand the checking question. Changing an AND rule to a vote without that diagnosis could restore exactly the unsafe frames QA was catching.

## 2. Four ranked options

These are ranked by likely architectural value, not by which should be implemented first. The inexpensive diagnostic for option 2 comes next.

### 1. Joint evidence verification, organized by error kind

**UNTESTED — proposed design:** Have the checker evaluate **the complete owner–relation–value binding and its assertion scope**, while returning an auditable support record. Use your existing planned span machinery and speech-act components; I am not presenting those as new inventions. The proposed difference is a verifier trained and evaluated on **specific semantic mistakes**, rather than another generic approval prompt.

**UNTESTED:** The division of responsibility should be:

| Error kind | Required evidence or check | Important limitation |
|---|---|---|
| **Value/spelling** | Exact source offsets; comparison with confirmed entity identity where available. | Cannot recover an unknown intended spelling. |
| **Speech act** | Whether this particular clause asserts the fact, rather than asks, imagines, quotes, or retracts it. | A familiar cue such as “so” is not a complete decision rule. |
| **Binding** | Why this owner is linked to this value through this relation. | Finding all three somewhere in the message is insufficient. |
| **Relation** | Predicate meaning and argument roles support the selected relation. | Alias matching alone will miss paraphrases or confuse nearby meanings. |

**UNTESTED — example:** In “Mira is Tovan’s sister; Leto studies at Alder School,” the words needed for `Mira | school | Alder School` all occur, but that triple is unsupported. Separately approving the owner, relation and value would miss the error. **Keep separate diagnostic scores, but require a joint tuple decision.** Do not multiply field probabilities as though the fields were independent.

**SUGGESTED:** HANS, *Right for the Wrong Reasons*, **arXiv:1902.01007**, demonstrates how inference models can rely on lexical overlap and misleading syntactic patterns. It supports training and testing on contrasts that preserve the words while changing their relationships—not the claim that doing so will solve Premonition’s gate. 

**SUGGESTED:** Requiring quoted evidence is useful for inspection, but not sufficient permission to write. Ye and Durrett, *The Unreliability of Explanations in Few-shot Prompting for Textual Reasoning*, **arXiv:2205.03401**, found explanations that were not grounded in the input or did not entail the prediction, including extractive explanations. 

**UNTESTED — cost and limit:** Prefer one shared verification pass with several outputs, not four serial model calls. Training cost, latency and recall are unknown until measured. This may still be another semantic reader with the ear’s blind spots; it does not establish independence or constitute a formal proof of meaning.

### 2. Calibrated selective acceptance

**UNTESTED — proposed role:** Freeze the checker and choose a cutoff on explicitly designated calibration data. This is the right first diagnostic because it changes neither the representation nor the language-reading task.

**SHOWN — published:** *Learn then Test*, **arXiv:2110.01052**, provides high-probability risk control under its sampling assumptions and explicitly handles error conditional on accepting a prediction. It also addresses the multiplicity problem when selecting among candidate settings. 

**SHOWN — published:** The basic *Conformal Risk Control* result, **arXiv:2208.02814**, controls an expected loss under exchangeability and monotonicity conditions. That is not automatically a 95%-confidence certificate that a fixed deployed gate’s conditional wrong-save rate is below 1%. 

**SHOWN — published:** More recent work, *Conformal Selective Prediction with General Risk Control*, **arXiv:2603.24704**, explicitly distinguishes different deployment-risk targets and provides expectation-based guarantees under specified assumptions. Those distinctions still matter when selecting a method for your particular certificate. 

**UNTESTED — cost and limit:** Calibration adds essentially a score comparison at runtime, but consumes fresh labels. It cannot create semantic separation, recover omitted facts, or guarantee performance under arbitrary new wording. Calibrating on one writer does not, by itself, justify treating another writer’s language as exchangeable.

### 3. Targeted user confirmation

**UNTESTED — proposed design:** Route unresolved cases to a confirmation that displays the **specific proposed fact**, including the spelling and owner. A structured confirmation is preferable to passing a free-form “yes” through the same unreliable reader.

**UNTESTED — what it fixes:** Confirmation can supply missing information about intended spelling, group ownership or whether the user was telling versus checking. Unlike a second model vote, it can introduce new evidence.

**UNTESTED — what it costs:** Count a true fact awaiting confirmation as **not saved on the original turn**, even if later confirmed. Report immediate recall and eventual recall separately. One clarification holding back four true facts counts as four delayed facts, not one.

**UNTESTED — metric rule:** Report all of the following without changing denominators between arms:

\[
R_{\text{immediate}}
=\frac{\text{true facts correctly saved immediately}}{\text{all asserted gold facts}},
\]

\[
H_{\text{gate}}
=\frac{\text{true proposed facts delayed or rejected by the gate}}{\text{all asserted gold facts}}.
\]

Also report ear misses, and the fraction of turns interrupted. If your 12% bar instead means **all** true facts not immediately saved, it implies \(R_{\text{immediate}}\ge88\%\), stronger than the separate 85% target. The supplied wording does not settle which interpretation generated the existing reports.

**UNTESTED — limitation:** A “cheap risky-case detector” becomes a safety-critical component. Its unflagged mistakes must be audited; showing that flagged cases are difficult is not enough. User confirmation can also be mistaken, and later confirmation must not retroactively turn an unsupported original extraction into a correct one.

### 4. Candidate-blind disagreement between genuinely different readers

**UNTESTED — proposed design:** A second reader independently extracts from the unchanged turn **before seeing the ear’s answer**. Compare full tuples and assertion status, not just generated sentences. Independence of the data should concern constructions, generation processes and supervision—not merely fictional names or random seeds.

**SUGGESTED:** *Selective Question Answering under Domain Shift*, **arXiv:2006.09462**, found benefits from training an error predictor with examples from additional domains. It also found that detecting unfamiliar-domain inputs was not equivalent to predicting errors. That supports diverse error supervision, rather than simply rejecting unfamiliar wording. 

**UNTESTED — cost and limit:** This adds training and inference work and can reject correct facts whenever the readers disagree. Agreement still does not establish correctness. It is a lower-priority route than diagnosing the existing scores, and should not be sold as a new version of the Qwen-full-reader experiment you already tried.

## 3. The one experiment to run next

### Experiment: frozen-score threshold rescue

**UNTESTED — hypothesis:** A single cutoff fitted on fresh calibration data can transfer to new writers while producing **zero observed wrong saves** and retaining at least **88% of correctly proposed facts**.

**UNTESTED — my prediction:** This hypothesis will fail: even the best hindsight cutoff will lose too many correct proposals on at least one held-out writer. That prediction is falsifiable; a successful transferred cutoff would count against my diagnosis that the current score lacks sufficient separation.

### The single system change

**UNTESTED — protocol:** The base is the current frozen ear, brake, checker prompt, claim renderer and **0.25 cutoff**. The candidate changes **only the cutoff**. No new prompt, normalizer, confirmation rule, verifier, relation rule or retraining is allowed.

**UNTESTED — protocol:** Seal the deterministic cutoff-fitting algorithm before calibration. Seal its resulting cutoff before opening the test. Calibration examples are explicitly **not TEST-ONLY examples**; none of the registered test examples may influence the cutoff.

### Sample size and construction

**UNTESTED — protocol:** Use **630 fresh turns maximum**:

| Partition | Size | Purpose |
|---|---:|---|
| Calibration | 150 | Fit one cutoff. |
| Registered test | 450 | Three isolated writers, 150 turns each. |
| Director probe | 30 | Separately sealed; used only after a provisional PASS. |

**UNTESTED — protocol:** Each 150-turn partition contains 30 turns in each of five families: ordinary/paraphrased assertions; multiple entities and appositives; corrections and ownership; non-assertions including punctuation-free checks; casual typing and spelling ambiguity. The director probe contains six per family.

**UNTESTED — protocol:** Writers must not see model outputs, calibration items or one another’s items. Do not split paraphrases of a common seed across calibration and test. This tests transfer across isolated writing processes; it does not make three AI writers a representative sample of all future users.

**UNTESTED — sample-size rationale:** This is a diagnostic study, not the final 1% certification study. Require the registered test to contain at least **200 distinct turns with a correct incoming proposal** and **30 distinct turns with a genuinely wrong incoming proposal**, measured after the unchanged brake.

**UNTESTED — calculation:** Thirty independent wrong-proposal cases would give only a \(0.9^{30}=4.24\%\) chance of observing zero acceptances if the gate actually accepted 10% of such errors. Thus, the error quota can distinguish a grossly leaky gate from a much better one. It cannot establish a 1% wrong-save rate, and clustering or shared writing processes weaken that independence assumption.

**UNTESTED — protocol:** The 450-turn test is fixed in advance. If those challenge quotas are not met, record **FAIL TO ESTABLISH**, with insufficient challenge as the reason. Do not extend the panel until a favorable result appears.

### Gold labels and scoring

**UNTESTED — protocol:** Before evaluation, two isolated graders independently enumerate all asserted canonical facts. Adjudicate omissions, appositives, relation equivalences and spelling policy without seeing gate scores. Legitimate ambiguity receives a preregistered “clarification required” disposition rather than being removed from the panel.

**UNTESTED — protocol:** Preserve original keys and every amendment. Apply any preregistered adjudication rule equally to both arms, blind to arm identity. Unresolved grading disputes prevent PASS; they must not be quietly assigned whichever label improves the result.

### Fit exactly one cutoff

**UNTESTED — algorithm:** On the calibration set, select the **lowest cutoff that rejects every genuinely wrong proposal**. This maximizes retention among cutoffs having zero calibration wrong saves.

Because acceptance is \(s\ge t\), the cutoff must be just above the largest wrong-proposal score. Specify the floating-point convention before sealing. If calibration has no wrong proposals, use zero and flag that the calibration set supplied no negative evidence. If the largest wrong score forces rejection of everything, retain that result rather than changing the algorithm.

**UNTESTED — limitation:** This is deliberately a simple diagnostic cutoff fit, **not** a conformal procedure or a certificate. The independent test determines whether it transfers.

### Exact pass marks

**UNTESTED — protocol:** A **THRESHOLD-RESCUE PASS** requires all the following:

| Measure | Registered requirement |
|---|---:|
| Wrong accepted facts | **0** across all 450 test turns |
| Retention of correct incoming proposals | **At least 88.0% overall and within each of the three writers** |
| Challenge adequacy | **At least 200 correct-proposal turns and 30 wrong-proposal turns** |
| Candidate median full-turn latency | **At most 800 ms** |
| Director probe | **0 wrong saves**, at least **88.0% gate retention**, and at least **10 correct incoming proposals** |
| Unresolved scoring disputes | **0** |

**UNTESTED — protocol:** For a writer with \(C\) correct incoming proposals, retaining at least \(\lceil0.88C\rceil\) is required: 88/100, 176/200, and so forth. Report end-to-end recall, both held-back definitions, wrong/save counts and family-level results alongside this verdict.

**UNTESTED — important scope:** This is a **gate-diagnostic PASS**, not a deployment PASS. It cannot waive the assistant’s overall recall target or its certification requirement. The 88% incoming-proposal retention bar is explicitly an experimental measure, not a silent reinterpretation of the original 12% metric.

**UNTESTED — execution:** Use the same recorded proposals and checker scores for paired decision comparisons. For latency, run the actual candidate pipeline with score computation included; timing a cached score lookup does not count. Use isolated notebook states so one arm cannot influence the other.

### The decisive diagnostic: could any cutoff have worked?

**UNTESTED — preregistered analysis:** After scoring the frozen candidate, compute the complete test-set threshold frontier. In particular, find the lowest hindsight cutoff yielding zero wrong saves, and calculate its retention overall and for each writer.

This is an **oracle diagnostic**, not a new deployable candidate. Its cutoff must not be adopted from the test.

| Outcome | Interpretation |
|---|---|
| Frozen cutoff passes, including probe | Evidence that cutoff recalibration transferred on these writing processes. |
| Frozen cutoff fails, but a hindsight cutoff meets all safety/retention bars | The scores contain usable separation on this test, but the fitted cutoff did not transfer. |
| Even hindsight cannot achieve zero wrong saves and 88% retention for every writer | No scalar cutoff can meet those empirical requirements on this fixed test. More cutoff tuning is not the remedy for those examples. |
| Gate passes but end-to-end recall remains below target | The ear remains a separate bottleneck. |

**UNTESTED — falsification:** A transferred PASS would refute my preregistered prediction that the current score cannot support the required separation across these writers. An oracle failure would refute the **threshold-only rescue hypothesis on this panel**, not prove that no future verifier could work. It also would not, by itself, prove that every threshold’s population error exceeds 1%.

### What comes later—not in this experiment

**UNTESTED — next-step rule:** If the oracle fails, use the one permitted diagnosis-driven follow-up to target the dominant verified failure kind with a changed verifier. Do not simultaneously add four specialists and a normalizer. If the frozen cutoff passes, the separate next step is certification of a fixed pipeline and resolution of the ear’s recall deficit.

**UNTESTED — statistical calculation:** For a fixed system and independent, identically distributed saved-fact audit units with reliable labels, zero errors in \(n\) observations gives the one-sided 95% upper bound

\[
U=1-0.05^{1/n}.
\]

It takes **299 such observations** for \(U<1\%\). But 299 chat turns are not necessarily 299 saved facts, and several saved facts from one turn are not automatically independent. The deliberately balanced, writer-blocked diagnostic above should not be relabeled as that certificate. Selective-error inference must use the accepted-prediction denominator. 

## 4. Strongest objection and rejected rival

**UNTESTED — strongest objection:** My preferred evidence-based gate may simply become a more elaborate version of the same unreliable language reader. Correct offsets do not prove correct attachment or assertion status, and additional checks may destroy recall. Your existing strict compiler’s **67.6% oracle coverage** is already a warning against assuming that more restrictions will meet the coverage target. 

**UNTESTED:** The threshold experiment also consumes fresh labels without improving the reader. Its value is narrower: it determines whether further cutoff work is justified before committing scarce effort to a new verifier. It does not validate the proposed replacement architecture.

**SHOWN — rejected rival:** I would not run another three-question QA variant next. The registered version already missed the safety, held-back and latency bars, with five wrong saves and 880 ms median latency.  

**UNTESTED:** Another prompt or voting-rule adjustment would entangle changed semantic judgments with changed acceptance policy. The frozen-score experiment separates those explanations more cleanly.

**Source-depth note:** I reviewed relevant full-text sections of the papers cited above; none of the recommendations relies solely on an abstract.

## Plain-language summary

**SHOWN:** Your gate has accepted real mistakes, and your ear has also missed many true facts. The separate registered test reports that the ear found only 95 of 125 facts before checking. 

**UNTESTED:** Raising the cutoff can help only when the checker gives good facts higher scores than the bad facts it needs to reject. The next experiment should change only that cutoff and test it on new writers. It should also check whether any cutoff could have succeeded on those same examples. If none could, the checker needs better understanding rather than another number. Better checks should verify who is connected to which fact, not merely whether the words appear. When the message does not reveal the intended meaning or spelling, ask the user and count the resulting delay honestly. Passing this experiment would be useful progress, but it would not by itself certify the whole assistant.

## Answer to question 2: Write rules that can cover 85% of real facts without licensing wrong ones
(message cmsg_01FuvegZXjMmeUzStiEFVnEWBYiiM61PKBi2w1uZTPhF5w, 2026-09-23T10:22:47Z)

## Recommendation

**UNTESTED — recommendation:** Keep a compiler as the only component allowed to write, but replace **“the right words appear somewhere”** with **“the whole source sentence supports this particular reading under a small, explicit grammar.”** Let the learned reader propose interpretations and abstain; do not let confidence override a missing licence or choose between substantively different licensed meanings.

**UNTESTED — immediate decision:** Run the queued plural-and-verb expansion as a **permission audit before training**. Measure both whether correct transactions are expressible and whether incorrect transactions can get through. The existing audit supports investigating this approach, but it does **not** establish that these additions will reach 85%, much less satisfy the separate 12% holdback limit.

## 1. Diagnosis: the present rules check evidence fragments, not complete meaning

### The coverage arithmetic is tighter than it first appears

**SHOWN — your reported measurements:** Version 0 permits 184 of 272 true facts, leaving **88 missed facts**. However, the listed miss reasons total **89**: \(59+12+10+7+1\). Also, allowing WE → ME gains nine facts, whereas ten misses have a WE owner. These differences could reflect overlapping blockers or transaction-level effects; the supplied summary does not resolve them. Do not add those categories as independent recoverable gains. 

**SHOWN — arithmetic from those measurements:** Reaching 85% on the same 272 facts requires at least **232 correct saves**, or **48 more** than the baseline. If those gains came entirely from the 59 no-cue misses, the expansion would need to recover **48/59 = 81.4%** of that group. Recovering all 59 would give 243/272 = **89.3%**, before accounting for overlaps and whole-turn blocking. That is a conditional calculation, not a forecast. 

**UNTESTED — interpretation of the targets:** “At least 85% saved” and “at most 12% held back” are compatible, but the second is stricter **if every unsaved true fact counts as held back**. Under that interpretation, the effective target is 88%: **240/272**, requiring **56 additional facts**, or 94.9% of the 59 no-cue cases under the same simplifying assumption. If “held back” excludes facts the ear never found, those must be separate metrics; otherwise omissions can disappear from the refusal count. I use the stricter, all-unsaved interpretation in the experiment below. 

### Four explanations need correcting or qualifying

**UNTESTED — diagnosis: “No relation cue” combines different problems.** A plural is a missing surface form. “Works at” requires a mapping from a grammatical construction to a relation. “Ada’s Pip” may lack an asserted relation altogether. Those are not interchangeable failures, and adding aliases cannot safely solve all three.

**UNTESTED — diagnosis: a span guarantee is not a meaning guarantee.** Copying owner and value from the message prevents invented strings. It does not prevent attaching the wrong owner, reversing a relation, copying a typo, or treating a question as an assertion. Likewise, finding “sister” somewhere does not establish that the proposed owner and value participate in that sister relation.

**SHOWN — published limitation:** Synchromesh explicitly distinguishes satisfying formal output constraints from capturing the user’s intended meaning. Its constrained decoding can prevent specified implementation errors, while conceptual errors can remain. That distinction applies directly to claims about what a compiler has proved. *Poesia et al., “Synchromesh,” arXiv:2201.11227*, especially §4.2. 

**UNTESTED — diagnosis: the oracle audit may hide the dangerous decisions.** An oracle supplying the correct mode, owner and relation can establish a coverage ceiling. It does not establish that a mistaken reader cannot submit an incorrect ASSERT frame that passes the compiler. The report does not say that all such alternative submissions were tested.

**UNTESTED — diagnosis: whole-turn atomicity requires completeness checking.** “Commit all submitted frames together” is weaker than “commit all facts asserted by the turn together.” A reader could submit one of three facts, and a compiler could atomically commit that incomplete list. The source analysis must establish the complete transaction, or decline it; a learned fact-count prediction is not a proof of completeness.

## 2. Three ranked options

**UNTESTED — design comparison:** These rankings concern Premonition; they are not measured results.

| Rank | Option | What it fixes | What it costs | What it cannot fix |
|---|---|---|---|---|
| **1** | **Source-grounded licences, with a learned proposer and abstention** | Extends beyond exact cue words while restricting which source interpretations may become writes. Makes particular failure classes inspectable. | A compositional grammar, evidence records, ambiguity handling and independent testing. | Meaning absent from the available text; every typo; arbitrary conversational intent; inadequate relation inventory. |
| **2** | **Selective learned parser with mechanical write checks and independently audited risk** | Potentially covers more varied phrasing without writing a rule for each construction. | Own-model training, representative calibration data, reliable labels and fresh testing after changes. | A guarantee for each individual write; missing information; protection against arbitrary wording shifts. |
| **3** | **Explicit teaching/confirmation language** | Makes write authorization and ambiguous values clearer: the user confirms a particular displayed transaction. | Additional interaction and more first-turn holdbacks. | The first-turn coverage target unless ordinary messages already fit the accepted language. |

**SUGGESTED — published precedent for option 1:** Restricted natural language can be parsed compositionally into formal representations. Schwitter demonstrates an explicit grammar-to-logic pipeline, rather than treating isolated words as sufficient evidence. That supports the engineering approach, not an 85% coverage prediction for casual chat. *“Controlled Natural Language Processing as Answer Set Programming: an Experiment,” arXiv:1408.2466.* 

**SUGGESTED — published precedent for option 2:** SelectiveNet jointly learns prediction and rejection and demonstrates improved risk–coverage trade-offs in classification and regression. It is a credible rival to an ordinary confidence threshold, but its experiments do not establish safe notebook writing. *Geifman and El-Yaniv, “SelectiveNet,” arXiv:1901.09192.* 

## 3. What the recommended licences should actually guarantee

### The common contract

**UNTESTED — proposed design:** A write proposal should carry a checkable evidence record: immutable source offsets, licence identifier, owner/value bindings, relation direction, assertion scope and the complete proposed transaction. A later context licence would also require references to specific earlier turns or a specific pending clarification.

**UNTESTED — proposed restriction:** The compiler must verify these against the source. It must not accept a generated explanation such as “this is an assertion” as evidence that it is one. Unsupported sentence structure, an unanalysed meaning-changing clause, or an unresolved binding must block the transaction.

**UNTESTED — conditional proof obligation:** Let \(\mathcal T_G(x,h)\) be the set of complete transactions allowed by grammar \(G\) for message \(x\) and permitted history \(h\). Automatic writing requires:

\[
\mathcal T_G(x,h)=\{A\},\qquad A\ne\varnothing.
\]

In words: **the supported readings agree on one complete write transaction**. Include non-writing readings in the ambiguity analysis; do not silently discard them.

**UNTESTED — important boundary:** A proof of this property would be relative to the grammar and its semantics. It would not prove that the grammar captures every possible English reading or the user’s unexpressed intention. A learned proposer must not turn an incomplete search into a false uniqueness claim by returning only its favourite interpretation.

**SUGGESTED — relevant evidence:** Saparina and Lapata find that generating alternative interpretations helps ambiguous semantic parsing, but explicitly report that valid interpretations can still be missed and incorrect ones generated. Thus, agreement among a few model-generated readings is not evidence that no other reading exists. *“Disambiguate First Parse Later,” arXiv:2502.18448*, §§6–7. 

### A. Cue words and morphology: preserve the relation, not merely the spelling

**UNTESTED — proposed licence:** Allow enumerated inflections of relation-table entries, checked in the appropriate grammatical position. For example, “sisters” can identify the same relation as “sister” when it is the relational noun in the accepted construction.

**UNTESTED — provable property to target:** Every accepted inflection maps to one registered relation, and the grammatical construction—not mere word presence—binds its arguments. This avoids a licence firing simply because a name, title or unrelated phrase contains a relation word. Do not use unrestricted stemming that can erase distinctions such as step-, half- or -in-law.

### B. Coordination: expand only the relationship actually distributed

**UNTESTED — proposed licence:** For:

> Mira and Tal are my sisters.

the construction can produce exactly:

> me | sister | Mira  
> me | sister | Tal

provided the relation’s schema permits those multiple values.

**UNTESTED — provable property to target:** Each output member is an explicitly coordinated source span, and the expansion preserves the construction’s owner and relation. It must not produce a cross-product across several owners, relations and values.

**UNTESTED — boundary:** Do not generalize this to every “and.” Collective ownership and lists of several different relatives require their own semantics. “Mira and Tal are my parents,” for example, does not license guessing which person is mother or father. WE remains unresolved under the owner’s existing rule.

### C. Verb templates: bind arguments and preserve tense and scope

**UNTESTED — proposed licence:** A verb entry should specify a complete construction, its argument positions and the exact table relation it entails. For example:

> Oren works at Brightline.

may license Oren’s workplace as Brightline **if that is the registered meaning of the table relation**.

**UNTESTED — required scope check:** The same embedded words must not license that write in “Oren plans to work at Brightline,” “Does Oren work at Brightline,” or a reported claim that the project’s policy excludes. The licence must inspect the enclosing construction, not just match “work at.”

**UNTESTED — important correction:** “Ada moved to Tolby” does not, without further assumptions, establish that Ada **currently lives** there. A move-destination or suitably time-qualified relation might represent what was asserted; a current-residence relation may not. I do not know whether the supplied 153-entry inventory contains an appropriate relation. Do not substitute the nearest available label to increase coverage.

**UNTESTED — provable property to target:** An accepted construction maps its grammatical arguments to the registered relation without dropping an excluded modal, reporting or temporal qualification. The semantic correctness of that mapping must be reviewed when the licence is created.

### D. Appositives: attach the description to the right entity

**UNTESTED — proposed licence:** In:

> Mira, my sister, works at Brightline.

a supported appositive construction can establish the sister fact, while the main clause establishes the workplace fact.

**UNTESTED — provable property to target:** The appositive modifies the entity selected by the grammatical construction, not whichever name is closest to the relation word. Both facts must remain inside the accepted assertion scope, and both must be accounted for before committing the turn.

**UNTESTED — boundary:** A comma pattern alone is insufficient. Quotation, reporting, negation, alternative attachments and unsupported surrounding clauses can invalidate the proposed transaction.

### E. Earlier-context binding: reuse explicit evidence, not plausibility

**UNTESTED — proposed licence:** Permit context initially through **explicitly identified pending questions or clarifications**, not unrestricted conversational inference. For example, after the assistant asks “Whose dog is Pip?”, the answer “Ada’s” can fill the owner of that particular pending question. The relation and value come from recorded evidence; the new owner comes from the current reply.

**UNTESTED — required change to the contract:** This is no longer “all arguments come from the current turn.” It is “all arguments come from identified, unchanged source turns under a registered binding rule.” That expansion must be explicit and separately tested.

**UNTESTED — boundary for “Ada’s Pip”:** The bare possessive does not itself establish *dog*. If an earlier assertion already established that Ada’s dog is Pip, recognizing that reference is useful, but rewriting the same fact is not newly recovered knowledge. If the relation remains unknown, ask. Do not infer it merely because Pip resembles a pet’s name or matches one plausible notebook entry.

**UNTESTED — pronoun rule:** Initially allow only a narrow, formally identifiable binding, such as the slot in a pending clarification. “Most recent compatible person” and “highest-confidence antecedent” are not equivalent to an unambiguous binding.

### Two cross-cutting safeguards

**UNTESTED — typos:** Exact copying can prevent the model from inventing a spelling, but cannot distinguish an intended new name from an accidental spelling with identical text. Some boundary mistakes can be rejected by the grammar. Genuine spelling ambiguity needs clarification or explicit confirmation; silently normalizing the source trades one possible error for another. Count those first-turn holdbacks honestly.

**UNTESTED — questions and edits:** Absence of “?” must never be sufficient evidence of ASSERT. Some statement-shaped checks cannot be distinguished from assertions using the available text alone; those need either abstention or an explicitly acknowledged statistical risk. Also, DENY must not become a positive TEACH: it should trigger only a precisely supported retraction or other registered negative operation. CORRECT must change only the identified relation/value, not every related notebook entry.

## 4. Expected coverage: what can and cannot be estimated now

**SHOWN — available evidence:** The audit gives 59 no-cue misses, but no separate counts for plurals, verbs and context-dependent possessives. It also reports 12 missing-table relations, ten WE-owner misses, seven value typos and one other owner miss. Therefore, numerical gains for individual licence families are not identifiable from the supplied totals. 

**UNTESTED — forecast and measurement plan:**

| Licence family | Expected contribution | Honest numerical statement now |
|---|---|---|
| Morphology plus supported coordination | First priority: directly addresses a named mechanical failure. | Its share of the 59 no-cue misses is **unknown**. |
| Verb constructions | Second priority: recover explicit relations expressed verbally. | Its share is **unknown**; some “moved to” cases may remain unrepresentable. |
| Appositives | Recover correctly attached relationships and complete multi-fact transactions. | **Unknown**; the audit does not isolate this family. |
| Explicit context binding | Recover replies whose omitted material is supplied by a specific recorded interaction. | **Unknown** for bound replies; **zero new-fact credit** for merely restating an already-known relationship. |
| Bare context guesses, WE → ME, automatic spelling repair, nearest-relation substitution | Not permitted by this recommendation. | **Zero intended recovery through those shortcuts.** |

**UNTESTED — how to measure before training:** Give each gold fact a unique identifier and record **all** its blockers. For every complete source interpretation, record which licences it requires. Then report direct recoveries, overlap between families, and additional facts recovered because an entire transaction becomes writable. Do not attribute a companion fact’s recovery to a new lexical licence it never needed.

**UNTESTED — planning implication:** I expect morphology and verb constructions to improve coverage, but **I do not know whether they reach 85%**. Even reaching an 88% oracle ceiling would leave no room for reader misses under the stricter holdback interpretation. For illustration, a 90% ceiling combined with recovery of 95% of those licensed facts gives only **85.5% overall recall**.

## 5. The ONE experiment to run next

### Registered question and single change

**UNTESTED — proposed experiment:** **“Cue-v1: does source-structured plural/verb licensing meet the coverage requirement without admitting an unsupported transaction?”**

**UNTESTED — named base:** Use the exact strict-compiler-v0 implementation and oracle harness that produced 184/272, identified by their hashes—not the borrowed production ear-plus-Qwen pipeline. This experiment tests the proposed write policy’s feasibility, not the production system’s final reliability.

**UNTESTED — single treatment:** Replace only the relation-licensing component. Retain existing relation meanings, owner rules, value-copy restrictions, mode allowlist and atomic commit policy. The replacement adds enumerated plural forms and registered verb constructions, with source-structure and scope checks. Do **not** add context licences, appositive support, spelling repair, new relations or a learned fallback in this experiment.

### Fixed sample: 600 utterances in two predeclared parts

**UNTESTED — ordinary panel:** Use **300 fresh turns** from the original audit’s frozen writing specification, written by a new independent writer. Do not increase the frequency of licence-friendly plurals and verbs. This is the coverage panel.

**UNTESTED — challenge panel:** Add **300 independently checked challenge utterances**, exactly **50 in each** of six families: punctuation-free checks; plans/hypotheticals/temporal overclaims; reporting/quotation/negation; coordination and argument-direction errors; value-boundary errors and typos; ambiguous context/pronouns/group owners. This panel tests permission failures and is not mixed into the ordinary-panel recall denominator.

**UNTESTED — why this size:** The 300-turn ordinary panel preserves the scale of the existing audit while changing the writer. The additional 50 cases per hazard provide targeted opportunities to falsify the proposed licence properties. This is a **feasibility and counterexample experiment**, not a statistically powered certification of every family’s error rate. The supplied aggregates are insufficient to calculate a reliable power estimate for the paired, multi-fact comparison.

### Audit permission, not just the oracle’s favourite answer

**UNTESTED — evaluation procedure:** For both v0 and v1, enumerate the complete readings their supported grammar permits. Check whether the exact gold transaction can pass. Separately check whether **any permitted transaction contains an unsupported write**, including submissions with deliberately wrong proposed owners, relations or ASSERT labels.

**UNTESTED — essential distinction:** Do not let gold labels supply a hidden safety veto. In particular, submit ASSERT on the check-question challenges and see whether source verification rejects it. If enumeration is incomplete, report a bounded challenge test—not a proof about every permitted reading.

### Exact pass marks

**UNTESTED — preregister all conditions below as mandatory:**

| Criterion | PASS requirement |
|---|---|
| **Ordinary-panel oracle recall** | At least \(\lceil0.88N\rceil\) correct, complete-transaction facts, where \(N\) is the ordinary panel’s total gold true-fact count. |
| **Causal improvement** | At least **one more** ordinary-panel true fact writable than under v0. |
| **Unsupported permission** | **Zero** audited utterances, across all **600**, with an admitted transaction containing an unsupported write. |
| **Atomic completeness** | **Zero** admitted nonempty proper subsets of a turn’s required transaction. |
| **Protocol validity** | **Zero** post-run changes to code, thresholds, licence inventory or scoring policy used for the registered verdict. |

**UNTESTED — denominator rule:** Keep unresolved WE cases, unsupported relations and typo cases in the ordinary-panel denominator wherever the original gold policy counts them as true facts. Do not remove difficult cases to make the ceiling pass. If \(N=272\), the recall requirement is exactly **240**; if \(N=300\), it is exactly **264**.

**UNTESTED — label control:** Have a second agent independently check the keys before system outputs are revealed. Resolve disagreements before sealing. An unresolved key prevents PASS; a subsequently discovered key mistake should be documented without silently rewriting the registered verdict.

**UNTESTED — falsification:** One admitted unsupported transaction refutes the tested safety claim. Recall below 88% refutes the claim that **this licence expansion** satisfies the jointly interpreted coverage constraints—even with a perfect reader. Neither outcome refutes every possible compiler design, but neither licenses an unregistered rescue.

**UNTESTED — separate later step:** Only after a PASS, train or evaluate the own reader under the frozen licences and separately certify the actual selected writes. Measure end-to-end recall and latency then; an oracle permission audit cannot establish the 800 ms turn target or the deployed wrong-save rate.

## 6. Strongest objection, and why I still reject the rival for now

**UNTESTED — strongest objection:** This can become another hand-written English parser with more formal-looking paperwork. If the grammar must resolve every relevant meaning before a model can write, the model may contribute little to accepted cases. If the grammar leaves important ambiguities for the model to decide, the safety claim again depends on learned interpretation. Formal terminology does not remove that trade-off.

**UNTESTED — what would change my recommendation:** A selective own parser that achieves the required recall and independently measured wrong-save risk on fresh writers could be preferable to a grammar whose safe coverage repeatedly falls short. Your present gate’s failure does not prove that every selective parser will fail.

**SHOWN — project evidence for caution:** The current gate passed 13 of 103 wrong development frames and 63 of 65 wrong fresh-writer frames. That is direct evidence against treating its development-set threshold as dependable authorization on new wording. 

**SHOWN — relevant statistical distinction:** Risk-controlling prediction sets provide high-probability risk guarantees under stated assumptions, including independent, identically distributed calibration examples and appropriate loss conditions. Basic conformal risk control instead controls an expected loss averaged over calibration and test randomness. Neither statement automatically equals “fewer than 1% of saved notebook facts are wrong at 95% confidence.” *Bates et al., arXiv:2101.02703*, §2; *Angelopoulos et al., arXiv:2208.02814*, §1.1. 

**UNTESTED — reason for rejecting the rival now:** Before paying to train a selective parser, determine whether a small, inspectable set of source licences has adequate coverage. That is a cheaper architectural question to answer without new model downloads or GPU training. Rejecting unrestricted learned write authority now is a sequencing decision, not a claim that rules will ultimately win.

## Plain-language summary

**SHOWN:** Your current rules block about one-third of the true facts even when the reader is perfect. 

**UNTESTED:** I recommend rules that check how a whole sentence expresses a fact, rather than whether certain words appear somewhere. Plurals and clear verb phrases are the best first additions, but we do not yet know whether they recover enough facts. A phrase like “Ada’s Pip” should not become a new dog fact unless the conversation explicitly supplies that meaning. Copying text exactly cannot solve every typo, and a confident model cannot recover information the message never provided. The next test should check both whether correct facts can pass and whether deliberately wrong readings can pass. Any unsupported write should fail the experiment, while the stricter reading of your coverage targets requires at least 88% of true facts to remain writable. Only after that test passes should you train the reader and measure how reliably the complete system uses those permissions.

## Answer to question 3: Telling, checking, supposing or planning: speech acts without the question mark
(message cmsg_01FuvegZXjMmeUzStiEFVnEWTYqGg7TCENHegxkiz9PKg5, 2026-09-23T10:22:14Z)

**UNTESTED—recommendation:** Train a **per-fact write-permission detector**, not merely a turn-level “statement detector.” Its question should be: **“Is the user explicitly presenting this exact notebook fact as something to record, with the right source, time and polarity?”** Give it the previous assistant reply as context, train it on carefully paired examples, and let genuinely ambiguous cases trigger clarification.

**SHOWN—important constraint:** Your current recall is 77.9%, and the proposed strict compiler permits only 67.6% of real facts even with a perfect reader.  **UNTESTED—deduction:** An additional veto cannot recover facts those components already miss. The next experiment should therefore test a narrowly named **speech-act safety improvement**, not claim to achieve the complete safety-and-recall contract.

Here, **SHOWN** means reported in your measurements or demonstrated in the cited source; it does not mean I independently reran your experiments. **SUGGESTED** means published evidence transferred from another setting. **UNTESTED** marks my proposed design and deductions rather than measured Premonition performance.

## 1. Diagnosis: the problem is broader than speech-act classification

### A statement can contain a fact that must not be saved

**UNTESTED—analysis:** Several examples in your question are genuinely statements. The mistake is selecting the wrong proposition from them:

| User’s words | What the user presents as true | What must not be silently substituted |
|---|---|---|
| “Mira wants a cat named Fig.” | Mira has that desire. | Mira currently has Fig. |
| “Tal says Mira’s boss is Oren.” | Tal made that report. | The user independently confirms that Oren is Mira’s boss. |
| “Ada used to live in Rook.” | A past residence. | Ada currently lives in Rook. |
| “Ada doesn’t have a cat.” | A negative fact. | A positive cat-ownership fact. |
| “Suppose Ada doesn’t have a cat.” | A hypothetical assumption. | A current negative fact or permission to delete an existing fact. |

**UNTESTED—conclusion:** Making `PLAN`, `REPORTED` and `DENY` compete with `STATE` in a single classification loses information. A person can **state a plan**, **state a report**, or **hypothetically deny something**. These are different dimensions, not mutually exclusive alternatives.

**SUGGESTED:** The *CommitmentBank* research distinguishes speaker commitments from directly asserted content, including material embedded under questions and negation. That supports separating “something follows from this sentence” from “the user explicitly asserted this notebook entry.” I inspected its abstract only; I am not relying on its experimental results or claiming a verified arXiv identifier. 

### One turn label cannot safely control every fact

**UNTESTED—analysis:** In “Mira’s dog is Pip; is Oren’s dog Fig,” one candidate is asserted and the other is questioned. A single `STATE` label may admit both; a single `ASK` label may discard both. A multi-label turn summary helps describe the turn, but **write permission must attach to individual candidate facts and their enclosing clauses**.

**UNTESTED—analysis:** Likewise, `CORRECT` and `DENY` must not be unconditional write permissions. “Let’s pretend I was wrong about Mira’s dog” is not a real correction. A direct denial needs a supported negative-fact or invalidation operation; it must not become a malformed positive triple.

### The quoted accuracy figures are not an error floor

**SHOWN:** Stolcke et al., **arXiv:cs/0006023**, report 71% dialogue-act accuracy from transcripts, 84% inter-annotator agreement over their 42-label scheme, and 85.9% words-only accuracy on a balanced question-versus-statement subtask. Their discussion explicitly notes that a *following* yes/no answer can resolve a declarative question. I checked the relevant full-text sections and table. 

**UNTESTED—interpretation:** None of those numbers establishes a 14.1%, 16%, or 29% unavoidable error rate for Premonition. They concern different labels, data and models. Conversely, an offline system that sees the next reply has information your live write decision does not yet have.

**UNTESTED—analysis:** “So Mira’s dog is Pip” is not intrinsically a check-question in every context. It can be a conclusion, a confirmation request, or an assertion. A writer’s private intention does not make that intention recoverable from the visible text.

### Underrepresentation is plausible, but not yet a demonstrated cause

**SHOWN:** Your proposed training data gives `SUPPOSE` and `PLAN` only 1.4% each. Your gate’s scores also change substantially with prompt wording, and its development-set performance did not carry over to fresh wording.  

**UNTESTED—interpretation:** More examples of these modes are warranted, but their frequency alone does not explain the failures. More repetitions of the same cues could teach a better keyword detector rather than better scope understanding. Nor should `P(YES)` be treated as a calibrated probability of safe writing merely because it is a token probability.

**UNTESTED—specification issue:** Clarify the relationship between your recall and withholding targets. If “held back” includes **every true fact not saved**, a 12% maximum means recall must be at least **88%**, not 85%. If it means intentional refusals only, distinguish those from extraction omissions. Do not combine or interchange those denominators.

## 2. Ranked options

The rankings and projected trade-offs below are **UNTESTED**.

| Rank | Option | What it fixes | Cost and limitation |
|---|---|---|---|
| **1** | **Fact-scoped detector with previous-turn context and selective clarification** | Separates asserted facts from nearby questions, assumptions, reports and plans; can preserve clear statements while withholding uncertain ones. | Requires new labeled data and a small trained component. Cannot recover invisible intent or facts the ear omitted. |
| **2** | **Explicit confirmation of the exact proposed write** | Obtains new evidence of the user’s intent instead of guessing it. A dedicated confirmation action can make authorization unambiguous. | Adds interaction. Requiring it for every fact conflicts with low withholding and effortless chat. Confirmation must expose the exact fact; otherwise extraction mistakes remain. |
| **3** | **A narrow, clause-scoped rule brake** | Quickly handles constructions whose scope is explicit, such as a particular “let’s suppose…” clause. | Cheap and inspectable, but brittle on new wording and nested clauses. Blanket bans on `so`, `not`, or `wants` sacrifice valid statements. |
| **4** | **Another prompt or threshold for the large gate** | Might improve specific known constructions. | Does not directly address missing context or the label mismatch. It also retains the borrowed component and another prompt-selection burden. |

**SHOWN—reason for ranking option 4 last:** Your existing gate let 63 of 65 wrong frames through on the fresh-writer test, while the three-question alternative failed withholding and latency requirements. That is evidence against relying on another prompt adjustment as the main solution—not proof that every large-model verifier must fail. 

## 3. Recommended labels, context and training data

### Label the candidate proposition, its context, and the permitted operation

**UNTESTED—design:** Keep the nine-way turn head only as an auxiliary training signal or diagnostic. For each candidate fact, predict the following separately:

| Field | Suggested distinctions |
|---|---|
| **Communicative function** | Inform, answer, correct, ask/check, acknowledge, unclear |
| **Commitment and source** | Explicit user assertion, hypothetical, desired/planned, attributed report/quotation, uncertain |
| **Time** | Current/timeless, past, future, unclear |
| **Polarity** | Positive, negative, unclear |
| **Write decision** | Permit this existing operation, no write, clarify |

**UNTESTED—design:** Also label the words governing the candidate: “wants,” “used to,” “Tal says,” “suppose,” and so forth. This provides a training target for **scope**—which part of the sentence an operator applies to. It is not a runtime proof that the interpretation is correct.

**UNTESTED—design:** The final write decision should be learned directly as well as supervised through these explanatory labels. Do not manufacture a confidence guarantee by multiplying several head probabilities or treating agreement between them as independent evidence.

**UNTESTED—design:** For the current notebook, authorize only operations its schema actually supports. An asserted desire, report or past fact is not necessarily representable as a current positive relation. Hold it rather than change its meaning. But **count that as a missed fact whenever the recall contract includes that kind of fact**; do not improve recall by relabeling unsupported information as “not a fact.”

**UNTESTED—design:** Transaction atomicity and speech-act labels are separate questions. In a mixed statement/question turn, the question is not an additional fact that must be committed. Your compiler can still require all intended factual writes to succeed together without treating the question as one of those writes.

### Use the previous assistant reply—but not as independent factual evidence

**SUGGESTED:** Bothe et al., **arXiv:1805.06280**, found that preceding utterances improve dialogue-act recognition. Their approach explicitly avoids the future-utterance information available to some offline models. This supports testing short preceding context here; it does not establish the benefit for your data or notebook policy. I inspected the relevant full text. 

**UNTESTED—design:** Give the detector the unchanged user turn, the candidate triple, the previous assistant reply and explicit speaker-role separators. When available, include a structured description of the assistant’s preceding action, such as “asked for a fact” or “requested clarification.”

**UNTESTED—safety boundary:** Context may help interpret the user’s action, but the assistant’s own words must not supply evidence for a new fact. An earlier assistant claim followed by “right” must not automatically become a user-taught notebook entry.

**UNTESTED—experiment boundary:** Do not add cross-turn reconstruction of facts from “yes” in this experiment. That would change the ear/compiler contract as well as the detector. Require a complete restatement for now; evaluate shorthand confirmations separately later.

### Generate contrast families, not just more negative sentences

**SUGGESTED:** Counterfactually augmented data—examples minimally edited to change the correct label—improved robustness in sentiment and natural-language-inference experiments in Kaushik et al., **arXiv:1909.12434**. *CheckList*, **arXiv:2005.04118**, supplies a complementary approach: test both changes that should alter a prediction and changes that should leave it alone. Neither result establishes a safety guarantee for synthetic speech-act training. 

**UNTESTED—training design:** Each family should contain an assertion, a permission-changing edit, and a misleading-cue control. For example:

> “Mira has a cat named Fig.”  
> “Mira **wants** a cat named Fig.”  
> “Mira wants a holiday. **She has a cat named Fig.**”

The second must not authorize ownership. The third must not lose the ownership fact merely because `wants` appears elsewhere.

**UNTESTED—training design:** Add context-only contrasts: the same user wording after different assistant replies. Include both cases where the prior reply genuinely resolves the interpretation and cases where it still leaves ambiguity. Never force an assertion/check distinction merely because the generator was instructed to intend one.

**UNTESTED—training design:** Cross these families with lowercase typing, omitted apostrophes, punctuation changes, reordered clauses, fictional names, corrections and mixed turns. Preserve the unchanged turn as the evidence source; noisy examples are not permission to “repair” names or values.

**UNTESTED—starting allocation:** For this first component, use **24,000 synthetic training turns**: 8,000 clear factual assertions, 8,000 cases that must not authorize the candidate, 4,000 mixed turns and 4,000 ambiguous cases. These are proposed training proportions, **not estimates of ordinary chat**. Use a separate 4,000-turn development set.

**UNTESTED—split rule:** Keep every contrast family together. Separate training, development and test by construction families and writer instructions—not merely by fictional names. Include fresh independently authored wording in test.

**SUGGESTED—important caution:** *PairCFR*, **arXiv:2406.06633**, discusses how counterfactual training can overemphasize edited features while neglecting unchanged context. That is exactly the danger of learning “`wants` means reject.” Its proposed remedy was studied elsewhere; I would first address this risk through the controls above rather than add another training technique to this experiment. 

### Clarification should ask about the user’s action

**UNTESTED—fallback:** Use a template such as:

> “Are you telling me that Mira’s dog is Pip, or asking whether that is true? I haven’t saved this as a fact.”

**UNTESTED—design:** Avoid “Is that right, or are you asking?” because a reply of “yes” is itself ambiguous. In this first implementation, request a complete factual restatement before saving. Clearly recognized questions should follow the question path rather than generate unnecessary clarification.

**UNTESTED—accounting:** A clarification is not a successful immediate save. Report immediate recall, eventual recall after clarification and the number of extra exchanges separately. On mixed turns, the response must accurately distinguish what was saved from what remains unresolved.

## 4. The one experiment to run next

### Experiment: `SCOPED-ACT-VETO-01`

**UNTESTED—single intervention:** Add **one frozen, from-scratch candidate-level permission detector** immediately before notebook commit. A four-layer, width-256 encoder is a reasonable starting specification, not a measured optimum. It may veto an existing candidate or request clarification; it may not create, repair or rewrite a fact.

**UNTESTED—frozen base:** Keep ear v4.1, the canonicalizer, rule brake, Qwen prompt and 0.25 threshold, notebook operations and question-answering behavior unchanged. The existing borrowed models remain placeholders. This experiment requires no new model download.

**UNTESTED—hypothesis:** This component can eliminate speech-act-based admissions while retaining at least 97% of clearly eligible candidate facts, with acceptable latency. That is deliberately narrower than “Premonition meets all hard targets.”

### Training and threshold selection

**UNTESTED—registration:** Use the training and development allocations above. Register the training recipe before training; then hash the resulting weights, decision threshold, templates and evaluation code before the blind run.

**UNTESTED—threshold rule:** On development data only, search the fixed grid \(0,0.01,\ldots,1.00\). Choose the lowest threshold producing zero unsafe admissions and retaining at least 98.75% of clear eligible candidates. If no threshold qualifies, record development failure rather than spending the blind panel. Do not interpret the selected score as a calibrated probability.

### Blind panel: 900 scored user turns

**UNTESTED—sampling plan:** Create **400 independently generated scenario families**, each containing one clear asserted candidate and one closely related candidate that must not be authorized. That produces 800 turns.

For each family, independently draw its negative construction from a frozen equal-weight mixture of punctuation-free checking, supposing/pretending, desire/planning, reporting/quotation, and temporal/negative-scope errors. Questions must be clear from the visible wording and context; genuinely unresolved cases belong in the ambiguity panel.

Add **50 mixed turns**, each with one eligible and one ineligible candidate, and **50 genuinely ambiguous turns**. Total: **900 turns**.

**UNTESTED—two measurement views:** Run the unchanged base and the variant on identical isolated notebook snapshots. Also evaluate the detector directly on the panel’s designated candidate records, including candidates the ear failed to produce. This prevents a missing ear output from masquerading as successful speech-act detection. Direct candidate tests are diagnostics, not a new deployment input path.

### Exact pass marks

All criteria below are **UNTESTED—proposed preregistered requirements**.

| Requirement | Pass mark |
|---|---|
| Unsafe designated-candidate admissions | **0/400** |
| Clear eligible designated candidates admitted | **At least 395/400** |
| Mixed-turn behavior | **0/50** unsafe candidates admitted; **at least 48/50** eligible candidates admitted |
| Ambiguity behavior | **50/50** produce no write and a clarification |
| Demonstrated pipeline benefit | Eliminate **at least 10** base speech-act wrong writes; introduce **zero** speech-act wrong writes across the panel |
| Preservation of existing successes | Lose **no more than 5** correct base saves among the 400 clear-assertion turns |
| Latency | Median complete-turn time **≤800 ms** and median added detector time **≤50 ms** |

**UNTESTED—timing protocol:** Measure batch-one, model-resident execution on the named machine after 20 fixed development warm-up turns, alternating arm order. Include the new detector’s actual work. Exclude human response time from machine latency, but report clarification exchanges separately.

### Why 400 per primary endpoint?

**SHOWN—statistical method:** Exact binomial limits are appropriate for fixed-sample binary outcomes with very few failures. Their validity depends on the sampling model, not just applying the formula. NIST describes the exact binomial construction. 

**UNTESTED—design, with calculated bounds:** Allocate 2.5% confidence error to each of the two primary endpoints. With zero unsafe admissions in 400 independent cases, the one-sided upper limit is

\[
q_U=1-0.025^{1/400}=0.0091798,
\]

or **0.918%**.

At **395 admissions out of 400** eligible cases, the corresponding one-sided exact lower limit is approximately **97.107%**. Together, the two bounds have at least 95% simultaneous coverage under the stated sampling and labeling assumptions. The minimum zero-error safety sample for this 2.5% tail allocation is 368; 400 provides a small margin.

**UNTESTED—dependence boundary:** Members of a pair are related. Use 400 independent families per endpoint—not “800 independent safety examples.” The bounds describe the registered synthetic challenge distribution, not every individual construction family and not automatically ordinary chat.

**UNTESTED—power warning:** A true unsafe-admission rate of 0.5% gives only

\[
0.995^{400}\approx13.5\%
\]

probability of observing zero failures. Your zero-observed-error bar is demanding. One failure means **this experiment does not certify the proposed claim**; it does not prove the underlying rate exceeds 1%.

### Gold labels and falsification

**SHOWN:** Six apparent errors on your previous fresh panel were answer-key mistakes. Label validity is therefore a demonstrated measurement problem, not a hypothetical concern. 

**UNTESTED—grading protocol:** Before exposing system outputs, two independent graders should inspect the visible conversation, mark permissible notebook operations and identify ambiguity. Resolve disagreements before sealing. A generator’s hidden intention cannot override ambiguous text. Any unresolved label dispute that could change the verdict prevents a clean PASS; do not delete failed items after seeing results.

**UNTESTED—falsification criterion:** Any missed pass mark falsifies this **specific proposed operating point**. Particularly informative failures are unsafe admissions on unseen constructions, rejection of valid facts because a dangerous word occurs elsewhere, or passing only when context makes the answer trivial.

**UNTESTED—interpretation boundary:** Even a component PASS leaves the overall assistant unqualified if extraction errors, unsupported schema cases or total recall still fail. Report all wrong saves, not only the error category this component targets.

**UNTESTED—separate later step:** Only after this result, evaluate exact-fact confirmation and shorthand replies as a separate intervention. A failed run gets the one diagnosis-driven follow-up your protocol allows—not a threshold rescue on the burned panel.

## 5. Realistic error floor and rare-event measurement

### The floor is unknown, but the trade-off can be measured

**UNTESTED—deduction:** If identical visible histories can accompany both “I am telling you this” and “I am checking this,” a system cannot always distinguish them without additional information. More synthetic examples cannot reveal information absent from the input. Clarification can obtain it.

**UNTESTED—answer:** **I do not know Premonition’s attainable error floor.** The cited research does not establish one for your chat distribution. Measure a curve showing unsafe admissions against eligible facts retained as the threshold changes, and separately measure how often visible language remains genuinely ambiguous.

**SUGGESTED:** This risk-versus-coverage framing is established in selective-classification research, including Geifman and El-Yaniv, **arXiv:1705.08500**. *Learn then Test*, **arXiv:2110.01052**, supplies finite-sample risk-control methods under specified sampling assumptions. Neither makes arbitrary distribution shift or incorrect gold labels disappear. 

**UNTESTED—deduction:** If more than 12% of true facts require clarification, the immediate withholding target already fails before other mistakes are considered. Whether that happens is an empirical question—not something the 2000 telephone-speech results answer.

### Keep three denominators separate

**UNTESTED—measurement definitions:** Report **unsafe admission per ineligible candidate**, **turns containing any wrong save per tested turn**, and **wrong saved facts per saved fact** separately. None can substitute for another. In particular, 400 negative candidate tests do not establish the error rate among all saved notebook facts.

**UNTESTED—calculation:** In a random 150-turn panel, a 5–10% prevalence produces only about 8–15 relevant turns on average. Even with zero errors, ordinary one-sided 95% upper limits at those realized sample sizes are about **31%** and **18%**. That is nowhere near precise enough for a 1% conditional claim.

**UNTESTED—measurement recommendation:** Deliberately oversample the rare constructions for the component test. Obtaining 400 such turns by natural sampling would require roughly 4,000–8,000 turns *on average* at the assumed prevalence. Separately estimate their frequency and wording mix from representative intended-use interactions. Without that representative evidence, publish the challenge-distribution result without a deployment certificate.

**UNTESTED—illustration:** If the relevant deployment prevalence were at most 10%, and the challenge conditional rate genuinely transferred, a 0.918% conditional error bound would contribute at most **0.0918 percentage points** to the all-turn error rate. That still leaves extraction mistakes, other constructions and mixed-turn failures. The assumed 5–10% prevalence is not itself a measured guarantee.

**UNTESTED—certification boundary:** All-AI authoring and grading can produce useful evidence, but shared semantic mistakes remain possible. More panel items reduce sampling uncertainty; they do not establish that the labeling policy is correct. Repeatedly trying new versions until one passes also requires a project-level testing policy beyond this one frozen experiment.

## 6. Strongest objection—and the rival I rejected

**UNTESTED—strongest objection:** This could become **another learned gate that succeeds on its generator’s habits and fails on fresh language**. Richer labels and cue spans make failures easier to diagnose, but do not guarantee generalization. Your present gate’s fresh-writer collapse is a direct reason to take that objection seriously. 

**UNTESTED—why recommend it anyway:** The proposal tests a different, narrower target: permission for an exact operation, with preceding context and explicit scope supervision. Its stringent retention test prevents “reject everything” from looking successful. Its paired controls test whether it learned scope rather than keywords.

**UNTESTED—strongest rival:** Require explicit confirmation of every exact write. That is stronger for obtaining authorization than guessing intent from ambiguous prose. I reject it as the default because it changes the interaction contract and makes immediate withholding expensive. I retain it as the fallback where the sentence does not provide enough evidence.

## Plain-language summary

**UNTESTED—recommended plan:** Teach the model to decide whether the user is offering a particular fact to save, not just whether the sentence looks like a statement. Give each candidate fact its own labels so a question cannot accidentally authorize a nearby claim. Show the model the previous assistant reply, but never treat the assistant’s own words as evidence for a new fact. Train with nearly identical examples where one cue changes permission, plus examples where that same cue should not matter. When the visible conversation remains ambiguous, ask what the user intended and save nothing uncertain. Test the new detector on 400 independent unsafe candidates and 400 clear eligible candidates, with additional mixed and ambiguous turns. Passing would support a narrow result on that test distribution, not prove that every kind of notebook write is safe in ordinary chat. Improve extraction separately, because a safer filter cannot recover facts the ear never found.

## Answer to question 4: Training a small own ear on synthetic data that works on real chat
(message cmsg_01FuvegZXjMmeUzStiEFVnEWEVke4rgm6Jbfz1pJHCgx85, 2026-09-23T10:22:19Z)

## Recommendation

**UNTESTED:** Keep the **33M ear as the first serious candidate**, but do not yet assume it can meet the error target. First test whether replacing template-dominated training examples with **independently written, contrastive chat examples** improves the existing ear. That separates “our training distribution is wrong” from “our new model is too small.”

**UNTESTED:** The central change should be **how examples are created and checked**, not simply more examples, more paraphrases, or a stronger model grading its own output.

Throughout this answer, **SHOWN** means a reported measurement or published result; **SUGGESTED** means published evidence supports the approach in a different setting; **UNTESTED** means my proposed design, inference, or conditional budget estimate.

## 1. Diagnosis: what is actually going wrong

### Exact spans are necessary, but they do not establish meaning

**SHOWN:** Your generator has 200,000 rows and 571,795 exact, whole-word spans, but its difficulty levels share surface patterns, and SUPPOSE and PLAN each represent only 1.4% of rows. The borrowed ear produced 30 wrong frames on the separate evaluation containing 125 fresh facts. Those measurements establish a substantial problem, but they do not isolate model capacity from training-data coverage or labeling errors. 

**UNTESTED:** Your most important missing distinction is between **copying the right words** and **recognizing what the speaker asserted**. Every word in a wrong frame can appear in the input. A model must still distinguish a statement from a check-question, identify which person owns which relation, separate actual facts from imagined ones, and extract several facts without mixing their arguments.

**SUGGESTED:** This resembles the shortcut problem demonstrated by **HANS, arXiv:1902.01007**: strong language-inference models performed poorly when familiar words and sentence structures no longer supported their usual shortcuts. That supports testing semantic contrasts, not merely lexical variety. My use of this paper here is limited to its abstract-level findings. 

### UniversalNER is encouraging—but its result does not establish your size target

**SHOWN:** **UniversalNER, arXiv:2308.03279**, used pretrained **7B and 13B LLaMA-based models**, not a 33M model trained from scratch. Crucially, its principal distillation inputs were passages sampled from the **Pile**, with ChatGPT supplying annotations; the teacher did not generate all the source passages. The reported 7–9-point improvement was average NER F1, not near-zero assertion-extraction errors. 

**SUGGESTED:** The transferable lesson is: **focused distillation over diverse inputs can outperform the teacher on a specialized task**. The paper does not establish that synthetic-only chat, a tiny random-initialized student, and your safety target will work together.

### “Looks like real chat” is not a measured deployment distribution

**UNTESTED:** Several agents can produce varied-looking sentences while sharing the same assumptions about what people say. Different prompts to the same model are different generation procedures, not independent language populations. Even different model families can share blind spots.

**UNTESTED:** Consequently, synthetic-only evidence should initially support the claim **“generalizes to withheld synthetic authoring processes”**, not “works reliably on real users.” A later owner-written, fictional-fact evaluation can test that remaining gap without using personal facts.

### Some failures are outside the ear’s learning problem

**SHOWN:** Your perfect-reader audit found that the planned compiler could write only **184/272 facts, or 67.6%**. 

**UNTESTED:** On that audited set, improving the ear cannot make the unchanged compiler reach 85% recall. Keep **ear extraction recall** and **eventual notebook-write recall** separate. Otherwise, an excellent reader could fail because of the compiler—or an unsafe reader could look good because the compiler concealed its mistakes.

**UNTESTED:** Likewise, a misspelled name creates a specification problem, not always a learning problem. From “Mria is my sister,” the system cannot generally establish that the intended name was “Mira.” Training it to repair every such example would conflict with the unchanged-input pointer requirement.

## 2. Three ranked options

**UNTESTED — proposed choices and trade-offs:**

| Rank | Option | What it fixes | Cost | What it cannot establish |
|---|---|---|---|---|
| **1** | **Diverse, independently checked, contrastive training data** | Wording shortcuts, missing assertion distinctions, ownership swaps, multi-fact extraction | New authoring and annotation pipeline; matched training comparison | Real-user reliability or sufficient 33M capacity |
| **2** | **Own encoder pretraining that includes substantial dialogue and task-like text** | Weak language representations before extraction training | A from-scratch pretraining run; estimate below | Correct notebook semantics from language modeling alone |
| **3** | **Increase the own ear to roughly 65–100M, only after diagnosing underfitting** | Insufficient capacity to learn even well-covered, verified examples | Roughly 2–3× parameter-dependent compute at equal token count | Missing coverage, ambiguous gold labels, or compiler restrictions |

**UNTESTED:** I would not make “train a larger own model on the same generator” the first move. Size becomes a stronger explanation when the 33M model cannot learn **verified, well-covered training cases and similar held-out cases**, rather than failing mainly on a new writer.

## 3. The generator-plus-distillation pipeline

### A. Generate a conversation first; establish its labels afterward

**UNTESTED — proposed procedure:** Give an author a fictional situation, a conversational purpose, and constraints on what should be mentioned. Do not always give it the final `TEACH | owner | relation | value` row to translate.

For example, the situation can include several people and relationships, while the conversational purpose is “correct one misunderstanding, ask about another relationship, and mention one actual fact.” The author must decide how to express that purpose naturally.

**UNTESTED:** The final text—not the situation sheet—is authoritative for labeling. A fact can be true in the fictional situation without being asserted in the message. Conversely, an author might accidentally add an assertion. Both cases must be caught before the example enters supervised training.

### B. Use a concrete starting mixture

**UNTESTED — initial sampling weights, not a published optimum:**

| Training share | Source | Purpose |
|---|---|---|
| **20%** | Existing exact templates | Reliable basic coverage of relations, directions, and pointers |
| **50%** | Scenario-first chat from varied authoring procedures | Natural variation in how facts appear inside conversation |
| **20%** | Independently checked minimal contrasts | Make small meaning changes require the right output changes |
| **10%** | Adversarial examples against a frozen development reader | Find confident mistakes the other sources miss |

**UNTESTED:** Start with **20,000 examples**, not a complete regeneration of 200,000. These proportions would mean 4,000 template examples, 10,000 scenario-first examples, 4,000 contrast examples, and 2,000 adversarial examples.

**UNTESTED:** Within that mixture, give PLAN and SUPPOSE at least **5% of rows each** initially, including varied ways to express them. This is a training emphasis, not an estimate of their real-world frequency. Include ordinary positive statements throughout; a dataset dominated by traps could reward excessive refusal.

### C. Build contrasts that remove the useful shortcut

**UNTESTED — illustrative training cases, not material from your panels:**

| Message | Required teaching behavior |
|---|---|
| “Mira is my sister.” | Extract the sister fact |
| “is Mira my sister” | Extract no teaching fact |
| “Suppose Mira is my sister.” | Extract no actual-world teaching fact |
| “Mira is my sister. Is Pip her dog” | Extract the sister fact, not the dog fact |

**UNTESTED:** Construct both kinds of transformations:

**Meaning-preserving changes** should preserve the answer: reorder clauses, replace fictional names consistently, remove ordinary punctuation, or express the same relationship through a different construction.

**Meaning-changing changes** must change the answer: swap owners, replace “studies” with “teaches,” change an assertion into a question, or move one clause under hypothetical scope.

**SUGGESTED:** This follows the distinction between invariance and directional tests in **CheckList, arXiv:2005.04118**. That paper supports testing relationships between predictions under controlled changes; your exact transformations and training mixture remain untested. 

**UNTESTED:** Do not apply “label-preserving noise” blindly. Removing an apostrophe may preserve an intended reading; altering a name may not. Reannotate every potentially meaning-changing transformation.

### D. Distill annotations, not the teacher’s confidence

**UNTESTED — proposed annotation process:** Use an author and two separate annotation passes. Each annotator sees the finished message and the fixed notebook policy, but not the author’s intended frames or the other annotator’s answer.

Each annotation should include the complete set of asserted facts, exact supporting spans, relation direction, and any hypothetical, planned, questioned, or ambiguous status. Require whole-message annotation rather than asking only whether a supplied candidate looks plausible.

**SHOWN:** Your existing YES/NO gate let **63 of 65 wrong frames** through on the fresh-writer evaluation. Its confidence is therefore not an adequate gold-label mechanism for this pipeline. 

**UNTESTED:** Resolve annotation disagreements before admission. A genuinely ambiguous message can receive a clarification target. An unresolved disagreement about an otherwise clear message should be quarantined—not automatically converted into `NONE`, which would teach the reader to avoid hard examples.

**UNTESTED:** Use already available models or agents. Different available model families are preferable for cross-checking, but two sessions of the same model must not be described as statistically independent graders. Do not download another model without approval.

### E. Measure diversity where shortcuts actually occur

**SHOWN:** **SimpleStories, arXiv:2504.09184**, explicitly investigated repeated phrasing and measured greater 4-gram diversity than TinyStories. That is useful evidence that generation procedures can change surface diversity; it is not evidence that a notebook reader will become reliable. 

**UNTESTED — proposed diversity dashboard:** Track four things:

1. **Delexicalized pattern frequency:** replace names and values with placeholders, then measure repeated phrases and sentence shapes. Changing “Mira” to “Lena” should not count as a new construction.
2. **Joint coverage:** cross speech act, ownership structure, clause arrangement, fact count, relation family, and typing style. Marginal coverage alone is insufficient.
3. **Contrast-pair correctness:** require both members to be correct. Giving the same wrong answer twice is not successful invariance.
4. **Performance by authoring process:** report the worst process alongside the average.

**UNTESTED:** For a compact repetition measure, let \(p_j\) be the fraction of examples using pattern \(j\), and report

\[
N_{\mathrm{effective\ patterns}}=\frac{1}{\sum_j p_j^2}.
\]

This helps reveal a large corpus dominated by a small number of patterns. It does **not** certify semantic diversity.

**SUGGESTED:** Adversarial collection has supporting evidence from **Adversarial NLI, arXiv:1910.14599**, which used human writers interacting with models to find difficult examples. Replacing those humans with your available authoring agents is an extrapolation. 

**UNTESTED:** Keep adversarial development separate from evaluation. Adversarial training writers may query a frozen development reader. Final-panel writers must not select examples by inspecting the candidate’s outputs.

### F. Keep the reader’s limits visible in the data

**UNTESTED:** Include mixed messages containing both teaching and non-teaching clauses. The global speech-act head must not become a shortcut that treats every clause alike; the per-fact mode labels need meaningful supervision.

**UNTESTED:** Preserve your “our/we requires clarification” policy. For the own ear, distinguish previous-assistant context from current-user evidence. Also measure how often the 128-token window or six-fact limit excludes a valid task. Do not silently truncate a message and count the remaining portion as complete extraction.

## 4. Pretraining and curriculum

### Do stories help?

**SHOWN:** **TinyStories, arXiv:2305.07759**, demonstrated coherent story generation with very small language models. Your talker’s 67.4% result is a separate, measured grammar result. Neither directly measures assertion extraction or safe ownership binding.  

**SHOWN:** The **TinyDialogues study, arXiv:2408.03617**, trained GPT-2 and RoBERTa models from scratch. Synthetic dialogue was useful for the RoBERTa model’s syntax evaluation, but performance depended on the dataset and evaluation; syntax and semantic results did not move uniformly together. 

**SUGGESTED:** **Don’t Stop Pretraining, arXiv:2004.10964**, supports adapting language representations to domain- and task-relevant text. Its experiments used an already pretrained RoBERTa and classification tasks, so it does not establish the benefit for your random-initialized 33M extractor. 

**UNTESTED:** My starting budget would be **400M input-token presentations**: 300M from a roughly equal story/dialogue mixture, followed by 100M emphasizing task-like conversations. These are processed tokens, not necessarily 400M unique tokens. Record unique text separately so repeated exposure is not mistaken for new diversity.

**UNTESTED:** Train the tokenizer only on training material. Do not include reserved evaluation text in masking pretraining: using its wording without its labels would still undermine the intended fresh-wording test.

### Curriculum

**UNTESTED:** Begin supervised training with shorter messages and fewer facts, but include statements, questions, plans, hypotheticals, and clarification cases from the start. Reach the full supported fact-count and construction range within the first **20% of training steps**. Continue mixing easy examples with difficult ones instead of finishing on adversarial examples alone.

**SHOWN:** The TinyDialogues study did not find a strong general benefit from its global developmental ordering for GPT-2; some RoBERTa ordering experiments also had convergence problems. “Easy to hard” should therefore be treated as a training hypothesis, not a brain-inspired guarantee. 

## 5. Which held-out split predicts fresh wording?

**UNTESTED:** **I do not know which split predicts your blind panels. No supplied measurement establishes that relationship.** Before training any own reader, a generator audit can expose missing coverage and label problems, but it cannot provide an honest numerical forecast of that reader’s accuracy.

**SUGGESTED:** The strongest relevant warning comes from **CFQ, arXiv:1912.09713**. Its tested architectures exceeded 95% on random splits but averaged below 20% on splits withholding combinations of familiar components. Randomly withholding rows can therefore greatly overstate compositional generalization in that setting. 

**UNTESTED — proposed split hierarchy:**

| Split | What it is useful for |
|---|---|
| Random rows, with duplicates removed | Basic implementation checks—not the main generalization claim |
| Entire scenario and paraphrase families withheld | Detecting memorization of a source example or its descendants |
| Constructions withheld in combination, while their components remain familiar | Testing whether familiar pieces can be recombined |
| **Authoring-process × construction-combination holdout** | My preferred candidate for estimating fresh synthetic wording |

**UNTESTED:** Put every descendant of a scenario—including contrasts, spelling variants, paraphrases, and reannotations—in the same split. Keep each relation class represented in training; withholding an entire relation class would mix wording generalization with learning an unseen output category.

**UNTESTED:** Reserve some authoring procedures for development and different ones for final testing. A generator family ceases to be a genuinely withheld family once repeated development feedback has shaped training around it.

**UNTESTED:** Maintain separate **ordinary-chat** and **adversarial-stress** evaluations. An adversarial failure rate measures vulnerability under that challenge process, not the frequency of errors in ordinary conversation. Neither should be silently substituted for the other.

## 6. Smallest plausible model and one-GPU compute

### Model size

**UNTESTED:** **33M is the smallest configuration I would currently back as a serious candidate—not a demonstrated minimum and not a promised success.** I do not know a published result showing that a from-scratch model of this size meets your combination of fresh wording, raw-frame safety, and recall.

**UNTESTED — parameter arithmetic:** Assuming a standard feed-forward width of \(4d\), your backbone is approximately

\[
8192(512)+8(12)(512^2)
=29.36\text{ million parameters}.
\]

Adding 3.5M heads gives about **32.86M**, before small normalization, bias, and positional terms. That is consistent with “about 33M.”

### Student training

**UNTESTED — conditional budget:** With 400M pretraining tokens and five passes over 200,000 supervised examples averaging 96 input tokens:

\[
D=400\text{M}+5(200{,}000)(96)=496\text{M tokens}.
\]

**SUGGESTED:** The common \(6ND\) training-compute approximation comes from transformer language-model accounting, including **Scaling Laws for Neural Language Models, arXiv:2001.08361**. Applying it to your encoder and heads is an approximation, particularly because masking and embedding/output computation differ. 

**UNTESTED — arithmetic:**

\[
6(33\times10^6)(496\times10^6)
\approx 9.82\times10^{16}\ \text{FLOPs}.
\]

At an **assumed**, not measured, 15,000–40,000 processed input tokens/second, this is approximately **3.4–9.2 GPU-hours**, excluding evaluation and data generation.

**SHOWN:** Your measured decoder throughput was about 49,000 tokens/second. 

**UNTESTED:** That is a useful local reference, but it is not a benchmark of this encoder, masking implementation, batch size, or extraction heads. Benchmark the actual training loop before treating the estimate as a schedule.

**UNTESTED — memory arithmetic:** At roughly 16–18 bytes per parameter for mixed-precision weights, gradients, master weights where used, and Adam states, 33M parameters require approximately **0.53–0.59 GB before activations and temporary buffers**. A 16 GB GPU appears adequate with moderate microbatches and 128-token inputs, but peak memory must be measured. Unload the large teacher before training.

### Teacher generation can cost more than training

**UNTESTED — illustrative budget:** Suppose authoring, annotation, and rejected attempts consume **600 decoded tokens per accepted example**. For 20,000 accepted examples:

\[
20{,}000(600)=12\text{M decoded tokens}.
\]

At an assumed 50 decoded tokens/second, that is **66.7 hours of generation**, before additional prompt-processing overhead. I do not know your teacher’s actual throughput or rejection rate.

**UNTESTED:** This is why I recommend a 20,000-example pilot rather than immediately regenerating the whole corpus. Use compact annotations and already available authoring resources, and keep the $30 cloud budget uncommitted until actual throughput is known. None of these estimates establishes the 800 ms end-to-end latency target.

## 7. The ONE experiment to run next

### Experiment: matched-data replacement on ear v4.1

**UNTESTED — preregistered design:** Use the **existing ear v4.1 checkpoint** as the common initializer. This is deliberately a data experiment on the placeholder, not a claim that the final model may borrow its weights.

Create 20,000 semantic case specifications and two training versions:

| Control | Treatment |
|---|---|
| Existing template-based realization | Proposed 20/50/20/10 realization mixture |
| Same underlying supported facts and non-assertion statuses | Same underlying supported facts and non-assertion statuses |
| Same relation, speech-act, and fact-count distribution | Same distribution |
| Same input/output interface and training budget | Same interface and budget |

**UNTESTED:** Reannotate each realization; intended equivalence is not enough. Match length buckets and padded-token budgets. Train both arms for **two passes**, using the same frozen optimizer recipe and three paired seeds: **1729, 1730, and 1731**. No threshold, gate, normalizer, parser, compiler, or mouth changes are allowed.

**UNTESTED:** The manipulated factor is the **training-input realization process**. The experiment tests that package; it will not identify which individual authoring component caused any improvement.

### Panel and scoring

**UNTESTED — fixed sample:** Use **600 fresh turns**, divided among four withheld authoring procedures, 150 each. Each procedure supplies:

- **75 one-fact turns**;
- **25 three-fact turns**;
- **50 turns permitting no teaching facts**.

That gives **600 gold facts**, including 300 in multi-fact turns, and **200 no-save turns**. Include questions, plans, hypotheticals, and unresolved group ownership in the no-save portion. Use different semantic roots throughout.

**UNTESTED:** Two annotators and the director establish the gold labels before seeing model outputs. Seal those labels, the data manifests, scoring rules, configurations, and pass marks. An unresolved gold-label dispute blocks a clean PASS; it must not be quietly removed after seeing which model failed.

**UNTESTED:** Score immediately after the ear, **before any brake, gate, or compiler**. Report:

\[
\text{wrong frames per turn}
=\frac{\text{unsupported emitted TEACH frames}}{600},
\]

and exact fact recall using one-to-one matching, so duplicates cannot inflate it. Separately report the number of turns containing any wrong frame, malformed outputs, and supported question-reading performance.

### Exact pass marks

**UNTESTED — every seed must satisfy every applicable mark:**

| Measure | Required result |
|---|---:|
| Total wrong teaching frames | **At most 4/600 turns** |
| Wrong teaching frames on no-save turns | **0/200 turns** |
| Exact fact recall | **At least 528/600 = 88%** |
| Exact recall within each writer procedure | **At least 132/150 facts** |
| Exact recall on multi-fact turns | **At least 264/300 facts** |
| Improvement over matched control | **At least 50% fewer wrong frames**, with no lower total exact recall |
| Paired evidence of fewer error-bearing turns | **One-sided exact McNemar \(p\le0.05\)** |

**UNTESTED:** I deliberately use 88% recall here to avoid ambiguity about the 12% held-back allowance. This is a conservative experimental bar, not an assertion that your two existing measures are necessarily complements.

**UNTESTED:** Three seeds assess training instability; they do **not** turn 600 test turns into 1,800 independent language examples. Do not choose the best seed after testing.

### Why 600—and what it does not prove

**UNTESTED:** Six hundred turns provide four fresh authoring sources and make the requested observed rate correspond to **four wrong frames**, rather than a verdict dominated by one example. I cannot honestly supply a power calculation from the brief: it does not provide the paired disagreement probabilities between these two future models.

**UNTESTED — statistical calculation:** This is a **development decision, not a below-1% safety certificate**. Even under ideal independent sampling, four error-bearing turns out of 600 have a one-sided exact 95% upper bound of approximately **1.52%**. That is a bound on error-bearing turns, not wrong frames per saved fact; the exact binomial method is described by NIST. Your deliberately structured panel also is not an established deployment sample. 

### What would refute the recommendation?

**UNTESTED:** The decisive adverse result is: **the treatment produces as many or more wrong frames at comparable recall**, especially across all three seeds. A reduction in errors achieved only by missing more facts also defeats the recommendation.

**UNTESTED:** Missing any registered pass mark remains FAIL. If both arms are already excellent and the comparative test lacks evidence of improvement, that is failure to establish the data package’s benefit—not proof that diversity is useless.

**UNTESTED — separate later step:** Only after this experiment, test the data substitution on the own 33M ear with an otherwise fixed pretraining and training recipe. A successful borrowed-ear result does not establish transfer to an own, much smaller model.

## 8. Strongest objection and the rival I rejected

**UNTESTED:** The strongest objection is that this pipeline may merely create a **more sophisticated synthetic distribution**. Its writers and annotators might agree on interpretations that actual users do not share. The borrowed ear might also exploit language knowledge that the 33M student never acquires.

**SUGGESTED:** **The False Promise of Imitating Proprietary LLMs, arXiv:2305.15717**, found that imitation could improve apparent style without closing capability gaps on insufficiently represented tasks. I consulted its abstract for this point; its models and tasks differ substantially from yours. 

**UNTESTED:** The rival is **capacity first**: build a larger own encoder immediately. I reject it as the next move because it changes the capacity question before establishing whether the training examples teach the right distinctions. I would reconsider it if verified examples remain difficult even within well-covered training conditions.

## Plain-language summary

**UNTESTED — recommendation:** Keep the 33M model as a candidate, but do not assume it can already meet your error goal. Spend the first effort on making the training conversations genuinely different, not just changing names inside familiar sentences. Include nearly identical messages where one states a fact and another only asks about it or imagines it. Have separate agents check what the finished message actually says, rather than trusting what its writer intended. Keep whole families of related examples out of training so the test really contains unfamiliar wording. Test this new data on the existing ear first, without changing its gate or other components. A strong result would justify testing the same approach on your own small model, but would not prove that the small model will succeed. Judge success by both the wrong facts it produces and the true facts it keeps, not by how natural its training sentences look.

## Answer to question 5: One principled question reader instead of a stack of patches
(message cmsg_01FuvegZXjMmeUzStiEFVnEW9AKetMxgknU6pfNCuMRCHf, 2026-09-23T10:22:09Z)

**UNTESTED — recommendation:** Replace the question-stage stack with **one typed query language, one compositional reader, and one read-only executor**. A *typed query* is a precise request that explicitly identifies the relation, its direction, the unknown being requested, and the operation—such as listing matches or checking a claim.

Start by testing the new reader **in shadow**, without letting it change live answers. Do not simultaneously retrain the ear, replace the learned reasoner, and change reply wording.

**UNTESTED — essential limitation:** This can eliminate “the wrong stage answered first” as a mechanism. It cannot make misunderstanding English impossible. A correct execution of the wrong interpretation is still a wrong answer.

## 1. Diagnosis: several different problems are being grouped together

### The direction failure is more than a missing phrase

**SHOWN — your measurements:** The forward-chain stage answered before the inverse stage and got all 16 questions in that panel wrong. Separately, multi-word-name detection improved from 6/24 to 24/24 after a detector change. Those are distinguishable failures: choosing the wrong operation versus failing to identify its arguments. 

**UNTESTED — diagnosis:** The deeper architectural problem is that a recognizer can start answering **before the system has committed to a complete interpretation**. “I found a named person and a relation” is being treated as sufficient permission to execute a forward lookup. But a question might put that person at the *end* of the relation, ask whether a complete claim holds, or request a count.

Reordering stages changes which incomplete interpretation wins. It does not repair that contract.

### “The losses are all in reading English” is too broad

**SHOWN — your measurements:** The notebook and reasoner scored 200/200 on the supplied structured benchmark. That supports correctness on those tested inputs; it does not establish support for every query graph, branching query, aggregation, ambiguity, or evidence request proposed here. 

**UNTESTED — diagnosis:** Separate four boundaries:

**English interpretation → formal request → execution → reply record.**

Your direction bug could involve interpretation, dispatch, or the translation into the reasoner’s input format. Without separately inspecting those outputs, “the reader failed” does not identify which boundary needs changing.

### Closed lists are the problem—not necessarily all rules

**SHOWN — published:** Shaw et al., *Compositional Generalization and Natural Language Variation* (**arXiv:2010.12725**), investigate grammar-based and neural approaches together. Their grammar-based method composes reusable source/target rules; the paper also emphasizes that handling unfamiliar combinations and handling natural wording variation are separate challenges. 

**UNTESTED — diagnosis:** A rule saying “this complete sentence shape means this complete answer operation” is different from a rule saying “a possessive phrase connects its owner to a relation’s value.” The latter can be reused inside forward, inverse, yes/no, and multi-hop questions.

A shared representation alone is insufficient: the old recognizers could emit that representation while retaining all their coverage gaps.

### The hash failure is a separate engineering issue

**SHOWN — your report:** Two lineages used different “not understood” wording, causing a byte-identity failure during integration. 

**UNTESTED — diagnosis:** That is a versioned-interface problem, not evidence against a particular parsing architecture. The reader should return a status such as `UNPARSED`, not own the sentence expressing it. One frozen mouth component should own the wording.

Keep three checks separate: **unchanged-file identity, interface compatibility, and semantic behavior**. Passing one does not imply the others.

## 2. The representation: ordered relation patterns plus an operation

### Core notebook-query form — UNTESTED

Use one versioned request envelope containing:

| Field | Meaning |
|---|---|
| **Patterns** | Ordered relation statements whose owner and value can be known entities, literals, or variables. |
| **Requested variables** | Which unknowns should appear in the answer. |
| **Operation** | Return distinct matches, count distinct matches, or test whether a claim is supported. |
| **Scope** | What the current notebook records—not an assumption that the notebook contains every real-world fact. |
| **Evidence request** | Whether the answer needs supporting row references. |
| **Source anchors** | The unchanged question spans supporting entity mentions, relation choices, and operators. |

Use stable entity identifiers internally. Preserve the original span for checking and display. A three-word name should be one possible entity mention, not three separate arguments.

**SHOWN — published foundation:** Ordered triple patterns, variables, joined patterns, and inverse traversal are established query-language ideas. In SPARQL 1.1, inverse traversal explicitly swaps subject and object roles; sequences can be expanded into connected triple patterns. You can borrow those semantics without installing a full SPARQL system. 

### Direction must be in the request—not selected by a stage — UNTESTED

Define

\[
r(o,v)
\]

to mean the notebook row **owner \(o\) | relation \(r\) | value \(v\)**.

Then these are different requests:

| Question | Pattern | Requested result |
|---|---|---|
| “Who is V’s spouse?” | \(\operatorname{spouse}(V,x)\) | \(x\) |
| “Whose spouse is V?” | \(\operatorname{spouse}(x,V)\) | \(x\) |
| “Is Pip Mira’s dog?” | \(\operatorname{dog}(Mira,Pip)\) | Support status |
| “Whose sister’s dog is Pip?” | \(\operatorname{sister}(x,y)\land\operatorname{dog}(y,Pip)\) | \(x\) |

In your example, with only `spouse(A,V)` and `spouse(V,W)`, the first question returns **W** and the second returns **A**. The executor does not need an “inverse question” recognizer. It matches whichever endpoint contains the variable.

Do **not** silently make spouse symmetric because that sounds natural. Execute the notebook’s declared semantics. Likewise, treat inverse relation-table entries as audited traversal mappings—not permission to invent additional taught rows.

For an approved lexical mapping, “Who works for V?” should produce `workplace(x,V)`. The grammatical role of V, not merely its presence in the sentence, determines its endpoint.

### One generic execution procedure — UNTESTED

For notebook queries, the executor should:

1. Validate the request against the relation schema.
2. Match its patterns against one immutable notebook snapshot, joining matches wherever they share a variable.
3. Project the requested variables and apply the specified operation.
4. Return a structured result with supporting row identifiers and the snapshot version.

The executor should not receive the English question as something it may reinterpret. Different join orders may improve speed, but they must not change the answer set.

A path is simply a connected set of patterns. Forward, inverse, and mixed-direction paths therefore share the same semantics. A branching question is also a set of patterns—not a special branch in the English dispatcher.

### Counts, negative answers, and explanations need explicit limits — UNTESTED

**Counts and lists.** `COUNT_DISTINCT d` over `dog(Mira,d)` counts distinct recorded matches. It does not establish how many dogs Mira has in reality. The reply should say “I have two dogs recorded for Mira,” unless completeness has separately been established. A single proof demonstrates one match; it does not demonstrate that a list is complete.

**Yes/no.** Distinguish:

- A claim supported by recorded facts.
- A claim contradicted under an explicitly supported rule.
- A claim for which information is missing.

Absence alone should not become “No.” Conversely, “Have I told you that Pip is Mira’s dog?” concerns notebook contents; “I have no such record” can be a complete answer to that narrower question. A relation being marked single-valued is not automatically sufficient to interpret every different value as a real-world contradiction; time and correction semantics matter.

**Explanations.** “How do you know?” should refer to a previous answer record containing its query, snapshot, and supporting rows. That is an explanation of the assistant’s evidence. “Why does Mira work there?” asks for a cause; a workplace row does not supply one.

**Metadata questions.** Put `Explain(previous_answer_id)` and `Capabilities(...)` in the same versioned request language, but give them explicit types. Capabilities should read the existing verified capability manifest. Forcing every question into the notebook’s 153 relations would itself introduce misinterpretations.

### Relationship to the learned reasoner — UNTESTED

This representation does **not** require immediately replacing the 79,316-parameter reasoner. First document which requests its present interface can express correctly.

A fully deterministic graph executor would be a reasonable reliability mechanism, but introducing it would change the reasoning backend. If it supplies all answers, do not attribute those answers to learned reasoning. Keep that architectural decision separate from the reader experiment.

## 3. How the reader should abstain

### Parse the original question, not an already-reduced frame — UNTESTED

The new reader should receive the unchanged turn, speaker metadata, and the approved relation/entity vocabulary. It should not rely solely on an earlier `ASK(owner, relation)` frame: that form has nowhere to preserve a count request, a proposed value in a yes/no question, or a general pattern of variables.

For the initial reader, use a **compositional chart parser**: it keeps possible interpretations of smaller phrases and combines them into complete interpretations. Unlike first-match dispatch, finding one partial interpretation does not end the search.

Normalize equivalent complete interpretations—such as different variable names or reordered conjunctions—before deciding whether they disagree.

### Four outcomes must remain distinct — UNTESTED

| Outcome | Meaning |
|---|---|
| **PARSED** | A complete request has been selected under the registered acceptance policy. |
| **CLARIFY** | The reader found materially different interpretations or unresolved ownership/reference. |
| **UNPARSED** | It cannot represent the request faithfully, or parsing exceeded its supported limits. |
| **UNKNOWN** | Execution understood the request but lacked the relevant information. |

`UNKNOWN` is an execution result, not a substitute for parsing failure. Conflicting notebook evidence should also have its own execution status rather than being silently resolved.

Your “our/we” ruling should be applied while interpreting the original question. Do not wait for another component to happen to emit a group-owner marker.

### Initial acceptance policy — UNTESTED

Accept only a complete, schema-valid interpretation with resolved arguments and supported operators. Ask for clarification when materially different complete interpretations remain. Return `UNPARSED` for unsupported scope, unresolved wording, or incomplete search.

Do not silently discard “not,” “only,” tense, a condition, or another meaning-changing phrase to obtain an easier query.

Most importantly, **do not choose a parse because it produces a nonempty answer**. Two interpretations can even give the same answer in today’s notebook and disagree after tomorrow’s edit.

**SHOWN — published:** Zhong, Yu, and Klein, *Semantic Evaluation for Text-to-SQL with Distilled Test Suites* (**arXiv:2010.02840**), explain why matching the answer on one database can accept an incorrect query. Their evaluation uses multiple databases to distinguish queries that otherwise appear equivalent. 

**SUGGESTED — transfer to Premonition:** Check interpretations against deliberately different notebook worlds. That is stronger evidence of semantic correctness than agreement on a single answer.

### What this does—and does not—guarantee — UNTESTED

“One remaining parse” means **one interpretation found by this grammar**, not “the only possible English meaning.” The correct interpretation might be missing from the grammar.

Likewise:

\[
\text{Notebook supports the selected query’s answer}
\]

does not establish

\[
\text{Selected query matches the user’s question}.
\]

A proof-carrying executor protects the first boundary. Parser testing and conservative abstention address the second. Neither should be advertised as an unconditional zero-error guarantee.

**SHOWN — published:** Dong, Quirk, and Lapata, *Confidence Modeling for Neural Semantic Parsing* (**arXiv:1805.04604**), found benefits from explicit confidence modeling over using model posterior probability alone. Kamath, Jia, and Liang, *Selective Question Answering under Domain Shift* (**arXiv:2006.09462**), found that probability-based abstention performs poorly on unfamiliar-domain inputs. Neither establishes Premonition’s requested error rate. 

**SUGGESTED — later extension:** A learned reader’s acceptance score should concern the **whole interpretation**, with calibration examples containing new wording and structural confusions. Do not reuse a threshold such as 0.25 merely because it was used elsewhere.

## 4. Ranked options

**UNTESTED — project-specific ranking and trade-offs:**

| Rank | Option | What it fixes | Cost | What it cannot fix |
|---|---|---|---|---|
| **1** | **Compositional grammar → typed requests**, with an own learned lexical component considered later | Removes first-match semantics; makes directions, variables, and ambiguity inspectable; reuses phrase rules across question types | Grammar/schema engineering and careful coverage testing; initial version needs no new model | Unfamiliar wording outside its grammar; unique but incorrect interpretations |
| **2** | **Own span-and-graph predictor → the same typed requests** | Can learn broader wording without adding a complete-question handler for each form | Verified question/request pairs, training, uncertainty calibration, and composition tests; required data volume is unknown | Formal validity does not guarantee correct relation, scope, or direction |
| **3** | **Generative parser with constrained formal output**, using an already-approved borrowed model only as a temporary prototype | Rapid exploration of broad language-to-query mapping | Model execution, latency testing, and a later own-weights replacement | Correct-looking queries can still mean the wrong thing; does not meet the final own-weights requirement |

**SHOWN — published:** PICARD, *Parsing Incrementally for Constrained Auto-Regressive Decoding* (**arXiv:2109.05093**), constrains generated formal output by rejecting inadmissible continuations. Its reported setting is text-to-SQL with pretrained models. 

**SUGGESTED — transfer:** Constrained decoding is useful for options 2 or 3, but it enforces the request language’s rules, not faithfulness to English.

**UNTESTED — strongest objection to option 1:** Your practical weakness is natural wording. Another hand-built grammar might produce beautifully structured refusals while understanding too little. That is why the next experiment must have a hard coverage requirement on independently written questions—not merely zero errors on familiar constructions.

**UNTESTED — rival rejected for the immediate next step:** Option 2 is the strongest longer-term rival. I would not begin by training it before fixing the target semantics and evaluation contract. Otherwise, an error could come from the labels, graph representation, decoder, abstention policy, or execution adapter. The same typed request language should make replacing the grammar with an own learned reader possible later.

## 5. The ONE experiment to run next

### E1: Compositional-reader shadow trial — UNTESTED

**Hypothesis:** A single compositional reader can produce correct typed requests across the specified question families, including unfamiliar combinations, without old-stage calls or first-match precedence.

**Named base:** Call the current verified deployed build **QBASE**. The director must insert its actual commit and SHA-256 manifest before sealing. I do not know those identifiers from the supplied context.

**Single intervention:** Add the candidate question reader as an **offline shadow component**. It receives the same original turns but cannot write to the notebook or replace visible replies. Do not change ear weights, gates, relation-table meanings, notebook behavior, reasoner weights, or mouth wording.

The reference interpreter and graders are evaluation apparatus, not replacements in the live pipeline. Seal them too.

### Sample: 360 fresh utterances — UNTESTED

Use **300 unambiguous, in-scope requests**, with **50 each** for:

| Family | Required content |
|---|---|
| Forward lookup | Including multi-word entity names |
| Inverse lookup | Including verbal forms such as workplace questions and misleading forward facts |
| Yes/no | Both argument orders; supported claims versus missing information |
| Multi-hop | Mixed directions; two and three hops; the longest previously verified depth must also be represented |
| Lists and counts | 25 of each; duplicates and incomplete real-world knowledge |
| Evidence and capabilities | 25 of each; evidence must match recorded answer provenance |

Add **60 requests requiring clarification or non-parsing**: 20 ambiguous references/owners, 20 unsupported operators or causal/temporal requests, and 20 questions whose embedded wording or scope makes a simpler extracted request incorrect.

Within the 300 supported requests, designate **60 composition-holdout cases** and **60 separate casual-wording cases** before building. The composition cases must combine familiar pieces in arrangements absent from development examples.

Use three independent panel writers, with each contributing across families. Two independent reviewers should settle the intended request and answer contract before seeing system output. Use only fictional names.

**SHOWN — published:** CFQ, *Measuring Compositional Generalization* (**arXiv:1912.09713**), explicitly separates familiarity with individual components from familiarity with their combinations. 

**SUGGESTED — transfer:** Hold out combinations, not just names and complete sentences. Otherwise the test can reward a renamed template collection.

### Additional semantic checks — UNTESTED

For the **250 notebook-query cases**, prepare four notebook worlds before execution: the original, a world distinguishing a plausible wrong interpretation, a relevant-edit world, and an irrelevant-edit world.

That creates **1,000 structured-query executions**, not 1,000 independent English examples. The evidence/capability cases instead use their sealed answer records and capability manifest.

Score the interpretation itself as well as its execution. Normalize approved equivalent forms; do not demand literal string identity between two equivalent queries.

### Pass marks—all required, fixed before the run — UNTESTED

| Check | Pass mark |
|---|---|
| Incorrect accepted requests | **0**, including wrong direction, operator, scope, or argument |
| Supported-request coverage | **At least 45/50 in every family**, therefore at least **270/300** |
| Composition-holdout subset | **At least 54/60** correct accepted requests |
| Casual-wording subset | **At least 54/60** correct accepted requests |
| Required clarification/non-parsing | **60/60** take the appropriate safe outcome |
| Fresh-case regression | **0 losses** among supported questions QBASE answers semantically correctly; a new refusal counts as a loss |
| Reference-interpreter audit | **1,000/1,000** gold-query executions match independently established results |
| Accepted candidate queries | **0 mismatches** against gold across their four worlds |
| Old recognizer/answer-stage calls by candidate | **0** |
| Rule-order dependence | **0 changed decisions** across 20 registered rule-order permutations of all 360 inputs |
| Unintended side effects | **0 notebook writes; 0 changes to frozen components** |
| Reader latency | **Median ≤100 ms**, on a fixed named machine, with result caching disabled |

Use ten development-only warm-up questions and one registered timed pass. The 100 ms threshold is a proposed reader budget, **not a measured speed**. Passing it does not establish the complete assistant’s 800 ms target.

### Why this sample size—and what it does not certify

**SHOWN — calculation:** Under independent trials with a 5% per-case failure probability, 50 cases have probability

\[
1-(1-0.05)^{50}\approx92.3\%
\]

of exposing at least one failure. That makes the family sizes useful for diagnosing substantial weaknesses.

For zero errors in \(n\) independent accepted predictions, the one-sided 95% exact binomial upper bound is

\[
p_U=1-0.05^{1/n}.
\]

At the minimum passing coverage, \(n=270\), this is approximately **1.10%**, not below 1%. The corresponding minimum for a bound below 1% is **299 accepted predictions with zero errors**, under the required sampling assumptions. 

**UNTESTED — interpretation:** E1 is an architectural engineering gate, **not deployment certification**. Its deliberate family allocation, related notebook worlds, and possible writer correlations must not be disguised as independent samples of actual user traffic. A later certificate needs its own fixed population, acceptance policy, labeling procedure, and treatment of repeated attempts.

### What would prove this recommendation wrong?

**UNTESTED — falsification criteria:** One incorrect accepted query disproves the claim that this implementation meets E1’s zero-error bar—even if its answer has a valid notebook proof. Falling below any coverage threshold rejects the grammar-first reader as a sufficiently useful next replacement. Any rule-order dependence or old-stage call rejects the claimed architectural separation.

A failure would not disprove query graphs generally. It would reject this implementation or the prediction that this reader is useful enough. Keep the registered FAIL, and permit only the specified diagnosis-driven follow-up.

## 6. Migration without silently losing verified behavior

### Separate later steps — UNTESTED

**After E1, the next separate experiment should be “typed execution-boundary extraction.”** Existing interpretation behavior remains fixed while execution is routed through a versioned structured interface. This is an equivalence/integration experiment, not a claim of improved English understanding. Requests outside the existing reasoner’s supported interface must be identified explicitly; supporting them is additional backend work.

**Only after that boundary is verified should another sealed change switch the active reader.** At that point, the candidate reader and executor should already be frozen. Do not simultaneously change sentence templates, relation meanings, or confidence thresholds.

Maintain a director-owned registry of previously verified **behavior contracts**, then write fresh cases exercising those contracts. Historical test panels must not quietly become a training set or be advertised as new blind evidence.

Preserve the selected base lineage’s unchanged artifacts byte-for-byte. New modules receive new hashes. Map statuses to the base mouth’s existing wording rather than importing competing decline strings from other lineages.

**UNTESTED — important limit:** No supplied finite benchmark establishes preservation of every English sentence the old system could answer correctly. You can preserve unchanged execution paths exactly, require no losses on known contracts and fresh regression cases, and withhold promotion when losses appear. Those are defensible claims; “all possible old behavior is preserved” is not.

### What establishes that it is not the old stack in disguise? — UNTESTED

You need both **implementation evidence** and **behavioral evidence**.

Implementation evidence means the executor cannot inspect English; the reader cannot call legacy answer stages; grammar-rule order cannot select the winning meaning; and every accepted answer is traceable to the emitted request.

Behavioral evidence means unfamiliar combinations succeed, reversed arguments produce the appropriate changed query, and the selected interpretation survives distinguishing notebook worlds and relevant edits.

A program can pass examples while hiding a stage stack. Conversely, a genuinely unified parser can still misunderstand English. Neither source inspection nor a benchmark replaces the other.

## Plain-language summary — UNTESTED

Give every understood question one precise plan before the assistant looks up an answer. That plan should say which relationship is involved, which way it points, and what the user wants returned. One component should understand the sentence, while another follows the plan without rereading the English. A notebook proof can show that an answer follows from the plan, but it cannot show that the plan understood the user correctly. When ownership, meaning, or scope is unclear, the reader should ask or decline rather than choose whichever lookup finds something. The next experiment should test a new compositional reader in shadow, leaving the working assistant unchanged. Require both zero incorrect accepted interpretations and high coverage on fresh wording and unfamiliar combinations. Only after the reader and its execution interface pass separate checks should they replace the live stage stack.

## Answer to question 6: Trustworthy evaluation when every panel writer and grader is an AI
(message cmsg_01FuvegZXjMmeUzStiEFVnEW9zVSAM5UuUUtoExoSowyXT, 2026-09-23T10:22:42Z)

**UNTESTED—recommendation:** Treat the evaluator as a second system that must earn trust. Keep synthetic panels for finding bugs, build a separate owner-origin sample for claims about everyday use, and make answer keys independently reconstructable from the text. **The next experiment should test an answer-key audit—not change the assistant or add another gate.**

**Labels:** **SHOWN** means a published result or a measurement reported in your file; I have not independently verified your experimental records. **SUGGESTED** means a published method whose usefulness here remains to be tested. **UNTESTED** means my proposed design or reasoning.

## 1. Diagnosis: several different problems are being called “evaluation noise”

**SHOWN—your measurements:** You have failures in answer-key completeness, semantic labeling, scoring arithmetic, evaluator sensitivity, information separation, and experiment specification. Six incorrect key judgments changed the interpretation of one run; another pair of scorers produced unresolved counts of 14/40 and 23/40. These are not all sampling errors that a larger panel would average away. 

**UNTESTED—diagnosis:** Your sealing process answers, “Did we run the registered procedure?” It does not answer, “Did that procedure measure the intended thing?” A hash can faithfully preserve an incorrect answer key, a circular denominator, or the wrong base. You need separate verdicts for **measurement validity** and **assistant performance**.

### What is wrong or incomplete in the existing explanations?

**SHOWN—published:** Different model providers do not guarantee independent errors. *Correlated Errors in Large Language Models*, **arXiv:2506.07962**, found substantial shared errors, including across providers, and demonstrated how those errors distort model-as-judge evaluations. Multiple AI reviewers can therefore provide useful disagreement without supplying independent confirmation of truth. 

**UNTESTED—interpretation:** “Use several writers” addresses some wording diversity; it does not establish the frequencies of everyday situations. “Use several graders” addresses some individual mistakes; it does not establish that unanimous answers are correct. These are useful safeguards, not foundations for a population certificate.

**SHOWN—published:** Incorrect benchmark labels can change conclusions about which model performs better. Northcutt and colleagues demonstrated this in *Pervasive Label Errors in Test Sets Destabilize Machine Learning Benchmarks*, **arXiv:2103.14749**. Your omitted appositives are especially important: missing gold facts can simultaneously make correct saves look wrong and inflate recall by shrinking its denominator.  

**UNTESTED—interpretation:** The 36/40 planted-error requirement is a useful malfunction detector, but not a calibration of performance on naturally occurring mistakes. Its meaning depends on which errors were planted. A grader that catches obvious verb-agreement errors may still miss fluent false claims. Conversely, marking every reply “okay” is not by itself proof of malfunction; failing known-error controls is.

**UNTESTED—metric contract:** Before certification, freeze these three different quantities:

| Quantity | Numerator | Denominator |
|---|---|---|
| **Wrong-write fraction** | Incorrect committed fact writes | All committed fact writes |
| **Bad-turn frequency** | Turns causing at least one incorrect write | All eligible turns, including no-save turns |
| **Fact recall** | Plainly asserted facts saved exactly | All plainly asserted facts identified independently of system output |

**UNTESTED—recommendation:** Make **wrong-write fraction** the headline meaning of “under 1% wrong saves,” and publish bad-turn frequency alongside it. The earlier proposal using 600 ordinary turns addresses bad-turn frequency, not necessarily wrong-write fraction. A mostly silent system can look excellent on bad-turn frequency while having unreliable writes.

**UNTESTED—specification issue:** Resolve “recall ≥85%” versus “true facts held back ≤12%.” If *held back* means every fact not saved correctly, the second requirement implies recall ≥88%. If it means only explicit refusals or clarifications, measure that separately from silent extraction misses. Do not let a scorer choose the interpretation after seeing results. Your current specification contains both bars. 

## 2. Four ranked options

**UNTESTED—ranking:** These are ranked by value **now**, and are complementary rather than four mutually exclusive systems.

| Rank | Option | What it fixes | Cost | What it cannot fix |
|---|---|---|---|---|
| **1** | **Independent, source-first answer-key audit** | Missing facts, wrong relation labels, unsupported gold facts, denominator errors | Another annotation pass and a limited owner reference check | Whether the panel resembles real use |
| **2** | **Probability sampling from an owner-origin chat stream** | The missing connection to the claimed deployment population | Collecting a suitable stream and reviewing its semantics | Generalization to other people, future changes, or excluded content |
| **3** | **Several-writer synthetic challenge suite** | Coverage of known linguistic hazards and writer-specific weaknesses | More varied generation and deduplication | Everyday occurrence rates or shared model blind spots |
| **4** | **Human-calibrated automatic evaluation** | Reducing manual review while accounting for grader error | An audited human sample, additional statistical implementation, continued recalibration | Bad reference labels or a synthetic-to-real sampling mismatch |

**SUGGESTED—evidence for option 3:** CheckList, **arXiv:2005.04118**, demonstrates the value of capability-focused behavioral testing. That supports keeping family-quota panels as a **challenge suite**, rather than treating their aggregate accuracy as a population estimate. 

**SUGGESTED—evidence for option 4:** Prediction-powered inference combines automatic labels with a human-labeled sample to correct statistical estimates. Relevant papers are **arXiv:2301.09633** and *Stratified Prediction-Powered Inference for Hybrid Language Model Evaluation*, **arXiv:2406.04291**. This is a credible later direction, not permission to count AI labels as gold. In particular, the stratified paper’s confidence-interval result is asymptotic; it is not automatically a finite-sample guarantee for a rare-error, 150-turn test. 

## 3. Where representative turns should come from

### Define the population before choosing a source

**UNTESTED—recommendation:** Replace “everyday chat” with an operational scope, such as:

> The owner’s English messages to this frozen assistant during ordinary notebook use, including questions, corrections, casual typing, and messages asserting nothing.

Record exclusions explicitly. A certificate about that population is narrower—and more meaningful—than a claim about arbitrary people’s everyday English.

**UNTESTED—recommended source:** Collect a prospective stream through ordinary use, with the assistant’s proposed writes recorded in shadow mode rather than trusted automatically. Keep every eligible turn during a registered collection window, not just fact-teaching turns or messages the assistant understood. Preserve the preceding context and notebook state needed to interpret each message.

**UNTESTED—important constraint:** Your “fictional names only; no personal data” rule prevents casually importing the owner’s existing private conversations. Replacing names alone does not remove identifying circumstances. Under the unchanged rule, the compliant alternative is **owner-written, naturally phrased interaction about a fully fictional notebook**. Label the resulting population honestly: “the owner’s fictional-notebook interactions,” not unrestricted personal chat. Using genuinely personal logs would require a separately approved privacy procedure. 

**UNTESTED—limitation:** Asking the owner to compose “a tricky correction” or “a sentence with three relatives” makes him another challenge-panel writer. For the owner-origin stream, he should use the fictional notebook for ordinary tasks without being shown family quotas or desired failure types. This still may differ from personal use; measure that limitation rather than assuming it away.

### You do not always need independently generated conversations

**SHOWN—sampling principle:** A probability sample requires a defined population and known selection probabilities. Simple random sampling without replacement starts from a complete list of population units. Statistics Canada’s sampling guidance distinguishes this from convenient or selectively collected examples. 

**UNTESTED—application:** Freeze an archive of eligible turns, assign IDs, then sample IDs uniformly without replacement. This supports an estimate about **that finite archive**. With fixed binary outcomes, the appropriate exact calculation is hypergeometric; neighboring turns do not have to be independent draws from a hypothetical language generator. The randomness comes from which archive entries are selected.

**UNTESTED—boundary:** That does not automatically establish future performance. Future-chat claims require an additional assumption that future usage resembles the collection period. For session-based sampling, retain session IDs and account for clustering. One turn from each session is not automatically a uniform sample of turns: long and short sessions otherwise receive the same weight.

### How the other proposed sources fit

**UNTESTED—recommendation:** Use several existing, authorized writer models for the challenge suite, with separate generation jobs and recorded model versions. Do not download new models for this purpose without permission. A topic generator can help allocate coverage, but its topic frequencies should come from an exploratory owner-origin sample—not from its own guess about “normal chat.” Keep the final certification sample out of that calibration loop.

**UNTESTED—boundary:** A small amount of owner-origin text is an anchor for discovering mismatch, not a license to treat thousands of synthetic paraphrases as thousands of real observations. Paraphrases retain their parent-source ID and remain synthetic.

## 4. Measuring how unrepresentative a synthetic panel is

**UNTESTED—recommendation:** Report a **mismatch dashboard**, not a single “representativeness score.”

**UNTESTED—first measurement: observable differences.** Compare synthetic and owner-origin samples on no-assertion frequency, facts per turn, corrections, missing punctuation, typos, context dependence, ambiguous owners, relation frequencies, and message length. Report percentage-point differences and uncertainty. Include interactions such as “multiple facts plus casual typing,” not only separate marginal frequencies. Human-check a random subset of these annotations so the dashboard does not merely repeat another AI’s mistakes.

**SUGGESTED—second measurement: a source-discrimination test.** *Revisiting Classifier Two-Sample Tests*, **arXiv:1610.06545**, trains a classifier to distinguish samples from two sources and evaluates it on held-out examples. Adapt that by asking whether a small classifier can distinguish owner-origin from synthetic turns. Keep complete sessions and paraphrase families within one split, and apply the same fictional-name treatment to both sources. Report held-out balanced accuracy and uncertainty. Strong discrimination demonstrates a detectable mismatch; near-chance results do **not** prove equivalence, because the test may lack power. 

**UNTESTED—third measurement: performance mismatch.** Run the same frozen assistant and audited evaluator on both sources. Compare errors and recall within matched categories, then standardize synthetic results to the observed owner-category frequencies. Any remaining gap suggests that category matching missed important wording differences. Report categories present in owner use but absent from synthetic data as **unsupported coverage**, not zero-error categories.

**UNTESTED—boundary:** None of these measurements supplies a universal conversion from synthetic accuracy to real-chat accuracy. I do not know a justified conversion for this project. In particular, a small overall wording difference can hide a rare construction responsible for most wrong writes.

## 5. The evaluation process

### A. Establish gold facts before looking at system output

**UNTESTED—proposed protocol:** The writer’s key becomes a **proposed key**. A separate annotator receives the original text, necessary context, and frozen relation policy—but neither the writer’s key nor the assistant’s output. It reconstructs a complete evidence ledger containing:

> Turn ID; speech act; all asserted facts; supporting text spans; permitted canonical forms; clarification requirements; unresolved ambiguity.

This is reconstruction, not “Does this proposed answer look right?”

**UNTESTED—proposed protocol:** Compare the independently produced ledger with the writer’s key. An adjudicator examines every disagreement against the unchanged source text. The adjudicator must identify the supporting wording and applicable policy rule. A majority vote without such evidence does not settle a disputed fact.

**UNTESTED—policy requirement:** Resolve relation granularity, appositives, corrections, duplicate assertions, spelling uncertainty, and ambiguous group owners on development material first. “Dog” and “pet” must not become interchangeable merely because doing so helps a tested model. Distinguish **a supported but insufficiently precise save** from **an unsupported save**, while retaining the exact-save recall requirement.

**UNTESTED—ambiguity handling:** Distinguish “the text is genuinely ambiguous” from “the evaluator cannot decide.” The former can have a registered clarification policy. The latter is unresolved measurement uncertainty. Keep such cases in the accounting; do not silently remove difficult items. For certification, either adjudicate them or take the worst result across defensible labels.

**UNTESTED—human anchor:** Give the owner a random selection of raw turns to label before revealing AI keys or assistant outputs. Include AI-agreement cases, not only disagreements. The owner need not run commands: the task is to identify what the displayed words assert. He is not an infallible oracle, and his intended meaning must not override wording that fails to express it.

### B. Make denominators a property of the registered task

**UNTESTED—proposed protocol:** The owner approves the metric definitions; the independent evaluation side freezes eligibility and gold facts; a small reference scorer performs the counting. The builder supplies outputs but cannot decide which expected facts count.

**UNTESTED—required accounting:** Count every registered turn, every independently identified target fact, and every actual committed write. Match each target fact at most once. Missing predictions remain misses; extra writes remain visible; duplicate outputs cannot increase recall or pad the write denominator. Crashes and malformed outputs receive their registered outcomes rather than disappearing.

**UNTESTED—cheap preflight:** Before spending a fresh panel, test the scorer on hand-checkable fixtures: no predictions, all predictions wrong, one extra wrong write, one omitted gold fact, duplicate predictions, a no-save turn, and a crashed turn. Have a separately implemented recount produce the same item-level counts. This directly targets your circular-denominator failure without requiring another language-model experiment.

### C. Validate graders on the errors they are supposed to detect

**UNTESTED—proposed protocol:** Keep separate grading axes for **grammar**, **truth relative to the notebook**, and **truth about the assistant’s capabilities or actions**. A fluent sentence can fail either truth check. Where possible, compare claims about capabilities and writes to a versioned capability manifest and execution log rather than asking for a stylistic judgment.

**UNTESTED—control design:** Mix hidden defective examples with matched correct controls. Include omitted facts, wrong owners, swapped values, unsupported assertions, question-versus-statement mistakes, and your actual grammatical failure types. Include correct but unusual wording to catch graders that simply reject unfamiliar sentences. Keep the controls out of the reported assistant performance rate.

**SHOWN—published:** Agreement statistics need careful interpretation when categories are imbalanced. Di Eugenio and Glass’s *The Kappa Statistic: A Second Look* shows how prevalence and annotator bias affect kappa. A universal “kappa above X means trustworthy” rule is therefore inappropriate here. 

**UNTESTED—reporting requirement:** Publish the disagreement counts, per-class agreement, and—on owner-checked references—false acceptance and false rejection counts. Kappa may accompany them. Also report how often **both** AI graders accept an owner-identified error. That last count directly tests the shared-blind-spot problem that overall agreement conceals.

### D. Track exposure, not merely file hashes

**SUGGESTED—documentation:** *Datasheets for Datasets*, **arXiv:1803.09010**, motivates recording data origin, composition, collection, preprocessing, and intended use. Extend that into a panel registry with model/prompt versions, parent sources, item hashes, access history, registered experiment, and exposure status. 

**UNTESTED—proposed rule:** Use statuses such as **draft**, **sealed**, **used**, **exposed**, and **retired**. Exposure includes raw rows, quoted snippets, inherited agent context, and near-duplicate paraphrases. A writer that has read an old panel must not be described as wholly unexposed. Keep panel contents outside builder-accessible repositories; record diagnostic information released to builders.

**UNTESTED—important distinction:** Exposure after a properly frozen, completed experiment does not automatically erase that historical result. It prevents treating the same material as fresh evidence for an adapted system. Preserve registered FAILs; attach audited corrections or measurement-invalid notices rather than quietly rewriting history. A wrong base or unresolved scorer discrepancy means the intended claim was not established.

**SHOWN—published:** Adaptive reuse of test information can cause overfitting even without directly training on the rows. Dwork and colleagues analyze this in *Generalization in Adaptive Data Analysis and Holdout Reuse*, **arXiv:1506.02629**. 

**UNTESTED—recommendation:** Keep development experiments separate from a final certification attempt. Pre-register how repeated certification attempts share the error budget; fresh panels alone do not justify repeatedly trying at 95% until one passes. Never pool different assistant versions as though they were one frozen system.

## 6. Certification mathematics: what it does and does not cover

**SHOWN—conditional calculation:** With correctly classified, independent Bernoulli observations, zero errors among \(n\) observations gives the one-sided upper bound

\[
U=1-\alpha^{1/n}.
\]

For 600 observations at \(\alpha=0.025\), that is **0.613%**. Allowing one error gives approximately **0.925%**, so the earlier arithmetic is sound. But allowing one observed error conflicts with your separate **zero observed wrong writes** pass rule. These calculations require the observations to match the claimed denominator. 

**UNTESTED—certification rule:** For the headline wrong-write fraction and recall, require an upper bound below 1% and a lower bound at or above the agreed recall bar. Allocate confidence across both claims. Use sampling-appropriate bounds: do not treat all facts from a few multi-fact turns as independent, and use finite-population inference when sampling from a fixed archive.

**UNTESTED—critical limitation:** Those bounds do not cover undetected labeling mistakes. The true error rate includes errors the evaluator flagged **plus errors it incorrectly accepted**. Either review every sampled write against the source, or estimate residual grader error from an independently selected reference audit and include that uncertainty. A tiny audit cannot make this term disappear.

**SHOWN—conditional calculation:** Even zero detected mistakes in an idealized 60-item independent evaluator audit leaves a one-sided 95% upper bound of **4.87%**. That audit is useful for finding a broken process, not certifying sub-1% labeling error. 

## 7. The ONE experiment to run next

### EVAL-GOLD-01: Does source-first auditing repair answer keys without damaging correct ones?

**UNTESTED—base and single change:** Freeze the current assistant: ear v4.1, current rule brake, current gate at 0.25, and the remaining current pipeline. Record the actual hashes before execution.

Compare:

**A:** Current writer-provided answer keys.  
**B:** The same keys after **one independent, source-first reconstruction-and-reconciliation stage**.

The assistant, writer distribution, panel specification, outputs, relation policy, and scoring code remain identical. **Only answer-key production changes.**

### Material and reference labels

**UNTESTED—registered sample:** Use **150 fresh ordinary panel turns**, generated under the existing specification. This remains a synthetic process test, not an everyday-chat certificate.

Add **80 audit-only controls**: 40 deliberately corrupted keys and 40 matched correct keys. Corrupt exactly ten keys in each category: omitted asserted facts; unsupported added facts; incorrect relation/granularity; incorrect owner or value. Present matched controls in isolated, randomly ordered jobs so the auditor cannot solve them by comparing the pair.

**UNTESTED—reference construction:** Before either evaluation arm is revealed, the owner checks the **40 distinct control source turns** and independently labels **60 uniformly selected ordinary turns**. That is **100 source turns of owner review**, not commands or model training. Keep which ordinary turns were selected hidden from the auditor. Unresolved reference ambiguity receives an explicit reference status, not a guessed answer.

**UNTESTED—execution:** The auditor first reconstructs facts without seeing the candidate key, then reconciles the two. Seal its final ledger before exposing assistant outputs. Score the same frozen outputs using A and B. Retain every changed label and its textual justification.

### Exact pass marks

**UNTESTED—pre-registered decision rule:** PASS requires **all** of the following:

| Check | Required result |
|---|---:|
| Corrupted controls recognized as defective | **40/40** |
| Corrupted controls repaired to the exact reference ledger, rather than merely flagged | **At least 38/40** |
| Correct controls preserved correctly | **40/40** |
| Ordinary audited keys match the owner reference, including explicit ambiguity status | **60/60** |
| Ordinary baseline key errors repaired in that 60-turn subset | **At least 1**, with **0 new errors** |
| Reference scorer and independent recount | **Exact agreement on every item and total** |

**UNTESTED—interpretation:** Requiring a baseline error to be repaired prevents declaring an improvement when the original keys were already correct on the checked sample. If none occurs, the experiment fails to demonstrate benefit; that is not evidence that auditing is harmful. Missing a pass mark remains a registered FAIL. A broken seal, leaked reference, or invalid control construction is a measurement-invalid run, not a model success.

### Why this size, and what would prove the idea wrong?

**UNTESTED—rationale:** The 150 ordinary turns preserve your current panel scale. The 60 owner-checked turns test whether the intervention works beyond obvious planted mistakes. The 40 defective and 40 clean controls test both error detection and overcorrection. Do not pool those deliberately enriched controls into a population accuracy number.

**UNTESTED—falsifier:** The most damaging result would be excellent planted-error detection but an ordinary key that becomes wrong after auditing—especially an AI-unanimous key that invents a fact or misses an appositive. That would refute the proposed stage’s readiness to become trusted infrastructure. Correct controls being “repaired” incorrectly would be another direct failure.

**UNTESTED—cost and scope:** This needs existing authorized AI access, 230 source-first audit records, and 100 owner source reviews. It needs no new model download or training. I do not know its wall-clock cost. Passing establishes only that this audit procedure survived this registered test—not that it has sub-1% residual error.

**UNTESTED—separate later step:** After a PASS, apply the audited process to the owner-origin sampling study. Do not simultaneously change the sampler in EVAL-GOLD-01; otherwise a difference could come from easier text rather than better keys.

## 8. Strongest objection and the rival I rejected

**UNTESTED—strongest objection:** This recommendation does not eliminate dependence on the owner’s judgment, and a small reference sample can miss shared AI mistakes. It also cannot make fictional interactions fully representative of personal use. The remedy is not stronger language in the report: retain those limitations, enlarge reference review for certification, and restrict the population claim.

**SHOWN—evidence for the rival:** A diverse-model voting panel is a serious alternative. *Replacing Judges with Juries*, **arXiv:2404.18796**, reported improvements over a single judge across its evaluation settings. It would be wrong to claim that AI committees never help. 

**UNTESTED—why I reject it as the foundation:** Voting does not independently establish missing gold facts, repair an output-dependent denominator, or connect synthetic wording to everyday use. Use another model to reveal disagreements; do not let the number of agreeing models substitute for evidence in the source.

## Plain-language summary

**SHOWN:** Your test process has already produced wrong answer keys, conflicting scores, and a claimed PASS that did not survive a recount. 

**UNTESTED—recommendation:** First test whether an independent reader can rebuild the correct facts from each message before seeing the assistant’s answer. Keep counting rules outside the builder’s control. Use hidden bad examples and correct examples together, so a grader cannot pass by accepting or rejecting everything. Keep synthetic panels for finding weaknesses, but use a clearly defined owner-origin sample for claims about everyday use. Review some cases where all the AI graders agree, because agreement can hide shared mistakes. The next experiment should change only answer-key auditing, leaving the assistant untouched. A later “under 1%” claim should say exactly which chats and which kind of error it covers, and should never imply that zero mistakes in a test proves the assistant will never make one.

## Answer to question 7: Reading several facts, appositives and pronouns in one sentence
(message cmsg_01FuvegZXjMmeUzStiEFVnEWMtwdCfmivrCZXUHommK6R1, 2026-09-23T10:22:38Z)

**UNTESTED — Recommendation:** Test a **span-preserving coordination reader for explicit lists of relatives** next. Let it represent the list as a group, then let code expand that group into notebook candidates under a narrowly defined rule. Keep the existing gate and all-or-nothing commit policy unchanged during this experiment.

**UNTESTED:** For the eventual own ear, I recommend a small structure containing mentions, groups, assertions and reference links—not just independent flat triples. However, **a correctly formatted structure is not proof that the sentence was understood correctly.**

## 1. Diagnosis: several different failures are being mixed together

### Missing names is not the same problem as binding a pronoun

**SHOWN — Your measurements:** Finding only 4 of 16 relative facts demonstrates a serious problem on that sample. The Ada/Bo mistake demonstrates a different problem: the reader selected an owner that was present in the sentence but was not the owner of the asserted residence fact. Exact copying of names would not have prevented that error.

**UNTESTED:** I would distinguish four stages when recounting failures: identifying every mention, assigning mentions to assertions, resolving references, and deciding which assertions may be committed. “Multi-fact recall” currently combines failures at all four stages. A counter that says “two facts” cannot tell you whether either fact has the right owner.

**SUGGESTED — Different setting:** Set prediction is a sensible replacement for sequential triple generation. *Joint Entity and Relation Extraction with Set Prediction Networks*, **arXiv:2011.01675**, predicts triples in parallel and uses permutation-invariant matching during training. This supports removing an unnecessary output-order burden; it does **not** establish that six slots will solve coordination, pronoun binding or assertion scope in Premonition. 

### The pick-one test may be partly mis-specified

**UNTESTED:** In “Mira and Tal are my sisters,” both `me | sister | Mira` and `me | sister | Tal` are correct. Choosing the “other name” is not, by itself, evidence of choosing a false interpretation. It could demonstrate an inadequate single-answer test, failure to preserve the identity of a requested candidate, or an actual reading error. **I do not know which without the items.**

**UNTESTED:** Have the director audit whether those rival choices were genuinely mutually exclusive. For future tests, distinguish **“Which candidates are supported?”**, which can have several answers, from **“Is this particular candidate supported?”** Do not retrospectively turn a registered failure into a pass.

### “Mostly caused by several facts” is plausible, not established

**SHOWN — Your measurements:** The relative-name sample is small, and the oracle compiler audit found that only 184/272 real facts were writable even with perfect reading.

**UNTESTED:** That audit means better extraction alone cannot reach the target under unchanged restrictive write rules. It also means the highest-payoff family is not yet known: payoff depends on both the family’s failure rate and how often it occurs. Explicit relative lists are my first choice because they have a measured failure and a relatively narrow semantic rule—not because the supplied measurements prove they account for most missing facts.

### All-or-nothing amplifies failures, but does not detect omissions

**UNTESTED — Illustrative calculation:** Suppose, purely for illustration, that each fact is correctly recovered and accepted with independent probability \(0.9\). Requiring four facts to succeed together gives

\[
0.9^4=0.6561.
\]

That is not an estimate of Premonition’s performance; errors may be strongly correlated. It illustrates why whole-turn acceptance can deteriorate with fact count.

**UNTESTED:** More importantly, an omitted fact may leave no visible error. The ear can emit two valid-looking facts from a three-fact sentence, and its count head can also predict two. Agreement between those outputs is a consistency check, not proof of completeness. Six fact slots also require an explicit overflow policy; seven facts must not silently become six.

**UNTESTED — Metric clarification:** If “held back” includes every unsaved true fact, the 12% limit effectively requires **88% recall**, not merely 85%. If it means only facts rejected after extraction, report extraction omissions separately. The proposed experiment uses a 90% family-level recall bar.

## 2. What the small structure should represent

**UNTESTED — Proposed design:** Use a compact **assertion graph**: a record of which words name entities, which entities form groups, which predicate applies to which arguments, and what scope or reference decision each assertion depends on. Its minimum contents should be:

- **Mentions and groups:** unchanged source spans; group members; `AND` versus alternatives such as `OR`.
- **Assertions:** relation-table identifier, argument links, evidence spans, and assertion status such as direct statement, question, hypothetical or unresolved.
- **Reference and edit links:** what “he,” “who,” or “whose” refers to; which additions and removals belong to the same correction.

**UNTESTED:** Assertion status belongs at the assertion level, not only the turn level. For example, “Nell is my neighbour; where does she work?” contains both teaching and asking. A single nine-way turn label is insufficient unless it can preserve such mixtures.

### Coordination: distribute only a licensed argument

**UNTESTED — Proposed interpretation:** For “Mira and Tal are my sisters,” the structure should identify one relation, one owner supplied by “my,” and a value group containing the two name spans. Code can then produce:

`me | sister | Mira`  
`me | sister | Tal`

For “my sisters are Mira, Tal and June,” it produces three candidates. It should not generate extra sibling relationships among the named people or conclude that no other sisters exist.

**UNTESTED:** The permission to expand should depend on the **predicate meaning, coordinated argument and scope**, not merely the presence of “and.” Similarly, two lists linked by “respectively” require aligned pairs, not every possible owner–value combination.

**SHOWN — Published documentation:** Enhanced Universal Dependencies explicitly propagates grammatical links to coordinated subjects and objects. Its documentation also warns that this produces unusual links for collective predicates and deliberately does not resolve the context-dependent distributive/collective distinction. Therefore, dependency links alone are not semantic permission to write separate facts. 

### Collective readings: preserve what the notebook would otherwise lose

**UNTESTED — Proposed policy:** “Mira and Tal own a bakery” should not automatically become two unqualified ownership facts. Joint ownership can support each person being a **co-owner**; it does not establish two separate bakeries or either person’s sole ownership.

**UNTESTED:** Whether two notebook rows are valid depends on the defined meaning of `owns` and whether both rows can refer to the same bakery. An unnamed “a bakery” also needs entity identity, rather than being treated as a reusable proper name. Until that meaning is representable, keep the joint assertion pending and ask a targeted question. Do not invent a group owner or a new relation-table meaning just to make the triples fit.

**UNTESTED:** “Our/we” remains an unresolved group under the owner’s rule. An explicit list of people does not authorize treating an unrelated “our” as “me.”

### Appositives: identity links, not comma splitting

**UNTESTED — Proposed interpretation:** In “Nell, my neighbour, works at Tolby Mill,” link “my neighbour” to **Nell**. The resulting supported candidates are the neighbour fact and Nell’s workplace fact. The commas mark the construction; they are not themselves fact boundaries.

**UNTESTED:** Conversely, a company name such as “Tolby, Lane & Co.” can occupy one value span despite containing punctuation. Replace the eventual blanket punctuation prohibition with validation of the identified span and construction. Do not simply remove the prohibition before the reader can distinguish these cases.

**UNTESTED:** Define the annotation policy separately for appositives inside questions, quotations and hypothetical passages. Do not silently assume that every side statement inherits the status of the whole turn.

### Relative clauses: bind the relative expression to its head

**UNTESTED — Proposed interpretation:** In “Nell, whose dog is Pip, works at Tolby Mill,” “whose” refers to Nell, yielding Nell’s dog and workplace facts. In a relative clause, the reader should identify that reference explicitly rather than choose whichever name is nearest to the predicate.

**SHOWN — Published documentation:** Enhanced Universal Dependencies represents relative-clause reference with an explicit link from the relative expression to its antecedent, plus the corresponding predicate–argument connection. That is a useful representational precedent, not a guarantee that a learned parser will predict the links correctly. 

**UNTESTED:** Also train the contrasting scope: “I need a neighbour who works at Tolby Mill” must not create a particular neighbour or assert that somebody already satisfies the description.

### Pronouns: keep a reference decision visible—and allow uncertainty

**UNTESTED — Proposed policy:** For the Ada/Bo example, require an explicit link from “he” to Bo before permitting the residence candidate; otherwise defer the residence claim. Do not resolve to the first name, the nearest name, or the person whose name seems most associated with a gender.

**UNTESTED:** The supplied sentence strongly invites the Bo reading, but a name alone does not establish Ada’s pronouns or rule out every alternative discourse interpretation. Gold labels must distinguish genuinely disambiguated examples from examples where the writer merely intended one reading. A reader receiving only one turn also cannot recover missing earlier discourse.

**SUGGESTED — Different setting:** *Mind the GAP*, **arXiv:1810.05201**, evaluates ambiguous pronoun resolution and explicitly accommodates candidates to which the pronoun does not refer. Its discussion supports evaluating reference resolution separately instead of assuming strong overall extraction scores imply reliable pronoun handling. It does not validate any particular threshold for this assistant. 

**UNTESTED:** Finally, “moved to” is partly a temporal-semantics problem, not a coordination problem. “Moved to Rook in 2018” does not by itself establish present residence. An alias change must not silently turn historical movement into current location.

## 3. Partial writes: eventually yes, but not independently per frame

**UNTESTED — Recommendation:** The eventual policy should be **atomic by semantic dependency and correction scope**, rather than always atomic by turn or always independent by frame.

**UNTESTED:** First read the complete turn into pending assertions and edits. Then identify which proposed changes depend on the same unresolved decision. Commit an independently supported component only when the unreadable remainder cannot change its owner, meaning, assertion status or correction scope. Merely sharing an owner does not make two facts inseparable.

**UNTESTED:** For example, an unreadable second assertion should not necessarily prevent saving a clearly stated workplace fact. But an unfinished “actually, not…” can potentially revise an earlier assertion; in that case, defer the affected component. When the scope of the correction itself is unresolved, retaining whole-turn atomicity is the safer fallback.

**UNTESTED — Correction policy:** Treat “replace Tal with June in my sisters” as one operation containing the removal and addition. Never apply one half alone. Preserve unrelated sister entries. Likewise, a newly stated list should not implicitly delete previously taught members unless the turn clearly requests or asserts a complete replacement under the notebook’s registered update policy.

**UNTESTED:** Self-corrections must be interpreted before any write occurs. In “Mira and Tal are my sisters—sorry, not Tal; June,” committing while reading left to right would expose a fact that the same turn retracts.

**UNTESTED:** Partial-write acknowledgements must come from the actual transaction receipt: what was saved, what remained pending, and what needs clarification. They must not say “saved everything” after a partial commit.

**UNTESTED:** Do **not** introduce this policy in the next experiment. It changes the safety boundary and would make it harder to determine whether coordination reading itself improved.

## 4. Ranked options

**1. UNTESTED — Guarded coordination constructor, next.**  
Fixes missing members of explicit, distributive relative-name lists. It requires one bounded reader/expander module and no training or model download. It cannot fix general pronouns, appositives, temporal meaning or arbitrary wording. More recovered candidates may increase gate latency.

**2. UNTESTED — Own ear with the compact assertion graph, later.**  
Makes group membership, argument binding, scope and edit dependencies explicit. It costs richer annotation, new prediction targets and compiler checks. It cannot eliminate semantic ambiguity or make incorrect graph predictions safe merely by being structured.

**3. UNTESTED — Keep flat set slots, improve supervision.**  
Use unordered matching, full-set targets and contrastive examples. This is a simpler rival and may learn the required distinctions without explicit group nodes. It still has the slot-cap problem and leaves reference and correction dependencies harder to inspect.

**4. UNTESTED — Dependency-scoped partial commits, after scope reading is tested.**  
Recovers clear assertions from partly unreadable turns. It costs transaction grouping, correction tests and accurate receipts. It cannot repair a wrong owner or a mistaken decision that two assertions are independent.

## 5. Training data that tests composition rather than name replacement

**UNTESTED — Recommendation:** Generate training examples from **verified meaning structures**, not only sentence templates. Each example should specify the intended entities, group memberships, reference links, assertion scope and—for corrections—the notebook before and after the turn.

**UNTESTED:** Have a separate realizer express that structure in varied language. A large model’s generated wording is permissible under your rules, but a second annotation pass must check the resulting text without assuming it preserved the intended meaning. A fluent paraphrase that changes scope must receive corrected labels or be rejected before training.

**UNTESTED:** Cover the following contrasts in combination, not just separately:

| Training dimension | Required contrasts |
|---|---|
| Enumeration | Two through more-than-six facts; reversed name order; owner-first and name-first wording; repeated versus shared predicates |
| Group meaning | `and` versus `or`; explicit `each`; joint action; `respectively`; one entity with several descriptions versus several entities |
| Reference | Named subject, appositive, relative subject/object, possessive `whose`, singular/group pronouns, unresolved antecedents |
| Scope and edits | Statement versus check-question; quotation/pretend; negation; mixed teaching and asking; addition versus replacement; readable and unreadable corrections |

**UNTESTED:** Randomize fictional names across grammatical roles, and include lower-case and punctuation variation without silently “repairing” the source. Train ambiguous cases as ambiguous—not with an arbitrary single antecedent chosen because the generator intended it.

**SUGGESTED — Different setting:** COGS, **arXiv:2010.05465**, tests new combinations of familiar words and structures and reports a large gap between ordinary test performance and compositional generalization. This supports holding out **structural combinations**, not merely names or random rows. For example, training separately on coordination and relative clauses should not count as testing their combination. 

**SUGGESTED — Different setting:** HANS, **arXiv:1902.01007**, demonstrates failures of word-overlap, subsequence and constituent-based entailment shortcuts. Use its methodological lesson: include examples where the same names and relation words occur but the owner, scope or supported fact set changes. Do not use substring presence as the semantic label. 

**UNTESTED:** No dataset construction can promise “no template memorization.” The evidence must come from independently written wording and held-out combinations. Keep all such registered test items outside training, including later training.

## 6. The one experiment to run next

### Change and hypothesis

**UNTESTED — Experiment name:** **Explicit relative-list construction versus the current ear.**

**UNTESTED — Named base:** Freeze the current ear v4.1, canonicaliser, brake, YES/NO gate with threshold 0.25, notebook, commit policy and mouth. Record their exact hashes rather than referring to “latest.”

**UNTESTED — Single intervention:** Add one guarded reader module before the ear. It handles explicit lists with one identifiable owner, one supported multi-valued person relation and named members.

**UNTESTED — Module contract:** For an unambiguous complete parse in its registered fragment, it builds a source-span group and expands it to ordinary TEACH candidates. These pass through the **unchanged brake and gate using the original, unchanged turn**. It does not paraphrase the turn or ask the gate to validate rewritten evidence.

**UNTESTED:** Within the module’s declared family, incomplete or unsafe parses defer rather than falling through to the old ear and accidentally recovering an unsafe write. Outside its declared family, execution remains exactly the base path. Freeze the routing definition, accepted constructions and relation whitelist before testing.

**UNTESTED:** This is one bounded reader change. It introduces no new weights, normalizer, gate prompt, threshold or partial-write policy. Its internal group structure need not change the existing notebook or external frame format.

**SUGGESTED — Different setting:** CALM/CALMIE, *Open Information Extraction from Conjunctive Sentences*, reports improved extraction yield from coordination-aware decomposition. That supports testing a coordination-specific intervention, but not assuming the reported gains transfer here. I checked the paper’s method text; I do not know a verified arXiv ID for it. Its verified identifier is **ACL Anthology C18-1194**. 

### Fixed panel: 500 turns

**UNTESTED — Proposed registration:**

| Stratum | Exact size | Purpose |
|---|---:|---|
| Positive relative lists | **300** | 100 turns containing exactly two target facts, 100 containing three, and 100 containing four: **900 target facts** |
| Boundary cases | **150** | 25 each covering check-questions; negation/disjunction; quotation/pretend/hypothetical scope; collective/group-owner traps; punctuation/attachment traps; corrections |
| Ordinary single-fact controls | **50** | Detect regressions outside list reading |

**UNTESTED:** The positive spec should describe the semantic family, not require the writer to use the implementation’s two favourite sentence patterns. Balance owner-first/name-first wording, relation aliases, name positions and ordinary typing variation. Unsupported but plainly stated positive examples remain misses; do not remove them after seeing the parser’s coverage.

**UNTESTED:** Boundary cases need full gold fact sets and, where relevant, before/after notebook states. Some will contain genuine assertions. **Do not label all boundary cases NONE for convenience.** Their omissions remain visible in the report even though this experiment’s primary recall endpoint is the explicit-list family.

**UNTESTED:** Before either system runs, an independent agent should label the texts without seeing the writer’s answers. Resolve disagreements against the registered annotation policy and seal the resulting keys. No builder sees test items before the registered verdict.

### Fixed pass marks—all must pass

**UNTESTED — Proposed registration:**

| Endpoint | Required result |
|---|---|
| Wrong final saves | **0 across all 500 turns** |
| Incorrect deletions or replacements | **0** |
| Positive-list exact fact recall | **At least 810/900**, or **90%** |
| Complete positive turns | **At least 270/300**, with **at least 88/100 in each list-length stratum** |
| Improvement over the named base | **At least 60 additional fully correct positive turns**, a **20-percentage-point** gain |
| Single-fact control recall | **At least 45/50**, and **no lower than the base** |
| Grammar | **At least 495/500 replies grammatical** |
| Unsupported acknowledgement or self-claim | **0** |
| Median complete turn time | **At most 800 ms**, both on the 300 positives and on all 500 turns |

**UNTESTED:** Measure the complete path—reading, all gate calls, commit and reply—on the target machine under a frozen timing protocol. Interleave base and candidate runs, fix decoding settings, and report cold-start behaviour separately. Increased gate workload is part of the intervention’s cost, not something to subtract.

**UNTESTED:** A shared baseline error still makes the candidate’s registered safety result FAIL. Stage attribution may explain that failure; it must not rescue the verdict.

### Why this size—and what it does not certify

**UNTESTED:** Three hundred positive turns provide 100 cases at each length, so success on pairs cannot hide failure on four-member lists. The paired 60-turn improvement requirement asks for a substantial effect, rather than another encouraging result from a handful of examples. The 150 boundary cases test whether expansion creates new unsafe interpretations.

**SHOWN — Statistical method:** Exact binomial confidence bounds require a defined trial and sampling model; they are obtained by inverting binomial probabilities. 

**UNTESTED — Calculation under an explicit independence assumption:** Zero errors in 300 independent, identically distributed turns would give a one-sided 95% upper bound of

\[
1-0.05^{1/300}=0.9936\%
\]

for the chosen **turn-level** error event. But 900 facts from those turns are not 900 independent trials, and a deliberately stratified agent-written panel does not automatically represent deployment. **This experiment is not the final “wrong saves below 1%” certificate.**

### Verification and falsification

**UNTESTED — Separate verification sample:** Pre-register **30 additional untouched director probes**: 18 positive turns, six at each list length, giving 54 facts; and 12 boundary cases. Require zero wrong changes, at least **16/18** complete positive turns, at least **48/54** correctly saved positive facts, zero unsupported reply claims and median time at most 800 ms. This verifies a registered pass; it cannot convert a failure into one.

**UNTESTED — Results that would reject the recommendation:** A newly introduced wrong owner/member or unsafe expansion directly falsifies the safety case for this constructor. Failure to reach the recall and paired-improvement bars rejects its practical payoff. Correct expanded candidates that the unchanged gate mostly blocks would show that candidate construction is not enough in the current pipeline. Exceeding 800 ms rejects it as a deployable improvement even if extraction improves.

**UNTESTED — Later step, separate:** Only after this test should the own ear be trained to predict the group structure. That would test whether a learned reader can replace the bounded hand-written recognizer. Partial commits remain a separate intervention.

## 7. Strongest objection and the rejected rival

**UNTESTED — Strongest objection:** This recommendation adds another hand-written reading stage to a system already suffering from accumulated special cases. A narrow grammar can look reliable by refusing wording it does not cover—the same general concern raised by the 67.6% oracle writability result. That is why the test must include independently worded positives, count uncovered wording as missed recall, and require a substantial gain.

**UNTESTED — Rival:** Option 3—training the flat reader on complete sets and carefully designed contrasts—may ultimately be better. Your current evidence does not prove explicit group nodes outperform it. I rank the constructor first because it isolates a concrete failure with no training expense and a visible safety boundary. A PASS would demonstrate an **engineered front-end improvement**, not that your own learned architecture beats an equal-size transformer.

## Plain-language summary

**SHOWN:** Your reader found only four of sixteen facts in the relative-name sample.  
**UNTESTED:** The next test should teach the pipeline to recognize a whole list before producing separate notebook entries.  
**UNTESTED:** Code should expand that list only when the sentence clearly applies the relationship to every named person.  
**UNTESTED:** It must not assume that doing or owning something together means doing or owning it separately.  
**UNTESTED:** Pronouns and descriptions need explicit links to the right person, rather than guesses based on name position.  
**UNTESTED:** Keep all-or-nothing saving for this test, because safe partial saving also requires understanding corrections.  
**UNTESTED:** Test 500 turns with fixed safety, recall and speed requirements, followed by 30 untouched verification probes.  
**UNTESTED:** Passing would justify this one improvement, not prove that the whole assistant is already below a 1% wrong-save rate.

## Answer to question 8: An own mouth that is fluent, faithful and 99% grammatical at about 30M parameters
(message cmsg_01FuvegZXjMmeUzStiEFVnEWSfrfcsuyCZsANxJ1xuMBGx, 2026-09-23T10:22:04Z)

## Recommendation

**UNTESTED — recommendation:** Use the own model to **choose among ways of expressing an already-fixed meaning**, while a small grammar-and-slot renderer remains responsible for the actual sentence. Do not give the model unrestricted control over names, relationships, negation, or claims that something was saved.

Start with the smallest useful version: **replace only the existing small-talk reply chooser with an own-weight learned chooser, keeping the existing reply inventory and factual mouth unchanged.** That tests whether learning adds conversational value without simultaneously rebuilding the part that already works.

**SUGGESTED — feasibility:** A roughly 30M model is plausibly sufficient for this constrained job. TinyStories and SimpleStories support the broader possibility of useful English generation at small sizes, but their story evaluations do **not** establish 99% error-free assistant replies or perfect record faithfulness. In particular, a high numerical grammar rating is not the percentage of outputs containing no grammatical errors. Relevant papers: **arXiv:2305.07759** and **arXiv:2504.09184**. 

The labels below distinguish your measurements or directly reported research (**SHOWN**), transfer from another research setting (**SUGGESTED**), and proposals or deductions not tested on Premonition (**UNTESTED**).

## 1. Diagnosis: several different failures are being grouped together

### BLiMP failure is not a measured 32.6% reply-grammar failure

**SHOWN:** BLiMP measures whether a model assigns greater probability to the acceptable sentence in a minimal pair. It is not an evaluation of the fraction of freely generated assistant replies that are grammatical. The benchmark paper is **arXiv:1912.00582**. 

**UNTESTED — interpretation:** talker101’s registered FAIL should remain FAIL, but the conclusion is narrow: it failed your chosen BLiMP-10 threshold. That does not establish that 30M parameters cannot support your mouth, or that increasing the model is the best next intervention. Passing story validation loss also does not establish competence at expressing reply records.

### The brake result does not establish a faithful learned generator

**SHOWN:** You measured 172 unfaithful replies out of 500 before the brake and zero afterward. You also identified name truncation caused by copying word pieces. 

**UNTESTED — interpretation:** That is evidence about the **combined generator-plus-brake**, not about an intrinsically faithful generator. I do not know how many outputs the brake replaced, refused, shortened, or otherwise changed. Without those counts, the result cannot establish that it preserved useful answer coverage.

**UNTESTED — diagnosis:** Whole-name copying addresses a real defect, but not the entire faithfulness problem. Both of these sentences contain exactly the same names and relation word:

> Farah’s dog is Pip.  
> Pip’s dog is Farah.

Only one follows from `Farah | dog | Pip`. Similar failures can preserve every name while adding “not,” changing a number’s unit, or saying “I saved that” when no save occurred. **A name whitelist is not a meaning-preservation rule.**

### Raw relation labels are not primarily a model-capacity problem

**SHOWN:** The hand mouth sometimes prints internal labels; the supplied report also records ten grammar failures among 1,205 replies. It does not identify those ten failures individually or establish that label leakage explains all of them. 

**UNTESTED — diagnosis:** The immediate remedy for label leakage is a reviewed mapping from relation meanings to English constructions. But a label such as “religion or worldview” cannot safely be shortened to “religion” unless that narrower meaning is actually justified. Some awkward labels may reveal an ambiguous relation definition, not merely ugly wording.

### Existing small-talk results establish only limited coverage

**SHOWN:** Fixed replies fit 31 of 35 greeting/closing items. 

**UNTESTED — interpretation:** That does not establish coverage of ordinary social conversation. It also does not tell us whether the four failures came from choosing the wrong available reply or having no suitable reply available. That distinction should drive the next experiment.

### “99.2% observed” is not yet “at least 99% certified”

**SHOWN — statistical method; calculation from your counts:** Under an ordinary independent-binomial model with correct labels, ten errors in 1,205 outputs gives a one-sided 95% upper error bound of approximately **1.404%**. Thus, the corresponding lower grammaticality bound is about **98.596%**, despite the observed rate being 99.17%. This calculation uses exact binomial interval inversion; clustering and grading errors introduce additional issues. 

**UNTESTED — implication:** Keep the excellent observed result, but distinguish it from the stronger certification claim.

## 2. Ranked options

The rankings and cost judgments are **UNTESTED recommendations**.

| Rank | Option | What it fixes | What it costs | What it cannot fix |
|---|---|---|---|---|
| **1** | **Learned choice over meaning-checked grammar constructions, with whole-value insertion** | Prevents free generation of corrupted names or unauthorized relationships; learns wording choice and conversational fit | Reviewing constructions, specifying their conditions, and training a chooser | Cannot express something absent from its permitted constructions; cannot repair an incorrect record |
| **2** | **Plan-then-realise neural decoder, with whole-value placeholders and coverage constraints** | Separates content from wording; prevents partial-name generation; permits substantially more linguistic variety | Record-to-text training, a constrained decoder, and extensive semantic evaluation | Copying and coverage alone do not prevent negation, role reversal, or misleading connective words |
| **3** | **Free-form distilled decoder plus a brake** | Offers the greatest wording freedom, including small talk | Clean paraphrase data, a sufficiently reliable checker, fallback handling, and potentially extra latency | Does not make faithfulness structural; can hide failures by replacing useful answers with generic safe text |

**SUGGESTED — support for option 1:** *Learning Neural Templates for Text Generation*, **arXiv:1808.10122**, demonstrates useful controllable template structures. However, its learned templates are not the same as a reviewed, meaning-preserving grammar: its examples still include problematic realizations. It supports investigating controllable generation, not claiming that “templates learned by a neural network” automatically guarantee faithfulness. 

**SUGGESTED — support for option 2:** *Step-by-Step: Separating Planning from Realization in Neural Data-to-Text Generation*, **arXiv:1904.03396**, found better semantic faithfulness from explicit planning, but remaining realization errors. It also replaced entities with unique tokens and restored their full strings afterward—directly relevant to your name-copying defect. 

**UNTESTED — important distinction:** Distillation is a training method, not a separate safety mechanism. It can help train either option 1 or option 2. Learning from correct examples does not, by itself, make incorrect outputs impossible.

Keeping the hand factual mouth and learning only the small-talk chooser is the first deployment stage of option 1, rather than a fourth competing architecture.

## 3. The recommended architecture

### Separate meaning decisions from wording decisions

**UNTESTED — design:** The reasoner’s reply record should determine the answer’s meaning. The mouth may choose sentence structure, a permitted paraphrase, and suitable social wording. It must not independently decide what happened in the notebook.

For record \(R\), define:

\[
\text{RequiredClaims}(R)
\subseteq
\text{ClaimsExpressed}(y)
\subseteq
\text{AllowedClaims}(R).
\]

Here, \(y\) is the final reply. “Required” means the answer essentials—not necessarily every supporting notebook row. “Allowed” includes the authorized answer, permitted supporting facts, and authorized status/self-description statements.

This prevents two different failures: inventing content and avoiding the task by saying something harmless but unhelpful.

### Let the model choose constructions, not arbitrary strings

**UNTESTED — design:** The model selects a construction identifier and, where permitted, an ordering of already-authorized clauses. A deterministic renderer supplies the final text.

For example, an authorized construction might have the form:

> `[OWNER]’s dog is [VALUE].`

Its definition includes the relation, the owner/value binding, and any grammatical conditions. The model cannot select that construction for a workplace fact or interchange the slots.

For longer answers, use a sequence of such checked clauses. Do not assume that arbitrary combinations of individually safe fragments remain safe: clause joining and pronouns require their own conditions.

### Whole values should be opaque to output generation

**UNTESTED — design:** Represent names and other literal values with placeholders such as `<ENTITY_0>`. After selecting the construction, insert the corresponding complete record string.

That does **not** require a permanent vocabulary entry for every possible name. The placeholder identifies a value in this particular record.

Preserve internal spelling, spaces, hyphens, and punctuation. Treat slot contents as data, not executable instructions or template syntax. Possessive punctuation and sentence punctuation belong to the renderer, outside the stored name.

### Status claims need status evidence

**UNTESTED — design:** A save confirmation must be licensed by a completed-save status, not merely by the user requesting a save. If your current `confirm-save` act already means “the notebook commit succeeded,” it can provide that license. The supplied description does not establish its implementation semantics.

The same principle applies to “I remember,” “I checked,” and capability claims. Use your existing fixed honest texts where they supply the appropriate statement; do not let a small-talk decoder invent autobiography or capabilities.

### Small talk needs restrictions on implied claims, too

**UNTESTED — design:** Greetings, thanks, and closings need not contain notebook facts to be legitimate. The requirement should be that **every factual assertion is authorized**, not that every word occurs in a notebook row.

Nevertheless, reviewed social phrases need conditions. “Welcome back” presupposes a previous interaction. “I’ll remember that” makes a commitment. “I had a busy day” invents an experience. A pleasant-sounding phrase is not automatically safe in every context.

### What is actually guaranteed?

**UNTESTED — conditional guarantee:** If the construction meanings are correct, their applicability conditions are sound, and slot binding/rendering is correct, then restricting the model to those constructions prevents it from departing from the authorized meaning.

Those are substantive assumptions—not a proof that the current implementation satisfies them. The grammar, conditions, and renderer form the **trusted part of the system** and need independent review.

Also, faithfulness to a record is not proof that the record accurately reflects the user or the outside world.

## 4. Training plan

**UNTESTED — proposal:** Reuse the owner-trained talker101 checkpoint instead of starting another general-language pretraining run. Add a small choice head that scores permitted construction or reply identifiers. Freeze the output inventory for each experiment.

The useful training example is:

> conversation context + reply record → suitable permitted choices

It is not merely another story or a sentence whose relation to the record is unknown.

**UNTESTED — data construction:** Use the hand layer to generate initial realizations. Have a separate agent propose paraphrases, then review each proposed construction’s grammar, meaning, and applicability conditions before admitting it. Teacher-generated text is a candidate training source, not an authority on correctness.

When several choices are equally suitable, label all of them as acceptable. One possible loss is:

\[
\mathcal L=-\log\sum_{t\in A}p_\theta(t\mid R,c),
\]

where \(A\) is the acceptable-choice set and \(c\) is conversational context. This penalizes putting probability on unsuitable choices without pretending there is only one correct sentence.

**UNTESTED — generalization tests:** Hold out conversational wording families and combinations of known relations, not merely different names. Separately test complete-string rendering with unfamiliar fictional names and awkward punctuation. Because placeholders hide name spelling from the chooser, a new-name split alone would be a weak language-generalization test.

**SUGGESTED — parameter accounting:** Count embeddings and all other unique parameters. SimpleStories explicitly discusses the misleading comparisons that arise when some reported model sizes exclude embeddings. Its **arXiv:2504.09184** is useful here; do not assume that a model called “33M” necessarily has 33M total parameters. 

**UNTESTED — resource estimate:** At the reported 28.85M parameters, BF16 weights occupy approximately:

\[
28.85\times10^6\times2=57.7\text{ MB}.
\]

Under an assumed training-state allowance of 16 bytes per parameter, parameters, gradients, and optimizer-related state would total about **461.6 MB**, before activations, workspaces, and framework overhead. These are accounting estimates, not measured peak memory.

Use existing own weights and existing permitted agents; allocate no new model download or cloud rental to this first test. Do not assume the large borrowed gate and training job can share the GPU. Measure deployment latency in the actual intended placement.

## 5. The ONE experiment to run next

### Experiment: learned small-talk selection, unchanged available replies

**UNTESTED — preregistered hypothesis:** Most remaining errors in the bounded small-talk task come from choosing an unsuitable available response, rather than needing unrestricted text generation.

This is deliberately narrower than replacing the whole mouth.

### Base and single change

**UNTESTED — protocol:**

**Base B0:** The SHA-256-sealed current system: present hand factual mouth, present small-talk reply inventory, and present small-talk selection rules.

**Treatment T1:** Replace **only the small-talk selection function** with the own-weight learned chooser.

Both arms receive the same available context and use exactly the same response inventory. The treatment returns an identifier; the existing string is emitted unchanged. All non-small-talk routing, factual wording, notebook behavior, and fixed honest texts remain unchanged.

**Do not add better replies to T1’s inventory, repair relation labels, or modify the ear in this experiment.** Those would confound the comparison.

The report must first enumerate the actual inventory. The measured “31 of 35 items” is not a count of available templates.

### Training specification

**UNTESTED — proposed fixed recipe:** Use **6,000 new training contexts and 600 development contexts**, with acceptable existing reply identifiers independently checked. Use no burned panel items.

Fine-tune the own checkpoint for **two epochs**, with a maximum input length of **128 tokens**, effective batch size **64**, and learning rate **\(10^{-4}\)**. These are proposed starting settings, not published optimal settings for Premonition.

Before the registered run, seal the exact architecture, optimizer details, training data, final checkpoint, inventory, decoder, grading prompts, and decision rule. Do not select another checkpoint after seeing test results.

### Test sample

**UNTESTED — protocol:** Use **600 fresh, independent small-talk contexts**, one scored response per context per arm. Freeze the sampling specification before writing the panel. Cover greetings, closings, thanks, re-entry into a conversation, brief social exchanges, and boundaries involving questions about the assistant itself.

Use new wording from writers who did not produce training examples. Do not manufacture an apparent sample of 600 by changing names in a handful of underlying conversations.

Add **200 fresh non-small-talk regression records**: 40 each for answer, abstain, confirm-save, decline, and clarify. These check that the supposedly unchanged paths really remain unchanged.

### Exact pass marks

All thresholds below are **UNTESTED proposed acceptance criteria**.

| Endpoint | Required result |
|---|---|
| **Faithfulness and self-description** | **0/600** unsupported factual, notebook-status, or self-description claims |
| **Grammar** | **0/600** grammatical failures under the frozen grading protocol |
| **Contextual appropriateness** | At least **570/600** replies appropriate to the context |
| **Preference over B0** | \(W-L\ge30\), **and** a one-sided exact sign test on decisive pairs gives \(p\le0.05\) |
| **Output restriction** | **600/600** treatment outputs exactly match an allowed existing response after any already-existing authorized insertion |
| **Unchanged factual paths** | **200/200** regression outputs byte-identical between B0 and T1 |
| **Latency** | Median full small-talk turn time **≤800 ms**, and median added chooser overhead **≤100 ms** |

For preference, \(W\) and \(L\) are treatment wins and losses after the frozen judging procedure. Identical responses are ties. An irrelevant generic reply cannot pass appropriateness merely because it is grammatical and safe.

Full-turn timing must include the unchanged upstream processing and actual deployment behavior—not just a cached-record mouth benchmark. Record cold-start behavior separately rather than silently excluding it from the report.

### Why 600?

**SHOWN — statistical method; calculated application:** With zero observed errors in 600 independent trials, the one-sided 95% binomial upper error bound is:

\[
1-0.05^{1/600}\approx0.004980,
\]

or **0.498%**. For comparison, 299 zero-error trials just barely put that bound below 1%. 

**UNTESTED — design rationale:** Six hundred gives more margin and a broader contextual test than the minimum zero-error sample. It is not a promise of a particular statistical power for the paired preference comparison; that depends on the unknown number of discordant pairs.

The interval remains conditional on the sampling and grading assumptions. This experiment would not certify the entire factual mouth or general English generation.

### The decisive diagnosis: catalogue ceiling versus chooser failure

**UNTESTED — protocol:** After outputs are locked, have evaluators determine whether **any** response in the unchanged inventory would have been appropriate for each context. This is an inventory-coverage diagnosis, not a second trained treatment.

The results that would reject my recommendation are:

- **Fewer than 570 contexts have any suitable inventory response:** the fixed-inventory approach cannot meet this experiment’s appropriateness target, regardless of model size or training.
- **The inventory covers at least 570, but T1 misses the target or the preference threshold:** the learned chooser has not justified replacing the rules.
- **An unsupported claim passes through the permitted inventory:** the supposed safety conditions are incomplete; restricting output to that inventory is not enough.
- **Latency fails:** the implementation is not an acceptable deployment improvement.

A registered FAIL remains FAIL. The diagnosis selects the one permitted follow-up; it does not authorize repeated adjustment against this panel.

**UNTESTED — later step, separate experiment:** Only after a PASS, test extending learned choice to factual grammar variants with whole-value insertion. Do not treat the small-talk result as evidence that this later system already works.

## 6. How AI graders should assess grammar

### Use separate judgments for separate properties

**UNTESTED — protocol:** Ask for a binary grammar judgment, not a broad “quality” score. For every alleged grammar error, require the affected span, error category, and minimal grammatical correction.

Grade contextual appropriateness separately. A fluent “Goodbye” can be wrong after a greeting without being ungrammatical. Likewise, define beforehand whether conversational fragments such as “You’re welcome” are acceptable; do not let graders invent different standards.

Check exact-name preservation and output-inventory membership mechanically. Do not spend a probabilistic judge on properties that exact comparison can establish.

### Calibrate with both errors and acceptable sentences

**SHOWN:** Your graders each caught at least 38 of 40 planted mistakes. 

**UNTESTED — interpretation:** That is useful evidence, but it does not measure how often they falsely reject grammatical replies or miss the particular errors your mouth makes. Two agents can also share the same blind spots.

**UNTESTED — proposed calibration gate:** Before the registered panel is graded, test the judging process on **100 independently checked corrupted sentences and 100 acceptable controls**. Include errors close to this mouth’s actual risks, rather than only conspicuous nonsense. Require each judge to identify at least **98/100** corrupted items and accept at least **98/100** controls.

Seal how disagreements are resolved. Use a separate adjudicating agent for flagged cases; unresolved cases count as failures. A failed calibration prevents a grammar-certification claim—it is not a reason to loosen the threshold after seeing treatment outputs.

These 200 calibration items are not additional model test trials.

### Blind preference judgments and control presentation order

**SHOWN:** *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*, **arXiv:2306.05685**, documents position and verbosity biases. *No Free Labels*, **arXiv:2503.05061**, finds that strong aggregate judge performance can conceal systematic failures and that reference quality matters. These studies are not specific validations of your grammar judges. 

**UNTESTED — protocol:** Hide system identities, show both response orders, and use separately prompted judges. Count a treatment win or loss only when the prescribed judgments agree across orders; otherwise record a tie. Multiple votes on one conversation are still **one evaluated conversation**, not additional independent samples.

For semantic grading, provide the actual reply record and authorized claims. Do not use a sentence produced by the candidate mouth as its own gold reference.

### Be precise about what an all-AI evaluation establishes

**UNTESTED — limitation:** Under the stated all-AI workflow, the defensible claim is “passed this frozen, calibrated evaluation protocol,” with explicit uncertainty about undetected errors. Agreement among agents is not independent proof of English correctness.

For a finite grammar, auditing its constructions and composition rules can supplement sampled grading. It still does not turn an AI-approved phrase inventory into an unconditional proof that every possible rendered sentence is grammatical and faithful.

## 7. Strongest objection, rejected rival, and the 30M question

**UNTESTED — strongest objection:** My recommendation may put most of the linguistic competence in the hand-written grammar and give the neural model only the comparatively small task of choosing among options. That could be a good assistant while being a less impressive learned language model.

That distinction must remain visible in the research claim: **“an own-weight hybrid mouth with constrained realization” is not “a 30M decoder independently learned 99% reliable English.”** A much smaller chooser might eventually perform equally well; there is no reason to pad it to 30M.

**UNTESTED — rejected rival:** The strongest rival is a genuinely learned plan-to-text realizer with whole-value placeholders, trained on reviewed paraphrases. I rank it second because it better addresses rigidity and phrase diversity. I would not deploy it first because exact copying still leaves the connective language free to alter meaning, and your current raw generator has substantial measured faithfulness problems. 

**UNTESTED — what would show 30M is insufficient:** One failed BLiMP threshold or one failed fine-tune cannot establish a parameter ceiling. Stronger evidence would be a well-specified task where clean-data learning curves flatten across the allowed training budget, while a larger own-trained control succeeds under otherwise matched conditions. Even that would establish a limit for the tested approach and budget, not every possible 30M architecture.

For the recommended constrained system, the sharper impossibility result is often simpler: **when the permitted output space contains no satisfactory reply, more parameters cannot help.**

## Plain-language summary

**SHOWN:** Your hand-written mouth already has a strong observed grammar result, while the learned mouth produced many unfaithful replies before its brake. The name-cutting problem is real, but fixing names alone would not fix every kind of wrong answer. 

**UNTESTED — recommendation:** Keep the reliable sentence-building code and teach your own model to choose suitable wording. Make it insert complete names and values rather than generate their pieces. Test this first on small talk, without changing which replies are available. Require it to improve conversational fit while producing no observed grammar or truthfulness errors. When it fails, check whether it chose badly or whether no available reply could have worked. A 30M model may be enough for this job, but the honest claim would be about the combined learned-and-rule-based system, not a completely free-writing model.

## Answer to question 9: Corrections, retractions and facts that change over time
(message cmsg_01FuvegZXjMmeUzStiEFVnEWDruFYDhhnE3CajBXi2zsYo, 2026-09-23T10:21:57Z)

## Recommendation

**UNTESTED:** Give Premonition a small, explicit **edit language**, backed by a history of notebook changes. An edit should identify **what the user asserted, which existing record it affects, and whether it describes a correction, a real-world change, or a withdrawal**. The compiler should apply the complete edit atomically—or change nothing.

**UNTESTED:** The next experiment should test that storage contract with perfectly interpreted inputs. Only afterward should you test an English reader that proposes edits. Otherwise, a parser mistake and a destructive storage mistake can look identical.

Here, **SHOWN** identifies supplied measurements or published findings; **SUGGESTED** identifies published approaches being transferred from another setting; **UNTESTED** identifies my proposed rules, predictions, and pass marks.

## 1. Diagnosis: several different operations currently look like “replace a value”

### The measured correction results do not yet establish safe updates

**SHOWN:** The correction piece achieved 54/80, with no reported false claims or junk writes. The fresh 96-item result came from a different base, without those pieces merged. Those are not a controlled before-and-after comparison. Also, “zero junk writes” and “zero false claims” do not, by themselves, establish zero well-formed but incorrect notebook values. Your report does not provide that missing breakdown for the 80-item panel. 

**UNTESTED:** Adding `DENY` frames is useful but incomplete. These three messages require different histories:

> “I was wrong: Ada lives in Tolby, not Rook.”  
> “Ada moved from Rook to Tolby.”  
> “Withdraw what I said about Ada living in Rook.”

The first corrects a report. The second describes a change. The third withdraws support without supplying a replacement or asserting the opposite. A delete-plus-insert operation cannot preserve those distinctions unless its meaning is recorded.

### Your proposed historical sentence is too strong

**UNTESTED:** Do not say:

> “Ada lived in Rook until you told me she moved.”

That makes the reporting time sound like the moving time. It also suggests continuous residence in Rook, which two separate reports might not establish.

A safer response is:

> “The notebook previously listed Rook. You later told me Ada moved to Tolby, but you did not give a moving date.”

If the earlier statement was corrected as mistaken, say:

> “You originally told me Rook, then corrected that to Tolby.”

Do not convert a mistaken report into a fact about where Ada formerly lived.

### Some missing information cannot be recovered from the sentence

**UNTESTED:** With Tal already recorded as Mira’s sister, “Mira’s sister is June” supplies another sister. It does not identify Tal as wrong. The default for a multi-valued relation should therefore be **add June and preserve Tal**.

If the user intended replacement but supplied no replacement cue, the reader cannot reliably discover that hidden intention. Conversely, “No, June” may signal correction while leaving the target unclear. Those are different cases; they should not share a blanket “conflict means replace” rule.

### A current-turn-only reader cannot support all the requested corrections

**SHOWN:** Your own-ear proposal points owner and value fields at spans of the unchanged current turn. The question explicitly asks for corrections such as “No, Milan.”  

**UNTESTED:** That span rule needs a narrow extension: an omitted owner or relation may point to a **specific, grounded dialogue record**, not to newly generated words. Otherwise, “No, Milan” is either unwritable by design or requires the reader to invent the missing fields.

### Correct graph updates and correct English interpretation are separate claims

**SHOWN:** Your reasoner already answers the stated clean structured benchmark exactly. That does not establish safe interpretation of correction language, historical questions, or destructive commands. 

**SHOWN—published:** MQuAKE specifically tests whether editing a fact changes the answers to dependent multi-hop questions. Its results demonstrate why checking only the edited fact is insufficient. It does not certify arbitrary conversational deletion or correction. *MQuAKE*, arXiv:**2305.14795**. 

---

## 2. Ranked options

**UNTESTED — predicted benefits and limitations:**

| Rank | Option | What it fixes | Cost | What it cannot fix |
|---|---|---|---|---|
| **1** | **Typed edit transactions, versioned history, and a current notebook view** | Separates correction, change, denial, withdrawal, and addition; prevents partial edits and accidental revival of old values | A storage/compiler change and explicit semantics to test | A reader that confidently chooses the wrong operation |
| **2** | **Confirmation-first editing using the same transaction system** | Makes uncertain targets visible before destructive changes | More turns and more facts initially held back | Ambiguous confirmations; meeting the holdback target if used too often |
| **3** | **An expanded learned contradiction gate that decides what newer statements replace** | Potentially handles varied wording with less explicit machinery | Model inference, training/evaluation, difficult-to-audit decisions | Structural guarantees about deletion scope, historical meaning, or partial writes |

**SUGGESTED:** Zep/Graphiti provides a relevant example of temporal graph memory, but its paper uses an LLM to identify contradictions and invalidate edges. Its architecture is useful precedent—not evidence that this decision is sufficiently reliable for Premonition. *Zep*, arXiv:**2501.13956**, especially §2.2.3. 

**UNTESTED:** Choose option 1, with option 2 only for genuinely unresolved scope or intent. Do not make another contradiction gate the authority that deletes records.

## 3. The proposed correction model

### A. Keep a change history and derive the current notebook from it

**SUGGESTED:** Bitemporal databases distinguish **record time**—when the database learned something—from **valid time**—when the reported fact applies in the world. That distinction fits this problem, although Premonition also needs to represent missing dates. *Bitemporal Property Graphs to Organize Evolving Systems*, arXiv:**2111.13499**, describes these two timelines and their separate query meanings. 

**UNTESTED — proposed storage contract:** Keep immutable assertion records and append edit events that refer to them. Each accepted event should contain:

| Field group | Contents |
|---|---|
| Identity and provenance | Event ID, source turn ID, exact evidence spans, referenced assertion IDs |
| Meaning | Operation, owner, relation, old/new value where applicable, polarity, edit scope |
| Record time | Commit time and notebook version |
| Reported world time | Explicit date/interval, or a category such as `CURRENT_REPORT` or `PAST_UNDATED`; unknown boundaries remain unknown |
| Lifecycle | Which records were retired, corrected, withdrawn, or replaced, and by which event |

**UNTESTED:** A `superseded` flag can be a convenient computed field, but should not be the entire history. It cannot explain whether a record was mistaken, became outdated, was withdrawn, or was replaced only for a particular time interval.

**UNTESTED:** Keep two query meanings separate:

> “What did the notebook say on September 10?” — replay record history.  
> “Where did Ada live on September 10?” — use supported world-time information.

Knowing the first answer does not establish the second. An unknown date is not an infinitely long validity interval.

### B. Give each operation a precise meaning

**UNTESTED — proposed operation semantics:**

| Operation | Notebook effect | Important restriction |
|---|---|---|
| **ASSERT** | Add a user-asserted fact | For multi-valued relations, preserve other values |
| **CORRECT** | Retire the targeted report as corrected; record the replacement | Do not automatically describe the old value as formerly true |
| **CHANGE** | Record a reported transition and update the applicable current view | Do not invent the change date or an unstated origin |
| **RETRACT** | Withdraw the targeted assertion as usable support | Does not create a negative fact |
| **DENY** | Record explicit negative information about a specified proposition | Negation applies to that proposition, not every related entity |
| **FORGET_SLOT** | Stop using information about the specified owner–relation slot | Must also block recovery through history, caches, or inference |
| **CLARIFY / NO_MUTATION** | Leave notebook knowledge unchanged | A question or hypothetical must not partially execute an edit |

**UNTESTED:** For single-valued relations, a clear new present-tense assertion can replace the *current notebook value* without deciding whether the old report was wrong or the world changed. Record the reason as **unspecified update** unless the user provides that distinction. Do not fabricate either a denial or a historical transition.

**UNTESTED:** Relation cardinality is a notebook policy, not a discovery about reality. If a statement explicitly supplies multiple simultaneous values for a relation your table declares single-valued, ask or reject that representation; do not silently discard one.

### C. Apply the difficult examples consistently

**UNTESTED — proposed interpretations:**

**“Ana’s cat is Fig, not Moss.”** Record the positive claim about Fig and the negative claim about Moss as one transaction. Retire any matching current Moss assertion. Preserve other cats if the relation is multi-valued. If Moss was never a matching current entry, do not say “I removed Moss.”

**“Mira’s sister is June,” with Tal already stored.** Add June. Preserve Tal.

**“June, not Tal, is Mira’s sister.”** Replace the identified Tal assertion with June and record the scoped denial. Preserve other sisters. Replacing the *entire sister set* requires language that actually expresses that scope, such as “Her only sister is June.”

**“Ada moved to Tolby.”** Record a reported move. Where the utterance is a current-update announcement, use Tolby as the latest reported location, with the moving date unknown. Where it is historical narration, do not silently replace the present location. Also, an old Rook entry does not by itself prove that this particular move was **from Rook**.

**“Ada used to live in Rook.”** Record an undated past assertion. Do not invent a new location, a departure date, or “Ada never lives in Rook now.” If it conflicts with an active current report, clarify whether the user is updating that report or merely describing earlier history.

**“Suppose Ada moved to Tolby.”** No factual notebook mutation. Hypothetical reasoning may use a temporary, explicitly hypothetical view that cannot commit.

**“Forget where Ana lives.”** Resolve Ana as the entity and `lives_in` as the relation; this is not a value-extraction request. Remove the slot from usable knowledge and prevent its reconstruction through another path.

**UNTESTED:** Retraction and forgetting also need different privacy wording. Retraction can retain an audit history. If “forget” merely disables retrieval while retaining content, say that honestly rather than claiming erasure. Actual erasure requires removing the content from assistant-controlled history and caches as well; it must not be promised merely because the current row disappeared.

### D. Handle “No, Milan” through a grounded correction target

**SHOWN—published, abstract only:** Dependency Dialogue Acts models response relations to particular prior utterances, rather than treating each utterance as independent. I read the abstract, not the full paper. *Dependency Dialogue Acts—Annotation Scheme and Case Study*, arXiv:**2302.12944**. 

**UNTESTED:** After an answer, retain a small **correction target record** containing the question, answered owner–relation slot, displayed value, supporting fact IDs, notebook version, and whether the answer was direct or inferred.

Allow automatic interpretation of “No, Milan” only when the immediately preceding exchange identifies **one unambiguous direct slot**, the notebook version still matches, and “Milan” supplies a valid replacement span.

For example:

> Assistant: “The notebook says Ada lives in Rook.”  
> User: “No, Milan.”

The replacement value comes from the user. The owner and relation come from the referenced grounded slot.

**UNTESTED:** Do **not** automatically back-propagate a correction to a multi-hop answer. After “Your sister’s dog is Pip,” “No, Moss” could mean the sister link is wrong, the dog link is wrong, or the answer was misread. Ask which fact should change. Never modify an intermediate premise merely to force the desired final answer.

### E. Make mutations atomic and prevent old values from returning

**UNTESTED:** A proposed transaction should include its expected notebook version and exact target record IDs. Before committing, the compiler should check all operands, scopes, references, and structural constraints against that same version. If any part fails, the entire transaction changes nothing.

**UNTESTED:** Most importantly, **withdrawing a replacement must not revive its predecessor**:

> Rook → corrected to Tolby → Tolby withdrawn  
> Result: no supported current location—not Rook.

Retiring Rook and withdrawing Tolby are separate historical events. Explicitly teaching Rook again can restore it; merely removing Tolby cannot.

**UNTESTED:** These rules protect transaction integrity. They do not prove that the English reader selected the right transaction. Matching a value to a source span is evidence of copying, not proof of assertion, negation scope, or intent.

## 4. What the reasoner should do after an edit

**SUGGESTED:** Research on maintaining logical conclusions after deletion distinguishes removing an invalid derivation from removing a conclusion that still has another valid derivation. *Optimised Maintenance of Datalog Materialisations*, arXiv:**1711.03987**, describes deletion/rederivation and alternative-support handling. 

**UNTESTED:** Start with the simplest safe policy: **change the notebook version on every accepted edit and invalidate all derived-answer caches**. Recompute answers from the current permitted notebook view. Introduce selective invalidation only after measuring a need for it.

For example:

> `me | sister | Mira`  
> `Mira | dog | Pip`

After correcting the sister link to June, “What is my sister’s dog?” must follow June. If June’s dog is unknown, abstain. Pip may remain a valid fact about Mira, but it no longer answers that question.

**UNTESTED:** A candidate answer should have a checkable support path. For a current question, every supporting edge must be active in the same notebook snapshot. For a dated historical question, the edges must also support the relevant time; combining facts that were true in incompatible periods is not a valid historical chain.

**UNTESTED:** Distinguish the following outcomes in reply records:

| Outcome | Appropriate response meaning |
|---|---|
| Current supported answer | Answer from the active notebook |
| Required fact withdrawn | “You withdrew that information, so I no longer have a supported answer.” |
| Required fact forgotten | “I’m no longer using that information.” Do not reveal the forgotten value |
| Missing intermediate link | Explain the missing link or say the current answer is unknown |
| Conflicting applicable reports | State the conflict and ask for clarification |
| Alternative valid support exists | Answer using that support, not the invalidated path |

**UNTESTED:** A fact is not invalid merely because it is old. In this initial design, “stale” means superseded, withdrawn, explicitly expired, contradicted without resolution, or disallowed—not “older than an arbitrary number of days.”

**UNTESTED:** Explicit taught facts must remain separate from derived answers. Invalidating an inference must not delete a separately taught fact with the same conclusion. Conversely, an explicit forgetting instruction must not be bypassed by deriving the forgotten information again.

---

## 5. The sealed experiment order

### Piece 1 — run next: atomic edit semantics under oracle interpretation

**UNTESTED — hypothesis:** A typed, versioned mutation boundary can apply correctly interpreted edits without collateral changes, misleading history, partial commits, or revival of retired facts.

**Single change:** Replace the notebook mutation boundary with the transaction/history module. Keep the ear, gate prompt and threshold, question parser, learned reasoner weights, and mouth unchanged.

**Named base:** `B0-current-unmerged`, defined by the actual sealed hash of the current system—not by merging the earlier correction pieces first.

**UNTESTED — test design:** Use **300 fresh structured episodes**, plus **60 separately sealed director probes**. Supply gold interpretations of the user’s intended operations so this test isolates update semantics rather than English recognition.

The main panel contains **50 episodes in each of six families**:

| Family | Required coverage |
|---|---|
| Correction versus change | Mistaken report, real transition, unspecified current update |
| Multi-valued relations | Addition, targeted replacement, explicitly complete-set replacement |
| Withdrawal and negation | Retraction, denial, forgetting, unknown targets |
| Temporal history | Dated versus undated reports, past assertions, incompatible periods |
| Transaction integrity | Invalid members, stale targets, duplicate delivery, interrupted commits |
| Dependent answers | Edited intermediate links, missing replacements, inverses, alternative support, no resurrection |

The director gets **10 additional episodes per family**. An episode may contain several operations and questions, but remains **one scored episode**, not many supposedly independent trials.

**UNTESTED — fixed pass marks:**

| Measure | Pass mark |
|---|---:|
| Complete expected current state, history classification, and transaction receipt | **360/360 episodes** |
| Unauthorized insertions, removals, scope expansions, or invented temporal claims | **0** |
| Partial commits or revival of retired values | **0** |
| Wrong specified post-edit structured answers, including required abstentions | **0** |
| Added median storage/update overhead in a sealed stress fixture of 1,000 active assertions and 10,000 history events | **≤20 ms**, measured against the base on the same machine |

**UNTESTED:** Use fresh gold question frames for the structured answer checks, so an English question-parser failure does not masquerade as a storage failure. Record the base’s outcomes on the same episodes. Any claimed improvement must come from that paired comparison, not from comparing these results with the earlier 80- or 96-item panels.

**UNTESTED — sample-size rationale:** This is coverage-driven engineering testing: six distinct mechanisms, 50 main episodes each, and independent probes. It is **not a certificate for English wrong-write probability**, because the interpretations were supplied correctly.

**UNTESTED — falsification:** One unauthorized deletion, partial correction, invented date, or resurrected old value falsifies the implementation’s safety claim. Failure with gold interpretations means improving the ear cannot rescue this storage design. If the current base already satisfies the entire contract, the argument for prioritizing a backend replacement is weakened substantially.

### Piece 2 — only after Piece 1 passes: explicit English correction pairs

**UNTESTED — separate hypothesis:** The existing ear can propose safe, complete correction transactions when the owner, relation, rejected value, and replacement are explicitly expressed.

**Single change:** Change the English-to-edit proposal component. Keep the accepted transaction compiler, gate settings, reasoner, and mouth frozen. Use the existing model resources; this step does not require downloading a new model.

**UNTESTED:** Do not bundle “No, Milan,” general temporal interpretation, or broad forgetting language into this experiment. Their intended semantics are specified above, but their English recognition remains separate work.

**UNTESTED — panel:** **600 fresh episodes**, plus **60 director probes**:

| Main-panel category | Count |
|---|---:|
| Unambiguous, fully expressed correction pairs | **400** |
| Non-assertions or genuinely ambiguous correction attempts that must not mutate | **100** |
| Ordinary teaching controls, including additions to multi-valued relations | **100** |

The probes contain **40 corrections, 10 non-mutation controls, and 10 ordinary controls**. Do not label a clear but unsupported assertion—such as an unambiguous historical fact—as “should save nothing” merely because this piece cannot handle it.

**UNTESTED — fixed pass marks:**

| Measure | Pass mark |
|---|---:|
| Fully correct correction transactions on the main panel | **≥360/400** |
| Correction completion gain over the frozen base | **≥40 additional correct episodes out of 400** |
| Fully correct correction transactions on director probes | **≥36/40** |
| Wrong insertions, wrong removals, collateral deletions, or partial new-path corrections | **0** |
| Mutations on non-mutation controls | **0/110** |
| Ordinary controls handled correctly by the base that become incorrect | **0** |
| Unsupported claims in correction-path acknowledgments | **0** |
| Grammatical correction-path replies | **≥436/440** |
| Median end-to-end correction-turn latency | **≤800 ms** |

**UNTESTED:** Ninety-percent complete correction recall leaves at most ten percent of these correction episodes held back, provided every accepted correction is exact. Measure positive and negative fact components separately too; an atomic pair must not earn partial credit for saving only the new value.

**UNTESTED — statistical interpretation:** Four hundred correction opportunities allow the test to collect at least 360 accepted corrections at the pass threshold. Under an independent, fixed-distribution binomial model, zero errors in 360 accepted correction turns gives a one-sided 95% upper bound of:

\[
p_{\mathrm{upper}}=1-0.05^{1/360}\approx0.00829=0.829\%.
\]

That calculation uses the exact-binomial framework; its assumptions matter. 

**UNTESTED:** Do not advertise that number as deployment-wide certification from a balanced, agent-written stress panel. It does not automatically account for correlated wording, incorrect gold labels, distribution shift, or repeated release selection. Also, the 100 negative controls do not separately establish a below-one-percent error rate for their category.

**UNTESTED — falsification:** Any new-path wrong mutation fails Piece 2, even if recall improves sharply. So does passing safety only by falling below the completion threshold. A safe but mostly refusing correction reader has not solved the requested problem.

### Sealing and grading

**UNTESTED:** For both pieces, seal the base, candidate, operation specification, panel-generation specification, scoring rules, timing procedure, and director-probe criteria before the registered run. Have independent agents establish and check expected operations before seeing outputs; agreement is useful but is not proof that the key is correct.

**SHOWN:** Your existing process requires a registered FAIL to remain FAIL, exactly one diagnosis-driven follow-up, and independent director verification. Apply those rules here; neither a new threshold nor a changed interpretation may rescue the same registered run. 

**UNTESTED:** These are component verdicts. They must not conceal remaining wrong writes on unchanged ordinary-teaching paths or imply that the entire assistant has met its release targets.

## 6. Strongest objection and rejected rival

**UNTESTED — strongest objection:** Your evidence identifies English interpretation as the main weakness, while the clean-input reasoner already works. A history redesign could therefore consume effort without making the family demo noticeably better.

**UNTESTED — response:** That objection is strong. It is why I recommend a bounded mutation-boundary experiment—not a new general-purpose temporal database, a new reasoner, and a new language model together. Destructive operations need an explicit contract before the ear is allowed to issue them. Once that contract passes, English recognition should regain priority.

**UNTESTED — rejected rival:** The tempting alternative is “add `DENY`, remove the old value, and trust the gate to approve the new pair.” I reject it because it leaves deletion scope, retraction, temporal meaning, and target resolution underspecified.

**SHOWN:** The supplied fresh-wording gate result—63 of 65 wrong frames admitted—also gives no basis for assigning that gate greater destructive authority. 

## Plain-language summary

**UNTESTED — proposed design:** Premonition should remember the difference between “that was wrong,” “that changed,” and “stop using that information.” Its history should record when you told it something without pretending that was when the event happened. Adding another sister should not remove a sister already recorded. A correction should happen completely or not at all, and withdrawing the new value should not bring an old value back. “No, Milan” should update something automatically only when the previous exchange identifies one clear fact to correct. After an edit, the reasoner should rebuild its answer from the usable notebook and say it does not know when a required link is missing. First test those rules with perfectly understood instructions, then test whether the English reader can produce the right instructions. Passing either test would establish a specific improvement, not prove that the whole assistant can never make a wrong write.

## Answer to question 10: Casual typing: lowercase, no apostrophes, typos, without silently changing names
(message cmsg_01FuvegZXjMmeUzStiEFVnEW7roa73fFvrmXQnDoZ3eXmm, 2026-09-23T10:21:42Z)

## Recommendation

**UNTESTED — My recommendation:** Train the reader to understand casual text **without rewriting the authoritative input**, and treat uncertainty about a name’s identity or spelling as a separate clarification problem. Recovering the missing possessive in “whats ana cat called” should change the *interpretation*, not change `ana` into another string.

**UNTESTED — The important limit:** A previously unseen name and a typo can produce exactly the same text. A known name gives the system a possible correction to ask about; it does not prove that correction is right. No training method removes that distinction.

I use **SHOWN** for your reported measurements or published findings, **SUGGESTED** for transferring a published result to this different setting, and **UNTESTED** for my proposed design and experimental choices. Your measurements are treated as reported, not independently audited here.

## 1. Diagnosis: these are several different problems

### Missing capitalization is not the same as missing grammar

**SHOWN — Your measurements:** The casual-question reader answered 9/25 questions, and 12 of the 16 misses omitted the possessive entirely. That is evidence against treating this primarily as an apostrophe-restoration problem.

**UNTESTED — Interpretation:** These require different capabilities:

| Input feature | What the reader needs to recover |
|---|---|
| `ana's cat` → `anas cat` | The boundary between a name and a possessive ending. |
| `ana's cat` → `ana cat` | An ownership relationship whose grammatical marker is absent. |
| `Rose` → `rose` | Whether the word denotes a person in this sentence. |
| `mira stil` | Whether the value contains two name words or an accidental trailing word. |

**UNTESTED — Design consequence:** Do not solve all four by adding, removing, or retaining a trailing `s`. A token ending in `s` could already be someone’s complete name. The reader should represent “owner of this cat” in its parsed meaning, rather than manufacture that meaning by editing a name.

**SHOWN — Published:** Bodapati, Yun, and Al-Onaizan found that named-entity recognizers could depend heavily on capitalization, and that training with case-altered examples improved robustness while largely retaining performance on normally written text. Their task was entity recognition, not safe notebook writing. **arXiv:1911.05241.** 

**SUGGESTED — Transfer:** This supports training your reader on both normally written and caseless text. It does **not** establish that capitalization dependence caused every Premonition failure; some questions may fail in the hand-written parser instead.

### The normalizer changed evidence, not just presentation

**SHOWN — Your measurements:** The normalizer added three wrong saves, including altered names, and failed its registered accuracy requirements. The scorer disagreement also means there is no single settled exact-accuracy result to cite.

**UNTESTED — Diagnosis:** The central problem is not merely that the correction rule was imperfect. Its output became material from which the system could create notebook facts. That lets a preprocessing mistake become an apparently well-supported write.

**UNTESTED — Required separation:** Preserve two things separately: the unchanged message, which is evidence, and any interpretation or correction hypothesis, which is not evidence by itself. A later copy-from-source compiler can prevent invented characters, but it still cannot establish that the chosen span has the right meaning.

### The typo failures need a more precise error taxonomy

**UNTESTED — Limitation:** I do not know from the report whether the two typo-related wrong saves were principally incorrect span boundaries, faithful copies of unintended spellings, or incorrect identification of an existing person. I am not disputing their recorded verdicts; those mechanisms need different remedies.

**UNTESTED — Key distinction:** Consider the same observed message:

> `my sisters name is mira stil`

The intended full name might be `mira stil`. Alternatively, the intended name might be `mira`, followed by a mistyped `still`. Without additional evidence, neither choosing the shorter span nor retaining both words is guaranteed to recover the intended name.

**UNTESTED — Gate diagnosis:** An entailment gate can also be answering the wrong safety question. “Does this message assert the literal string?” is different from “Is this the spelling the user intended?” A high YES score on the first question cannot settle the second. Raising the threshold does not provide missing information.

### “Known name = fixable” is incomplete

**UNTESTED — Correction:** When the notebook contains `Mira` and the user types `mria`, the system has a useful candidate for a question. But `mria` might denote a different person. Even a unique nearest spelling is not permission to merge identities.

**UNTESTED — Further limit:** A typo can also produce a perfectly ordinary name. A user could type `Mira` while intending `Mina`. Therefore, an unfamiliar-spelling detector cannot be a complete intended-spelling safeguard.

## 2. How the reader should behave

### Decide the word’s role from the sentence, not from a name dictionary

**UNTESTED — Proposed policy:** Neither “this is an ordinary English word” nor “this resembles a name” should decide whether a span is a name.

| Illustrative input | Proposed interpretation |
|---|---|
| `my sister is rose` | The sentence uses `rose` as a name. Preserve that spelling. |
| `my sister may visit` | `may` is not an asserted sister’s name; this also expresses a possibility. |
| `will my sister visit` | A question, not a teaching statement about someone named Will. |
| `my sisters name is mira stil` | Ask about the name boundary rather than choosing one silently. |

**UNTESTED — Lookup policy:** Case-insensitive matching may generate an existing-entity candidate, but must not silently merge two notebook identities. Keep the source spelling and the resolved entity identifier separate. The fact that `rose` matches an existing Rose matters only after the sentence has been interpreted as referring to a person.

**UNTESTED — Question policy:** For `whats ana cat called`, recover the possible ownership question directly. Answer only when the interpretation and notebook lookup are sufficiently unambiguous; never create an owner or a cat relationship while answering it.

### Ask a spelling question, not a disguised correction

**UNTESTED — Proposed distinction:**

| Situation | Appropriate clarification |
|---|---|
| A plausible match exists in the notebook | “Did you mean ‘Mira’, who is already in the notebook, or a different person?” |
| The name is new and its spelling is uncertain | “What exact spelling should I save?” |
| The name boundary is uncertain | “Should the saved name be exactly ‘mira stil’, or something else?” |
| The owner or asserted meaning is uncertain | Ask about that uncertainty—not about spelling as a substitute. |

**UNTESTED — Important restriction:** A genuinely unfamiliar spelling is not a false fact. Do not replace it with a familiar name, and do not describe it as incorrect unless the user has established that.

**UNTESTED — Compiler compatibility:** A bare “yes” does not contain the corrected name as a source span. Under the planned unchanged-turn compiler, the simplest compatible confirmation is to ask the user to restate the fact with the intended spelling. Saving a proposed correction after a bare “yes” would require a separately specified confirmation protocol; it should not quietly become an exception to source-span rules.

### How often is acceptable?

**UNTESTED — Recommended accounting:** Count every true fact not committed on its first presentation as held back, including clarification requests, refusals, and silent misses. Do not remove a holdback from that count merely because a later clarification succeeds.

Under that interpretation, your stricter requirement is:

\[
\text{first-pass exact recall}\ge 1-0.12=88\%.
\]

**UNTESTED — Consequence:** The 12% holdback limit is stricter than 85% recall when they use the same denominator and there are zero incorrect commits. I would register **88% first-pass exact recall**, rather than exploit a distinction between “missed” and “held back.”

**UNTESTED — Feasibility limit:** Asking about every new name is incompatible with that cap whenever new-name facts make up more than 12% of the relevant facts. Conversely, guaranteeing the intended spelling of every previously unseen name would require additional information whenever the text could be a typo. Those objectives cannot both be guaranteed for arbitrary input distributions.

**UNTESTED — Practical rule:** Ask whenever a proposed save requires an unresolved choice of spelling, identity, or meaning; do not spend a “clarification quota” and then start guessing. If this happens too often, the system fails the usability target. I do not know the owner’s actual acceptable clarification frequency beyond the stated 12% requirement.

## 3. Ranked options

### 1. Train the existing reader directly on raw casual text

**SUGGESTED — What it addresses:** Mixed clean/casual training is a credible way to reduce dependence on capitalization and familiar surface forms, based on the capitalization-robustness results above. **arXiv:1911.05241.** 

**UNTESTED — Proposed implementation:** Teach the existing ear to produce its existing frames from lowercase text, missing-apostrophe forms, omitted-possessive questions, and carefully constructed name/ordinary-word contrasts. Train uncertain cases toward the existing no-write outcome. Accepted name targets must use the actual source spelling.

**UNTESTED — Cost and limit:** This costs verified training data and one fine-tune, but adds no new inference stage. It cannot determine an unknowable intended spelling, and training alone does not structurally guarantee correct span copying. It also cannot fix a parser path that bypasses the ear.

### 2. Add a separate, notebook-aware confirmation mechanism

**UNTESTED — What it addresses:** This supplies the missing distinction between an unfamiliar new spelling and a possible reference to an existing entity. It can propose known candidates without treating them as corrections.

**UNTESTED — Cost and limit:** It requires a read-only notebook lookup, an explicit clarification outcome, and confirmation handling. It costs user interaction and consumes the holdback budget. It does not itself recover omitted grammar, and it should not be bundled into the next training experiment.

### 3. Give the reader raw text plus non-authoritative normalization hypotheses

**SHOWN — Published:** Mayhew, Gupta, and Roth improved entity recognition by adding predicted casing distributions as features, rather than relying only on a single restored-casing string. **arXiv:1912.07095.** 

**SUGGESTED — Transfer:** This supports an auxiliary-hypothesis design: retain the original text and offer uncertain casing or grammatical interpretations as additional information.

**UNTESTED — Cost and limit:** It adds alignment, ambiguity handling, and potentially inference work. It also cannot safely “protect all names before normalization” unless name recognition has already succeeded—the very problem being solved.

**UNTESTED — Answer about front-end normalizers:** Yes, preprocessing can be the right design when it provides aligned, non-authoritative information. I reject a whole-sentence corrected string as the sole evidence used for notebook writes.

## 4. The one experiment to run next

### Experiment: raw-casual training, with every runtime component except ear weights frozen

**UNTESTED — Hypothesis:** A fixed continuation fine-tune of the existing ear can substantially improve casual interpretation, especially omitted-possessive questions, without adding wrong writes or exceeding the holdback and latency limits.

**UNTESTED — Named base B:** Ear v4.1, the current brake, current gate prompt and threshold **0.25**, current canonicalizer, parser, notebook, and mouth; the failed normalizer remains disabled.

**UNTESTED — Candidate C:** Exactly the same runtime system, with only the ear checkpoint replaced. No new gate prompt, threshold, parser stage, spelling guard, notebook input, or confirmation action.

**UNTESTED — Scope restriction:** The current ear has `TEACH`, `ASK`, and `NONE`, not a dedicated clarification frame. Ambiguous training cases therefore use `NONE`. That is a safe hold—not evidence that the system can conduct a successful clarification dialogue.

### Fixed training intervention

**UNTESTED — Proposed training allocation:** Use 8,000 verified examples for one continuation epoch: 4,000 clean replay examples, 2,000 audited casual variants, 1,000 independently phrased omitted-possessive questions, and 1,000 contrastive cases covering name/word collisions, uncertain span boundaries, and statement-versus-question ambiguity.

**UNTESTED — Label rules:** Never corrupt a name and retain the original clean name as the target; that trains silent correction. When case changes, copy the source spelling in the target. When a transformation creates ambiguity or changes meaning, revise the target accordingly rather than assuming the original label survives. Never label two indistinguishable inputs differently merely because the data generator privately intended one as a typo.

**UNTESTED — Training controls:** Fix the training seed, reuse and seal the existing training hyperparameters, and use the final checkpoint—not whichever checkpoint performs best on the blind panel. Use only verified fictional data and already available weights. No new model download is required.

### Test population and sample size

**UNTESTED — Main audit:** Generate **700 independent episodes** from a registered synthetic mixture:

| Sampling probability | Episode family |
|---:|---|
| 50% | Casual teaching turns. |
| 20% | Normally written teaching turns. |
| 20% | Questions and other turns that should not teach. |
| 10% | Genuine ambiguities requiring a hold. |

**UNTESTED — Sampling rules:** Draw the family independently for each episode; these are probabilities, not fixed quotas. Each episode gets a fresh fictional notebook context. Teaching cases contain one target fact, and include new names, ordinary-word/name collisions, and legitimate multiword names. Do not manufacture hundreds of supposedly independent observations by paraphrasing one underlying case.

**UNTESTED — Additional challenge panel:** Add **240 fresh episodes** with fixed counts, evaluated separately:

| Challenge group | Count |
|---|---:|
| Questions with the possessive marker entirely absent | 80 |
| Clear casual teaching turns | 80 |
| Ambiguous names, identity, spans, or speech acts | 40 |
| Normally written controls | 40 |

**UNTESTED — Total:** Both B and C receive the same **940 episodes**, independently reset. Reserve another **40 sealed episodes** for the director’s required verification probe after a provisional PASS. Do not pool the fixed-quota challenge cases into the main statistical certificate.

### Gold-label requirements

**UNTESTED — Required preparation:** Two agents independently label the original message and notebook context before seeing either system’s output. Adjudicate disagreements and seal the key before execution.

**UNTESTED — Crucial distinction:** Record both “what the visible message supports” and any separately supplied intended spelling. A hidden intended spelling is not evidence available to the reader. Where confirmation is required, give legitimate unfamiliar spellings the same treatment as indistinguishable typos; do not create an artificially easy typo-detection benchmark.

**UNTESTED — Denominator protection:** A held-back teaching fact still counts against recall when it belongs to the registered true-fact denominator. Do not exclude difficult new-name cases after seeing the output. Unresolved possible wrong writes block a PASS rather than being discarded.

### Exact pass marks

**UNTESTED — All requirements below are mandatory and fixed before execution:**

| Requirement | Pass mark |
|---|---|
| Wrong saves | **0** across all 940 episodes; also **0** in the director’s 40-episode probe. |
| Statistical safety sample | At least **400 independent write-bearing episodes** in the 700-episode main audit. |
| Main-audit first-pass recall | At least **\(\lceil0.88T\rceil\)** true facts saved exactly, where \(T\) is fixed by the sealed gold labels. |
| Main-audit holdbacks | At most **\(\lfloor0.12T\rfloor\)** true facts not committed on first presentation. |
| Omitted-possessive questions | At least **72/80** correct end-to-end answers, and at least **24 more correct answers than B** on those same 80 cases. |
| Clear casual teaching | At least **71/80** facts saved exactly; at most **9/80** held back. |
| Ambiguity safety | **40/40** challenge cases produce no notebook write. |
| Normally written controls | At least **36/40** exact end-to-end outcomes, and no fewer than B. |
| Source preservation | **0** unauthorized name alterations, including added/dropped letters or absorbed trailing words. |
| Reply truthfulness | **0** unsupported claims about the notebook or assistant. |
| Reply grammar | At least **931/940** grammatical replies under the sealed grading rules. |
| Latency | Median at most **800 ms**, measured end-to-end on the target hardware, both overall and separately for substantive, non-refusal turns. |

**UNTESTED — Measurement discipline:** Log the raw message, ear frames, gate/brake decisions, parser result, notebook difference, and final reply. This is observational instrumentation, not a behavioral change. If the ear improves but the unchanged parser still rejects the questions, the end-to-end requirement fails.

### What the wrong-save certificate means

**SHOWN — Published statistical framework:** Selective prediction evaluates error among accepted outputs, separately from how often the model accepts. The binomial risk bound in Geifman and El-Yaniv also makes the independent-sampling assumption explicit. **arXiv:1705.08500.** 

**SHOWN — Mathematical calculation:** With zero errors in \(m\) independent accepted decisions, the one-sided upper bound is

\[
p_{\mathrm{upper}}=1-\alpha^{1/m}.
\]

At \(m=400\) and \(\alpha=0.025\),

\[
p_{\mathrm{upper}}
=1-0.025^{1/400}
\approx 0.00918
=0.918\%.
\]

This is below 1%. 

**UNTESTED — Proposed confidence allocation:** Use \(\alpha=0.025\) for this experiment, reserving the other 0.025 for its one permitted diagnosis-driven follow-up. That allocates a combined 5% error budget to this pair of certification attempts, not to every experiment in the project.

**UNTESTED — Define the unit honestly:** The certificate concerns a committed turn containing any wrong fact; do not count several frames from one message as independent safety trials. On these single-fact teaching cases, unexpected extra writes are failures. Do not advertise this as a per-frame certificate for unrestricted multi-fact conversations.

**UNTESTED — Claim boundary:** A PASS supports the registered synthetic input distribution under the sampling and labeling assumptions. It does not establish the same rate in all family conversations, nor does it certify recovery of unexpressed intended spellings. The other thresholds are held-out empirical pass marks, not additional population-level confidence guarantees.

### What would prove this recommendation wrong?

**UNTESTED — Falsification:** Any added wrong save, excessive holdback, failure to reach 72/80 omitted-possessive answers, or latency failure rejects the claim that this **data-only change is sufficient for the registered targets**. In particular, gains on lowercased copies but failure on independently phrased missing-possessive questions would show that the intervention learned superficial variation rather than the needed interpretation.

**UNTESTED — Separate later step:** A notebook-aware exact-spelling confirmation mechanism would be another experiment with the ear frozen. It is not included in this result, and the failed normalizer remains FAIL.

## 5. Strongest objection and the rejected rival

**UNTESTED — Strongest objection:** Direct training may be the wrong use of limited data. The reader must learn grammar recovery, source copying, and abstention together, while the current gate provides weak protection. Better average accuracy could coexist with one unacceptable high-confidence write. I do not know whether the proposed fine-tune will meet the safety and recall requirements simultaneously.

**SHOWN — Evidence favoring the rival:** Náplava and colleagues compared noise training with external grammatical correction and found that the better approach depended on the task. External correction performed better in their low-resource tagging/entity-recognition settings, whereas internal noise training did better in their larger machine-translation setting. **arXiv:2110.07428.** 

**SUGGESTED — Implication:** That is a real argument for auxiliary correction in a data-limited reader, not something to dismiss.

**UNTESTED — Why I still rank direct training first:** Your observed failures include the corrector changing notebook values, and the immediate experimental question can be tested by changing only one checkpoint. I reject *authoritative whole-sentence rewriting*, not all preprocessing. A raw-plus-hypotheses reader is the strongest rival if direct training fails.

**SHOWN — Reading scope:** I consulted the full-text HTML versions of the four cited papers, not only their abstracts. None of their reported experiments establishes safe casual-text notebook writing under Premonition’s requirements. 

## Plain-language summary

**UNTESTED — Recommendations and reasoning:** Teach the reader to understand casual messages instead of automatically rewriting them first. It should recover missing grammar without adding or removing letters from names. Words such as “rose” and “will” should be interpreted from their role in the sentence, not from a list of ordinary words. A similar name already in the notebook is a reason to ask, not permission to substitute it. A completely new name may be impossible to distinguish from a typo without asking the user. Those questions must count against the holdback limit, even when the fact is saved later. The proposed experiment changes only the reader’s weights and requires substantially better casual understanding with no wrong writes. Passing would support that reading improvement, but it would not prove that the system knows spellings the user never actually supplied.

## Answer to question 11: Proving the design beats an equal-size plain transformer, fairly
(message cmsg_01FuvegZXjMmeUzStiEFVnEWKzJrMUf9ymGBNWjaaQU43F, 2026-09-23T10:21:16Z)

**UNTESTED—recommendation:** Make two separate claims: **“This is a better assistant under a stated resource budget”** and **“This particular reasoning component explains the improvement.”** A notebook can legitimately help establish the first claim without establishing the second. The most useful next experiment is a **shared-notebook answerer swap**, using an already available model, before spending the training budget on the final equal-size comparison.

Here, **SHOWN** means supported by your report or cited research—not independently reproduced by me. **SUGGESTED** means published evidence supports a transfer to your setting. **UNTESTED** marks my proposed procedures, deductions, and numerical planning assumptions.

## 1. Diagnosis: what is actually being compared?

### The proposed parameter match appears incomplete

**SHOWN—your report:** The planned ear is approximately 33M parameters, the planned mouth is 28.85M, and the learned lookup reasoner has 79,316 parameters. Your proposed plain-transformer baseline is described as approximately 33M.  

**UNTESTED—arithmetic and implication:** Assuming those modules have separate weights, the planned total is approximately

\[
33+28.85+0.079316 \approx 61.93\text{ million parameters},
\]

before any additional learned components. **A 33M decoder would therefore not be an equal-size whole-assistant baseline.** Count all unique learned tensors used in the deployed pipeline, including frozen components and embeddings; count genuinely shared weights once. Do not pad a smaller baseline with unused parameters to create an artificial match.

### “You gave it a database” is an attribution objection, not an automatic disqualification

**UNTESTED—interpretation:** Your architecture deliberately moves changing facts into explicit storage instead of requiring the language model’s weights to hold them. That is a legitimate systems-design choice. The appropriate question is whether it delivers better correctness, editing behavior, or efficiency after accounting for its memory, computation, supervision, and hand-written rules.

However, beating a decoder that receives only the chat history does **not** show that your learned reasoner is better. The gain could come from cleaning the facts, removing obsolete information, canonicalizing relations, or executing ordinary database joins.

**SHOWN—published precedent:** External memory with multiple computational hops is established prior work; *End-To-End Memory Networks*, arXiv **1503.08895**, is one example. Consequently, a successful benchmark would establish the value of your implementation and choices, not by itself establish that memory-based multi-hop reasoning is a new architectural idea. 

### The reversal and editing claims need narrower wording

**SHOWN—published distinction:** *The Reversal Curse*, arXiv **2309.12288**, distinguishes learning facts in weights from using facts supplied in the prompt. Its in-context experiments largely succeeded at reversal. It therefore does not justify handicapping your transformer baseline by withholding the taught facts. 

**SHOWN—published distinction:** MQuAKE, arXiv **2305.14795**, evaluates questions whose answers change as consequences of factual edits. Its MeLLo method stores edits externally and repeatedly decomposes questions, retrieves relevant edited facts, and checks tentative answers. Simple retrieval over chat history is a useful baseline, but it is not a reproduction of MeLLo. 

**UNTESTED—claim boundary:** Describe your tasks as **in-context relational reversal** and **multi-hop question answering after explicit memory edits**. Call the latter “MQuAKE-style,” not performance on MQuAKE or success at editing knowledge inside model weights.

### “The risk is all in reading English” is not yet established

**SHOWN—your report:** The 200/200 result is an internal structured-input benchmark. The current system also contains a substantial hand-written question-processing stack. The reported English-facing failures include missed facts, incorrect writes, and unrecognized question forms.  

**UNTESTED—interpretation:** That makes language handling a demonstrated bottleneck, but 200 examples do not establish universal correctness of the reasoning system. Nor do they tell you whether the learned 79,316-parameter component, rather than the surrounding code, deserves credit.

## 2. Three ranked options

**UNTESTED—proposed priorities:**

| Rank | Option | What it fixes | Cost | What it cannot establish |
|---|---|---|---|---|
| **1** | **Shared-notebook answerer swap** | Tests whether the current answerer adds value once both systems receive identical stored facts. | An adapter, development prompting, and local evaluation using the already available gate model; no new rental or model download. | Equal-size or equal-training-data superiority, because the borrowed comparator has different weights and training. |
| **2** | **Whole-system, from-scratch matched comparison** | Directly tests the final headline against history-only, retrieved-history, and notebook-equipped transformer systems. | Training, tuning, and replication. I do not know its dollar cost without the token budget and measured throughput. | Which internal component causes the gain unless accompanied by controlled comparisons. |
| **3** | **Deterministic executor control** | Measures whether the learned lookup reasoner contributes beyond ordinary traversal, joins, inverse lookup, and missing-fact checks. | CPU implementation and verification; no model training. | General English understanding or the value of learning outside the supported relation system. |

**UNTESTED—priority judgment:** Option 1 is the best next diagnostic. Option 2 is necessary for the eventual headline. Option 3 is necessary before claiming that the *learned reasoner specifically* explains the result.

## 3. The baseline set and fairness rules

### Four comparators answer four different objections

**UNTESTED—proposed baseline set:**

| Comparator | Information available at question time | Main purpose |
|---|---|---|
| **T-History** | Complete chronological teaching history, including corrections. | Tests the whole architecture against an ordinary history-conditioned decoder. |
| **T-Retrieval** | The same history, plus a registered retrieval procedure over it. | Tests whether finding relevant past turns explains the advantage. |
| **T-Notebook** | Exactly the same notebook snapshot supplied to Premonition. | Tests whether structured, updated storage explains the advantage. |
| **S-Notebook** | The same notebook and formal query, executed by straightforward deterministic code. | Tests the contribution of the learned executor. |

**UNTESTED—important distinction:** Use the **same decoder checkpoint** across History, Retrieval, and Notebook conditions when isolating the effect of the information format. But do not then automatically call every condition an equal-size *deployable system*.

A real notebook-equipped baseline needs a way to build that notebook. If it uses your ear, count the ear’s parameters and ingestion cost. With a total budget near 61.93M and a shared 33M ear, roughly 28.93M remains for the baseline’s other learned components. A 61.93M decoder receiving an oracle notebook is a useful, generously resourced diagnostic—not a parameter-matched complete assistant.

### Information and supervision parity

**UNTESTED—proposed rules:** Both systems must receive the same underlying teaching turns, question meanings, speaker identity, and temporal information. Supply the baseline with the relation definitions, aliases, single-/multi-valued semantics, correction policy, and abstention policy. “Newer wins” should apply only where the registered semantics authorize replacement; it must not silently erase other values of a multi-valued relation.

For the main history-conditioned comparison, keep every required supporting fact inside the baseline’s context window. Evaluate longer histories separately as a **memory-scaling advantage**, not as proof that the transformer cannot reason over information it was never allowed to see.

Give every trained system access to the same approved training information: English examples, structured facts, question–answer pairs, and any supporting-fact or reasoning supervision used by Premonition. Different architectures may use different losses, but extra labels cannot disappear from the data ledger merely because they train an intermediate component.

Keep entire fictional worlds—and their paraphrases, edited variants, and counterfactual siblings—together when splitting data. Hold out some relation compositions and language constructions, not just new names substituted into familiar templates. Test-time teaching must not update either model’s weights in this comparison.

### Training and tuning budgets

**SHOWN—published evidence:** *Show Your Work*, arXiv **1909.03004**, documents comparisons whose conclusions change with the tuning budget. It also explains why equal numbers of trials do not necessarily mean equal computational expenditure or equal prior development effort. 

**UNTESTED—proposed budget for the later matched trial:** Define \(C\) as the registered training-computation allowance for one complete run of a model family. Allow each family **six pilot configurations at \(0.1C\) each**, followed by **three complete runs of the selected configuration at different seeds**:

\[
6(0.1C)+3C=3.6C
\]

per model family. Select configurations on development data only. Give each inference wrapper at most **six registered prompt/retrieval configurations** evaluated on the same **200 development worlds**.

These are proposed limits, not a claim that six trials find the best possible model. Publish the configurations, development scores, and learning curves. If the winning setting lies at the edge of the search range or is still improving sharply at the cutoff, disclose that rather than declaring the baseline fully optimized.

**UNTESTED—accounting rule:** Separate three ledgers: training-data exposure, training computation, and inference cost. Equal parameters and equal access to data do not guarantee equal FLOPs. When equal exposure and equal computation cannot both be achieved, report separate data-matched and compute-matched comparisons rather than quietly calling one run both.

Historical parser patches, prompt searches, and failed experiments are also development effort. You cannot retroactively make that effort identical; document it and establish a fair prospective budget.

**SUGGESTED—transfer from benchmarking research:** Multiple final seeds reduce dependence on one fortunate training run, but three seeds are not a universal adequacy guarantee. *Accounting for Variance in Machine Learning Benchmarks*, arXiv **2103.03098**, shows that data sampling, initialization, and tuning choices can all affect comparisons. Thousands of test worlds cannot eliminate uncertainty about having trained only one checkpoint. 

## 4. Separate reading, execution, and speaking

**UNTESTED—proposed diagnostic matrix:** Run both answerers on the same worlds in these four conditions:

| Notebook | Question representation | What the comparison measures |
|---|---|---|
| Gold notebook | Gold formal query | Execution once facts and the requested operation are already understood. |
| Gold notebook | Original English question | Question understanding plus execution. |
| Actual saved notebook | Gold formal query | Consequences of ingestion errors, with question interpretation removed. |
| Actual saved notebook | Original English question | The actual question-answering pipeline. |

A formal query can already specify the required relation chain. Success in that first row therefore demonstrates **execution**, not necessarily discovering how to decompose an English question.

Score the canonical answer record before rendering, then score the actual sentence separately. Otherwise a grammatical failure can masquerade as a reasoning failure—or a fluent sentence can conceal an incorrect answer.

**UNTESTED—metrics:** Use exact entity/value-set correctness, with a frozen alias policy. Report each target capability separately and a preregistered macro-average. Also report whole-world success: whether every scored question in a world was answered correctly.

For answerable questions, an unnecessary refusal is a failure. For unanswerable questions, distinguish correct abstention from fabricated answers. Missing information must not automatically become a negative answer.

For edits, measure the corrected direct fact, the dependent multi-hop answer, and unaffected control answers. Include edits that should change the answer and edits that should not, so “always change something after a correction” cannot succeed.

Keep notebook-write precision, fact recall, unsupported answer claims, grammaticality, and latency as separate outcomes. Show error counts and denominators, not just a combined score. Measure median and tail latency on the same hardware, including ingestion, gating, retrieval, reasoning, and rendering; cached notebook construction must not vanish from the user-facing timing.

**SHOWN—current limitation:** Your reported 77.9% recall is below the stated 85% target. A reasoning-comparison victory would not erase that failure or establish the assistant’s write-safety certification.  

### Check the answer keys before measuring the models

**SHOWN—your report:** Six of nine scored wrong saves in one panel were answer-key mistakes. The older comparison also had prompt defects and answer leakage.  

**SHOWN—published warning, abstract only:** The ICLR 2025 paper *MQuAKE-Remastered: Multi-Hop Knowledge Editing Can Only Be Advanced with Reliable Evaluations* reports substantial benchmark corruption and exploitation of dataset peculiarities. I inspected its abstract, not its full paper. 

**UNTESTED—proposed safeguard:** Derive expected answers from the fictional world state using an independently checked reference implementation, not Premonition’s own executor. Separately verify that the English turns express that state. Resolve disputed labels while system outputs remain hidden, then seal the final key. A hash protects against later modification; it does not establish semantic correctness.

## 5. How much testing is enough?

### Count independent worlds, not every question as a new experiment

**SUGGESTED—methodological transfer:** Dror and Reichart’s statistical-testing appendix, arXiv **1809.01448**, recommends paired tests when systems are evaluated on the same examples. For your task, pair results on the same world and keep all questions, paraphrases, and before/after-edit results from that world together. 

**UNTESTED—proposed analysis:** For a binary whole-world score, define:

- \(W\): worlds only Premonition passes.
- \(L\): worlds only the comparator passes.

Then the observed advantage is

\[
\widehat{\Delta}=\frac{W-L}{n}.
\]

Use an exact paired McNemar test for the registered binary comparison, under the stated sampling assumptions. For fractional world scores or macro-averages, use a world-clustered paired analysis, preserving registered strata. Exact McNemar implementations use the binomial distribution for the discordant pairs. 

Do not compute uncertainty as though the two systems were tested on unrelated samples.

### Five hundred worlds can be enough—but not for every effect

**UNTESTED—planning calculation:** Let \(q\) be the probability that the systems disagree on whole-world success, and let the true difference be \(\delta\). A normal-approximation planning calculation for two-sided 5% significance and 80% power gives approximately

\[
n\approx
\frac{\left[1.96\sqrt q+0.84\sqrt{q-\delta^2}\right]^2}
{\delta^2}.
\]

For a **five-percentage-point** difference, this gives approximately **312 worlds when \(q=0.10\)** and **940 when \(q=0.30\)**. Those disagreement rates are hypothetical, not measurements from your project. These calculations concern detecting a nonzero difference, not the probability of passing an additional five-point practical-benefit requirement.

For four separately advertised capability wins, a conservative four-comparison correction increases those examples to approximately **444** and **1,336 worlds per capability**, respectively. Use development results—not an interim look at the blind test—to estimate disagreement and finalize power calculations.

**UNTESTED—implication for your sealed benchmark:** The 2,500 worlds may be adequate for an aggregate comparison, but their count alone does not establish power for four separate claims. Your description does not identify what the five blocks represent. Do not assume there are 500 independent worlds for each named capability without checking the sealed manifest’s metadata.

### Define wins, ties, and losses in advance

**UNTESTED—proposed interpretation:** Set a practically meaningful gain of **five percentage points** and a practical tie margin of **two percentage points** before testing.

An aggregate win does not establish a win on all four capabilities. Advertise four wins only if the four registered comparisons support them with the chosen multiplicity control. Use a suitable paired confidence interval for the effect; for binary outcomes, a conservative option is to bound the win and loss probabilities separately and subtract the bounds, splitting the error allowance.

A confidence interval entirely below zero supports a baseline advantage. An interval entirely inside \([-0.02,+0.02]\) supports practical equivalence under that margin. An upper bound below \(+0.05\) rules out the proposed five-point benefit at that confidence level. A wide interval crossing zero is **inconclusive**, not evidence of equality.

## 6. The ONE experiment to run next

### Registered experiment: identical notebook, different answerer

**UNTESTED—hypothesis:** On gold notebooks and natural-language questions, Premonition’s current answerer provides at least a five-percentage-point observed advantage over the already available general-purpose model, with statistical evidence of positive superiority.

This deliberately tests the **current answerer stack**, including question interpretation and hand-written logic—not just its learned lookup network.

**Single change.** Replace only the question-to-answer-record block with the already available Qwen gate model used in answer-generation mode. Keep the ear, gate policy, notebook construction, speaker handling, and renderer fixed. The comparator receives the same notebook snapshot and original question, but not Premonition’s selected answer or hidden execution trace.

Require the comparator to return the existing answer-record schema. An adapter may validate syntax; it may not solve the question or repair semantic mistakes.

**Development budget.** No new model downloads, no rental spending, and no gradient training. Allow exactly **six configurations**: three prompt styles—direct instruction, worked examples, and explicit stepwise lookup—at total generation caps of **256 or 1,024 tokens**, including any reasoning tokens. Choose using **200 non-test development worlds** and the same registered accuracy objective.

Before sealing, require the selected comparator to achieve at least **99/100 correct answers on separate simple one-hop format controls**, with **100/100 syntactically valid records**. A model that cannot use the interface is not an adequate reasoning comparator.

**Test sample.** Select **500 independent base worlds** from the existing 2,500-world pool using registered seed **20260923**, before anyone selecting the subset views its contents. Treat related variants as one base world. Verify the sampling structure and gold labels before the run; do not silently claim 500 independent observations when the material contains repeated variants.

Those 500 become used test material. Leave the remaining worlds untouched for a separately registered later comparison.

**Primary condition.** Gold notebook plus original English questions. A world passes only if every registered answer record is correct.

**Exact pass marks:**

| Requirement | Registered threshold |
|---|---:|
| Premonition’s gold-notebook whole-world success | **At least 495/500** |
| Observed paired advantage over the comparator | **At least 25 additional passed worlds** |
| Evidence of positive superiority | **Two-sided exact McNemar \(p<0.05\), with \(W>L\)** |
| Notebook divergence caused by the answerer replacement | **0 differences in the stored fact state** |

These are proposed decision thresholds, not predicted results. The 99% success threshold is an observed-score requirement, not certification that the population success probability exceeds 99%.

**Secondary conditions.** Replay the same worlds with the real ear’s notebook, and with formal queries for the execution-only diagnostic. Report all outcomes without promoting a favorable secondary result into the primary verdict. Repeated conditions do not increase the independent-world count beyond 500.

**Why 500?** It is a useful first test for a moderate difference while preserving most of the sealed pool. The planning calculation above supports that choice under relatively low disagreement; it is not guaranteed to settle a small difference under every error pattern.

**What would contradict the idea?** A sufficiently narrow interval showing practical equivalence would contradict a meaningful answerer-accuracy advantage. An upper bound below five points would contradict the proposed benefit size. A clear comparator advantage would contradict the direction of the hypothesis. Failure to meet a pass mark remains a registered FAIL, but the diagnosis must distinguish underperformance from insufficient precision.

**Separate later step:** Train and test the final own-weight, whole-system parameter-matched baselines. **This first experiment cannot establish the equal-size headline**, regardless of how impressive its result looks.

## 7. Strongest objection—and the rival I rejected

**UNTESTED—strongest objection:** Qwen is much larger and differently pretrained, so this diagnostic is not a fair final architecture contest. A loss to it does not show that an equal-size from-scratch transformer will beat Premonition. A win over one prompt-selected checkpoint does not establish superiority over every way of using that model either.

I nevertheless recommend it first because it asks a useful, inexpensive question: **after the notebook is shared, is there a substantial answerer advantage left to explain?** It also exposes interface and benchmark defects before the larger training commitment.

**UNTESTED—rejected rival:** I would not first train the proposed 33M plain decoder and announce a head-to-head result. The whole-system parameter accounting appears wrong, the comparison would still mix memory and reasoning effects, and one hastily trained baseline would be vulnerable to an undertraining objection. Correcting those issues matters more than producing an early win.

## 8. What claims would different outcomes justify?

**UNTESTED—conditional claim boundaries:**

| Outcome | Defensible conclusion |
|---|---|
| Premonition beats History, but Retrieval closes the gap. | Relevant-history access explains the measured advantage. |
| Premonition beats History and Retrieval, but ties Notebook. | Explicit structured memory is valuable; extra answerer accuracy is not established. |
| Premonition beats Notebook as well. | Its answerer stack adds value beyond receiving the same stored facts, under the tested conditions. |
| Deterministic execution matches or beats the learned executor. | The learned executor’s accuracy contribution is not established for these tasks. |
| Gold-input results are strong but real-chat results lose. | The controlled component works; the deployed assistant does not yet outperform the baseline. |

**UNTESTED—headline template:** After the final matched trial, an appropriate claim would be: “On held-out fictional teaching dialogues, our from-scratch assistant achieved higher specified task scores than the registered transformer baselines at matched total learned parameters and disclosed training and inference budgets.”

That is stronger scientifically than an unrestricted “our architecture beats transformers.”

## 9. An honest five-minute family demo

**UNTESTED—proposed script:** Display both systems, what information each receives, and an unedited timer. Disclose any borrowed model and do not describe this preliminary comparator as equal-size.

| Time | Demonstration |
|---|---|
| **0:00–0:45** | Explain that the names and facts are fictional. Let a family member choose replacement names for the prepared story. |
| **0:45–1:30** | Teach both systems: “My sister is Mira.” “Mira’s dog is Pip.” Show the saved notebook. |
| **1:30–2:15** | Ask: “What is my sister’s dog’s name?” Then: “Whose dog is Pip?” |
| **2:15–3:15** | Teach an explicit correction: “Correction: Mira’s dog is Nori, not Pip.” Ask the two-hop question again and show the changed row. |
| **3:15–4:00** | Ask about an untaught relation that the interface supports. The desired behavior is admitting that the information was not taught. |
| **4:00–5:00** | Let a family member rephrase one question. Show the result even if a system fails or both succeed. |

**UNTESTED—presentation rule:** Freeze the software and script beforehand, but do not select the demonstrated run because it made the rival fail. If both systems succeed, call it a tie on the demonstration. The demo shows behavior; the sealed benchmark supplies comparative evidence.

## Plain-language summary

**UNTESTED—summary:** Give every system access to the facts it is being tested on. First compare the answerers while they use exactly the same notebook. Then compare complete assistants while counting all their learned components and resource costs. Keep reading mistakes separate from mistakes made after the facts are already understood. A notebook-based win can be a meaningful engineering achievement without proving that the learned reasoner is special. A tie against a notebook-equipped transformer would narrow your claim rather than make the project pointless. Start with the 500-world answerer swap, and reserve the equal-size headline for the later from-scratch comparison. In the family demo, show the facts, the correction, the uncertainty, and the actual result—even when both systems get it right.

## Answer to question 12: "Our" and "we": group owners in a person-by-person notebook
(message cmsg_01FuvegZXjMmeUzStiEFVnEWGcALJDwQa7i8M1pHh4Hr4L, 2026-09-23T10:21:47Z)

## Recommendation

**UNTESTED — Represent a known group as one explicit group entity, with its membership recorded separately. Never turn a group fact into facts about each member automatically. Keep an unresolved “our” outside the trusted notebook, and ask which group the user means.**

**UNTESTED — Do not add automatic group writes while the text-level detector’s registered run is unfinished. Complete that run under its existing registration. The one new experiment I recommend afterward is a narrowly scoped, oracle-input test of group-owner storage—not another simultaneous change to English parsing, clarification memory, and notebook semantics.**

*SHOWN below means a supplied measurement or a published result, not an independent reproduction. SUGGESTED means a transfer from published work in another setting. UNTESTED marks proposed designs, interpretations, examples, and experimental thresholds.*

## 1. Diagnosis: three different problems are being mixed together

### The immediate failure is upstream of the rule

**SHOWN — Your measurements:** The rule acted correctly on all 23 group owners it received, but only 14/30 relevant turns reached the desired “ask whose” outcome. On the other 16 turns, the ear changed the owner into something else in 10 cases, and the brake removed the frame in six. The 23/23 figure therefore measures behavior **conditional on receiving the right kind of input**, not end-to-end group detection.

**UNTESTED — Interpretation:** The diagnosis “the group-owner rule does not work” is incomplete. Its decision appears to work on the measured inputs; its attachment point is too late to recover group information that has disappeared. Adding more downstream cases for `our`, `we`, and `us` cannot repair an owner already converted to `me`, or a frame already deleted.

**SHOWN — Published:** *Free the Plural* distinguishes resolving a plural expression to multiple antecedents from detecting those expressions in the first place; its original evaluation supplied gold mentions and gold split-antecedent expressions. That distinction is directly relevant to interpreting your conditional success, although its results are not results for Premonition. arXiv: **2011.00245**; relevant full-text sections checked. 

### “Ownership” is the wrong general category

**UNTESTED — Interpretation:** In this notebook, `owner` is really the **subject of a relation**, not necessarily someone who legally owns something. “Our meeting is at 3” contains a group-dependent reference even though a meeting is not a possession. “We went to Tolby” makes a claim about an event involving a group, although it does not assert dog ownership or residence.

**UNTESTED — Recommended distinction:** Ask **“Does an unresolved group reference affect a fact or answer we are about to produce?”**, not simply “Does this sentence contain group ownership?” A group word can appear in a turn without affecting the owner of the relevant fact: “We checked: Mira’s dog is Pip” should not cause the dog to be assigned to a group.

**UNTESTED — Interpretation of the owner’s ruling:** “Our dog is Pip” should not become `me | dog | Pip` under your policy. But that is a conservative storage rule, not a claim that ordinary “our” necessarily excludes the speaker. Equally, “our” does not establish that the group is a household.

### Knowing a group exists is not knowing that “our” refers to it

**UNTESTED — Interpretation:** A notebook containing one household and one tennis team has not resolved a new “our.” Even a notebook containing only one known group has not proved that the user means that group. There could be an unrecorded group.

**SHOWN — Your measurements:** The raw-text check’s 46/46 detections and zero false asks in 53 development controls are encouraging development results. Its unfinished registered run supplies no fresh verdict yet.

**SUGGESTED — Published transfer:** Experiments on ambiguous plural reference found that the tested models struggled to recognize ambiguity without direct instruction and sometimes failed to consider possible referents. That supports explicitly representing unresolved reference instead of trusting a fluent interpretation. It does not establish the reliability of your particular gate. arXiv: **2510.04581**, *Can LLMs Detect Ambiguous Plural Reference?*; relevant full-text sections checked. 

## 2. Ranked options

**UNTESTED — Proposed ranking; all costs and limitations below are design judgments, not measured Premonition results.**

| Rank | Option | What it fixes | What it costs | What it cannot fix |
|---|---|---|---|---|
| **1** | **One group ID as the owner; separate membership records** | Preserves group identity, supports inverse answers, permits incomplete membership knowledge, isolates group edits from personal facts. | An entity registry, owner-type checks, and explicit display labels. | Wrong English interpretation, unresolved pronouns, or whether a statement applies jointly or individually. |
| **2** | **An explicit member set as one collective owner** | Represents “Mira and me” without choosing one person or duplicating the fact. | Complete member identification and canonical ordering of member IDs. | Named groups with unknown or changing membership; distinct groups containing the same people. |
| **3** | **Keep person-only storage and request explicit individual statements** | Avoids introducing group semantics into the current notebook. | More clarification or refusal; genuine collective facts remain unsupported. | Convenient “ask once and remember” behavior for households and teams. |
| **4** | **A person owner plus `shared=true`** | Marks that the existing personal row is not exclusive. | Little storage, but substantial ambiguity in every later query. | Who shares it, which group was intended, membership changes, and accurate inverse answers. I would reject it. |

**SUGGESTED — Published transfer:** W3C’s Organization Ontology treats an organization as an entity and models membership separately, including optional membership intervals. This is a useful precedent for separating identity from membership—not a ready-made semantics for household dogs. The source is a W3C Recommendation, not an arXiv paper. 

## 3. The representation I recommend

### Keep one owner per row—but permit that owner to be a group

**UNTESTED — Proposed contract:** The owner field should reference exactly one entity whose type is either `PERSON` or `GROUP`. An unresolved plural reference is neither: it remains an unresolved slot in a pending transaction.

**UNTESTED — Illustrative state after explicit clarification:**

| Record | Stored content |
|---|---|
| Group identity | `g7`, displayed as “your household,” explicitly identified by the user |
| Membership | Only independently taught members; completeness remains unknown unless explicitly established |
| Notebook fact | `g7 | dog | Pip` |
| Unsupported additions | No automatic `me | dog | Pip`; no automatic `Mira | dog | Pip` |

**UNTESTED — Essential invariant:** Group membership must not itself authorize copying a group relation to an individual:

\[
\operatorname{member}(p,g)\ \land\ \operatorname{dog}(g,\text{Pip})
\quad\not\Rightarrow\quad
\operatorname{dog}(p,\text{Pip}).
\]

**UNTESTED — Consequence:** “Pip is our household’s dog” and “Pip is Mira’s dog” are separate assertions under this conservative contract. They can both be recorded when both are taught. One must not silently manufacture the other.

**UNTESTED — Important limitation:** This does not mean every plural sentence should be stored collectively. “Mira and Tovin each have a dog” asserts something about the individuals; “Mira and Tovin share one dog” asserts a shared relationship. When the wording does not determine the distinction needed by the notebook, clarification is still necessary.

### A named group is not just its current member set

**UNTESTED — Proposed contract:** A household keeps its group ID when someone joins or leaves, unless the user explicitly identifies a different household. Conversely, a study group and a tennis group remain distinct even when they contain the same people.

**UNTESTED — Proposed contract:** An explicitly enumerated group such as “exactly Mira and me” can use a group entity backed by that exact set. Do not silently merge it with a named household merely because the currently known members match. Unknown membership is not evidence of complete membership.

**SUGGESTED — Published transfer:** Separating a continuing group’s identity from its particular members also appears in the W3C ontology’s treatment of organizational collaborations. Applying that distinction to your conversational notebook remains a design choice. 

### Inverse answers should preserve the recorded level

**UNTESTED — Proposed behavior:** Given only `g7 | dog | Pip`, “Whose dog is Pip?” should receive:

> “Pip is listed as your household’s dog.”

**UNTESTED — Proposed behavior:** It should not receive “Yours,” “Mira’s,” or a list of every known household member. For “Is Pip Mira’s dog?”, the answer should distinguish absence of evidence from contradiction:

> “I have Pip recorded as your household’s dog, but not specifically as Mira’s.”

**UNTESTED — Proposed behavior:** Keep the wording at the strength of the stored relation. A `dog` relationship should not become a stronger claim about legal ownership. Multiple matching notebook owners should produce multiple recorded associations, not an invented exclusive owner.

## 4. Asking the fewest questions without remembering too much

### Ask for the referent, not for a guessed owner

**UNTESTED — Suggested first clarification:**

> “Who does ‘our’ refer to here? You can name the people or the group.”

**UNTESTED — Proposed behavior:** “My household” is sufficient to identify a group without listing everyone. “Mira and me” can identify an explicitly enumerated group. Neither response, by itself, authorizes distributing every group fact to its members.

**UNTESTED — Proposed principle:** **Ask once for the unresolved reference in a transaction, not once per extracted fact—and not once for every future use of “our.”** Several facts can share one owner clarification when the user’s answer explicitly covers them. Different group references must not be combined merely to reduce the question count.

**SUGGESTED — Published transfer:** CLAM studies selective clarification: asking where information is missing while avoiding unnecessary questions on unambiguous inputs. Its evidence concerns question answering, not persistent notebook writes or safe pronoun caching. arXiv: **2212.07769**; relevant full-text sections checked. 

### Remember the fact separately from a language shortcut

**UNTESTED — Proposed behavior:** After resolving the first transaction, retain `household | dog | Pip`. A later question mentioning Pip directly need not reopen the original group ambiguity.

**UNTESTED — Proposed behavior:** Do **not** infer a permanent rule `our → household` from one clarification. A persistent shortcut requires an explicit instruction such as:

> “When I say ‘our dog,’ I mean my household’s dog.”

**UNTESTED — Proposed behavior:** Store that as a narrowly scoped reference rule, with its source and revision history. It applies to “our dog,” not automatically to “our school,” “our meeting,” or every occurrence of “we.” An explicit conflict or competing interpretation should suspend its use until clarified.

**UNTESTED — Limitation:** No reference cache can detect every unannounced change of meaning. Conservative scoping reduces exposure; it does not eliminate semantic ambiguity.

### Clarification requires a two-turn evidence record

**UNTESTED — Proposed contract:** The final write must be supported by the original assertion **plus** the clarification. Preserve both unchanged turns and the relevant spans. Do not manufacture a rewritten sentence and pretend that it was the user’s original assertion.

**SHOWN — From your stated plan:** The planned compiler accepts facts from spans of the unchanged turn. A clarification that supplies an owner missing from an earlier turn requires an explicitly specified extension to that evidence contract; it cannot be assumed to work already.

**UNTESTED — Proposed mixed-turn behavior:** Under your all-or-none policy, a turn containing an unresolved group fact and an independent personal fact stays pending as a whole. Preserve the personal fact candidate, resolve the missing group reference, and then validate the whole transaction. Never say “saved” while the transaction is pending.

**UNTESTED — Evaluation requirement:** Report immediate recall and recall after clarification separately. Count held-back personal facts in mixed turns against the applicable initial-turn hold metric. Later recovery must not erase an initial refusal cost from the report.

## 5. How the reader should decide whether a group matters

**UNTESTED — Proposed reader target:** Replace the vague category “group ownership” with three explicit decisions: whether the turn asserts a supported fact, which span fills each argument of that fact, and whether a required argument has a resolved referent. The group detector must inspect the original text, not rely exclusively on the ear’s owner field.

**UNTESTED — Illustrative decisions:**

| Turn | Required interpretation |
|---|---|
| “Our dog is Pip.” | A group-dependent dog assertion; hold and clarify an unresolved group. |
| “We own Pip.” | A collective ownership assertion, if that relation is supported; it does **not** establish that Pip is a dog. |
| “We went to Tolby.” | A group event assertion; no dog or residence write. Do not ask “whose?” merely because `we` occurs. |
| “Our meeting is at 3.” | A group-linked event reference. Resolve it only if needed for a supported event record or answer. |
| “We checked: Mira’s dog is Pip.” | The dog fact’s owner is Mira; the introductory `we` should not seize that owner slot. |
| “We’re fine.” | No ownership inference; no ownership clarification solely because the subject is plural. |

**UNTESTED — Proposed safeguards:** Speech act and scope still matter. A question without `?`, a quotation, a hypothetical, a future plan, or a negated statement must not become a positive group fact merely because the group is known. Resolving “our” answers **who is being referred to**; it does not establish **that the user asserted the proposed claim**.

**UNTESTED — Training implication:** For the own ear, supervise group-mention spans and their attachment to individual fact slots, rather than just a turn-wide `contains_group` flag. This is a proposed training target, not a reason to add another large-model gate.

### Wrong saves introduced by the group model itself

**UNTESTED — Failure cases to prohibit:** Four particularly important classes are:

| Failure class | Example of an unsupported result |
|---|---|
| **Membership propagation** | Recording Pip as every household member’s dog, or making a new member inherit all existing group facts. |
| **Identity merging** | Combining two groups named “our team,” or merging different named groups because their known members match. |
| **Reference-cache overreach** | Applying a household clarification to a later school or travel group; treating a casual clarification as a permanent global alias. |
| **Transaction or edit leakage** | Applying “yes” to the wrong pending assertion, saving after cancellation, or editing an individual’s dog when the user corrected the group’s dog. |

**UNTESTED — Additional boundary:** Group labels, membership records, and persistent reference rules can themselves be wrong notebook additions. They must be audited as claims—not treated as harmless internal metadata exempt from the wrong-save target.

## 6. The ONE new experiment: typed-owner oracle audit

### Sequencing and single change

**SHOWN — Current status:** Your raw-text detector already has an unfinished registered run. I do not know its original pass marks.

**UNTESTED — Recommendation:** Finish that run unchanged; do not replace its marks with the ones below. The following is a separate new experiment about **representation**, not a second rescue attempt for the failed downstream detector.

**UNTESTED — Experiment name:** `G12-TYPED-OWNER-ORACLE`.

**UNTESTED — Named base:** `CURRENT-PERSON-OWNER`: a frozen snapshot of the currently deployed system, excluding unfinished experimental changes. Record its actual SHA-256 in the registration; no hash is supplied here because I cannot inspect your artifacts.

**UNTESTED — The single change:** Permit an owner reference to denote an explicitly identified group, with separate identity/membership metadata and no automatic group-to-member propagation. Leave the English reader, gate, question parser, learned reasoner weights, and mouth templates unchanged. Do not add persistent pronoun caching in this experiment.

### What the test supplies—and what it does not test

**UNTESTED — Common test harness:** Both arms receive independently authored, gold structured write/query records at the notebook boundary. The records specify asserted relations, resolved or unresolved owners, and authorized edits. This deliberately bypasses English interpretation in both arms.

**UNTESTED — Scope:** This tests whether the group representation can preserve the intended facts, reject unresolved owners, and return correct answer records. It does **not** test whether the ear recognizes “our,” whether a clarification answer is parsed correctly, or whether the full system meets its conversational recall and latency targets.

### Panel and exact marks

**UNTESTED — Proposed sample:** **360 fresh scenarios**, with 60 in each family below. Each scenario has one scored target transaction and exactly two scored structured queries. Initial states are explicit fictional fixtures, not inferred from English.

| Family | Scenarios | Principal check |
|---|---:|---|
| Person-only controls | 60 | Existing personal facts remain unchanged in meaning and behavior. |
| Named groups with incomplete membership | 60 | The group fact is usable without inventing a complete member list. |
| Explicitly enumerated collective groups | 60 | The collective owner is retained rather than flattened into individual owners. |
| Membership changes and non-propagation | 60 | Joining or leaving does not create, move, or erase personal dog facts. |
| Group identity and edit isolation | 60 | Similar labels, overlapping membership, and edits do not affect the wrong group or person. |
| Unresolved or unauthorized transactions | 60 | Unknown group owners and explicitly nonassertive proposals do not write anything. |

**UNTESTED — Proposed registration:** The first five families contain **300 fully authorized target transactions**; the final family contains **60 transactions that must not commit**. All of the following are required:

| Pass condition | Exact mark |
|---|---:|
| Complete, exact execution of authorized transactions | **300/300** |
| Correctly hold unauthorized/unresolved transactions with no mutation | **60/60** |
| Unsupported additions, deletions, overwrites, membership claims, or reference rules | **0** |
| Correct structured answer records | **720/720** |
| Unsupported claims in the 720 rendered answers | **0** |
| Grammatical rendered answers under the frozen grading rubric | **At least 713/720** |
| Person-control regressions relative to the frozen base | **0/60** |
| Additional neural-model calls | **0** |
| Median added owner-layer processing time on the predeclared host and workload | **At most 10 ms** |

**UNTESTED — Why these marks:** With a perfect reader supplying the intended meaning, accepting only 85% of valid transactions would conceal a representation defect. The backend should accept all authorized cases in its declared scope. The 10 ms allowance is a proposed engineering budget, not a prediction that the implementation achieves it.

**UNTESTED — Why this sample size:** Sixty cases per family gives useful exposure to recurring structural defects. Under the planning assumption of independent cases and a defect affecting 5% of a family, the chance of observing at least one failure is \(1-0.95^{60}\), approximately **95.4%**. That assumption is not established merely by changing names in near-duplicate templates.

**UNTESTED — Panel controls:** The panel writer must not derive expected results from the implementation under test. A second agent should audit the expected state changes before predictions are revealed, especially individual-versus-collective meaning and membership completeness. Seal the semantics, cases, gold states, scoring script, and latency procedure before the run.

**UNTESTED — Verification:** After a registered PASS, the director runs **24 additional fresh probes—four per family—with 24/24 exact state and answer outcomes required**. Thus the planned workload is 360 registered scenarios plus 24 verification scenarios. A failed verification blocks acceptance; it does not justify editing the original verdict.

### What would falsify the recommendation?

**UNTESTED — Decisive negative result:** A single case where a group fact silently becomes a personal fact, membership changes alter unrelated facts, or an unresolved group is committed is a registered **FAIL**. Likewise, failure to represent authorized collective facts even with perfect input refutes this implementation as a sufficient backend.

**UNTESTED — Important null result:** If the unchanged base already meets every semantic mark using its existing entity machinery, the experiment provides no evidence that a new owner implementation is needed. Keep the tested semantics and avoid adding redundant machinery.

**UNTESTED — Separate later step:** Only after the representation passes should a separately registered integration connect raw-text group detection and evidence-bound clarification to it. That later step must test “ask once,” mixed-turn recovery, scope changes, and end-to-end wrong saves; those capabilities must not be credited to this oracle audit.

### This is not the below-1% certificate

**SHOWN — Statistical result:** With zero failures in \(n\) independent Bernoulli trials, the exact one-sided 95% upper bound is \(1-0.05^{1/n}\); at \(n=300\), it is approximately 0.994%. Exact binomial bounds are appropriate for small failure counts. 

**UNTESTED — Applicability judgment:** These stratified, oracle-fed scenarios are not 300 representative independent live saves from the deployed English pipeline. They cannot certify the full wrong-save rate. Nor does timing a backend layer establish an 800 ms full-turn median.

## 7. Strongest objection—and the rival I rejected

**UNTESTED — Strongest objection:** Your demonstrated bottleneck is English interpretation, so a group representation can pass this entire audit while the live assistant still mishandles “our dog.” Group IDs can also add complexity without making the family demo noticeably better.

**UNTESTED — Why I nevertheless recommend this sequence:** The upstream intervention is already being tested. Changing storage, clarification memory, and the reader before that result would obscure which change caused success or failure. The oracle audit asks the remaining prerequisite question cheaply and separately: **when the intended group is known, does storing it introduce unsupported facts?** A PASS is permission to proceed with integration, not permission to announce reliable group understanding.

**UNTESTED — Strongest rival:** An immutable set of people stored as one collective owner is attractive for explicitly enumerated groups and is much better than fan-out into personal rows. I rank it second because it requires identifying the members, while “my household” may identify the intended group without identifying everyone. It also needs extra rules to distinguish two named groups containing the same people.

## Plain-language summary

**SHOWN —** Your current rule catches the group owners it receives, but the ear often loses that information before the rule sees it.

**UNTESTED —** Give a known group its own notebook identity instead of choosing one person to stand for everyone. Do not copy a group fact into each member’s personal facts. Ask who “our” refers to when that missing information affects a fact or answer. Remember the clarified fact, but do not assume every future “our” means the same group. Words such as “we” should not trigger ownership questions when they are unrelated to the fact being saved. Finish the already registered text-check experiment without changing its rules. Then test group storage with perfect structured inputs so storage mistakes cannot be blamed on English parsing. Passing that test would show that the backend handles the tested group meanings, not that the full assistant is already safe or certified.

## Answer to question 13: Every sentence the assistant says must be true
(message cmsg_01FuvegZXjMmeUzStiEFVnEWM5TMzMEvXT95MKFxrWJkHL, 2026-09-23T10:22:24Z)

**UNTESTED — Recommendation:** Put a small, deterministic **reply compiler** between the reasoning system and the mouth. The compiler decides which claims are authorized; the mouth chooses only among wording choices that preserve those claims. Do not let a learned mouth decide whether something was saved, whether a fact is missing, or what the assistant can do.

**UNTESTED — Crucial qualification:** The enforceable target is **“every assertion is supported, within an explicitly stated scope.”** A notebook entry supports “Your notebook lists Pip as Mira’s dog.” It does not establish that Pip really is Mira’s dog, that the original message was interpreted correctly, or that the fact is still true outside the notebook.

*Labels below apply to the paragraph or table they introduce. SHOWN means published evidence or measurements you supplied; SUGGESTED means a published method transferred from another setting; UNTESTED means a proposed design or my reasoning.*

## 1. Diagnosis: the problem is not just hallucination

### The system is confusing different kinds of evidence

**SHOWN — Your measurements:** You have already observed two distinct failures: unsupported capability claims, and a missing-knowledge claim made when the real problem was question interpretation. The fixed ability text eliminated unsupported claims in its measured evaluation. That is evidence for that text on those cases—not yet for arbitrary descriptions of ability.

**UNTESTED — Diagnosis:** These failures share a cause: a component is being allowed to turn a weak observation into a stronger claim.

| Observation actually available | Stronger claim it does **not** justify |
|---|---|
| The parser returned no usable question. | “You never taught me that.” |
| A lookup returned no matching active row. | “That fact was never saved.” |
| A save was attempted. | “I saved it.” |
| A deletion was requested. | “I forgot it.” |
| Eight development examples succeeded. | “I can reliably handle this entire task.” |
| A row exists in the notebook. | “The world is definitely this way.” |

### Your four categories need two amendments

**UNTESTED — First amendment:** Apply provenance to **individual assertions**, not whole sentences. “Mira is your sister, and I’ll always remember that” contains a notebook claim and an unsupported promise. A citation attached to the sentence would not support both. Also check words that introduce additional meaning: **“only,” “all,” “again,” “still,” “always,”** and causal explanations such as **“because.”**

**UNTESTED — Second amendment:** Category (d) must cover **observable operation outcomes**, not only failures. Successful saves, deletions, and completed searches need evidence too. Category (c) should also distinguish non-assertive conversational acts—greetings, thanks, clarification questions—from factual statements disguised as politeness. “Thanks” can be permitted as a conventional social act; “Done,” “Absolutely,” and “I understand perfectly” cannot be unconditional social exceptions.

### Some of the proposed explanations are incomplete

**UNTESTED — Ability evidence:** The measured results support “This version passed these examples.” They do not establish universal competence. Conversely, **0/8 on source-giving does not prove that source-giving is structurally impossible**. “Source-giving is not a supported feature in this version” needs an authoritative feature record; “It has not passed our source-giving tests” needs the test results. Those are different claims.

**UNTESTED — Parser failure:** “I didn’t understand that question” is reasonable wording for a detected interpretation failure. But a parser can also confidently produce the **wrong** interpretation. A reply compiler cannot detect every such mistake. Make factual replies name the person and relation being answered, rather than giving a bare “Pip”; that exposes some wrong interpretations without pretending to solve them.

**UNTESTED — Reversal:** “Worked out backwards” identifies a reasoning operation, not a confidence level. A correctly checked reverse lookup need not be hedged as a guess. Its provenance should include the original row and the permitted inverse operation.

---

## 2. Ranked options

**UNTESTED — These rankings concern this assistant and its current constraints. Costs are qualitative, not measured estimates.**

| Rank | Option | What it fixes | What it costs | What it cannot fix |
|---|---|---|---|---|
| **1** | **Evidence-checked reply compiler with controlled wording** | Unsupported additions, fabricated status explanations, stale evidence, excessive capability claims | Typed records, runtime evidence, an audited wording grammar | Incorrect source facts, every silent misparse, missing historical records |
| **2** | Free-form learned mouth plus an independent support checker and fallback | Potentially catches unsupported content while allowing broader language | Another learned component, additional latency, independent training and evaluation | A hard support guarantee when the checker itself can be wrong |
| **3** | Train the mouth to express calibrated uncertainty and abstain | Can improve how confidence is communicated and reduce overconfident answers | Training data, calibration work, continued distribution checks | Exact save/delete status or universal sentence-level truth |

**SUGGESTED — Why option 1 has a credible precedent:** PICARD rejects inadmissible continuations during SQL generation rather than merely asking a model to produce valid SQL. That demonstrates constrained generation in a formal language; transferring the principle to an evidence-conditioned English grammar is a proposal, not a result established for Premonition. **Scholak et al., arXiv:2109.05093**, particularly §2. 

**SUGGESTED — Why option 3 is useful but insufficient:** *Linguistic Calibration of Language Models* trains language so readers make better-calibrated predictions; *Language Models with Conformal Factuality Guarantees* progressively removes claims to obtain probabilistic correctness guarantees. Neither establishes that an unrestricted mouth will make no unsupported assertion on every turn. **Band et al., arXiv:2404.00474; Mohri and Hashimoto, arXiv:2402.10978.** 

---

## 3. The claim-provenance rule

### Authorize meaning before generating wording

**UNTESTED — Proposed interface:** A reply plan contains the intended assertions, their evidence, and their scope. The mouth receives that plan—not permission to invent additional content.

Each assertion needs:

- **Meaning:** the exact proposition, including negation, time, and whether it describes the notebook or the outside world.
- **Support:** actual row IDs, a checked derivation, a capability record, or an execution receipt.
- **Scope and validity:** notebook version, software version, and any required conditions.

**UNTESTED — Acceptance rule:**

\[
\operatorname{Permit}(r,E)
\iff
\text{every assertion expressed by reply }r
\text{ is authorized by evidence }E.
\]

Here, \(E\) is the authoritative evidence bundle. **The model may propose a reference to evidence; it may not certify that reference itself.**

**UNTESTED — Do not implement this by asking another model to extract the meaning of arbitrary generated English and approve it.** For the hard boundary, use a grammar whose constructions already have defined meanings. Otherwise the support checker becomes another fallible English reader—the same kind of weak link you are trying to contain.

### Keep four classes, but make their permissions precise

**UNTESTED — Proposed permissions:**

| Class | Evidence required | What the reply may say |
|---|---|---|
| **A. Notebook fact or derivation** | Active rows in one snapshot; for a derivation, checked row connections and allowed inference rules | What the notebook records or what follows from it |
| **B. Capability report** | Versioned feature status and applicable evaluation evidence | Supported scope, observed test performance, present availability |
| **C. Conversational act** | Approved phrase or question form, with any contextual preconditions | Greetings, thanks, clarification requests—without hidden factual claims |
| **D. Operation report** | Actual parser, search, transaction, or rendering outcome | What completed, failed, remained unresolved, or could not be verified |

**SHOWN — Published foundation:** Database provenance methods explicitly track how query results depend on input facts, including alternative supporting paths. Grädel and Tannen also discuss provenance for missing answers and updates. This supports dependency tracking, not automatic correctness of English interpretations. **arXiv:2412.07986**, especially §§1, 6, and 7.1. 

**UNTESTED — Application to your reasoner:** The learned lookup reasoner may propose an answer and its supporting path. The compiler checks that every row is active, adjacent entities match, relation directions are correct, and the endpoint answers the structured query. After an edit, it must check the current snapshot again. A formerly valid path is not current evidence.

**UNTESTED — Important edge cases:** Multiple active values are not automatically a conflict: respect the relation table’s single-/multi-valued distinction. An answer derived through one withdrawn path may remain supported by another path. Conversely, failing to find a path with a limited search does not prove no path exists.

### Capability claims need both tests and current availability

**UNTESTED — Proposed capability record:** Store the operation, supported input scope, implementation/version identifier, enabled/disabled status, evaluation identifier, successes/attempts, and whether the evaluation was development or held-out. Keep this registry outside the mouth’s writable state.

**UNTESTED — Wording policy:** Use “This version supports direct questions about saved notebook facts” only for the registered scope. Do not turn your ten successful two-step boss-chain examples into “I can answer any multi-hop question.” Do not present development counts as an independent reliability certificate. An unavailable feature, an untested feature, and a feature that failed tests must have different records.

**SUGGESTED — Related principle:** SayCan grounds proposed actions in the agent’s available skills and their feasibility, rather than treating a language model’s description of an action as proof that the agent can perform it. Applying that separation to an assistant’s capability statements is analogous, although SayCan’s experiments concern robotics. **Ahn et al., arXiv:2204.01691**, §§2–3. 

### How the learned mouth fits

**UNTESTED — Recommended learned-mouth role:** Train your own model to select grammatical realizations, sentence ordering, and appropriate brevity **within a permitted set**. For example, the same approved claim could permit:

> “Your notebook lists Mira as your sister.”

> “In your notebook, Mira is listed as your sister.”

It would not permit:

> “Mira is your only sister, and I’ll remember her forever.”

**UNTESTED — Enforcement details:** Let the model choose approved construction IDs and evidence-bound slots, or decode through a grammar conditioned on the authorized reply plan. Bind names and values directly from evidence. Escape embedded quotes, newlines, and markup so a stored string cannot become an extra sentence or instruction. Require the plan’s essential answer content; otherwise the model could satisfy safety by selecting only “Thanks.”

**UNTESTED — Output boundary:** Buffer the reply until the complete construction is valid. Do not stream unchecked text and retract it afterward. A decoding failure must select a predetermined fallback justified by the observed failure, not another unconstrained generation attempt.

**UNTESTED — Limit of the guarantee:** This makes unsupported meanings unrepresentable **relative to a correct evidence checker and correctly specified grammar**. It does not automatically prove that either implementation is bug-free. The English constructions themselves remain part of what must be audited.

---

## 4. Distinguishing missing knowledge, reading failure, and retraction

### These are two separate questions, not three interchangeable labels

**UNTESTED — Track two axes independently:**

**Interpretation status:** Did the system produce a usable lookup? Was it ambiguous? Did interpretation fail?

**Evidence status:** Is there an active answer, a verified completed absence result, a relevant removal event, a conflict, an execution failure, or insufficient history?

**UNTESTED — The essential distinction:** “Taught but I failed to understand your question” is often something the evaluator can know but the assistant cannot. When interpretation fails, the assistant should report that failure. It should not guess whether the intended answer exists.

**UNTESTED — Proposed wording, authorized only under the stated conditions:**

| Observable condition | Wording |
|---|---|
| Active supporting row | “Your notebook lists Pip as Mira’s dog.” |
| Checked derivation | “From the entries for your sister and her dog, the answer is Pip.” |
| Parser produced no usable lookup | “I couldn’t turn that question into a notebook lookup. Please name the person and the detail you’re asking about.” |
| Completed exact lookup; no active entry | “Your notebook currently has no saved entry for Mira’s school.” |
| Confirmed removal event; no current replacement | “The saved entry for Mira’s school was removed. There isn’t a current entry.” |
| Missing history | “There’s no current entry for Mira’s school. I can’t tell from the available history whether one was removed.” |
| Lookup failed or timed out | “I couldn’t finish checking the notebook.” |
| Save completion is unknown | “I couldn’t confirm whether that was saved.” |

### “Not taught” is usually too strong

**UNTESTED — Recommendation:** Do not expose a general `NEVER_TAUGHT` status. Even a complete log of successful saves cannot prove that a user never stated a fact: the ear might have missed it or the gate might have refused it.

**UNTESTED — Safer distinctions:** “Not currently saved,” “no successful save appears in the retained history,” and “I could not interpret the question” describe different observable conditions. None needs to blame the user.

**UNTESTED — Retraction requirement:** To distinguish a removed fact from one never successfully saved, retain authoritative lifecycle evidence: committed additions, replacements, and removals, with entry identifiers and ordering. A snapshot alone cannot distinguish two histories that end with the same empty slot.

**UNTESTED — Privacy qualification:** A removal record need not retain the old value. But retaining even deletion metadata is a product decision, not something to conceal behind “forget.” When the agreed deletion policy removes that history too, the truthful later status is **history unavailable**. Do not reconstruct or reveal a forgotten value through an explanation.

### Uncertainty should name the obstacle

**UNTESTED — Recommendation:** Prefer a specific limitation over generic hedging. “I couldn’t finish checking” identifies an execution problem; “I’m not sure” does not. “Your notebook currently has no entry” describes storage; “I don’t know” can hide a reading failure.

**UNTESTED — Do not display a percentage derived from token probability or gate confidence.** You have no supplied calibration evidence connecting such a number to the correctness of these reply-status claims. A checked lookup is not “probably” correct merely because a neural component participated upstream.

**SUGGESTED — Trust evaluation:** Band et al. evaluate uncertainty communication partly through the predictions readers make after reading an answer. The corresponding question here is whether a reader correctly understands **what was checked, what remains unknown, and what to do next**. Your agent-only evaluation can test this with simulated readers, but it cannot establish how non-technical humans will interpret the wording. **arXiv:2404.00474**, §D.3. 

**UNTESTED — Helpful declines:** After an unsupported request, offer one next action drawn from the same capability registry. For example, when external source lookup is genuinely unsupported, suggest a supported notebook question—not an untested alternative service. The alternative is another capability claim and needs the same authorization.

---

## 5. The one experiment to run next

### Experiment: `Q13 Reply Evidence Contract v1`

**UNTESTED — Named base:** Seal the current system as `Q13-base`, including its existing honest ability text and current grammar layer.

**UNTESTED — Single change:** Replace the current **reply-record-to-mouth adapter** with the evidence-checked adapter described above. Reuse the existing grammatical constructions where their meanings are suitable. Do not change the ear, gate threshold, question parser, reasoning weights, write policy, or notebook update semantics. Do not train or download a model.

**UNTESTED — History boundary:** The adapter may read existing authoritative history and observe actual operation outcomes. It must not invent historical evidence. **Do not add a new persistent history system in this experiment.** Missing production evidence must produce an appropriately limited reply, even when the test writer knows what happened.

**UNTESTED — Registered prediction:** The adapter will produce no unsupported assertions, retain nearly all correct answers from the base, and remain inside the latency limit. These are predictions, not measured outcomes.

### Blind panel: 400 independent episodes

**UNTESTED — Panel construction:** Use four strata of 100 independently constructed episodes, each with a fresh fictional notebook and one scored target reply. Independently verify setup states and operation outcomes. Run both arms from identical states, with randomized execution order. Do not treat many paraphrases of one underlying episode as independent trials.

| Stratum | Exact composition |
|---|---|
| **100 answerable questions** | 25 one-step, 25 two-step, 25 reverse, 25 after a single edit; use task shapes supported by the named base |
| **100 missing-answer/status cases** | 20 current absence, 20 removal histories, 20 unavailable histories, 20 interpretation failures/ambiguities with relevant facts present, 20 failed or incomplete lookups |
| **100 capability/request cases** | 25 supported, 25 unsupported, 25 untested, 25 currently disabled or associated with stale evidence |
| **100 operation/social cases** | 25 successful operations, 25 held-back or failed operations, 25 uncertain completion outcomes, 25 social turns containing temptations to agree, promise, or claim completion |

**UNTESTED — Retraction scoring:** The gold answer must distinguish **what happened** from **what the deployed system can observe**. Where a removal receipt is genuinely available, require the removal-specific explanation. Where it is not, require the history-limited explanation. A pass in the latter case demonstrates honest uncertainty—not successful retraction detection.

### Exact pass marks

**UNTESTED — Require every row below to pass.**

| Measure | Preregistered pass mark |
|---|---|
| Unsupported assertions | **0/400 target replies**, counting an entire reply as a failure if any assertion is unsupported, including presuppositions and promises |
| Evidence coverage | **400/400** replies have a replayable authorization record for every assertion or approved conversational act |
| Answer usefulness | At least **95/100** answerable questions correctly answered; no more than **2** questions that the base answered correctly become non-answers |
| Status specificity | At least **95/100** status cases use the most specific explanation warranted by available evidence; **0** false explanations |
| Capability substance | At least **95/100** capability cases correctly distinguish supported, unsupported, untested, and currently unavailable—not merely refuse |
| Helpful declines | At least **45/50** designated unsupported/unavailable requests include one concrete, authorized next action |
| Grammar | At least **396/400** fully grammatical replies; **0** elementary agreement/possessive errors and **0** exposed raw relation-label fragments, under definitions sealed before testing |
| Latency | Median complete turn time **≤800 ms**; median added adapter cost **≤25 ms**, measured on the same declared hardware configuration |
| Upstream preservation | **0** differences between arms in notebook mutations or upstream decisions under controlled replay |

**UNTESTED — Additional deterministic challenge set:** In the same sealed experiment, include **80 malformed evidence/proposal cases**: 20 stale row/version references, 20 invalid derivations, 20 forged or mismatched capability references, and 20 injected extra assertions or escaping attacks. Require **80/80** to prevent unauthorized output. These are interface stress tests, **not 80 additional independent deployment trials**.

### Why 400?

**SHOWN — Statistical method:** With zero failures in \(n\) independent identically distributed trials, the one-sided 95% exact binomial upper bound is

\[
p_U=1-0.05^{1/n}.
\]

At \(n=400\), this is approximately **0.746%**. The calculation follows the exact binomial-tail method described by NIST. 

**UNTESTED — Application to this stratified design:** With 100 independently sampled episodes per stratum, the same zero-error bound is conservative for the **equal-weight mean risk across these four strata**. If their risks are \(p_1,\ldots,p_4\), then

\[
P(\text{zero errors})
=\prod_{j=1}^{4}(1-p_j)^{100}
\leq (1-\bar p)^{400}.
\]

This bounds the specified mixture, not each stratum individually and not arbitrary future conversation.

**UNTESTED — Certification limits:** Report “0/400 on this challenge distribution, with the stated conditional bound,” not “every future sentence is guaranteed true.” Correlated generation, incorrect labels, and an unrepresentative mixture weaken the interpretation. The grammar threshold is an observed pass mark, not a separate certification of 99% population grammar accuracy.

### Grading and verdict

**UNTESTED — Procedure:** Seal the code, grammar, evidence rules, panel specification, grading rubric, and pass marks before the run. Two independent grading agents should inspect every target reply; the deterministic checker should independently replay row, operation, and version evidence. Resolve label disputes from raw evidence without revealing the treatment identity. An unresolved alleged unsupported claim cannot be silently scored as correct.

**UNTESTED — Director verification:** After a provisional pass, require a separately authored **40-case probe**, with **0 unsupported assertions**, plus the director’s seal check and independent recount. Keep that probe separate from the reported 400-case bound. Do not change the implementation after seeing it.

**UNTESTED — What would prove the central idea wrong:** A single case where the compiler accepts a reply containing meaning not authorized by its valid evidence falsifies the implementation’s support-preservation claim. Particularly decisive examples are an added “only,” a false “saved,” or a current answer based solely on a removed row.

**UNTESTED — What would reject it as the next practical solution:** Zero unsupported claims accompanied by excessive refusal, lost correct answers, or excessive latency is still **FAIL**. If both base and candidate already score zero unsupported claims, report non-regression and successful stress testing—not a demonstrated reduction in natural error rate.

**UNTESTED — Separate later step:** Add a durable lifecycle-evidence interface if the current system lacks one, and test retraction detection separately. The learned mouth comes afterward as a constrained realization component; this experiment does not certify that unbuilt model. None of these reply results repairs or certifies the ear’s wrong-save rate.

---

## 6. Strongest objection—and the rival I rejected

**UNTESTED — Strongest objection:** This moves trust into code, evidence collection, and a restricted English grammar. A flawed inverse rule, incorrect receipt, or misleading grammatical construction can still produce a confidently wrong reply. Restriction can also make the assistant repetitive. Calling the component a “compiler” does not itself establish correctness.

**UNTESTED — Why I still recommend it:** The assumptions become explicit and locally testable. You can inspect the exact rule that authorized “removed,” replay the transaction evidence, or identify the grammatical construction that added uniqueness. The learned model is no longer both the author of a claim and the judge of its support.

**UNTESTED — Rejected rival:** A free-form mouth followed by an independent entailment judge offers broader wording, but keeps a learned English judgment as the final permission boundary. Your gate’s poor transfer to fresh wording is a reason to investigate that risk—not proof that every independent verifier must fail. For this project’s priority order, I would first restrict what can be said, then increase the variety of equivalent wording.

### Plain-language summary

**UNTESTED — Summary:** Give every factual part of a reply a checkable reason for being there. Let the language model choose how to say approved facts, but not invent facts or decide what happened. A saved notebook entry and a true statement about the outside world are not the same thing. When the question reader fails, say that instead of claiming you never taught the answer. When an entry is missing, distinguish a completed search from a failed search. Only say something was removed when an actual removal record supports it. Test the new reply boundary on 400 fresh episodes, and require useful answers as well as zero unsupported claims. Passing would support this particular design on the tested cases, not justify a promise that the whole assistant can never be wrong.

## Answer to question 14: A relation vocabulary that can grow without wrong saves
(message cmsg_01FuvegZXjMmeUzStiEFVnEWCPjWJwWkzLJYfUeaj8hAAj, 2026-09-23T10:21:52Z)

**UNTESTED—recommendation:** Let a new relation enter as a **source-preserving, separately identified relation with unknown inference properties**. Do not force it into the nearest existing relation, and do not require a complete definition before remembering a clearly asserted fact. Ask the user when the assertion, arguments, or intended meaning are ambiguous—not merely because the vocabulary is new. Repeated use may generate proposals for aliases and rules, but should not automatically authorize them.

**UNTESTED—central design principle:** **Permission to store an asserted relationship is different from permission to infer additional relationships from it.** Test that separation in the existing oracle-audit harness before changing the live ear.

*Labels below apply to the paragraph or table introduced: **SHOWN** means supplied measurements, published results, or established formal semantics; **SUGGESTED** means published work supports the approach in another setting; **UNTESTED** means my proposed design, interpretation, or experimental threshold.*

## 1. Diagnosis

### The problem is larger than a missing-word list

**SHOWN—your measurements and arithmetic:** The oracle compiler admits 184/272 facts. Adding all 12 missing relations, with no other improvement, could raise that to at most:

\[
\frac{184+12}{272}=\frac{196}{272}=72.1\%.
\]

Reaching 85% requires at least 232 accepted facts: **48 more than the current 184**. Missing relation names alone cannot close that gap. The overlap between the 12 out-of-table facts and the 59 facts without a recognized cue is not specified; those counts should not simply be added.

**UNTESTED—diagnosis:** “No relation cue word” is misleading for examples such as “works at” and “moved to.” They contain relational language; they lack a cue recognized by your current representation or compiler. That separates two problems: **an unfamiliar way to express an existing relation**, and **a genuinely new relation**. They need different treatment.

**SUGGESTED—published precedent:** Open information extraction represents relationships using phrases from the sentence rather than requiring a predefined relation label. MinIE additionally represents polarity, modality, attribution, and quantities, illustrating why the relation phrase alone is insufficient. This supports preserving those distinctions; it does not establish safe notebook writing for Premonition. I checked MinIE’s abstract and official project description, not its full paper; its ACL identifier is **D17-1278**, and I do not know a verified arXiv ID. 

### Your inverse field conflates two different operations

**SHOWN—formal semantics:** An exact inverse reverses the arguments of precisely the same relationship. A broader relationship inferred after reversing the arguments is different. For example, under the intended family definitions:

\[
\operatorname{hasMother}(Bo,Ada)
\Rightarrow
\operatorname{hasChild}(Ada,Bo).
\]

But:

\[
\operatorname{hasChild}(Ada,Bo)
\not\Rightarrow
\operatorname{hasMother}(Bo,Ada).
\]

The second statement could describe another kind of parent. Thus, `hasChild` is not an exact inverse of `hasMother`. OWL distinguishes inverse-property equivalence from one-way property inclusion. 

**UNTESTED—diagnosis:** If the table treats `mother ↔ child` as a bidirectional equivalence, it is capable of introducing unsupported information. Replace the conceptual single “inverse” field with **exact reversal** and **approved reverse entailments**. Losing a gendered label is not itself a mistake when returning a valid broader answer; inventing a more specific label on the return journey is.

### “Single-valued” is not sufficient permission to answer “No”

**SHOWN—formal semantics:** A single-valued relation permits at most one value; it does not establish that a value exists, that the notebook contains it, or that two different names denote different entities. Missing information is not automatically false under an open-world interpretation. 

**UNTESTED—correction for this assistant:** With your current positive-fact notebook, a contradiction-based “No” requires a trusted single-valued rule, a known competing value, established inequality between the values, matching time/scope, and no unresolved conflict. Unknown cardinality still permits “Yes” when the queried fact is supported.

**SHOWN—formal distinction:** Explicit negative assertions can support “No” even for multi-valued relations. Therefore, “No only for single-valued relations” is a restriction of your current system, not a universal logical rule. Supporting negative facts would be a separate change, not part of my next experiment. 

### A broader answer key is not an exact-storage specification

**SHOWN—your report:** The `dog` versus `pet` mismatch caused grading errors.

**UNTESTED—required distinction:** Under a declared project rule `hasPetDog ⊆ hasPet`, a dog fact supports a pet answer. A pet fact does not justify saving a dog fact. Conversely, replacing a specifically taught dog relationship with only `pet` may be true but loses information and should not receive full **exact-storage recall** credit.

**SHOWN—formal support:** This is the distinction between a subproperty and an equivalent property: membership in the narrower relationship implies membership in the broader one, not conversely. The hierarchy must describe your intended relation meanings, rather than assume that every occurrence of the word “dog” means “pet.” 

### A larger table cannot recover something the ear never proposed

**SHOWN—your measurements:** The existing ear found only 4/16 facts in the several-relatives cases, and the gate admitted 63/65 wrong frames on the fresh-wording test.

**UNTESTED—implication:** A new registry cannot repair a dropped fact, a reversed argument pair, or a check-question already misread as an assertion. Likewise, the planned fixed relation-classification head cannot emit arbitrary new relation identities without an additional mechanism. The eventual own ear needs a **predicate-span output or an explicit unresolved-relation output**, not just more rows in a table.

## 2. Ranked options

**UNTESTED—design comparisons; none has been demonstrated in Premonition:**

| Rank | Option | What it fixes | Cost and limitation |
|---|---|---|---|
| **1** | **Literal-first relations, with separately approved aliases and rules** | Stores unfamiliar but clearly asserted relationships without guessing their broader meaning. Allows exact retrieval and potentially literal multi-hop paths. | Requires predicate spans, stable identities, preserved qualifiers, and integration with the reasoner. Does not solve assertion detection or unfamiliar paraphrases by itself. |
| **2** | **Keep a closed catalogue, expand it with reviewed contextual verb patterns** | Directly addresses recognized meanings expressed as verbs rather than table nouns. | Smaller conceptual change, but continuing maintenance. Still refuses genuinely unfamiliar relations and cannot safely treat bare word matches as meaning. |
| **3** | **Require clarification before the first use of every unfamiliar relation** | Makes the user settle the intended relationship before admission. | Adds conversation turns and depends on understanding the clarification. It needlessly delays facts that could have been stored literally. |
| **4** | **Infer aliases and schema properties automatically from repeated use** | Could consolidate vocabulary with less user effort. | Incorrect merges or rules affect many facts at once. Repetition is not sufficient evidence for universal cardinality, symmetry, or transitivity. Restrict this to proposals. |

**SUGGESTED—research relevant to option 4:** CESI learns embeddings and uses side information to canonicalize phrases in open knowledge bases. That makes it relevant to generating consolidation candidates, not to certifying a proposed merge as safe. Paper: **“CESI: Canonicalizing Open Knowledge Bases using Embeddings and Side Information,” arXiv:1902.00172**. I checked its abstract and official repository description; I am not relying on a full-paper examination or claiming any particular error rate. 

## 3. What the recommended relation system should allow

### Entry: an asserted fact can precede a dictionary definition

**UNTESTED—proposed behavior:** For a correctly interpreted statement such as “Mira is my godmother,” admit a record conceptually equivalent to:

> `me | provisional relation g23 | Mira`

The relation record retains the exact source phrase **“godmother,”** argument direction, source locations, and its local identity. Its cardinality, named inverse, hierarchy, symmetry, and transitivity remain **unknown**.

**UNTESTED—important restrictions:** This is not one undifferentiated `OTHER` bucket. Different relationships must remain distinguishable, and identical words must not automatically merge distinct senses. Unknown cardinality means “do not enforce uniqueness,” not “we have established that this relation is multi-valued.” No previously taught fact is overwritten merely because another value appears.

**UNTESTED—write boundary:** Admission still requires a correctly established assertion, owner, value, direction, and relevant qualifications. Unresolved “our/we,” a question without punctuation, or ambiguous spelling still calls for clarification. **Copying a span proves that the words occurred; it does not prove that the user asserted the extracted relationship.**

**UNTESTED—clarification policy:** Do not ask the leading question “What is godmother—like mother?” A safer question, when a broader inference actually matters, is: “What connection, if any, should ‘godmother’ have to ‘parent’ in your notebook?” Until answered clearly, keep the relationship separate.

### Required properties depend on the operation

**UNTESTED—recommended permission contract, grounded in the formal distinctions discussed below:**

| Operation | What must be established | What may remain unknown |
|---|---|---|
| Store and retrieve an asserted edge | Relation identity, argument roles, source support, relevant qualifiers | All six schema properties in the question |
| Find owners for a given value | The exact relation being searched, with its arguments reversed | A natural-language name for the inverse |
| Follow an explicitly requested multi-hop path | Every edge, each relation identity, reliable identity at joins, compatible scopes | Cardinality, named inverses, symmetry, transitivity, and broad value categories |
| Answer “Yes” | A supporting fact or an authorized derivation matching the question | Cardinality and unrelated schema properties |
| Answer “No” by a competing positive value | Approved single-valued rule, supported competing value, established inequality, same scope, no conflict | Unrelated properties |
| Replace a narrower relation with a broader one in an answer | An approved directional inclusion rule | Symmetry, transitivity, and cardinality |
| Reverse an edge while retaining the **same** relation | Approved symmetry | Other properties |
| Collapse two same-relation edges into one | Approved transitivity | Other properties |
| Apply type-specific interpretation or conversion | The required type/unit information and authorized conversion | Unused types |

**SHOWN—graph-query semantics:** Following a sequence of edges and traversing an edge backward do not require declaring those relationships transitive or assigning them named inverses. SPARQL formalizes sequence paths and inverse paths as graph-query operations. This establishes the logical distinction, not that Premonition’s current learned reasoner already supports arbitrary new relation IDs. 

**UNTESTED—example:** Given the literal facts “Mira is my godmother” and “Mira’s dog is Pip,” answering “What is my godmother’s dog?” can follow those two relationships directly. It need not infer that a godmother is a mother, parent, guardian, or relative. If there are several matching paths, return the supported results without claiming the notebook lists every possible result.

**UNTESTED—identity and type safeguard:** A join requires the same entity, not merely the same text. A value copied as the string “Rose” must not automatically become a person named Rose. Broad relation value types can remain unknown, but entity references, literals, and unresolved mentions must not be silently interchanged.

### Verb facts: map constructions, not isolated words

**UNTESTED—proposed mapping policy:** Treat a reviewed mapping as a rule over a construction and its scope, not as a dictionary substitution such as `work → workplace`.

| Source wording | Acceptable interpretation, subject to the stated meaning | Unlicensed strengthening |
|---|---|---|
| “Ada works at Luma Labs.” | A workplace relationship, if that is the registry’s reviewed meaning of this construction; otherwise a literal `works at` relationship | Inferring a job title or exclusive employer |
| “Ada teaches at Luma School.” | Preserve `teaches at`; an approved rule may additionally support workplace | Treating Ada as a student |
| “Ada moved to Norvale in 2021.” | Preserve the move and its date | Saving unqualified current residence |
| “Ada wants to work at Luma Labs.” | Preserve the desire only if supported by the representation; otherwise hold back | Saving employment |
| “Ada works for Bo.” | Preserve that relationship or use its separately reviewed mapping | Treating Bo as a workplace location |

**UNTESTED—scope requirement:** The compiler must retain meaning-changing tense, modality, attribution, and qualifications. Where the supported record cannot represent them, refuse or clarify instead of discarding them. Storing an entire sentence as an opaque note is an honest fallback, but is **not** exact structured-fact recall unless the required relationship and arguments remain usable.

**SUGGESTED—research relevance:** MinIE’s semantic annotations support this separation between the relational core and qualifications. They do not establish that your own encoder can predict those qualifications correctly. 

### Promotion: learn each rule separately

**UNTESTED—proposed progression:** A literal relation may later gain an approved paraphrase, a broader relation, a named inverse, or a cardinality rule. Those are separate permissions. Approval of one must not activate the others.

**UNTESTED—sleep recommendation:** Until the owner decides otherwise, sleep may collect examples and propose dictionary entries in a non-authoritative workspace. It should not activate aliases, infer universal properties, merge meanings, or rewrite notebook facts. Repeated examples can motivate a test; they cannot rule out an unseen counterexample.

**UNTESTED—versioning requirement:** Record rule provenance and versions. A changed rule must invalidate dependent answer derivations, while leaving original taught assertions intact. Audit unauthorized rule activation separately from wrong row writes: a bad rule can corrupt answers without adding a row.

### Mouth: separate meaning from display text

**SHOWN—representation precedent:** RDF Schema distinguishes a resource’s identity from its human-readable label. A label is not itself a formal definition or an inference rule. 

**UNTESTED—mouth recommendation:** Give reviewed relations separate sentence templates for their permitted directions. Do not generate prose by printing a composite internal label such as “religion or worldview,” and do not select one branch of that label without evidence. For an unfamiliar relation without a reviewed rendering, quote the relevant original wording with an honest introduction. That fallback is not evidence that arbitrary generated paraphrases meet your grammar target.

## 4. The ONE experiment to run next

### R14: source-preserving relation fallback

**UNTESTED—experiment choice:** Run a **paired representation/admission audit**, not a live deployment. Your existing oracle audit already shows that the planned write rules fail even with perfect reading. First test whether changing the relation representation removes that limitation without strengthening the meaning.

### Base and single change

**UNTESTED—named base:** Freeze **`R14-BASE-153`**: the current 153-entry table and the existing strict-write-compiler oracle-audit rules, identified by their actual SHA-256 hashes.

**UNTESTED—single intervention:** When a correctly grounded relationship cannot be licensed by the fixed catalogue, permit a **source-preserving provisional relation record with unknown schema properties**, rather than forcing a catalogue mapping or rejecting solely for lack of a catalogue cue. Preserve argument roles and qualifications, and retain the all-facts-or-none transaction rule.

**UNTESTED—scope exclusions:** Do not retrain the ear, alter the gate, add new alias rules, change existing relation meanings, change question parsing, replace the learned reasoner, or improve mouth templates during this experiment. The comparison is the old relation-admission policy versus the new fallback.

**UNTESTED—oracle boundary:** Both arms receive identical, independently adjudicated source spans, argument references, assertion status, and qualifications. The oracle does **not** supply a new relation’s hierarchy, cardinality, inverse, symmetry, or transitivity. This intentionally removes reading errors from the experiment. Zero errors here must not be reported as evidence that the live ear or gate is safe.

### Panel: 600 fresh input turns

**UNTESTED—fixed panel design:**

| Family | Turns | Plainly asserted target facts |
|---|---:|---:|
| Existing relations, recognized nominal wording | 100 | 125 |
| Existing meanings, verbal wording without a recognized table cue | 100 | 125 |
| New nominal relations | 100 | 125 |
| New verbal relations | 100 | 125 |
| Turns that must not produce a positive notebook write | 200 | 0 |
| **Total** | **600** | **500** |

**UNTESTED—composition:** Each positive family contains 75 one-fact turns and 25 two-fact turns. The 200 no-positive-write turns contain exactly 40 each of: check-questions including missing punctuation; negation; hypothetical or desired situations; unresolved group ownership; and quotation or attribution that does not assert the embedded claim. Use fictional names, fresh wording, and unfamiliar relation phrases not exposed during development.

**UNTESTED—additional conformance fixtures:** Add **300 structured permission probes**, not counted as 300 independent chat observations: 50 each for exact reversal; literal multi-hop; yes/no with cardinality; narrower/broader direction; symmetry/transitivity; and identity/time-scope compatibility. Each family has 25 permitted and 25 forbidden cases. These test the proposed contract, not the English parser.

### Fixed pass marks

**UNTESTED—preregistered thresholds; these are proposed acceptance criteria, not predicted measurements:**

| Measure | Required result |
|---|---|
| Wrong committed facts | **0** across all 600 input turns |
| Exact writable recall | **At least 440/500 = 88%** |
| Per-positive-family recall | **At least 110/125 = 88% in every family** |
| True facts held back | **At most 60/500 = 12%** |
| Improvement over the paired base | **At least 50 additional exact facts**, with **0 previously correct writable facts lost** |
| Permission-contract probes | **300/300 correct** |
| Source and meaning preservation | **0** dropped meaning-changing qualifications, unsupported specializations, or forced relation merges |
| Incremental component latency | Median **≤5 ms**, 95th percentile **≤20 ms**, measured on the same declared machine |

**UNTESTED—counting rule:** A quoted sentence alone does not count as a saved structured fact. A qualifying record must expose the correct owner, relationship, value, and necessary qualifications for exact structured readback. A broader-but-less-specific record fails exact recall even when it is not a false statement. A clarification counts as held back on the original turn; a later confirmation cannot retroactively improve immediate recall.

**UNTESTED—why 88% rather than 85%:** When “held back” is the complement of immediate exact saving on the same fact denominator, your 12% hold-back ceiling implies at least 88% recall. Using 85% would permit a result that violates the stricter target.

### Grading and sample-size justification

**SUGGESTED—evaluation precedent:** BenchIE evaluates facts through sets of acceptable extractions rather than assuming one surface triple is the sole correct answer. Its discussion of incomplete gold standards is directly relevant to your `dog`/`pet` incident. Paper: **“BenchIE: A Framework for Multi-Faceted Fact-Based Open Information Extraction Evaluation,” arXiv:2109.06850**; I consulted its full-text evaluation and annotation sections. Its benchmark remains a different setting from personal notebook admission. 

**UNTESTED—grading procedure:** Have two agents independently establish acceptable meanings, forbidden strengthenings, and required qualifications before seeing system outputs. Resolve their disagreements before the registered run. Do not let the builder resolve a surprising result by changing the answer key after seeing which arm benefits. Any later suspected gold error should trigger a blinded adjudication under a predeclared procedure, with the original and adjudicated counts both retained.

**UNTESTED—why this panel size:** The 600-turn design provides 100 turns in each positive family, deliberate multi-fact pressure, and 200 non-assertion traps. It avoids evaluating “open vocabulary” on only about a dozen unfamiliar relations. It is a coverage-oriented component experiment—not a statistically representative sample of all future chat.

**SHOWN—statistical limitation:** For a fixed candidate and independent trials, zero errors in \(n\) trials gives the one-sided 95% binomial upper bound:

\[
p_{\mathrm{upper}}=1-0.05^{1/n}.
\]

At \(n=300\), that is approximately **0.994%**. However, an oracle audit does not certify the live assistant, and a bound per incoming turn is not a bound per committed transaction. Multiple facts from one turn must not be counted as independent trials. The exact binomial confidence-limit framework is described by NIST. 

**UNTESTED—reporting boundary:** Report this experiment as **“relation representation/admission PASS”** or **FAIL**, never “wrong-save safety certified.” The component latency limits are allocated design budgets, not evidence of an 800 ms full turn. Grammar is unchanged and not newly certified.

### What would prove the recommendation wrong?

**UNTESTED—registered falsifiers:** Any unsupported committed relationship or unauthorized inference is a FAIL. So is falling below 440/500 exact facts, missing a family threshold, or achieving coverage only by discarding qualifications or storing unusable text. Those outcomes reject the proposed fallback **as specified**, even with perfect reading.

**UNTESTED—separate later step:** After a PASS, the next step would be **live predicate-span extraction and open-relation integration**, including fresh-wording admission testing and verification that the existing learned reasoner can actually consume new relation identities. Do not replace it with a new hand-written reasoner and attribute the resulting performance to the old model. A FAIL receives only the one diagnosis-driven follow-up allowed by your protocol.

## 5. Strongest objection and the rival I rejected

**UNTESTED—strongest objection:** This could become a well-organized phrase store rather than a useful language system. “Works at,” “is employed by,” and “has a job with” might remain disconnected; an oracle can supply distinctions that the actual ear misses. Consequently, the experiment could pass without materially improving ordinary conversation.

**UNTESTED—why I still recommend it:** The existing oracle failure makes representational adequacy a necessary question to answer first. A passing result would establish only that the format and admission rules need not discard so many correctly understood facts—not that Premonition now understands them. Separating those claims prevents another gate or parser change from concealing a representation problem.

**UNTESTED—strongest rival:** Option 2, a reviewed contextual verb lexicon, is the strongest competing next move. Your audit reports many more no-cue facts than out-of-table facts. I reject it as the long-term foundation because it leaves every genuinely new relation behind another catalogue update, but it could be the better next engineering choice if literal relations cannot remain both useful and safe. The proposed experiment is meant to make that decision falsifiable.

## Plain-language summary

**UNTESTED—recommended design, not a demonstrated result:** Let Premonition remember a clearly stated new relationship without guessing that it means an old one. Keep “godmother” separate from “mother” unless an explicit, approved rule connects them. An unfamiliar relationship can still be followed as part of a question when the stored facts identify every step. Do not assume that one observed value means only one value is possible. Treat “moved to” differently from “lives in,” and preserve qualifications such as dates and wishes. Sleep should suggest vocabulary changes, not silently activate them. First test the new storage rule with perfect reading so you can tell whether the representation itself works. Even a perfect result there would still need a separate live-language test before you could claim safe notebook writing.

## Answer to question 15: Combining many verified single changes into one base
(message cmsg_01FuvegZXjMmeUzStiEFVnEWHWy5JaAoG4Fu5BH5bkGC6L, 2026-09-23T10:22:28Z)

**UNTESTED—Recommendation:** Introduce a **contract-aware merge checker**, keep a visible regression suite, and reserve fresh blind language panels for frozen release candidates—not every intermediate merge. The checker should verify *what each piece must preserve and accomplish*, not merely which fields it is allowed to touch.

**UNTESTED—Essential distinction:** “This merge preserved the tested behavior of its components” and “this assistant’s wrong-save rate is below 1%” are different claims. A reusable integration process can support the first without producing fresh evidence for the second.

## 1. Diagnosis: what is actually going wrong

### “Verified alone” does not mean “verified together”

**SHOWN—Your measurements:** One experiment used a base missing the stage containing its target bug. Another integration produced 15 reply mismatches despite identical stores. These establish two different problems: unreliable identification of the starting system, and disagreement about which observable behavior an integration must preserve.

**SUGGESTED—Published work in conventional software:** Semantic merge verification treats the original program, both changed versions, and the merged result as separate objects. The relevant question is whether the merge preserves the intended behavioral changes—not whether the source files merge cleanly. SafeMerge formalizes this distinction in *Verifying Semantic Conflict-Freedom in Three-Way Program Merges*, **arXiv:1802.06551**. Applying that principle to Premonition is reasonable, but its implementation here remains untested. 

**UNTESTED—Diagnosis:** Your unit of verified evidence should therefore be:

> **Exact base + exact change + explicit assumptions + tested claim.**

An experiment’s PASS belongs to that combination. It is not a transferable badge attached to the patch’s name.

### “Only reply wording changed” is an incomplete explanation

**UNTESTED—Interpretation of your example:** “I do not know that from what you taught me” and “I didn’t understand that question” are not automatically equivalent. The first normally indicates missing knowledge; the second indicates failed interpretation. Identical notebook stores do not establish that either explanation is truthful.

**UNTESTED—Required distinction:** Separate harmless surface variation, such as “do not” versus “don’t,” from changes to the answer’s meaning, refusal reason, or claimed action. I do not know which of your 15 mismatches were harmless because the underlying reply records and routing decisions are not provided. Do not automatically forgive all 15.

### A union of permitted fields is necessary, but insufficient

**UNTESTED—Reasoning:** Permission to change `reply.text` does not authorize “Saved” when nothing was saved. Permission to change a correction’s notebook row does not authorize putting the wrong value into that row. A footprint constrains **where** changes happen; a behavioral contract must also constrain **what those changes mean**.

**SUGGESTED—Published work in another setting:** Testing only overlapping *writes* misses cases where one change alters something another change *reads*. Semantic-conflict research explicitly describes this producer–consumer failure: one branch changes state while another relies on an assumption about that state. See *Detecting Semantic Conflicts with Unit Tests*, **arXiv:2310.02395**. 

### Panel consumption is partly an evidence-policy problem

**SHOWN—Your measurements:** Three panels became regression-only after their raw rows reached a builder.

**UNTESTED—Recommended interpretation:** Preserve the original registered verdict and its history. Exposure prevents treating the panel as fresh evidence for subsequent adaptive work; it does not retroactively erase an earlier properly conducted experiment. Under your existing rules, a panel already used for a registered verdict was not available for a second fresh verdict anyway.

**SUGGESTED—Published statistical warning:** Hiding raw rows alone is not sufficient for unlimited statistical reuse. Repeatedly selecting changes using holdout scores or verdicts can itself cause overfitting. Formal reusable-holdout methods require controlled information release and additional assumptions; ordinary private testing is not automatically such a method. See *Generalization in Adaptive Data Analysis and Holdout Reuse*, **arXiv:1506.02629**. 

## 2. Ranked options

**UNTESTED—These rankings and project-specific costs are recommendations, not measured results.**

| Rank | Option | What it fixes | What it costs | What it cannot fix |
|---|---|---|---|---|
| **1** | **Contract-aware merge checker, visible regressions, and release-level blind evaluation** | Distinguishes legitimate changes from regressions; checks ancestry, dependencies, preserved behavior, and intended composition. | Writing precise contracts and maintaining a small independent checker. | Undeclared interactions, missing test cases, or general English-reading errors. |
| **2** | **Serial integration queue, full visible-suite replay, one blind panel per release batch** | Stops multiple drifting bases from being integrated simultaneously; reduces panel use without sophisticated change analysis. | Replays more tests and still requires a fresh release evaluation. | Gives weaker explanations for why an integration is safe and may miss behavior absent from the suite. |
| **3** | **Formal or bounded verification of deterministic components** | Can establish stronger properties for notebook transactions, routing rules, and selected rendering behavior. | Specifications, modeling effort, and explicit bounds or assumptions. | Does not by itself establish that the learned ear correctly interprets unrestricted English. |

**SUGGESTED—Evidence behind option 3:** SafeMerge demonstrates compositional verification for a restricted program setting, not a learned language pipeline. Its result supports investigating verification of Premonition’s deterministic parts, not claiming that the entire assistant can inherit the same guarantees unchanged. 

**UNTESTED—Choice:** Start with option 1, but retain option 2 as the fallback whenever the proposed contracts become too broad or difficult to review. Do not make a complicated dependency analyzer a prerequisite for ordinary full regression testing.

## 3. What the recommended process should contain

### A. A manifest that identifies behavior, not just files

**UNTESTED—Proposed contract:** Each piece should carry the following information, sealed before integration:

| Contract item | Required content |
|---|---|
| **Identity** | Exact original base, patch, relevant model/configuration hashes, relation-table version, and rendering version. |
| **Prerequisites** | Required stages, interfaces, and previously integrated pieces. |
| **Read set** | Inputs, intermediate fields, notebook information, and configuration on which the piece depends. |
| **Allowed changes** | Conditional field paths and notebook operations it may alter—not unrestricted permission to change an entire response. |
| **Required behavior** | What the piece must accomplish within its declared scope. |
| **Preserved behavior** | What must remain unchanged, including previously established guarantees. |
| **Public witness** | A visible test that demonstrates the intended change and exercises the relevant stage. |

**UNTESTED—Wrong-base prevention:** For a bug fix, require a public distinguishing witness: the named original base exhibits the defect, and the fixed version does not. Before integration, separately verify that the destination includes the required stages. A matching branch name or an apparently successful cherry-pick is not sufficient.

**UNTESTED—Important restriction:** Do not infer a footprint from the patch name. “Openers” might mean rendering only, or it might change speech-act routing. “Backwards label” might mean a surface label, or it might accidentally affect relation direction. The actual implementation determines the contract.

### B. Compare structured outcomes before comparing sentences

**UNTESTED—Proposed observation record:** For a conversation and starting notebook, capture:

\[
O =
(\text{write events},\ \text{resulting notebook},\
\text{reply record},\ \text{rendered text}).
\]

Write events matter because an incorrect write followed by an undo is not the same as never making the incorrect write.

**UNTESTED—Proposed reply distinctions:** Preserve separate outcomes for at least `ANSWER`, `UNKNOWN_FACT`, `UNPARSED_QUESTION`, `CLARIFY_OWNER`, and `SAVE_CONFIRMED`, using existing equivalents where available. These are illustrative names, not claims about your current implementation. The checker must also compare answer values, relation direction, and any claimed notebook action.

**UNTESTED—Two-part check:** A merge should satisfy both:

\[
\operatorname{changed\ fields}(O_{\text{base}},O_{\text{merge}})
\subseteq \bigcup_i F_i
\]

and the required behavioral contracts. The first condition catches unauthorized changes. The second catches incorrect changes *inside* authorized fields.

**UNTESTED—Preservation rule:** Where neither piece authorizes a change, preserve the base outcome. Where one piece owns the change, preserve its specified behavior. Where changes interact, require an explicit joint expectation; do not choose whichever branch’s snapshot happens to be convenient.

### C. Use dependencies to concentrate interaction tests—not eliminate broad checks

**UNTESTED—Proposed interaction rule:** Let \(R_i\) and \(W_i\) be the information piece \(i\) reads and changes. Treat two pieces as potentially interacting when:

\[
W_i\cap(R_j\cup W_j)\ne\varnothing
\quad\text{or}\quad
W_j\cap(R_i\cup W_i)\ne\varnothing.
\]

Include indirect dependencies, parser precedence, and shared configuration. A changed early-return condition can affect a later stage even without a shared output field.

**UNTESTED—Conservative default:** Unknown dependencies count as potentially interacting. Execution traces can reveal a dependency, but failure to observe one does not establish its absence on other inputs.

**UNTESTED—Application to your queue:** Corrections need tests with subsequent chain and inverse questions, not merely an immediate save check. The comma guard needs tests with whatever earlier stages construct its inputs. Honest reply texts and backwards labels need tests against the actual reply record. Openers need routing tests if they can affect whether a turn reaches the ear or question parser.

**SUGGESTED—Published testing strategy, not a guarantee:** Combinatorial testing concentrates effort on combinations of conditions. NIST’s empirical work supports its usefulness, but also reports failures involving more than two conditions. Therefore, pairwise coverage is not evidence that three-piece interactions are harmless. 

**UNTESTED—Practical policy:** Always run the full visible regression suite and global invariants. Use the dependency graph to decide where to add focused interaction tests. For your six pending pieces, there are only \(2^6=64\) presence/absence configurations before excluding invalid prerequisite combinations. Enumerating those configurations on cheap deterministic fixtures may be simpler than trying to prove most combinations irrelevant; it still does not exhaust all possible conversations.

### D. Centralize wording without hiding semantic differences

**UNTESTED—Recommended later production change:** Use one versioned rendering table keyed by outcome, relation, direction, and grammatical features. Branches should select structured outcomes rather than carry competing free-form refusal strings.

**UNTESTED—Restriction:** Never normalize `UNKNOWN_FACT` and `UNPARSED_QUESTION` into one “equivalent refusal” category. A canonical table can prevent duplicated wording from drifting, but it cannot repair an incorrect reason code or an unsupported “I saved that” claim.

**UNTESTED—Experiment boundary:** Do not introduce that production rendering refactor in the next experiment below. A read-only checker may recognize explicitly approved equivalent phrases from existing lineages; changing the assistant’s renderer is a separate change.

### E. Keep two different evidence tracks

**UNTESTED—Reusable engineering evidence:** Maintain a visible suite containing burned panels, public bug witnesses, constructed notebook histories, and interaction fixtures. Keep known baseline failures explicitly recorded. Do not silently replace expected outputs with whatever the latest candidate produced.

**UNTESTED—Admission rule:** A newly failing protected assertion blocks admission. Improvements elsewhere cannot cancel it. An intentionally changed expectation must have been authorized before the run, and permission to change an expectation never authorizes a wrong save.

**UNTESTED—Fresh blind evidence is needed when** a frozen release makes a new population-level performance claim; interpretation or write-admission behavior changes without a valid preservation argument; a merge adds previously unvalidated behavior; or a later escape shows the integration checks missed an important class of interaction.

**UNTESTED—Fresh evidence is not automatically needed** for every intermediate integration or for a change with a valid, narrowly scoped preservation argument. For example, an isolated renderer change could preserve notebook behavior if the write path is demonstrably unaffected. Passing a finite regression suite alone is not proof of that universal preservation.

**SHOWN—Your measurements:** The supplied results already contain real wrong saves and recall of 77.9%. A successful integration experiment would not repair those deficiencies or establish the overall safety target.

**UNTESTED—Panel handling:** Keep release panels outside builder-accessible repositories and logs. Builders receive the registered verdict and permitted diagnostic summary, not raw rows or item-containing exception traces. Continue treating subsequent reuse according to your existing test-only policy.

## 4. The ONE experiment to run next

### Experiment: challenge the merge checker, not the assistant

**UNTESTED—Single intervention:** Add one **offline, read-only contract-aware merge checker in shadow mode**. Compare its admission decisions with the existing byte-identity check. Do not merge the pending production pieces, alter the assistant’s renderer, retrain anything, or change production prompts and thresholds.

**UNTESTED—Base:** Call the current director-verified assistant artifact \(B_0\), and record its actual hashes before preregistration. I do not know those hashes. Do not use the in-progress second merge as the base unless it has independently become the verified current base.

**UNTESTED—Prediction:** The checker will block every deliberately inadmissible candidate while accepting legitimate wording changes and valid compositions, without consulting a new blind language panel for each decision.

### Audit sample: 42 candidate integrations, plus 4 director probes

**UNTESTED—Sample definition:** The unit is a **candidate integration**, not a chat turn. A candidate may require a multi-turn conversation to demonstrate its defect.

| Main-audit group | Exact count | Purpose |
|---|---:|---|
| Incorrect behavior inside an allowed footprint | 4 | Detects the “authorized field therefore acceptable value” mistake. |
| Read/write interaction with disjoint declared write sets | 4 | Tests dependencies that write-overlap checks miss. |
| Parser-order or early-return interaction | 4 | Tests whether one stage prevents another from doing its job. |
| Reply-reason or action-claim mismatch | 4 | Includes missing-knowledge versus failed-parsing confusion and unsupported save confirmations. |
| Correction followed by chain or inverse queries | 4 | Tests behavior across notebook histories. |
| Three-piece-only interaction | 4 | Each proper subset passes the relevant witness; the full combination fails it. |
| Wrong-base or missing-prerequisite candidates | 6 | Tests ancestry and prerequisite enforcement. |
| Legitimate wording-only changes | 6 | Prevents “reject every changed sentence” from passing. |
| Valid compositions: four pairs and two triples | 6 | Prevents “reject every integration” from passing. |
| **Main-audit total** | **42** | **30 inadmissible; 12 admissible.** |

**UNTESTED—Challenge validity:** All 24 behavioral-failure candidates must have valid lineage, build successfully, and stay within their declared field-change union. Their constituent pieces must pass their local contracts. Otherwise, the audit would mostly test easy hash or scope violations rather than the difficult composition problem.

**UNTESTED—Construction:** A separate agent should construct executable candidate variants around the actual assistant stages, using visible fixtures and fictional names. Use historical examples when suitable artifacts exist; otherwise label them constructed. Four renamed copies of the same trigger do not count as four distinct interaction cases.

**UNTESTED—Independent ground truth:** Each behavioral-failure candidate needs a hidden executable witness with an explicit expected notebook operation or reply-record outcome. Another agent and the director check the witness before sealing. Do not use agreement between two free-form language judges as the sole oracle.

**UNTESTED—Blinding:** Freeze the checker, its public tests, contract rules, and verdict logic before exposing it to audit candidates. Keep hidden witness inputs and expected outcomes out of the checker’s test resources. Candidate identifiers must not reveal their class.

**UNTESTED—Director verification:** Independently seal **four additional probes: two inadmissible and two admissible**. Use them only after a main-audit PASS. Thus the total is **46 integration-level decisions**, with no retraining or checker revision between the two stages.

### Exact pass marks

**UNTESTED—Preregister all of these requirements:**

| Requirement | Pass mark |
|---|---:|
| Behavioral regressions admitted | **0 of 24** |
| Wrong-base/prerequisite candidates admitted | **0 of 6**, blocked before conversational execution |
| Valid controls automatically accepted | **12 of 12** |
| Director probes classified correctly | **4 of 4** |
| Hidden audit witnesses consulted by the checker | **0** |
| Fresh blind language panels consulted for individual admission decisions | **0** |
| Changes to the reference production assistant during the experiment | **0** |

**UNTESTED—Verdict handling:** `REJECT` or `ESCALATE` both safely withhold an inadmissible candidate, but escalation does not count as acceptance of a valid control. This prevents a checker that sends everything for fresh testing from appearing successful.

**UNTESTED—Sample-size rationale:** This is a coverage-driven engineering audit: four distinct mechanisms in each of six behavioral categories, six ancestry controls, and twelve positive controls. It is **not** a random sample of future integrations. Passing cannot support a numerical claim that fewer than 1% of real regressions will escape. I do not know a defensible escape-rate bound for these constructed, dependent cases.

**SUGGESTED—Published rationale for this limitation:** Fault-seeding research distinguishes how a constructed fault looks from how it actually behaves. A mutant’s resemblance to real code changes does not automatically make it a representative real failure. See *Syntactic Vs. Semantic Similarity of Artificial and Real Faults in Mutation Testing Studies*, **arXiv:2112.14508**. 

**UNTESTED—Cost:** This requires agent effort to construct and adjudicate the candidates, but no new model or training run. Reuse unchanged model artifacts across candidates. Cached intermediate results may be used only where the entire upstream computation is unchanged; otherwise they could conceal the interaction being tested. I do not know the runtime on your machines.

### What would prove the recommendation wrong?

**UNTESTED—Decisive falsifier:** The checker admits **one independently confirmed behavioral regression** despite valid lineage and apparently compliant footprints. An especially informative example would be an accepted correction–chain–inverse integration that returns the old relationship after an edit while every constituent piece passes alone.

**UNTESTED—Operational falsifier:** Failure to accept even one of the twelve stipulated valid controls fails this deliberately strict first experiment. That would show that this checker has not yet delivered the promised reduction in unnecessary blocking.

**UNTESTED—Follow-up boundary:** A FAIL stays FAIL and receives only the permitted diagnosis-driven follow-up. A PASS supports using the checker as an engineering aid—not certifying the assistant. The separate later step is a frozen integration release evaluated on one fresh blind language panel for whatever new end-to-end claims that release makes.

## 5. Strongest objection, and the rival I rejected

**UNTESTED—Strongest objection:** The contracts may reproduce the same blind spots as the hand-written parser. If the same reasoning invents the patch, its footprint, its tests, and its expected outcomes, the process can become a self-consistent way to approve mistakes. The dangerous case is a wrong behavior that is both authorized by an overly broad contract and absent from every visible fixture.

**SHOWN—Published warning:** The semantic-merge testing study above detected only **9 of 28** conflict cases in its evaluated setting. That is evidence that generated tests can expose integration faults, but also that passing such tests is not a complete safety argument. It is not an estimate of Premonition’s future performance. 

**UNTESTED—Mitigation:** Keep the checker small, require independently checked behavioral witnesses, treat uncertainty as a reason not to auto-admit, and retain fresh release-level evidence. Do not give the checker authority to relax notebook truth requirements.

**UNTESTED—Strongest rival:** Option 2—the serial integration queue with full visible regressions and one blind evaluation per release batch—is simpler and may be the better practical choice. I rank it second because it does not directly resolve your current distinction between harmless text differences, wrong reply explanations, and failures hidden inside an allowed change. If the proposed audit fails, use that simpler process rather than expanding the checker indefinitely.

**SHOWN—Source scope:** I checked relevant full-text HTML methods or results sections for the cited arXiv papers, not only their abstracts. None directly evaluates Premonition.

## Plain-language summary

**UNTESTED—Summary:** Give each change an exact starting version and a clear promise about what it may change and what it must preserve. Check the meaning of replies, not just whether their words match. “I don’t know” and “I didn’t understand” must stay different when they describe different problems. Look for places where one change affects information another change uses, even when they edit different fields. Reuse old tests openly, but do not call their results fresh proof of real-world accuracy. Test the proposed merge checker by giving it deliberately broken integrations and legitimate ones. One real regression that it accepts is enough to fail this first experiment. Save new blind language panels for frozen releases and new performance claims, rather than spending one on every intermediate combination.

## Answer to question 16: Speed: a 5% time bar measured on a busy machine, and a 27B gate per fact
(message cmsg_01FuvegZXjMmeUzStiEFVnEWNWL5mc3vswbegviqSGDgkV, 2026-09-23T10:21:36Z)

## Recommendation

**UNTESTED — my recommendation:** First replace the “one suite run must be within 5%” rule with a paired, confidence-bound rule. For the gate, the first optimization worth testing is **reuse of identical prompt prefixes without changing the prompt, model, threshold, or decisions**. Check the current server’s actual cache hits before building anything: caching may already be active.

**SHOWN — your measurements:** The old mouth experiment remains a registered **FAIL**. However, the evidence you supplied does **not establish that the mouth itself is more than 5% slower**. Separately, making the 27B gate faster would not fix its poor performance on fresh wording.

*Labels below distinguish SHOWN results or documented behavior, SUGGESTED transfers from other settings, and UNTESTED proposals or calculations.*

## 1. Diagnosis: what the existing results do—and do not—show

### The mouth’s failure is a measurement problem, but not necessarily only noise

**SHOWN — your measurements:** The candidate passed per-turn latency and failed total suite wall time by reporting an 8.1% increase against a 5% limit. Run-to-run variation exceeded the distance from the result to the limit.

**UNTESTED — interpretation:** This supports “the registered speed requirement was not demonstrated,” not either of these stronger claims: “the mouth is definitely too slow” or “background activity definitely caused the failure.” A genuine slowdown, scheduling interference, longer-tail turns, and time spent outside the assistant could all contribute. Without paired raw measurements and timing boundaries, I do not know which did.

**UNTESTED — recommendation:** Preserve the historical FAIL, but distinguish two future outcomes: **demonstrated regression** and **insufficient timing evidence**. Both can block promotion without pretending they establish the same thing.

### The gate’s cost is not just “27B parameters”

**UNTESTED — latency model:** The useful decomposition is

\[
T_{\text{turn}}
=
T_{\text{other}}
+
\sum_{j=1}^{N_{\text{checks}}}
\left[
T_{\text{queue},j}
+T_{\text{request},j}
+T_{\text{prompt},j}
+T_{\text{extra output},j}
\right].
\]

Here, “other” includes the ear, notebook, reasoner, mouth, and application overhead. Your YES/NO version requests up to four checks; the three-question version requests up to twelve. But their costs depend on **uncached input tokens, generated tokens, cache reuse, residency, and scheduling**, not merely the number of calls.

**SHOWN — published implementation:** Processing a prompt produces next-token logits—the scores used to predict the first answer token. llama.cpp exposes those logits through its native API. Therefore, obtaining a single-token YES probability does not inherently require generating an explanation or a second answer sequence. 

**UNTESTED — implication:** A “single-forward-pass logits” optimization may save almost nothing if the existing gate already reads the first answer-token probability and stops. Inspect that path before claiming a speedup.

**SHOWN — model documentation:** Qwen3.8-27B’s published default is thinking enabled. Your actual server configuration might disable it; the project context does not say. Record the rendered prompt and output-token count rather than assuming “YES/NO” means only one token was computed. 

**UNTESTED — memory arithmetic:** Nominal 4-bit storage for 27 billion parameters is \(27\times10^9\times 0.5=13.5\) GB, or about **12.57 GiB**, before quantization metadata, higher-precision tensors, cache, and working buffers. That arithmetic does not establish whether your actual model is completely GPU-resident. Record the actual offload and memory allocations; do not infer residency from “4-bit, 16 GB.”

### An 800 ms median can conceal the actual problem

**UNTESTED — mathematical implication:** A workload containing many zero-fact turns can meet an 800 ms overall median while multi-fact turns remain slow. Freeze the workload mix and report latency separately for **0, 1, 2, 3, and 4 candidate facts**, alongside the overall result. Do not use the number of successfully saved facts for these groups: refusing more facts must not make the speed benchmark easier.

**SHOWN — your measurements:** The QA variant failed both latency and true-fact holdback. The fresh-wording YES/NO result also makes the 27B model an unreliable “expert fallback” for a smaller model. Speed work must not be reported as repairing those quality failures.

## 2. A trustworthy “no more than 5% slower” protocol

### Write the bar around a defined quantity

**UNTESTED — proposed contract:**

> On the frozen workload, hardware configuration, and declared background-load regime, the one-sided 95% upper confidence bound on the candidate/base ratio of mean assistant execution time must be at most 1.05. Separately, the one-sided 95% upper confidence bound on median complete-turn latency must be at most 800 ms. Timing begins when the application accepts the turn and ends when required notebook work and the complete reply are finished.

**UNTESTED — clarification:** “No more than 5% slower” is preferable to “within 5%”: the latter could accidentally reject a 10% speed improvement. The relative mean-time bar controls total processing cost; the median bar controls typical responsiveness. Neither replaces the other.

**UNTESTED — timing boundaries:** Exclude panel generation, grading, report writing, and unrelated harness work from *assistant execution time*. Record their costs separately. Declare whether the primary test is warm-service operation; report cold startup separately rather than quietly deleting it after inspection. For the mouth specifically, also replay identical reply records directly through each mouth version, so an unrelated gate delay cannot masquerade as a mouth regression.

### Pair and interleave the work

**UNTESTED — proposed execution:** Divide the workload into short, matched blocks. For each block, randomly choose **ABBA** or **BAAB**, where A is the base and B is the candidate. Each run uses the same ordered inputs and initial notebook fixture. Average the two A totals and two B totals inside that block.

**UNTESTED — rationale:** Close pairing reduces the opportunity for one version to receive systematically better machine conditions. The symmetric order counters approximately linear drift within a block, such as gradual warming. It does not eliminate sudden competing jobs or all cache effects.

**UNTESTED — cache safeguard:** Before each constituent run, establish the same declared starting conditions. Do not let B receive an already-computed test prompt merely because A just processed it. For a cache experiment, warm up with separate development turns—not the upcoming test items.

### Use confidence bounds, not a significance-test shortcut

**SHOWN — published methodology:** Kalibera and Jones show why performance comparisons need uncertainty estimates on the **ratio of execution-time means**, and why repetitions at different levels—within a process, between executions, and beyond—cannot simply be treated as interchangeable independent samples. Relevant paper: **arXiv:2007.10899**, especially Sections 6–7. I checked the full-text methods, not only the abstract. 

**UNTESTED — proposed analysis:** Let \(A_b\) and \(B_b\) be matched block totals. Estimate

\[
\widehat R=\frac{\sum_b B_b}{\sum_b A_b}.
\]

Use a **paired block bootstrap**, resampling whole matched blocks and keeping all their internal repetitions together. Fix the procedure and random seed before testing; **20,000 resamples** is a reasonable computational choice for this experiment.

**UNTESTED — decision rule:** Pass only when the one-sided 95% upper bound is at most **1.05**. Call a regression demonstrated when the corresponding lower bound exceeds **1.05**. Otherwise report **INCONCLUSIVE—no promotion**. “No statistically significant difference from equal speed” is not evidence of being within the allowed margin.

**UNTESTED — important limitation:** If several blocks share one long background-load episode, they are not automatically independent. Select the outer block duration using development-only timing, and resample at that outer level. A bootstrap cannot manufacture independent evidence from thousands of correlated timings. No protocol can guarantee a 5% conclusion under unrestricted, changing machine interference; the honest result can remain inconclusive.

### CPU time and instruction counts are supporting measurements

**SHOWN — documented behavior:** Process CPU time measures CPU consumption by the process, while elapsed-time clocks include waiting. Python’s `process_time` and `perf_counter` explicitly make this distinction. 

**UNTESTED — proposed use:** For the mouth, record elapsed time and CPU time together, including relevant child processes. Similar CPU time with worse elapsed time suggests scheduling interference, but does not prove it: memory contention and other effects still need consideration. For the gate, client CPU time is particularly inadequate because it excludes most GPU execution.

**UNTESTED — proposed use:** Retired instruction counts, where available, can reveal increased computational work. They are not a replacement latency bar: equal instruction counts can have different memory stalls, scheduling delays, and execution times. Treat them as diagnosis, not permission to overrule a wall-time failure.

### How many repeats?

**UNTESTED — planning approximation:** There is no defensible universal “repeat five times.” For roughly independent matched blocks, a useful approximate sample-size calculation is

\[
n\approx
\left[
\frac{(1.645+0.842)s}
{\log(1.05)-\log(R_*)}
\right]^2,
\]

where \(s\) is the development-estimated standard deviation of paired log-time ratios and \(R_*\) is the true ratio you plan to distinguish from the limit. This uses one-sided 5% testing and approximately 80% power; it is planning arithmetic, not a guaranteed confidence statement.

**UNTESTED — calculated examples:** With no true slowdown, \(s=0.10\) gives approximately **26 independent blocks**; \(s=0.20\) gives **104**. With a true 2% slowdown and \(s=0.10\), it takes approximately **74**, because the candidate is closer to the rejection boundary. Small-sample corrections, dependence, and heavy tails can require more.

## 3. Four ranked gate options, with conditional milliseconds

**UNTESTED — assumptions for the calculations below:** I do not know your actual prompt-processing speed, output speed, or non-gate cost. The following is an explicit scenario, **not a benchmark of your GPU**:

| Quantity | Assumed value |
|---|---:|
| All non-gate turn work | 200 ms |
| Request overhead per check | 8 ms |
| Effective prompt-processing speed | 2,000 tokens/s |
| Each additional output token after the first | 25 ms |
| Shared instruction prefix | 256 tokens |
| User message | 80 tokens |
| Per-fact claim and suffix | 24 tokens |

**UNTESTED — calculated reference:** With no effective prefix reuse and a one-token decision, each check costs \(8+360/2=188\) ms. Complete-turn times are therefore **388, 576, and 952 ms** for one, two, and four facts. These numbers are not fitted to the measured QA median of 880 ms.

### 1. Reuse identical prompt prefixes

**SHOWN — current implementation:** llama.cpp documents shared-prefix reuse through `cache_prompt`, currently defaulting to true. Its documentation also warns that different processing batch sizes can produce logits that are not bit-for-bit identical. Consequently, both cache hits and decision equivalence need checking. 

**SUGGESTED — published elsewhere:** SGLang’s RadixAttention demonstrates the value of reusing shared prefixes across related calls. This supports the mechanism, not a particular speedup on your model and server. Relevant paper: **arXiv:2312.07104**, Section 3 and Appendix A; I checked those full-text sections. 

**UNTESTED — calculated times:**

| Cache state | 1 fact | 2 facts | 4 facts |
|---|---:|---:|---:|
| Only the 256-token static prefix is already cached | 260 ms | 320 ms | 440 ms |
| Static prefix cached; message also reused between facts | 260 ms | 280 ms | 320 ms |
| First check cold; subsequent checks reuse prefix and message | 388 ms | 408 ms | 448 ms |

**UNTESTED — trade-off:** This targets repeated prompt computation without intentionally changing the question being asked. It costs state management and memory. The more optimistic rows require an existing prompt layout and model/server state representation that actually permit that reuse. **Reordering the prompt to create a larger prefix is a separate semantic change**, not a free cache switch. Caching cannot repair the gate’s judgment or recover facts missed by the ear.

### 2. Stop at the necessary logits

**SHOWN — implementation:** llama.cpp can expose logits after processing input tokens. Its server also distinguishes probability reporting before and after sampling operations. The native logits API and the server’s probability interface are not interchangeable without checking how the existing score is defined. 

**UNTESTED — calculated gain:** If the current gate already scores the first decision token, expected avoided decoding is **0 ms**. If it unnecessarily generates three tokens, stopping after the first avoids approximately **50 ms per fact** under this scenario: 50, 100, or 200 ms per turn.

**UNTESTED — critical preservation rule:** Keep the original probability definition. These are different quantities:

\[
\frac{e^{z_{\rm YES}}}{\sum_v e^{z_v}}
\qquad\text{and}\qquad
\frac{e^{z_{\rm YES}}}{e^{z_{\rm YES}}+e^{z_{\rm NO}}}.
\]

Switching to YES/NO-only normalization while retaining the **0.25** threshold changes the gate. Also check tokenization, leading spaces, and the exact answer position. A top-token response that omits YES is not a complete YES score.

**UNTESTED — trade-off:** This removes unnecessary output work, not prompt processing. It may require a scoring adapter, but no new model. Disabling thinking or changing the answer template would require a separately evaluated decision rule.

### 3. Batch a turn’s checks—but distinguish two different operations

**UNTESTED — distinction:** **Computational batching** evaluates the original independent prompts together. **Prompt consolidation** asks one new prompt to judge all claims. The first aims to preserve the individual questions; the second changes their context and potentially their answers.

**SHOWN — implementation:** llama.cpp’s native batch structure supports multiple sequences. At the server level, parallel slots and continuous batching are separate configuration concepts; sending multiple requests to your current single-slot configuration does not, by itself, establish simultaneous evaluation. 

**UNTESTED — calculated prompt-consolidation example:** Suppose one prompt contains the shared instructions, message, all claims, and emits a compact verdict sequence taking \(2f-1\) tokens. Without caching, the scenario gives **388, 450, and 574 ms** for one, two, and four facts. The savings come from reading the common material once, partly offset by generating a longer answer.

**UNTESTED — trade-off:** Consolidation needs fresh semantic testing: claims can influence one another, verdicts can be misaligned, and the old threshold may no longer have the same meaning. Independent computational batching avoids that intentional prompt change, but its milliseconds depend on measured batch throughput and memory headroom. I do not know those values. Four independent checks in one computational batch are not automatically four checks for the cost of one.

### 4. A smaller checker first, with selective escalation

**SUGGESTED — published elsewhere:** FrugalGPT studies model cascades that select cheaper or more expensive models for different queries: **arXiv:2305.05176**. That is evidence for the general approach, not for your notebook-write safety target. For this paper, I checked the abstract and authors’ repository, not the full experimental methods. 

**UNTESTED — calculated example:** Assume a small checker costs **15 ms per turn**, independently escalates each fact with probability **0.20**, and each escalation costs the reference **188 ms**. Expected mean turn times become about **253, 290, and 365 ms** for one, two, and four facts. Under these simplified assumptions, medians are **215, 215, and 403 ms**, respectively. Means and medians differ because this is a mixture of fast and escalated turns.

**UNTESTED — trade-off:** This requires training or calibration, extra runtime machinery, and validation of the routing errors. Easy acceptance can bypass needed checks; reject-only filtering can lower recall. Most importantly, your current 27B gate has not earned the role of trustworthy fallback. This is a later architecture experiment, not my next speed experiment. No model download should occur without approval.

### Why I would not spend the next experiment on speculative decoding

**SHOWN — published mechanism:** Speculative decoding proposes several future tokens with a cheaper model and verifies them with the target model. Relevant paper: **arXiv:2211.17192**, Sections 2–3; I checked the full-text algorithm and analysis. 

**UNTESTED — application here:** For a decision obtained from the first answer-position logits, there is no useful multi-token continuation to accelerate. Expected avoided continuation time is **0 ms**, with additional overhead unknown. Longer QA answers might benefit, but speculation does not remove their prompt-processing cost or fix the QA variant’s holdback failure.

## 4. The ONE next sealed experiment

### CACHE-PRESERVE-01: identical decisions, less repeated prompt processing

**UNTESTED — scope:** This is a **runtime-only optimization experiment**, not a new safety certification. The base is the exact current ear v4.1 + rule brake + YES/NO gate at **0.25** + current notebook/reasoner/mouth, identified by hashes. Do not use the failed three-question gate as the base.

**UNTESTED — single change:** Enable supported reuse of identical prompt prefixes on the existing gate slot. Keep the rendered token sequences, request order, model, quantization, context capacity, KV precision, threshold, output settings, and all other pipeline components unchanged.

**UNTESTED — stop-before-testing condition:** On development-only requests, inspect actual evaluated and reused token counts. **If the current base already performs the same reuse, there is no candidate change to test. Stop; do not burn a fresh panel or manufacture a “cache improvement.”** Likewise, do not quietly bundle a server upgrade or prompt rearrangement into this experiment.

### Workload and sample size

**UNTESTED — fixed design:** Use **300 fresh fictional-name turns**, with **60 in each 0–4 candidate-fact group**. A separate agent writes them from a frozen specification that includes ordinary statements and the known difficult language families. Candidate-count grouping is determined from the frozen upstream path, without examining gate verdicts.

**UNTESTED — repetitions:** Form **60 matched blocks**, each containing one turn from every candidate-count group. Run each block as ABBA or BAAB, yielding **1,200 complete-turn observations**: two observations per arm per unique turn. Treat the block—not each repeated observation—as the basic paired unit. Fix the scheduling windows and any larger resampling units from development timing before sealing.

**UNTESTED — why 60 blocks:** This is a practical fixed budget. In the earlier approximation, 60 independent blocks provide approximately 80% power for the 5% non-inferiority question when the true ratio is 1.00 and paired log-ratio standard deviation is about 0.15. It does not guarantee enough precision for your actual machine or for median bounds. Insufficient precision means no promotion.

### Exact pass marks

**UNTESTED — proposed registered marks; all must pass:**

| Requirement | Fixed pass mark |
|---|---|
| Behavioral preservation | **0** differing gate accept/reject decisions, notebook mutations, or final reply records across corresponding runs |
| Useful relative improvement | One-sided 95% upper confidence bound on candidate/base **mean complete-turn time ≤ 0.90** |
| Absolute responsiveness | One-sided 95% upper confidence bound on complete-turn **median ≤ 800 ms**, both overall and separately for each **1–4 candidate-fact group** |
| Reliability | **0** crashes, timeouts, context truncations, or incomplete replies |

**UNTESTED — analysis details:** Use the registered paired block-bootstrap procedure with **20,000 resamples**. Report the 0-fact group and p95 latency as diagnostics, plus cache hits, prompt time, generated-token count, queue time, and per-stage time. Include all completed timing observations; do not remove a slow block because the machine became busy. Any timeout fails reliability rather than disappearing from the latency sample.

**UNTESTED — practical setup:** Warm the resident service with separate development turns before each constituent run, and reset test-item state so a repeated test prompt cannot create an artificial cache hit. Include all per-request cache handling inside measured time. Report cold-start behavior separately.

**UNTESTED — what would refute the recommendation:** No additional prefix reuse refutes its premise for the current system. Any changed write decision refutes the claim that this implementation preserves behavior. A lower confidence bound above **0.90** refutes the targeted 10% reduction; an interval crossing that threshold is inconclusive. A median lower bound above **800 ms** demonstrates that the optimization is insufficient for that group.

**SHOWN — existing limitation:** Because the base already makes wrong saves and misses recall targets, unchanged behavior still does not meet the product’s safety requirements. A successful result must be called **PASS—runtime optimization**, not “Premonition certified safe.”

**UNTESTED — verification:** The director should independently recount decision differences and recompute the timing statistics from raw logs, then run the required held-out probe. The earlier mouth FAIL remains untouched. A separately registered logits-only change would be a possible later step only if traces show unnecessary decoding.

## 5. Strongest objection and rejected rival

**UNTESTED — strongest objection:** Caching may already be working, or repeated prompt processing may be a small part of turn time. In either case this recommendation offers little value. That is why the stop-before-testing inspection is essential: **I cannot honestly promise saved milliseconds from the configuration description alone.**

**UNTESTED — rejected rival:** Consolidating all claims into one gate prompt has a potentially larger practical benefit when many independent prompts are being recomputed. I reject it as the next experiment because it changes the verifier’s question and can change its error pattern. Cache-only work is preferable first precisely because its intended behavior is unchanged and its failure modes are easier to isolate.

## Plain-language summary

**SHOWN:** The mouth failed the old timing rule, but the measurements do not prove that the mouth itself caused the slowdown.  
**UNTESTED:** Compare the old and new versions close together, in randomized order, rather than trusting one long suite run.  
**UNTESTED:** Pass only when the uncertainty bound fits below the allowed limit; an unclear result should block promotion without being called a proven slowdown.  
**SHOWN:** The gate’s first answer-token scores are available after processing its prompt, so a YES/NO check does not necessarily need a generated explanation.  
**UNTESTED:** Reusing identical prompt prefixes is the first speed optimization to test, but only after confirming that the server is currently repeating that work.  
**UNTESTED:** Test multi-fact turns separately so fast empty turns cannot hide them.  
**UNTESTED:** The proposed experiment requires unchanged decisions, a supported reduction of at least 10% in mean turn time, and median latency below 800 ms.  
**SHOWN:** Even a successful speed experiment would leave the gate’s existing wrong-save and recall problems unresolved.

## Answer to question 17: What should "sleep" do in a system with an explicit notebook?
(message cmsg_01FuvegZXjMmeUzStiEFVnEWPbWR1kFysDyuMLh3si3Q4q, 2026-09-23T10:21:23Z)

## Recommendation

**UNTESTED — My recommendation:** Define sleep as **offline maintenance and rehearsal that produces a candidate update, never an automatic change to what the assistant believes or may save**. The notebook remains the authority for facts. Sleep may improve how the assistant reads and expresses those facts, or build disposable indexes over them.

The next experiment should test **one reversible ear adapter, trained with replay, entirely outside the live write path**. Keep the existing gate frozen for comparison—not because freezing it makes the adapter safe. Replace the no-op “merge” mark with a release decision that rejects both an unchanged model and a model that makes even one wrong save.

**Labels used below:** **SHOWN** means reported in your supplied results or demonstrated in a cited paper; I have not independently reproduced your experiments. **SUGGESTED** means published evidence supports trying something here, but in a different setting. **UNTESTED** means my interpretation, proposed design, or mathematical application.

## 1. Diagnosis: sleep is mixing three different jobs

### Remembering facts is not the demonstrated problem

**SHOWN — Your results:** The structured reasoner scored 200/200 internally. Meanwhile, the ear misses facts, the gate admitted 63/65 wrong frames on fresh wording, and the planned strict compiler could represent only 184/272 legitimate facts even with a perfect reader.

**UNTESTED — Interpretation:** Those results point primarily to **language interpretation and write-policy coverage**, not a demonstrated need to consolidate notebook facts into weights. An ear adapter cannot raise the future compiler’s 67.6% oracle ceiling. That requires a separate compiler experiment.

**UNTESTED — Important distinction:** “Facts live in the notebook, not weights” should be an **authority rule**, not a claim that weights contain no factual associations. A model trained on example sentences may memorize their names and relationships incidentally. The enforceable requirement is that memorized associations never authorize a save or substitute for reading the current notebook.

### A frozen gate does not preserve safety

**UNTESTED — Reasoning:** Let \(E\) be the ear and \(G\) the gate. Changing \(E\) changes which claims reach \(G\), even when \(G\)’s weights, prompt and threshold remain identical:

\[
\Pr(\text{wrong write})
=
\Pr\bigl(E\text{ proposes an unsupported claim that }G\text{ accepts}\bigr).
\]

Consequently, an old certificate for \(G\circ E_{\text{old}}\) does not certify \(G\circ E_{\text{new}}\). Your fresh-wording gate results make relying on that assumption especially hazardous.

### Low rank and “hardening” are not semantic guarantees

**SHOWN — Published:** LoRA trains a low-rank change to a frozen matrix. Biderman and colleagues found that LoRA often forgot less than full fine-tuning in their language-model experiments, but also learned less in the tested coding and mathematics settings. That is a learning–forgetting trade-off, not preservation of every previous decision. See *LoRA*, **arXiv:2106.09685**, and *LoRA Learns Less and Forgets Less*, **arXiv:2405.09673**. 

**UNTESTED — Interpretation:** A rank-one change can still reverse a critical decision. Likewise, freezing, merging, quantizing or otherwise “hardening” a candidate does not establish that its interpretation is correct. **Test the exact final inference artifact after every transformation that could change its outputs.**

### Your “merge” mark is testing the wrong thing

**UNTESTED — Diagnosis:** A completed merge operation, a nonzero weight change, or a lower training loss establishes neither useful learning nor safe behavior. A valid consolidation mark needs two independent questions:

> Did the candidate improve on fresh examples?  
> Should the release mechanism reject it when improvement or safety is absent?

**UNTESTED — Policy:** When there is nothing eligible to learn, sleep should return **NO CHANGE**. That is legitimate operation, but it is not evidence of successful consolidation.

## 2. A precise sleep contract

**UNTESTED — Proposed definition:**

\[
\operatorname{Sleep}(N_v,\theta_v,D_{\text{approved}})
\longrightarrow
(C_v,\Delta\theta_{\text{candidate}},\text{audit report}),
\]

where \(N_v\) is a versioned notebook, \(C_v\) contains rebuildable indexes or caches, and the candidate update is inactive until separately approved. The deployed parameters remain \(\theta_v\), and sleep has **no write permission to the authoritative notebook**.

**UNTESTED — Permitted learning:** Sleep may learn reusable procedures: interpreting familiar relation words in different sentence structures, handling approved typing variations, distinguishing statements from check-questions, and selecting suitable wording for a supplied reply record. Its learning target is **“how to read or express this kind of input,” not “which fictional person owns which dog.”**

**UNTESTED — Permitted maintenance:** Lossless compression and indexes are acceptable only when they preserve the complete authoritative record, including provenance and edit information. Inverse and chain caches must identify their source notebook version or dependencies. After an edit, stale results must be invalidated or bypassed. Derived relationships stay in caches, never in the taught-fact table.

**UNTESTED — Prohibitions:** Sleep must never silently repair a taught fact, promote an inference to a teaching, resolve “our” into “me,” invent a relation or its inverse semantics, or treat a gate acceptance or successful round trip as a training label. It must not delete the original evidence behind an approved training example.

**UNTESTED — Confirmation needs a precise meaning:** “Yes, that fact is true; save it” does **not necessarily mean** “my previous message asserted that fact.” For example, a confirmation following a check-question can authorize a new save without making the earlier question a positive extraction example. Store the original turn, confirmation, exact approved interpretation and their relationship separately.

**UNTESTED — Relation-word ruling:** For the next experiment, do **not intentionally teach new relation words**. Use the existing relation vocabulary and aliases. Later, the owner could authorize learning a new alias for an existing relation, but that must not automatically change the relation’s direction, inverse, cardinality or meaning. Freezing the relation table alone does not freeze the neural model’s interpretation of words, so unintended changes still require testing.

## 3. Ranked options

### 1. Shadow ear adaptation with replay — recommended next experiment

**UNTESTED:** Train a small, removable adapter using audited examples of the target typing style, mixed with older training examples. It could improve lowercase, punctuation and sentence-structure handling while keeping the base checkpoint available for exact rollback.

Its costs are training, reliable labels, retention testing and fresh safety certification. It cannot by itself repair an inadequate compiler, establish that the frozen gate is reliable, or fix every unsupported shape in the hand-written question parser. While confined to a sandbox, it cannot corrupt the live notebook; deployment would require a new safety decision.

### 2. Deterministic notebook maintenance — safest production sleep

**UNTESTED:** Rebuild indexes, verify integrity and maintain versioned inverse or frequently used query caches. This could reduce lookup work without changing language interpretation.

Its costs are cache storage and correct invalidation. It cannot improve extraction recall or conversational understanding. I do not know whether it would noticeably reduce your turn time: no notebook-versus-language latency breakdown was supplied. Do not precompute every possible chain without first measuring the benefit and growth in storage.

### 3. Mouth preference learning over approved alternatives

**UNTESTED:** Let sleep adjust preferences among already checked realizations of the same reply record—for example, choosing between two grammatical, equally truthful sentences.

This could improve consistency and word choice without changing notebook contents. It costs template coverage and truthfulness checks, and cannot improve the ear. Unrestricted decoder adaptation would be a substantially riskier version because a fluent sentence can still misstate the record.

### 4. Explicitly authorized relation-alias learning

**UNTESTED:** Learn that an approved expression denotes one of the existing 153 relations, with examples showing both when that interpretation applies and when it does not.

This could expand language coverage, but requires the owner’s unresolved permission, contrastive examples and new write-safety testing. It cannot safely stand in for automatically inventing new relation definitions or inference rules. Keep it out of the next experiment.

## 4. What the continual-learning literature actually supports

| Work | Published result | Application to Premonition |
|---|---|---|
| **On Tiny Episodic Memories in Continual Learning**, Chaudhry et al., **arXiv:1902.10486** | **SHOWN:** Mixing current examples with stored older examples was a strong baseline across the paper’s supervised continual-learning benchmarks.  | **SUGGESTED:** Replay older reading examples during style adaptation. Include negative and ambiguous cases, not just successful teachings. |
| **Gradient Episodic Memory**, Lopez-Paz and Ranzato, **arXiv:1706.08840** | **SHOWN:** GEM constrains updates using gradients on stored examples. Its derivation explicitly relies on local approximations and representative memory.  | **SUGGESTED:** Useful if replay alone produces retention failures. **UNTESTED:** Preserving sampled losses would still not certify all future notebook writes. |
| **Overcoming catastrophic forgetting in neural networks**, Kirkpatrick et al., **arXiv:1612.00796** | **SHOWN:** Elastic Weight Consolidation penalizes changes to weights estimated to matter for previous tasks; the paper also documents limitations of those importance estimates.  | **SUGGESTED:** A possible retention aid, not a semantic safety mechanism. I would not add it to the first replay experiment. |
| **LoRA Learns Less and Forgets Less**, Biderman et al., **arXiv:2405.09673** | **SHOWN:** LoRA retained more source-domain performance than full fine-tuning in the tested settings, with learning trade-offs.  | **SUGGESTED:** A reversible adapter is worth testing under your resource constraints. The paper does not establish the best rank for your ear. |
| **Learn then Test**, Angelopoulos et al., **arXiv:2110.01052** | **SHOWN:** The framework separates model development from risk testing; its selective-classification example measures errors conditional on making a prediction. Its guarantees require the stated sampling assumptions.  | **SUGGESTED:** Certify each frozen candidate on fresh data, with an explicit denominator and an allowance for repeated attempts. |

**UNTESTED — Bottom line:** These papers justify testing adaptation with retention controls. They do not establish that continual adaptation of this assistant is safe. The cited descriptions above are based on relevant full-text sections, not only abstracts.

## 5. The one experiment to run next

### SLEEP-EAR-01: a syntax-and-typing adapter with replay

**UNTESTED — Registered hypothesis:** One replay-trained adapter will improve complete, correct saving on unseen target-style turns by **at least 10 percentage points**, while meeting the absolute safety, recall, retention and latency marks below.

### The single change

**UNTESTED — Base:** Name and hash the current complete pipeline: ear v4.1, canonicalizer, rule brake, gate model and prompt, threshold 0.25, notebook behavior, relation table, parser, reasoner and mouth.

**UNTESTED — Intervention:** Add a **rank-4 LoRA adapter to the ear’s attention query and value projections**. Freeze all existing weights and every other pipeline component. Keep the adapter separate; do not merge it into the base checkpoint.

Use this fixed training recipe:

| Item | Proposed fixed setting |
|---|---|
| New training data | **512** audited, fictional target-style turns: **384** teaching turns and **128** turns that must save nothing |
| Replay data | **1,024** audited TRAIN-only examples: **512** teachings, **256** questions and **256** other no-save or clarification cases |
| Exposure | **2 epochs**, effective batch size **16**: **192 optimizer updates** |
| Optimization | AdamW; learning rate **\(10^{-4}\)**; weight decay **0**; LoRA scaling parameter **8**; dropout **0**; seed **17** |
| Selection | Final checkpoint only; no test-driven checkpoint, threshold or hyperparameter selection |

**UNTESTED — Scope:** Target casing, punctuation and sentence arrangement using existing relation expressions. Do not add a normalizer or teach corrections to uncertain names and values. Preserve the unchanged input as evidence. Replay must not contain current **or burned** test-panel items.

**UNTESTED — Data honesty:** Under your no-personal-data rule, this first experiment uses agent-written fictional examples, independently checked against their intended assertions. It is a prototype of confirmation-based sleep—not yet proof of adaptation to your actual personal messages. Neither the existing ear nor its gate supplies the gold labels.

**UNTESTED — Resource rule:** Use the existing GPU, with the large gate unloaded during adapter training. Permit **$0 cloud spending and no new model downloads**. Record peak memory and actual training time; I do not know those measurements in advance. This experiment uses a borrowed placeholder ear and therefore does not satisfy the final own-weights requirement.

### Fresh evaluation: 600 primary turns, 120 challenges, 24 verification probes

**UNTESTED — Primary sample:** Generate **600 independent fictional episodes** from a frozen distribution:

- **40%** target-style factual turns;
- **40%** ordinary-style factual turns;
- **20%** turns that must save nothing.

Within each factual group, use a registered mixture of **75% single-fact** and **25% three-fact** turns. Draw these categories independently rather than adjusting the mixture after observing results. Use held-out constructions and names, not merely renamed training sentences.

**UNTESTED — Challenge sample:** Add **120 fresh scored turns**, with **20 each** covering check-questions without “?”, plural owners, plans/pretend statements, ambiguous spelling requiring clarification, three-relative assertions and corrections. These are stress tests, **not extra independent samples to inflate the primary certificate**.

**UNTESTED — Verification:** After a provisional pass, the director independently recounts the outputs and runs **24 additional fresh probes**: eight target-style teachings, eight ordinary teachings and eight no-save turns.

**UNTESTED — Paired comparison:** Run both frozen base and candidate on identical, isolated notebook states. Record the rows each would actually commit **after the unchanged gate and brake**, not just its proposed frames. All writes go to disposable test notebooks.

### Gold-label protection

**SHOWN — Your results:** Six of the nine initially scored errors in one panel were answer-key mistakes. Label quality is therefore already a measured threat to the verdict.

**UNTESTED — Required procedure:** Have two independent graders establish the exact permissible saves before seeing either model’s outputs. Resolve disagreements before sealing. Subsequent suspected key errors go through a predefined adjudication process blinded to model identity, applied equally to both arms. An unresolved interpretation blocks a PASS.

**UNTESTED — Limitation:** Agreement between two AI graders is not proof of semantic truth. Any certificate remains conditional on the correctness of the adjudicated labels; I do not know their residual error rate.

### Exact pass marks

**UNTESTED — Proposed preregistration:** **Every row below must pass.** These numbers are proposed acceptance criteria, not reported results.

| Mark | Exact requirement |
|---|---|
| **Wrong saves** | **0 unsupported rows** committed by the candidate across all **720** primary and challenge turns. A wrong save from a no-save turn counts identically. |
| **Safety sample size** | At least **400 of the 600 primary turns** must result in one or more saved rows. No topping up the panel after seeing the count. |
| **Recall and holdback** | Save **at least 88%** of gold facts in **each** primary factual group. Count every missing gold fact as held back, including facts silently missed by the ear. |
| **Target-style benefit** | Complete-turn save accuracy improves by **at least 10 percentage points** over the paired base; one-sided exact McNemar test **\(p\le0.025\)**. “Complete” means all and only the gold facts were saved. |
| **Retention** | Ordinary-style complete-turn accuracy falls by **no more than 2 percentage points** against the paired base. |
| **Hard positive cases** | Save at least **53/60** facts in the three-relative challenge and **18/20** corrected facts in the correction challenge. |
| **Replies** | At least **713/720** replies are grammatical, and **0/720** make an unsupported claim about the notebook, save outcome or assistant. This is an observed-panel grammar mark, not a population certificate. |
| **Latency** | Candidate median complete-turn time **≤800 ms** on the primary panel, on the same hardware and with the real gate enabled. |
| **Isolation** | **0 live-notebook mutations**; all frozen-component hashes unchanged. |
| **Director probes** | **0 wrong saves**, at least **15/16** taught facts saved, and **24/24** replies grammatical and truthful. |

**UNTESTED — Recall clarification:** I use 88%, rather than 85%, because saving at least 88% satisfies your stronger “at most 12% held back” requirement when both use the same gold-fact denominator.

**UNTESTED — Timing procedure:** Use the same production inference settings, warm both arms consistently, randomize their execution order and include parsing, gate calls, notebook operations and reply generation. Do not reuse cached gate answers between arms.

### The replacement for the no-op merge mark

**UNTESTED — Two mandatory veto tests:** Exercise the release logic with two controlled fixtures:

1. **Unchanged-base fixture:** Give it the original model as the “candidate,” with identical scores. It must reject promotion because the required improvement is absent.
2. **Unsafe-candidate fixture:** Give it an otherwise passing result containing exactly **one wrong save**. It must reject promotion despite passing recall, grammar and latency.

Require **2/2 correct rejections**. These test the validator, not model performance. A candidate can therefore fail because it did not learn, because it learned unsafely, or because the release mechanism cannot enforce its own rules.

### What the safety calculation means

**UNTESTED — Explicit denominator:** For this experiment, certify

\[
q=\Pr(\text{at least one wrong row in a turn}\mid
\text{the turn saves at least one row}).
\]

This is **accepted-turn contamination**, not a claim that multiple rows from one turn are independent. Report wrong-row counts separately. This certificate must not be renamed a row-weighted error-rate certificate.

**UNTESTED — Calculation:** With zero contaminated accepted turns among \(m\) independent accepted turns, the one-sided exact upper bound is

\[
q_{\mathrm{upper}}=1-\delta^{1/m}.
\]

Using \(\delta=0.025\) and \(m=400\),

\[
q_{\mathrm{upper}}
=1-0.025^{1/400}
\approx 0.00918
=\mathbf{0.918\%}.
\]

Thus 400 zero-error accepted turns clear 1% at a one-sided 97.5% confidence level, under the sampling and labeling assumptions. Since the chance of any wrong save on an incoming turn is no larger than \(q\), the same bound also controls that turn-level risk.

**UNTESTED — Why 600 inputs:** Refusals cannot supply evidence about the correctness of accepted saves. Six hundred inputs leave room for no-save cases while requiring 400 actual save-bearing turns. The exact minimum zero-error count at this confidence level is 368; 400 is the proposed round-number requirement. I do not know the learning test’s power in advance because its paired error pattern is unmeasured.

**UNTESTED — Repeated adaptation:** Start a separate sleep-certification error-budget ledger with

\[
\delta_t=\frac{0.05}{2^t},
\]

where every registered attempt, including a failed attempt or diagnosis-driven follow-up, consumes the next entry. The first receives 0.025. Later attempts require their own fresh samples and tighter bounds. Do not reset the ledger by renaming the experiment.

**UNTESTED — Limits:** This controls erroneous certification within that program under its assumptions; it does not guarantee zero future mistakes, repair incorrect labels, or make an agent-generated panel representative of unrestricted human chat. A PASS applies to the **tested frozen version and specified population**, not to an automatically changing model.

### What would refute the recommendation?

**UNTESTED:** A gain below 10 percentage points fails the registered usefulness claim, even if training loss decreases. One wrong save fails release, even if recall rises dramatically. Excessive old-style regression or latency also fails the proposed recipe.

**UNTESTED:** That rejects this operational proposal; it does not disprove all replay or all continual learning. Any allowed follow-up must address the diagnosed failure and use a fresh seal and panel. A later, separate experiment would need to test **multiple sleep cycles**—one successful update cannot establish indefinite retention.

## 6. Strongest objection, and the rival I rejected

**UNTESTED — Strongest objection:** This may be an expensive way to discover that a better ear still cannot satisfy the safety bar. The gate is already demonstrably weak on fresh errors, and increased extraction coverage could expose more unsafe cases. Reliable labeling and repeated certification may cost more effort than training the adapter itself.

**UNTESTED — Why recommend it anyway:** The experiment answers a narrow, useful question without risking the live notebook: **can rehearsal improve reusable language handling while preserving acceptable behavior?** It does not assume that replay works, and it does not let relative improvement excuse failure of the absolute targets.

**UNTESTED — Rejected rival:** Maintenance-only sleep is the safer production choice, and should remain the fallback. I did not choose it as the next learning experiment because your supplied evidence identifies language handling—not notebook lookup or storage—as the main demonstrated weakness. A latency profile showing expensive notebook operations could change that ranking.

**UNTESTED — Is continual adaptation safe at all?** It can be isolated safely while inactive, and its releases can be subjected to quantified, limited risk checks. An automatically changing neural reader plus finite tests does **not** establish a literal never-wrong guarantee. A stronger authorization guarantee would require a restricted verified input language or explicit confirmation of the exact proposed facts, with the relevant interface and implementation assumptions made explicit.

## Plain-language summary

**UNTESTED:** Sleep should improve how Premonition reads your messages, not move your facts out of its notebook. **UNTESTED:** It should practice on checked examples and older examples without touching the live notebook. **SHOWN — Your tests:** The existing gate passed 63 of 65 wrong frames on fresh wording. **SUGGESTED:** Replay research makes a small, removable adapter worth testing, but does not guarantee safe saves. **UNTESTED:** The proposed test requires useful improvement on unseen wording, no wrong saves, and little loss of older reading ability. **UNTESTED:** An unchanged model must fail the improvement check, and a model with one wrong save must fail the release check. **UNTESTED:** Passing would support a limited risk claim for that frozen version, not a promise that future versions will never make mistakes. **UNTESTED:** Until a candidate passes, production sleep should stay with reversible maintenance and keep learned changes away from live writes.
