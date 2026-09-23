# Research note: reader and gate, correlated errors (2026-09-23)

Written by an Opus research subagent for Ben and the director. It covers only the chat pipeline (ear → canonicaliser → brake → Qwen checker → notebook). It is not about the small card experiments or the village model.

**Labels.**
- **shown**: a paper I opened, or a number I recomputed from repo files.
- **suggested**: published, but in a different setting.
- **untested**: my own reasoning.

**How strong the paper evidence is.** WebFetch was switched off partway through this work, and arxiv.org is blocked for downloads. So each paper is marked by how much of it I actually read:
- **[abstract]**: I read the abstract page.
- **[title]**: I only confirmed the title, authors and ID with a web search. What I say about its content is from memory, so treat it as thinner evidence.

No blind TEST-ONLY panel was opened. For 261 I use only the category counts the brief already gave. Every file-level number below comes from **development** files on `origin/claude/card-experiment-handoff-7c5b27`:
- `artifacts/claude-earcheck261-20260922/`: `dev_checker.jsonl`, `devcheck_manifest.json`, `dev257_manifest.json`, `devcheck_pyesB.json`, `devcheck_pyes.json` (prompt A) and `theta.json`;
- `artifacts/claude-smolear257-20260922/dev/dev_tau.jsonl`.

I did not open `panel261_*`, `RESULTS.md` or any `run/` file.

---

## 1. Result first

1. **The three real errors in 261 probably don't share one cause.** The two typo saves were confident approvals (P(YES) 0.85 and 0.68). That fits a real blind spot: the checker is asked "does the message say this?", and a string copied from the message, typo and all, always "is said". The check-question save scored 0.37. The checker leaned NO (below 0.5), but the save cutoff is 0.25. That fits a cutoff set right at the edge of one narrow development family, not a shared blind spot. **untested** as a diagnosis, but it rests on the **shown** numbers below.
2. **On development data the checker is mostly *not* making the ear's mistakes.** How often it approves a frame the ear got wrong (all figures at theta 0.25):

   | Ear error kind | Approved | Source |
   |---|---|---|
   | All ear errors, sealed scorer | 13 of 103 | `theta.json` |
   | All ear errors, my rough matcher | 19 of 109 | my recount |
   | No-save turns | 0 of 43 | my rough matcher |
   | Wrong owner | 6 of 41 | my rough matcher |
   | Wrong span or relation (mostly label artefacts, see 2.2) | 13 of 25 | my rough matcher |

   **shown** for dev. The weakness sits where the rendered claim is almost a copy of the turn's words.
3. **The pronoun errors the checker approved on dev are mostly *ambiguous* turns** ("A's mother is B and she ..."), where both readings are possible. A checker shown only one reading can't see that another reading exists. **shown** for the dev scores; the mechanism is **untested**.
4. **Recommended single change (§5): a "rival readings" checker.** The checker sees the ear's fact next to 2 to 5 nearby readings built mechanically from the turn: other owners, trimmed or extended name spans, "only asking", and "none". It must pick one. A save needs the ear's reading to win clearly. This changes the checker's *input view*, which is the classic way to make two checkers' errors less correlated (N-version and co-training literature). It also turns hidden ambiguity into a visible split vote. **untested** in our setting.
5. **No checker can fix recall.** Recall is capped before the checker: the ear writes only 4 of 16 facts in plural-relative sentences. Section 6 gives one recall alternative. Any checker experiment should state in advance that it will not reach 85% recall on its own. **untested**, but it follows from the arithmetic in the v3 note (about 101 of 122 with the dog/cat ruling).

---

## 2. What the development files show (my recount; shown)

### 2.1 The checker's scores are spread out, and the cutoff sits at the edge of a single dev template

Prompt B, all 1,207 checked dev frames. Right and wrong come from my rough matcher (owner, relation and value all equal after lower-casing and the "me" mapping), so it counts a few label artefacts as wrong:

| P(YES) band | right frames | wrong frames |
|---|---|---|
| < 0.05 | 0 | 48 |
| 0.05–0.10 | 0 | 15 |
| 0.10–0.25 | 19 | 27 |
| 0.25–0.50 | 92 | 2 |
| 0.50–0.75 | 175 | 4 |
| 0.75–0.90 | 213 | 2 |
| 0.90–0.97 | 486 | 7 |
| ≥ 0.97 | 113 | 4 |

- **Most approved errors are confident.** 17 of the 19 approved wrong frames have P(YES) ≥ 0.5. Moving the cutoff from 0.25 to 0.5 would stop about 2 of them and hold back about 92 right frames. The sealed sweep agrees: dev recall falls from 91.9% to 84.2%, and wrong saves fall only from 13 to 11. On dev, then, the remaining errors are confident errors, not cutoff errors.
- **The dev check-question family is a single template, and the cutoff was fitted just above it.** All ten "so NAME lives in PLACE" dev turns score 0.119 to 0.237 under prompt B. The three "..., right" turns score 0.16 to 0.245. The cutoff 0.25 is the smallest that meets ≤ 1% wrong on dev, so it sits 0.005 above the highest check-question score.
- **Prompt B's wording had just moved that same family down.** Under prompt A the ten "so ..." turns scored 0.60 to 0.70. The builder chose prompt B *and* the cutoff on the same dev set (PASSMARKS D1). The blind "so ..." turn scored 0.37: above the cutoff, but still leaning NO.
- **What this means (untested):** the check-question result depends on the prompt's wording and on one dev template. It is not a stable skill.

### 2.2 Which dev errors the checker approves

These are the dev errors approved at the sealed cutoff, by kind. Names are the dev set's own made-up names.

- **Span boundary or filler inside a value.** Examples: "... plays reggae music" stored as genre "reggae music" (0.92), and "cla amberly btw" stored as the subject of "works for" (0.26). Prompt B tells the checker to say NO to filler words such as "btw", and it still approved this one. The 261b mixed-case guard does **not** cover this case, because it lets all-lowercase spans through.
- **Pronoun owner in ambiguous turns.** "Imogen Pepperell's mother is Wrenna and she speaks ..." with owner Imogen (0.76); "Drystan Vellacott's husband is Norwin and he ..." with owner Drystan (0.61); a "mum ... she" turn (0.73). In each, both readings are grammatical.
- **The dev answer key is sometimes the problem.** "Casimir Nettlefold's wife is Fenwick and he lives in ..." scored 0.96 for owner Casimir, and the key says Fenwick. In 9 of the 30 D_apos rows the key's pronoun reading clashes with the relation's gender ("X's brother is B and she ..."). Other artefacts:
  - symmetric "neighbour" facts counted as wrong in one direction;
  - "works for" versus "workplace";
  - "spouse" versus "wife".

  These echo 261's dog/cat-versus-pet recount.
- **Wrong-owner frames are mostly caught.** Of 41, 35 scored below 0.25, including most gender-clear cases. On pronoun binding the checker is largely independent of the ear.

**Takeaway (untested):** the common-mode weakness is narrower than "the checker shares all the ear's blind spots". It is concentrated in two places:
- (a) exact surface strings, where the claim copies the turn;
- (b) turns with two readings, where the checker is shown only one of them.

---

## 3. Literature

### (a) Correlated errors between a generator and its checker

- **Knight & Leveson 1986**, IEEE TSE 12(1), DOI 10.1109/TSE.1986.6312924 [title]. Program versions written independently still failed together far more often than independence predicts. **Suggested**: "separately built" does not mean "independent errors".
- **Eckhardt & Lee 1985**, IEEE TSE, DOI 10.1109/TSE.1985.231895 [title], and **Littlewood & Miller 1989**, IEEE TSE 15(12), DOI 10.1109/32.58771 [title]. Inputs differ in difficulty, and when both versions find the same inputs hard their failures correlate even if they were built independently. Littlewood and Miller show that *forced* design diversity (different methods) can, in principle, give negative correlation. **Suggested**: our ear and checker both find the same inputs hard (copied typos, turns with two readings). Diversity has to come from a different *method or view*, not only a different model.
- **Kim, Garg, Peng & Garg 2025**, "Correlated Errors in Large Language Models", ICML, arXiv 2506.07962 [abstract]. Over 350 LLMs: on one leaderboard, "models agree 60% of the time when both models err". Larger, more accurate models have more correlated errors even across architectures and providers, and the paper traces effects on LLM-as-judge. **Suggested**: a bigger checker does not buy independence.
- **Goel et al. 2025**, "Great Models Think Alike and this Undermines AI Oversight", arXiv 2502.04313 [abstract]. Introduces CAPA, a chance-adjusted agreement on mistakes. LLM judges favour models similar to themselves, and errors grow more correlated as capability rises. **Suggested**: gives a ready way to *measure* common mode (§4.3).
- **Monperrus et al. 2026**, "N-Version Programming with Coding Agents", arXiv 2606.20158 [title plus the authors' public summary]: coding agents "often fail together on tricky specs", but three-agent voting cut bugs by 66%. **Suggested**, thin evidence: voting helped despite correlation. I did not read the body.
- **Blum & Mitchell 1998**, co-training, COLT, DOI 10.1145/279943.279962 [title]. Two classifiers help each other when each sees a different, conditionally independent *view* of the input. **Suggested** principle for the gate: change what the checker sees, not only who the checker is.
- **Zhang et al. 2023**, SAC3, arXiv 2311.01740 [title]. Self-consistency checks miss errors a model makes consistently; perturbing the question and checking with other models catches more. **Suggested**, thin evidence.
- **Kadavath et al. 2022**, arXiv 2207.05221 [abstract]. Large models are well calibrated on multiple-choice and true/false questions "in the right format", and judging one answer went better after the model had seen several of its own attempts. **Suggested**: comparing alternatives can be better calibrated than judging one claim alone. This supports §5.
- **Zheng et al. 2024**, "LLMs Are Not Robust Multiple Choice Selectors", ICLR, arXiv 2309.03882 [abstract]. Models favour certain option letters regardless of content. PriDe estimates that letter preference from permuted options on a small sample and removes it at test time without labels. **Shown** as a risk for any option-picking checker; §5 includes the fix.
- **Tripathi et al. 2025**, "Pairwise or Pointwise?", arXiv 2504.14716 [title]. From memory: side-by-side judges can be *more* swayed by irrelevant surface features than one-at-a-time judges. **Suggested** caution, thin evidence: a comparison format is not automatically better, so §5 has its own falsification test.
- **Gardner et al. 2020**, contrast sets, arXiv 2004.02709 [title]. Small edits to inputs expose decision boundaries that ordinary test sets miss. **Suggested**: our rival readings are contrast sets built at test time.

### (b) Checking assertion status and surface corruption

- **Stolcke et al. 2000**, dialogue acts on Switchboard, arXiv cs/0006023 [abstract]. Uses word, word-pattern and *prosodic* cues. The SwDA coding manual (web.stanford.edu/~jurafsky/ws97) has a separate tag for "declarative yes/no questions" (qy^d), and **Shriberg et al. 1998**, DOI 10.1177/002383099804100410 [title], study prosody for exactly these act distinctions. **Suggested**: a question phrased like a statement ("so you live in X") is often marked only by intonation. In text without "?", some such turns are *really ambiguous*. The right action is to ask, not to make a sharper yes/no call.
- **de Marneffe, Manning & Potts 2012**, "Did It Happen?", Computational Linguistics 38(2), DOI 10.1162/COLI_a_00097 [title], and **Jiang & de Marneffe 2021**, "BERT for Event Factuality Fails on Pragmatics", TACL, arXiv 2107.00807 [title]. Whether a speaker *commits* to an event depends on context and pragmatics, and fine-tuned models fail most on the pragmatic cases. **Suggested**: "is this asserted?" is a hard task of its own, separate from "is this in the text?".
- **Cao et al. 2023**, "Unnatural Error Correction", EMNLP, arXiv 2311.18805 [abstract]. GPT-4 reconstructs heavily scrambled text almost perfectly, and most strong LLMs read through scrambled words that keep their first and last letters. **Suggested**: a strong checker *reads through* typos. That robustness is exactly why it approves a stored typo, because to it the typo "means" the name.
- **Pruthi, Dhingra & Lipton 2019**, arXiv 1905.11268 [title]. A separate word-recognition front end guards a classifier against misspellings. **Suggested**: catching typos is better done by a dedicated surface check (261b's guard, or the span rivals in §5) than by a model that is built to read through them.

### (c) Checking omissions, not only commissions

- **Gero et al. 2023**, "Self-Verification Improves Few-Shot Clinical Information Extraction", arXiv 2306.00024 [abstract]. The LLM gives evidence spans for its own extractions and checks its outputs, which improves accuracy across LLMs. From memory, but not re-read: it has a separate "find what was missed" step that raises recall and a pruning step that raises precision. **Suggested**, thin evidence.
- **Zou et al. 2023**, "Towards Understanding Omission in Dialogue Summarization", ACL, arXiv 2211.07145 [title]. Omission is a major error source, and detecting omissions is hard even with labelled data. **Suggested**, thin evidence.
- **Wei et al. 2024**, long-form factuality (SAFE, F1@K), arXiv 2403.18802 [title]. It adds a recall term because checking precision alone rewards saying little. **Suggested**: same point as the v3 note's "score recall three ways".
- **Wang et al. 2023**, GPT-NER, arXiv 2304.10428 [title]. From memory: it adds a self-verification pass against invented entities, which is a precision tool, not a recall tool. **Suggested**, thin evidence.

**What the literature adds overall (untested synthesis).** A checker that sees the same view as the reader, and is asked a question the reader's output answers by construction, will share the reader's hard inputs. Checks get less correlated by changing the *view* (co-training, contrast sets, perturbed questions) and by adding a separate surface check. Recall needs its own check, because a gate that approves or rejects only what it is shown can't see what is missing.

---

## 4. Diagnosis: why the checker approved the three real errors

### 4.1 Rival explanations

- **H1: copy blind spot, a capability limit.** The claim is built from strings copied out of the turn. "Does the message state X?" is true on the surface whenever X is copied, typo included. A strong LLM also reads through typos (Cao et al.). The checker can't flag a string it reads as the intended name.
  - Predicts: high P(YES) on copied, corrupted spans *even when a clean alternative is shown next to them*.
  - Fits: the typos (0.85, 0.68) and dev "reggae music" (0.92).
- **H2: cutoff and prompt overfitted to a narrow dev family.** The checker leans NO but is unsure. Prompt B and theta 0.25 were both picked on a dev set whose check-questions follow one template, so a slightly different blind wording lands just above the cutoff.
  - Predicts: new check-question templates score mostly between 0.15 and 0.6, and which side of 0.25 they land on depends on the template.
  - Fits: the check-question save (0.37), and §2.1.
- **H3: the single-claim format hides knowledge the model has.** The checker could pick the right reading if it saw the rivals, but a yes/no question about one claim gives it nothing to compare against. So it approves any *plausible* reading, which covers ambiguous pronoun turns and near-copy strings.
  - Predicts: the same model, shown the ear's reading plus a rival, picks the right one far more often than yes/no rejects the wrong one.
  - Fits: the ambiguous pronoun approvals on dev, and possibly the typos.
- **H4: answer-key error.** Some "errors" are key artefacts: 6 of 9 in 261, and several on dev (§2.2). The three real 261 errors were already re-checked by the director, so H4 does not explain them, but it inflates dev error counts. **shown** for dev.

H1 and H3 lead to different fixes:
- if H1 holds, only a mechanical surface rule or asking the user helps;
- if H3 holds, changing the checker's input view (§5) helps;
- if H2 holds, the fix is a fairer cutoff procedure, not a new format.

### 4.2 A cheap test to tell them apart (development data only, one GPU session, no training)

**Build a probe set.** Write "dev-probe" fresh. A separate agent writes it from a written spec, and it does not reuse dev257 or the dev_checker templates. It has 4 families of 30 turns each; every turn gets its gold fact and a gold *rival*:

- **T, surface.** A lowercase typo or filler word glued to a name, in mixed-case *and* all-lowercase chat. Rival: the clean span.
- **Q, check-questions.** Written in at least 6 templates without "?": "so ...", "..., yeah", "and X is Y then", "you said ...", "X lives in Y, doesn't she", and lowercase variants. Gold: nothing saved. Rival: "only asking".
- **P, pronouns after "A's R is B and he/she ...".** Half have a clear gender cue, half are genuinely ambiguous. Gold: B for the clear half, *ask* for the ambiguous half.
- **C, clean controls.** Plain facts with a distractor rival.

**Score each item three ways**, with the frozen Qwen3.8-27B and the same transport as 261:
1. prompt B yes/no on the wrong or corrupted claim;
2. prompt B yes/no on the correct claim;
3. a one-letter choice between the two readings plus "none", with the letter bias removed as described in §5.

**Decision rules, fixed in advance:**
- **H1 supported for family T** if (3) picks the clean span in < 80% of T items *and* (1) approves the corrupted claim at ≥ 0.5 in ≥ 50%. The fix is then mechanical (261b extended to all-lowercase spans), or ask.
- **H3 supported** for a family if (3) picks the gold reading in ≥ 90% of items *while* (1) approves the wrong reading (≥ 0.25) in ≥ 30%. The knowledge is there; the format hides it. Run §5.
- **H2 supported for family Q** if ≥ 40% of Q items under (1) score between 0.15 and 0.6, *and* the per-template approval rate at 0.25 varies from 0% to ≥ 30% across templates. Fix the cutoff procedure (§6, alternative 3) before changing formats.
- **Ambiguity check:** on ambiguous P items, (3) should split its probability, with the top reading ≤ 0.7, in ≥ 60% of items. If the choice format is confidently one-sided on truly ambiguous turns, it can't be the ask trigger.

Cost: about 120 turns, 2 to 3 prompts each, at about 0.3 s per prompt: well under 5 minutes on the 5070 Ti. **untested**; the latency estimate comes from the dev checker's median of 282 ms in `devcheck_pyesB.json`, **shown**.

### 4.3 Measuring common mode in future experiments (untested)

Report three numbers per experiment on the frozen ear's *real* outputs:
- `q_wrong` = P(gate approves | ear frame wrong);
- `q_right` = P(gate approves | ear frame right);
- `q_syn` = P(gate approves | synthetic corruption of a right frame, same error kinds).

If `q_wrong` is well above `q_syn`, the ear's real errors are specifically the ones the gate misses. That is common mode in the Eckhardt–Lee sense.

Dev values today: `q_wrong` ≈ 13/103 = 12.6% (sealed scorer) and `q_right` ≈ 98% (my rough matcher). `q_syn` has not been measured. **shown** for the first two.

---

## 5. ONE change to try first: the rival-readings checker

### 5.1 Mechanism (untested)

Keep everything frozen (ear v4.1, brake, canonicaliser, 261b guard if accepted, relation table, renderer) and replace only the checker question. For each TEACH frame, a small deterministic rule module builds a list of **rival readings** from the turn and the frame, with no model involved:

1. **Owner rivals.** The claim with the owner replaced by every other person mentioned in the turn (capitalised name spans, plus "the speaker" if a first-person word appears), at most 2.
2. **Span rivals.** For the subject and the value:
   - if an edge token is lowercase and not a particle (this includes all-lowercase chat), the span with that token trimmed;
   - if the turn's next token after the span is capitalised, the span extended by it.

   At most 2.
3. **Act rival.** One line, always included: "The speaker is only asking or checking whether ⟨claim⟩, or supposing or planning it."
4. **None.** Always included: "None of these: the message doesn't tell any of these as a fact."

The ear's claim goes in at a position fixed by a hash of the turn ID, so placement is deterministic but not always first. The list has at most 6 options.

**Prompt** (fixed before the seal; same transport as 261: `/no_think`, temperature 0, one token, top-10 probabilities):

```
/no_think
Message from the speaker: «{turn}»
Which ONE of these does the speaker tell as a real, current fact, with every name written exactly as the speaker meant it (no extra words)?
A) {option}
B) {option}
...
Answer with one letter.
Answer:
```

**Score:**
- Read the probabilities of the letter tokens.
- Divide by a per-letter bias estimated with PriDe (Zheng et al.): average the letter probabilities over cyclic permutations of the options on 50 *design-dev* items, with no labels needed.
- Renormalise to get `s` = the corrected probability of the ear's option.
- **Save if the ear's option is the top pick and `s ≥ θ`.** Otherwise hold back as UNSURE, as in 261.

**Why this targets the diagnosis:**
- The checker sees a different view: the space of nearby readings, not only the ear's one (co-training and contrast-set logic).
- Ambiguity shows up as a split vote, not two separate approvals (H3).
- Copied typos now compete with their trimmed version (H1, if the model can tell them apart at all; §4.2 decides).
- The act rival gets a comparative, normalised judgement, not an absolute cutoff sitting at the edge of one template (H2).

This is **not** the planned question-answering checker, which writes an answer with a hidden slot and can copy the typo back. It is also not the separate "stating or checking?" question, which never sees the fact. Here all readings are scored against each other in one prompt.

### 5.2 Setting θ without touching blind data (untested procedure)

1. Freeze the rival rules, the prompt and the PriDe bias vector on the **design-dev** set: dev-probe plus the existing `dev_checker.jsonl`.
2. Have a separate agent write a fresh **threshold-dev** set from a spec (about 300 turns covering the same families plus plain turns). The ear output on it is generated once.
3. Choose θ on threshold-dev with a stricter version of 257's rule: **the smallest θ where every family *separately* has wrong-save rate ≤ 1%**, then the most recall. Using the worst family, not the pooled rate, stops a cutoff from sitting just above one template, which is what happened to 0.25 (§2.1).
4. Use threshold-dev once. If the choice fails, report it; don't iterate on the same set.

### 5.3 Sealed experiment

Two arms, run on the **same frozen ear outputs** of a fresh blind panel written from a spec by the usual separate agent:
- **YN**: prompt B, θ = 0.25, as sealed;
- **RIV**: rival-readings checker, θ from §5.2.

Everything else is byte-identical. Scoring follows 261b (a narrower relation counts as a hit).

**Before running, check the dev-probe gate:** only run the sealed experiment if §4.2 supports H3 for at least one of the T, Q or P families. If H1 holds everywhere, stop and use alternative 1 instead.

**Pass marks, fixed in advance:**

| Mark | Bar |
|---|---|
| R1 | RIV wrong saves ≤ 1 per 150 turns (statement families plus no-save turns) |
| R2 | Of the real errors YN approves on these frames, RIV approves at most one third, rounded down, with at least 1 fewer in absolute terms. If YN approves 0, R2 is void, report only. |
| R3 | RIV loses at most 3 facts that YN saved correctly |
| R4 | Common mode: RIV's `q_wrong` ≤ half of YN's `q_wrong` on the same ear-wrong frames |
| R5 | Median ear+checker time per turn ≤ 800 ms; slowest 10% ≤ 1,500 ms |
| R6 | Report only, not a pass mark: exact recall. **Declared in advance: this change is not expected to reach 85% recall by itself**, because the ear caps it. |

**Proved wrong if either holds:**
- RIV approves at least two thirds of the real errors YN approves (the errors stay common-mode even with rival views);
- RIV's error reduction comes with R3 failing, and YN at a stricter cutoff giving the same recall has the same error count. That would mean RIV is only a stricter cutoff under another name.

**Latency guess (untested):** one forward pass per fact. The prompt is about 60 to 120 tokens longer than prompt B, and llama-server's prompt cache can reuse the turn prefix across facts in a turn. Expected per-fact time is 300 to 400 ms against 282 ms now; 4-fact turns may exceed 1.5 s.

**Risks (suggested or untested):**
- Letter-position bias (Zheng et al.); PriDe correction is included.
- Side-by-side judges can be swayed by surface features (Tripathi et al., thin evidence).
- Crude rival rules could lose true facts by offering a "better-looking" wrong span. That is why R3 exists.

---

## 6. Ranked alternatives (at most 3)

1. **Recall: a mechanical coordination distributor for plural relatives (the ear-side cap).** If the turn has "A, B and C are my Rs" (or "A and B are X's Rs") and the ear wrote at least one fact (owner, R-singular, name) whose name sits in that list, propose the same fact for the other names in the list. Every proposed fact still goes through the checker.
   - Target: the largest measured recall loss (4 of 16 found).
   - Pass: that family goes from 4/16 to ≥ 12/16 with 0 added wrong saves.
   - Proved wrong if the added facts produce any wrong save, or the family recall is < 10/16.
   - **untested.** It is a rule and not count-then-list, but it is related.
2. **Extend 261b's surface guard to lowercase chat, plus a filler-word lexicon.** Hold back any stored span whose edge token is a known chat word (btw, tho, lol, ok, yeah ...) or not in a name or word dictionary, including in all-lowercase turns. This targets the dev "cla amberly btw" case, which 261b explicitly lets through.
   - Cheap, and does not depend on the model.
   - Real-word typos still slip (v3 note), and unusual names will be held too often (suggested by Pruthi et al.'s framing).
3. **Fix how the cutoff is chosen, with no change to the checker.** Refit θ for the *current* prompt B on a fresh threshold-dev set with the worst-family rule (§5.2), and never on the set used to pick the prompt. This is the pure H2 fix. If the §4.2 test says H2 explains check-questions and H1 explains typos, then alternative 3 together with 2 may beat §5 at a fraction of the cost.

---

## 7. Plain-language summary for Ben

The checker is not just copying the ear's mistakes. On practice data it caught 90 of the 103 wrong facts the ear wrote. The mistakes it lets through are specific ones:
- **Copied spelling mistakes.** If the ear copies a typo into a fact, the typo really is in your message, so "does the message say this?" comes out yes. Big language models also read straight through typos.
- **Sentences with two meanings.** "Imogen's mother is Wrenna and she speaks X" could mean either woman. The checker only ever sees one reading, so it approves it.
- **The check-question.** The checker actually leaned "no" on it, but the save cutoff was set just above the practice questions, and those all used one sentence pattern.

My suggestion: show the checker the ear's fact alongside a few close alternatives, and make it pick one. The alternatives are a different owner, the name with the extra word trimmed, "they're only asking", and "none". A fact is saved only if the ear's version clearly wins; a split vote means Premonition should ask you. Before building it, a five-minute test on practice data can show whether the checker can tell the right version from the alternatives at all; if it can't, we use simple spelling rules instead. None of this fixes the facts the ear never writes down (it found only 4 of 16 in "my sisters are A, B and C" sentences), so that needs its own fix.

---

## PAPERS TO READ IN FULL

These are the arXiv IDs whose body text (methods or numbers) a claim above relies on, and which I could not read beyond the abstract or title:
- **2309.03882**: PriDe procedure details and the size of the letter bias (used in §5 scoring).
- **2207.05221**: the exact finding that seeing several samples improves P(True), and the "right format" conditions (used to motivate §5).
- **2504.14716**: whether side-by-side judges are more swayed by surface features than one-at-a-time judges, and by how much (the §5 risk).
- **2306.00024**: whether there is a separate omission-finding step, and its recall and precision effect (§3c).
- **2211.07145**: how hard omission detection is, in numbers (§3c).
- **2311.01740**: cross-model and cross-question consistency results (§3a).
- **2606.20158**: the "fail together" analysis and the 66% vote figure (§3a).
- **2506.07962**: the LLM-as-judge downstream analysis (§3a).
- **cs/0006023**: statement versus declarative-question confusions and the role of prosody (§3b).
- **2107.00807**: which pragmatic cases event-factuality models fail on (§3b).
- **2004.02709**: contrast-set construction, as background for the rival rules.

Classics cited by title and DOI only: Knight & Leveson 1986 (10.1109/TSE.1986.6312924), Eckhardt & Lee 1985 (10.1109/TSE.1985.231895), Littlewood & Miller 1989 (10.1109/32.58771), Blum & Mitchell 1998 (10.1145/279943.279962), de Marneffe et al. 2012 (10.1162/COLI_a_00097), Shriberg et al. 1998 (10.1177/002383099804100410).

## Addendum (research thread, 2026-09-23 06:10 UTC): the 13 of 103 figure, and 267

**What 13 of 103 means (shown).** It comes from the sealed dev sweep in `artifacts/claude-earcheck261-20260922/theta.json`:
- at cutoff 0 (checker passes everything), 103 dev frames were scored wrong;
- at the sealed cutoff 0.25, 13 were still passed, so the checker held back 90.

Three cautions:
- The 103 includes label artefacts from the scorer.
- This dev set is the same one the prompt wording (B) and the 0.25 cutoff were chosen on. So 90 held is an in-sample figure.
- On a fresh dev set from a separate writer, experiment 267 had the yes/no checker let 63 of 65 wrong frames through (23 of 25 after the relative-gold artefact).

**Reading (suggested, not shown).** The drop from about 87% held on the tuning set to about 3–8% held on fresh wording supports the "0.25 is fitted to the practice set" hypothesis. The two sets have different error mixes, so this is not a controlled comparison.

## Corrections after reading the full papers (2026-09-23, research thread)

The paper texts arrived through Ben's Mac. Every claim was checked against them in `reviews/paper-claims-check-2026-09-23.md`: 30 of 36 confirmed, 5 overstated, 1 wrong. I spot-checked items 2 and 6 and the CoVe finding myself. Corrections:

1. **2606.20158.** The authors are Ron, Baudry and Monperrus (first author Ron), not "Monperrus et al.". The paper has no "66%" and no "bugs" figure. It reports the mean number of failing test inputs (out of 1,000,000) falling from 387.44 for single versions to 130.99 for three-version units.
2. **2207.05221 (Kadavath et al.).** The same paper finds that "replacing an option with 'none of the above' reduces accuracy and calibration significantly". §5's rival-readings checker always includes "none", so this paper is partly *against* that design choice. A §5 build should test with and without the "none" option.
3. **PriDe (2309.03882).** The per-item prior is a softmax of the *log* probabilities averaged over cyclic permutations (Eq. 7). The prior is then averaged over items and divided out (Eq. 8). It is defined for a fixed number of options, while §5 uses 2 to 6, so the prior has to be estimated separately for each option count.
4. **Contrast sets (2004.02709).** They are written by hand by experts, for evaluation. The paper warns that rule-built perturbations rarely cross the decision boundary. §5's rule-built rivals are *inspired by* contrast sets; they are not contrast sets.
5. **Stolcke et al. (cs/0006023).** Statement-shaped questions are confused with statements, but the next turn (for example a yes/no answer) also resolves them. Words alone separate questions from statements 85.9% of the time on balanced data. "Often marked only by intonation" overstates this.

**Findings that back the plan (confirmed in full text):**
- CoVe (2309.11495, Table 4): open verification questions beat yes/no questions, and the model tends to agree with yes/no facts whether they are right or wrong. This supports testing a question-answering checker.
- 2306.00024: its separate "find what was missed" step raised recall (medications 0.928 → 0.946), but lowered precision (0.929 → 0.881).
