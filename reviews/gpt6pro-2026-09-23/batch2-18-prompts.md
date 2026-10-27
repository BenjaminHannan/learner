# GPT-6 Pro prompts, batch 2 (2026-09-23)

18 prompts, hardest first. Paste each code block into its own GPT-6 Pro chat. Every block is complete on its own: it starts with the same full project context, because GPT runs as a plain chat and can't see the repo. Bring the answers back to the research thread; they will be checked against the code and the papers before anything is acted on.

No blind-panel items are quoted; every example sentence is invented, with fictional names.

## Contents

1. A gate that still works on wording it has never seen
2. Write rules that can cover 85% of real facts without licensing wrong ones
3. Telling, checking, supposing or planning: speech acts without the question mark
4. Training a small own ear on synthetic data that works on real chat
5. One principled question reader instead of a stack of patches
6. Trustworthy evaluation when every panel writer and grader is an AI
7. Reading several facts, appositives and pronouns in one sentence
8. An own mouth that is fluent, faithful and 99% grammatical at about 30M parameters
9. Corrections, retractions and facts that change over time
10. Casual typing: lowercase, no apostrophes, typos, without silently changing names
11. Proving the design beats an equal-size plain transformer, fairly
12. "Our" and "we": group owners in a person-by-person notebook
13. Every sentence the assistant says must be true
14. A relation vocabulary that can grow without wrong saves
15. Combining many verified single changes into one base
16. Speed: a 5% time bar measured on a busy machine, and a 27B gate per fact
17. What should "sleep" do in a system with an explicit notebook?
18. A safe "thinking" mode that uses the web without polluting the notebook

## 1. A gate that still works on wording it has never seen

```text
=== PROJECT CONTEXT (the same block starts every question in this batch) ===
You are advising on a research project through a plain chat. You cannot see the code, the files, or earlier chats, so everything you need is below. Where I give a number, it was measured; where I say "suggested" or "I think", it was not.

WHAT PREMONITION IS
Premonition is a personal assistant being built by a high-school senior (the owner), with AI coding agents doing the building and Claude directing and verifying. It starts knowing nothing. The user teaches it facts in plain English chat. It stores them in an explicit notebook, reasons over them (two-hop and beyond), says "I don't know" instead of guessing, and replies in fluent English. The end goal is a system on the owner's OWN architecture and OWN weights that beats an equal-size plain transformer (same data, same parameter count) on two-hop questions, reversal questions (asking the inverse of a taught fact), abstention on untaught facts, and multi-hop answers after a fact is edited (MQuAKE-style), plus a live demo for the owner's family.

HARD TARGETS
- 0 wrong notebook writes, certified below 1%. A wrong save is worse than a refusal or a clarifying question.
- Recall: at least 85% of plainly stated facts saved exactly; at most 12% of true facts held back.
- 99%+ grammatical replies, no simple mistakes, and no reply may claim something untrue about the notebook or about the assistant itself.
- Median turn time at most 800 ms.

THE PIPELINE TODAY (numbers are from sealed experiments)
1. EAR (English -> frames), BORROWED: SmolLM2-360M fine-tuned ("ear v4.1") to write one line per frame:
     TEACH | owner | relation | value      (e.g. TEACH | me | sister | Mira)
     ASK   | owner | relation              (e.g. ASK | Mira | dog)
     NONE
   A plain-code "speaker canonicaliser" maps I/me/my to the user ("me").
2. RULE BRAKE (plain code): drops frames with junk, e.g. a stored name containing a comma, or a value not found in the turn.
3. GATE, BORROWED: Qwen3.8-27B (4-bit, local on one RTX 5070 Ti 16 GB) is asked YES/NO "does this message explicitly assert this claim?" per frame; saved if P(YES) >= 0.25. The prompt wording and the 0.25 threshold were both chosen on a development set.
4. NOTEBOOK: rows owner | relation | value, e.g.  me | sister | Mira ;  Mira | dog | Pip. "X is the R of Y" is stored as "Y's R is X". Taught facts are never overwritten by inferences. Inverses ("Whose dog is Pip?") are computed at answer time. Relations come from a fixed relation table of 153 entries (each with aliases, an inverse, single- or multi-valued, and the kind of value) plus "other".
5. REASONER (ours): a question parser built as a stack of hand-written stages, each added by one past experiment (a reverse-question stage, a table stage, a yes/no reader, an n-hop chain stage, a decline-wording rewrite, ...), plus a 79,316-parameter learned lookup reasoner for multi-hop. On clean structured input it answers two-hop, reversal, abstention and single-edit multi-hop questions exactly (200/200 on an internal benchmark). The weak point is reading English, in and out.
6. MOUTH (ours, hand-made): a grammar layer that turns reply records into sentences. Grammar 1195/1205 = 99.2% under two independently checked graders; a blind judge preferred it 97 wins / 9 losses / 14 ties over the previous version. It still sometimes prints raw relation-table labels (e.g. "religion or worldview").
7. OWN-MODEL PLAN (not built yet): a ~33M-parameter own ear (8-layer width-512 bidirectional encoder, pretrained by fill-in-the-blank on simple-English stories and dialogues; heads that POINT at whole-word spans of the turn for owner and value; relation chosen from the table; a 9-way speech-act head; a fact-count head; 6 set-prediction fact slots) and an own mouth (a 28.85M decoder trained from scratch, "talker101"). Only a small plain-code "write compiler" may write to the notebook, from spans of the unchanged turn, all facts of a turn together or none. A round trip (fact -> sentence -> fact) is used for TRAINING only and is never permission to write, because it can agree with itself on a wrong fact.

MEASURED STATE OF EACH PART (fresh blind panels unless noted)
- Ear + gate (150 fresh turns): 9 scored wrong saves; 6 of those were answer-key mistakes (key said "pet", ear said "dog"), 3 were real: 2 chat typos stored inside a value (gate P(YES) 0.85 and 0.68) and 1 fact saved from a check-question with no "?" (0.37). Recall 77.9%. Threshold sweep: 19 wrong at threshold 0, 9 at 0.25, 7 at 0.7. Sentences naming several relatives: 4 of 16 facts found.
- On the development set used to choose the gate prompt and threshold, the gate let 13 of 103 wrong frames through. On 120 fresh turns from a new writer it let 63 of 65 through. So the gate barely works on fresh wording.
- A 3-question QA gate (ask "whose R is V?", "what is O's R?", "how is O related to V?" in separate prompts): 5 wrong out of 86 saved vs YES/NO 6 out of 100, but it held back 30% of true facts (bar 12%) and took 880 ms median (bar 800). Registered FAIL.
- Own-model write rules, oracle audit (a perfect reader, the planned strict write compiler): only 184 of 272 real facts (67.6%) are writable (bar 85%); 0 of 76 should-not-save facts writable.
- Casual typing (all lowercase, no apostrophes, typos) is read badly: a normaliser experiment failed and itself added 3 wrong saves.
- "our/we" is NOT the speaker (owner's ruling): the assistant must ask whose. An "ask whose" rule failed because the ear rarely hands it a group owner (14 of 30 asked, bar 27).
- Questions outside the parser's known shapes get "I didn't understand that": 40 of 51 yes/no questions were not understood.
- Replies: an honest "what can you do" list now makes 0 unsupported claims.

HOW WORK IS DONE (the rules)
- Every change is ONE sealed, pre-registered experiment: one change against a named base, predictions and pass marks fixed before the run, files sealed with SHA-256 hashes before the registered run.
- Pass/fail is decided on a blind TEST-ONLY panel written by a separate AI agent from a spec. Panels are never trained or tuned on, never quoted, and become "burned" once a builder sees items.
- A registered FAIL stays FAIL. A failed experiment gets exactly one diagnosis-driven follow-up.
- Director verifies every report: seal check, own recount from raw files, a held-out probe for every PASS.
- Fictional names only in all test and training data. No personal data. Unverified web text never goes into weights.
- The only human is the owner, a high-school senior who does not run commands; AI agents build, write panels and grade.

HARDWARE AND BUDGET
One RTX 5070 Ti (16 GB), sometimes offline; a busy shared Mac for CPU work; cloud GPU rentals within a $30 TOTAL budget. Downloading any new model needs the owner's explicit yes. A big model's GENERATED TEXT may be used as training data (stated honestly); borrowing its WEIGHTS for the final system is not allowed (borrowed parts are placeholders).

SCOPE
Only the chat assistant (ear, gate, notebook, reasoner, mouth). The owner has other projects ("small card experiments", "a village model"); do not mix them in.
=== END OF PROJECT CONTEXT ===

QUESTION 1 OF A BATCH (answer only this one): A gate that still works on wording it has never seen

THE PROBLEM
The gate (the 27B YES/NO checker) looked good on the development set it was tuned on and almost useless on fresh wording. I need a way to stop wrong notebook writes that holds up on new wording, costs little recall, and whose mistakes are not the same as the ear's.

DETAIL (all measured)
- Dev set (used to choose the prompt and the 0.25 threshold): 103 wrong ear frames, the gate let 13 through; recall 91.9%.
- Fresh blind panel, 150 turns: 3 real wrong saves (2 typos inside a value, gate P(YES) 0.85 and 0.68; 1 check-question without "?", 0.37). Threshold 0 -> 19 wrong, 0.25 -> 9, 0.7 -> 7 (these counts include 6 answer-key mistakes), recall 77.9% -> 77.1%.
- Fresh development set by a new writer (120 turns, 117 gold facts). Hits / wrong-of-saved:
    ear alone          90 hits, 65 wrong of 155 saved
    YES/NO gate        90 hits, 63 wrong of 153 saved
    3-question QA gate 76 hits, 31 wrong of 107 saved
    pick 1 of 4 readings (the ear's frame vs 3 rivals, plus "none") 74 hits, 55 wrong of 129
  About 40 of each arm's "wrong" were answer-key mistakes (appositive relatives the key left out). Without them: ear 25, YES/NO 23, QA 2, pick-1-of-4 16. Pick-1-of-4 broke on any turn with a second name (13 of 14 plural frames picked the other name).
- Registered QA-gate test, 150 turns: QA 81/125 facts, 5 wrong of 86 saved, held back 30.4% (bar 12%), 880 ms median (bar 800). YES/NO: 94/125, 6 wrong of 100. Ear alone: 95/125, 30 wrong.
- Two prompt wordings gave very different P(YES) on "so ..." check-questions: 0.12-0.24 with one, 0.58-0.70 with the other.
- My reading (suggested, not shown): the threshold was overfit to the dev wording; the gate and the ear share blind spots because both read the same surface cues; QA removes real bad readings but gives three chances to say no, so it loses true facts.

ALREADY TRIED OR ADOPTED (do not re-propose as new)
Logit margin score, relation-specific claim renderers, "explicitly asserts / ambiguity = NO" wording, the 3-question QA gate, pick-1-of-4 with "none", a mixed-case typo guard, count-then-list, a separate "telling or checking?" question (planned), Qwen as the full reader, a trained 360M verifier (planned), round-trip as permission (rejected).

THE HARD QUESTION
What gate design has errors that are nearly independent of the ear's and still generalises to fresh wording? Consider, among others: asking the user to confirm only when a cheap signal says "risky" (and how to count that against the 12% held-back bar), gating by error KIND (typo, act, binding, relation) with a different check for each, selective prediction / conformal risk control with a threshold fitted on a fresh calibration set, disagreement between two readers trained on different data, span-level evidence the checker must quote, and gating the relation, owner and value separately. How much of this is a threshold problem and how much a reader problem? Which single experiment best separates those two explanations?

WHAT I NEED BACK
1. Your diagnosis: what is really going on, and which of my explanations above is wrong or incomplete.
2. At most 4 ranked options, each with what it fixes, what it costs, and what it cannot fix.
3. The ONE experiment to run next: a single change against the current system, pass marks with exact numbers fixed in advance, the sample size and why, and the result that would prove your idea wrong. If it needs a later second step, name it but keep it separate.
4. The strongest objection to your own recommendation, and the rival you rejected.
5. Label every claim as SHOWN (published or measured), SUGGESTED (published, but in a different setting) or UNTESTED (your reasoning). Cite papers with arXiv IDs where you can, and say when you know only the abstract. Do not invent numbers or citations; say "I don't know" instead.
6. Keep this only about the chat assistant; no "small card experiments" or "village model".
7. End with a plain-language summary of 6-10 sentences that a high-school senior can follow.
```

## 2. Write rules that can cover 85% of real facts without licensing wrong ones

```text
=== PROJECT CONTEXT (the same block starts every question in this batch) ===
You are advising on a research project through a plain chat. You cannot see the code, the files, or earlier chats, so everything you need is below. Where I give a number, it was measured; where I say "suggested" or "I think", it was not.

WHAT PREMONITION IS
Premonition is a personal assistant being built by a high-school senior (the owner), with AI coding agents doing the building and Claude directing and verifying. It starts knowing nothing. The user teaches it facts in plain English chat. It stores them in an explicit notebook, reasons over them (two-hop and beyond), says "I don't know" instead of guessing, and replies in fluent English. The end goal is a system on the owner's OWN architecture and OWN weights that beats an equal-size plain transformer (same data, same parameter count) on two-hop questions, reversal questions (asking the inverse of a taught fact), abstention on untaught facts, and multi-hop answers after a fact is edited (MQuAKE-style), plus a live demo for the owner's family.

HARD TARGETS
- 0 wrong notebook writes, certified below 1%. A wrong save is worse than a refusal or a clarifying question.
- Recall: at least 85% of plainly stated facts saved exactly; at most 12% of true facts held back.
- 99%+ grammatical replies, no simple mistakes, and no reply may claim something untrue about the notebook or about the assistant itself.
- Median turn time at most 800 ms.

THE PIPELINE TODAY (numbers are from sealed experiments)
1. EAR (English -> frames), BORROWED: SmolLM2-360M fine-tuned ("ear v4.1") to write one line per frame:
     TEACH | owner | relation | value      (e.g. TEACH | me | sister | Mira)
     ASK   | owner | relation              (e.g. ASK | Mira | dog)
     NONE
   A plain-code "speaker canonicaliser" maps I/me/my to the user ("me").
2. RULE BRAKE (plain code): drops frames with junk, e.g. a stored name containing a comma, or a value not found in the turn.
3. GATE, BORROWED: Qwen3.8-27B (4-bit, local on one RTX 5070 Ti 16 GB) is asked YES/NO "does this message explicitly assert this claim?" per frame; saved if P(YES) >= 0.25. The prompt wording and the 0.25 threshold were both chosen on a development set.
4. NOTEBOOK: rows owner | relation | value, e.g.  me | sister | Mira ;  Mira | dog | Pip. "X is the R of Y" is stored as "Y's R is X". Taught facts are never overwritten by inferences. Inverses ("Whose dog is Pip?") are computed at answer time. Relations come from a fixed relation table of 153 entries (each with aliases, an inverse, single- or multi-valued, and the kind of value) plus "other".
5. REASONER (ours): a question parser built as a stack of hand-written stages, each added by one past experiment (a reverse-question stage, a table stage, a yes/no reader, an n-hop chain stage, a decline-wording rewrite, ...), plus a 79,316-parameter learned lookup reasoner for multi-hop. On clean structured input it answers two-hop, reversal, abstention and single-edit multi-hop questions exactly (200/200 on an internal benchmark). The weak point is reading English, in and out.
6. MOUTH (ours, hand-made): a grammar layer that turns reply records into sentences. Grammar 1195/1205 = 99.2% under two independently checked graders; a blind judge preferred it 97 wins / 9 losses / 14 ties over the previous version. It still sometimes prints raw relation-table labels (e.g. "religion or worldview").
7. OWN-MODEL PLAN (not built yet): a ~33M-parameter own ear (8-layer width-512 bidirectional encoder, pretrained by fill-in-the-blank on simple-English stories and dialogues; heads that POINT at whole-word spans of the turn for owner and value; relation chosen from the table; a 9-way speech-act head; a fact-count head; 6 set-prediction fact slots) and an own mouth (a 28.85M decoder trained from scratch, "talker101"). Only a small plain-code "write compiler" may write to the notebook, from spans of the unchanged turn, all facts of a turn together or none. A round trip (fact -> sentence -> fact) is used for TRAINING only and is never permission to write, because it can agree with itself on a wrong fact.

MEASURED STATE OF EACH PART (fresh blind panels unless noted)
- Ear + gate (150 fresh turns): 9 scored wrong saves; 6 of those were answer-key mistakes (key said "pet", ear said "dog"), 3 were real: 2 chat typos stored inside a value (gate P(YES) 0.85 and 0.68) and 1 fact saved from a check-question with no "?" (0.37). Recall 77.9%. Threshold sweep: 19 wrong at threshold 0, 9 at 0.25, 7 at 0.7. Sentences naming several relatives: 4 of 16 facts found.
- On the development set used to choose the gate prompt and threshold, the gate let 13 of 103 wrong frames through. On 120 fresh turns from a new writer it let 63 of 65 through. So the gate barely works on fresh wording.
- A 3-question QA gate (ask "whose R is V?", "what is O's R?", "how is O related to V?" in separate prompts): 5 wrong out of 86 saved vs YES/NO 6 out of 100, but it held back 30% of true facts (bar 12%) and took 880 ms median (bar 800). Registered FAIL.
- Own-model write rules, oracle audit (a perfect reader, the planned strict write compiler): only 184 of 272 real facts (67.6%) are writable (bar 85%); 0 of 76 should-not-save facts writable.
- Casual typing (all lowercase, no apostrophes, typos) is read badly: a normaliser experiment failed and itself added 3 wrong saves.
- "our/we" is NOT the speaker (owner's ruling): the assistant must ask whose. An "ask whose" rule failed because the ear rarely hands it a group owner (14 of 30 asked, bar 27).
- Questions outside the parser's known shapes get "I didn't understand that": 40 of 51 yes/no questions were not understood.
- Replies: an honest "what can you do" list now makes 0 unsupported claims.

HOW WORK IS DONE (the rules)
- Every change is ONE sealed, pre-registered experiment: one change against a named base, predictions and pass marks fixed before the run, files sealed with SHA-256 hashes before the registered run.
- Pass/fail is decided on a blind TEST-ONLY panel written by a separate AI agent from a spec. Panels are never trained or tuned on, never quoted, and become "burned" once a builder sees items.
- A registered FAIL stays FAIL. A failed experiment gets exactly one diagnosis-driven follow-up.
- Director verifies every report: seal check, own recount from raw files, a held-out probe for every PASS.
- Fictional names only in all test and training data. No personal data. Unverified web text never goes into weights.
- The only human is the owner, a high-school senior who does not run commands; AI agents build, write panels and grade.

HARDWARE AND BUDGET
One RTX 5070 Ti (16 GB), sometimes offline; a busy shared Mac for CPU work; cloud GPU rentals within a $30 TOTAL budget. Downloading any new model needs the owner's explicit yes. A big model's GENERATED TEXT may be used as training data (stated honestly); borrowing its WEIGHTS for the final system is not allowed (borrowed parts are placeholders).

SCOPE
Only the chat assistant (ear, gate, notebook, reasoner, mouth). The owner has other projects ("small card experiments", "a village model"); do not mix them in.
=== END OF PROJECT CONTEXT ===

QUESTION 2 OF A BATCH (answer only this one): Write rules that can cover 85% of real facts without licensing wrong ones

THE PROBLEM
The own-model plan says only a plain-code write compiler may write, from spans of the unchanged turn. An oracle audit says even a perfect reader could write only 2 in 3 real facts under those rules. The bar is 85%.

HOW THE STRICT RULES WORK (version 0)
- Owner: a whole-word span of the turn, or ME (I/me/my). "we/our" gives WE, which may not write.
- Relation: one of 153 table relations, and the turn must contain a CUE word for it (the relation name or an alias, e.g. "mum" for mother) as a whole span.
- Value: a whole-word span of the turn.
- Mode: only ASSERT, CORRECT or DENY may write; ASK, CHECK, SUPPOSE, PLAN, REPORTED never write.
- A turn's facts are written all together or not at all.

MEASURED (oracle audit, 300 hand-written dev turns, 272 real facts, 76 must-not-save facts)
- Writable: 184/272 = 67.6%; 193/272 if WE -> ME were allowed; 0/76 must-not-save facts writable (good).
- Misses: 59 no relation cue in the turn, 12 relation not in the table, 10 WE owner, 7 typo in the value, 1 owner.
- The 59 no-cue misses are mostly: plurals ("Mira and Tal are my sisters" has "sisters", not "sister"), verb facts ("Oren works at Brightline", "Ada moved to Tolby"), and bare possessives ("Ada's Pip" meaning Ada's dog Pip, known only from earlier context).
- Queued follow-up: cue v1 (plural forms + verb templates from the table), on 300 fresh turns by a new writer, also reporting the ceiling if a learned licence were allowed as a backup.

THE HARD QUESTION
Is "strict compiler + plain-code licences" the right design at all, or should the system use a selective learned parser (it may write anything it is confident about, with an audited error rate)? Is there a middle path: a small set of formal licences (cue word, verb template, earlier-context binding, appositive, coordination) that each has a provable property, plus a learned component that can only choose among licensed readings? How do verb facts and context-dependent facts ("Ada's Pip") get licensed without opening the door to the known wrong-save kinds (typos stored, check-questions saved, plans saved, pronoun bound to the wrong person)? Give the coverage you expect from each licence family and say how to measure it before any model is trained.

WHAT I NEED BACK
1. Your diagnosis: what is really going on, and which of my explanations above is wrong or incomplete.
2. At most 4 ranked options, each with what it fixes, what it costs, and what it cannot fix.
3. The ONE experiment to run next: a single change against the current system, pass marks with exact numbers fixed in advance, the sample size and why, and the result that would prove your idea wrong. If it needs a later second step, name it but keep it separate.
4. The strongest objection to your own recommendation, and the rival you rejected.
5. Label every claim as SHOWN (published or measured), SUGGESTED (published, but in a different setting) or UNTESTED (your reasoning). Cite papers with arXiv IDs where you can, and say when you know only the abstract. Do not invent numbers or citations; say "I don't know" instead.
6. Keep this only about the chat assistant; no "small card experiments" or "village model".
7. End with a plain-language summary of 6-10 sentences that a high-school senior can follow.
```

## 3. Telling, checking, supposing or planning: speech acts without the question mark

```text
=== PROJECT CONTEXT (the same block starts every question in this batch) ===
You are advising on a research project through a plain chat. You cannot see the code, the files, or earlier chats, so everything you need is below. Where I give a number, it was measured; where I say "suggested" or "I think", it was not.

WHAT PREMONITION IS
Premonition is a personal assistant being built by a high-school senior (the owner), with AI coding agents doing the building and Claude directing and verifying. It starts knowing nothing. The user teaches it facts in plain English chat. It stores them in an explicit notebook, reasons over them (two-hop and beyond), says "I don't know" instead of guessing, and replies in fluent English. The end goal is a system on the owner's OWN architecture and OWN weights that beats an equal-size plain transformer (same data, same parameter count) on two-hop questions, reversal questions (asking the inverse of a taught fact), abstention on untaught facts, and multi-hop answers after a fact is edited (MQuAKE-style), plus a live demo for the owner's family.

HARD TARGETS
- 0 wrong notebook writes, certified below 1%. A wrong save is worse than a refusal or a clarifying question.
- Recall: at least 85% of plainly stated facts saved exactly; at most 12% of true facts held back.
- 99%+ grammatical replies, no simple mistakes, and no reply may claim something untrue about the notebook or about the assistant itself.
- Median turn time at most 800 ms.

THE PIPELINE TODAY (numbers are from sealed experiments)
1. EAR (English -> frames), BORROWED: SmolLM2-360M fine-tuned ("ear v4.1") to write one line per frame:
     TEACH | owner | relation | value      (e.g. TEACH | me | sister | Mira)
     ASK   | owner | relation              (e.g. ASK | Mira | dog)
     NONE
   A plain-code "speaker canonicaliser" maps I/me/my to the user ("me").
2. RULE BRAKE (plain code): drops frames with junk, e.g. a stored name containing a comma, or a value not found in the turn.
3. GATE, BORROWED: Qwen3.8-27B (4-bit, local on one RTX 5070 Ti 16 GB) is asked YES/NO "does this message explicitly assert this claim?" per frame; saved if P(YES) >= 0.25. The prompt wording and the 0.25 threshold were both chosen on a development set.
4. NOTEBOOK: rows owner | relation | value, e.g.  me | sister | Mira ;  Mira | dog | Pip. "X is the R of Y" is stored as "Y's R is X". Taught facts are never overwritten by inferences. Inverses ("Whose dog is Pip?") are computed at answer time. Relations come from a fixed relation table of 153 entries (each with aliases, an inverse, single- or multi-valued, and the kind of value) plus "other".
5. REASONER (ours): a question parser built as a stack of hand-written stages, each added by one past experiment (a reverse-question stage, a table stage, a yes/no reader, an n-hop chain stage, a decline-wording rewrite, ...), plus a 79,316-parameter learned lookup reasoner for multi-hop. On clean structured input it answers two-hop, reversal, abstention and single-edit multi-hop questions exactly (200/200 on an internal benchmark). The weak point is reading English, in and out.
6. MOUTH (ours, hand-made): a grammar layer that turns reply records into sentences. Grammar 1195/1205 = 99.2% under two independently checked graders; a blind judge preferred it 97 wins / 9 losses / 14 ties over the previous version. It still sometimes prints raw relation-table labels (e.g. "religion or worldview").
7. OWN-MODEL PLAN (not built yet): a ~33M-parameter own ear (8-layer width-512 bidirectional encoder, pretrained by fill-in-the-blank on simple-English stories and dialogues; heads that POINT at whole-word spans of the turn for owner and value; relation chosen from the table; a 9-way speech-act head; a fact-count head; 6 set-prediction fact slots) and an own mouth (a 28.85M decoder trained from scratch, "talker101"). Only a small plain-code "write compiler" may write to the notebook, from spans of the unchanged turn, all facts of a turn together or none. A round trip (fact -> sentence -> fact) is used for TRAINING only and is never permission to write, because it can agree with itself on a wrong fact.

MEASURED STATE OF EACH PART (fresh blind panels unless noted)
- Ear + gate (150 fresh turns): 9 scored wrong saves; 6 of those were answer-key mistakes (key said "pet", ear said "dog"), 3 were real: 2 chat typos stored inside a value (gate P(YES) 0.85 and 0.68) and 1 fact saved from a check-question with no "?" (0.37). Recall 77.9%. Threshold sweep: 19 wrong at threshold 0, 9 at 0.25, 7 at 0.7. Sentences naming several relatives: 4 of 16 facts found.
- On the development set used to choose the gate prompt and threshold, the gate let 13 of 103 wrong frames through. On 120 fresh turns from a new writer it let 63 of 65 through. So the gate barely works on fresh wording.
- A 3-question QA gate (ask "whose R is V?", "what is O's R?", "how is O related to V?" in separate prompts): 5 wrong out of 86 saved vs YES/NO 6 out of 100, but it held back 30% of true facts (bar 12%) and took 880 ms median (bar 800). Registered FAIL.
- Own-model write rules, oracle audit (a perfect reader, the planned strict write compiler): only 184 of 272 real facts (67.6%) are writable (bar 85%); 0 of 76 should-not-save facts writable.
- Casual typing (all lowercase, no apostrophes, typos) is read badly: a normaliser experiment failed and itself added 3 wrong saves.
- "our/we" is NOT the speaker (owner's ruling): the assistant must ask whose. An "ask whose" rule failed because the ear rarely hands it a group owner (14 of 30 asked, bar 27).
- Questions outside the parser's known shapes get "I didn't understand that": 40 of 51 yes/no questions were not understood.
- Replies: an honest "what can you do" list now makes 0 unsupported claims.

HOW WORK IS DONE (the rules)
- Every change is ONE sealed, pre-registered experiment: one change against a named base, predictions and pass marks fixed before the run, files sealed with SHA-256 hashes before the registered run.
- Pass/fail is decided on a blind TEST-ONLY panel written by a separate AI agent from a spec. Panels are never trained or tuned on, never quoted, and become "burned" once a builder sees items.
- A registered FAIL stays FAIL. A failed experiment gets exactly one diagnosis-driven follow-up.
- Director verifies every report: seal check, own recount from raw files, a held-out probe for every PASS.
- Fictional names only in all test and training data. No personal data. Unverified web text never goes into weights.
- The only human is the owner, a high-school senior who does not run commands; AI agents build, write panels and grade.

HARDWARE AND BUDGET
One RTX 5070 Ti (16 GB), sometimes offline; a busy shared Mac for CPU work; cloud GPU rentals within a $30 TOTAL budget. Downloading any new model needs the owner's explicit yes. A big model's GENERATED TEXT may be used as training data (stated honestly); borrowing its WEIGHTS for the final system is not allowed (borrowed parts are placeholders).

SCOPE
Only the chat assistant (ear, gate, notebook, reasoner, mouth). The owner has other projects ("small card experiments", "a village model"); do not mix them in.
=== END OF PROJECT CONTEXT ===

QUESTION 3 OF A BATCH (answer only this one): Telling, checking, supposing or planning: speech acts without the question mark

THE PROBLEM
Many real wrong saves were not misreadings of WHAT was said but of WHAT THE SPEAKER WAS DOING: a check-question without "?" ("so Mira's dog is Pip"), a pretend turn ("let's say Oren's boss is Tal"), a plan or wish ("Mira wants a cat named Fig"), reported speech ("Tal says her boss is Oren"). The fact inside them looks exactly like a statement.

DETAIL
- 1 of the 3 real wrong saves on the last fresh panel was a check-question with no "?". An earlier panel had pretend turns, plans and check-questions saved as facts.
- The 27B gate's verdict on "so ..." check-questions depended on prompt wording: P(YES) 0.12-0.24 with one prompt, 0.58-0.70 with another. So the gate is not a reliable act detector.
- The own-model plan adds a 9-way act head (STATE / CORRECT / DENY / ASK / CHECK / SUPPOSE / PLAN / CHAT / UNCLEAR) and a per-fact mode (ASSERT / CORRECT / DENY / ASK / CHECK / SUPPOSE / PLAN / REPORTED / NONE); only STATE/ASSERT, CORRECT and DENY may write. In its synthetic training data SUPPOSE and PLAN are only 1.4% of rows each.
- Published (Stolcke et al. 2000, arXiv cs/0006023, telephone speech): dialogue-act tagging from word transcripts reached 71% accuracy (chance 35%; human labellers agreed 84%). Words alone separated questions from statements 85.9% of the time on balanced data; statement-shaped questions were resolved by intonation or by the next turn.
- A turn can hold a statement and a question at once. Past facts that are no longer true ("Ada used to live in Rook"), negation ("Ada doesn't have a cat"), sarcasm and jokes also exist.

THE HARD QUESTION
How do I get near-zero false "this is a statement" on non-assertions while letting nearly all real statements through, with a small model and synthetic training data? What label scheme (per turn or per fact?), what data (how to generate hard negatives that differ from statements by one cue), what use of the previous assistant reply, and what fallback (ask the user "Is that right, or are you asking?") gives the best trade-off? What is the realistic error floor, and how would I measure the false-statement rate precisely enough when these turns are maybe 5-10% of chat?

WHAT I NEED BACK
1. Your diagnosis: what is really going on, and which of my explanations above is wrong or incomplete.
2. At most 4 ranked options, each with what it fixes, what it costs, and what it cannot fix.
3. The ONE experiment to run next: a single change against the current system, pass marks with exact numbers fixed in advance, the sample size and why, and the result that would prove your idea wrong. If it needs a later second step, name it but keep it separate.
4. The strongest objection to your own recommendation, and the rival you rejected.
5. Label every claim as SHOWN (published or measured), SUGGESTED (published, but in a different setting) or UNTESTED (your reasoning). Cite papers with arXiv IDs where you can, and say when you know only the abstract. Do not invent numbers or citations; say "I don't know" instead.
6. Keep this only about the chat assistant; no "small card experiments" or "village model".
7. End with a plain-language summary of 6-10 sentences that a high-school senior can follow.
```

## 4. Training a small own ear on synthetic data that works on real chat

```text
=== PROJECT CONTEXT (the same block starts every question in this batch) ===
You are advising on a research project through a plain chat. You cannot see the code, the files, or earlier chats, so everything you need is below. Where I give a number, it was measured; where I say "suggested" or "I think", it was not.

WHAT PREMONITION IS
Premonition is a personal assistant being built by a high-school senior (the owner), with AI coding agents doing the building and Claude directing and verifying. It starts knowing nothing. The user teaches it facts in plain English chat. It stores them in an explicit notebook, reasons over them (two-hop and beyond), says "I don't know" instead of guessing, and replies in fluent English. The end goal is a system on the owner's OWN architecture and OWN weights that beats an equal-size plain transformer (same data, same parameter count) on two-hop questions, reversal questions (asking the inverse of a taught fact), abstention on untaught facts, and multi-hop answers after a fact is edited (MQuAKE-style), plus a live demo for the owner's family.

HARD TARGETS
- 0 wrong notebook writes, certified below 1%. A wrong save is worse than a refusal or a clarifying question.
- Recall: at least 85% of plainly stated facts saved exactly; at most 12% of true facts held back.
- 99%+ grammatical replies, no simple mistakes, and no reply may claim something untrue about the notebook or about the assistant itself.
- Median turn time at most 800 ms.

THE PIPELINE TODAY (numbers are from sealed experiments)
1. EAR (English -> frames), BORROWED: SmolLM2-360M fine-tuned ("ear v4.1") to write one line per frame:
     TEACH | owner | relation | value      (e.g. TEACH | me | sister | Mira)
     ASK   | owner | relation              (e.g. ASK | Mira | dog)
     NONE
   A plain-code "speaker canonicaliser" maps I/me/my to the user ("me").
2. RULE BRAKE (plain code): drops frames with junk, e.g. a stored name containing a comma, or a value not found in the turn.
3. GATE, BORROWED: Qwen3.8-27B (4-bit, local on one RTX 5070 Ti 16 GB) is asked YES/NO "does this message explicitly assert this claim?" per frame; saved if P(YES) >= 0.25. The prompt wording and the 0.25 threshold were both chosen on a development set.
4. NOTEBOOK: rows owner | relation | value, e.g.  me | sister | Mira ;  Mira | dog | Pip. "X is the R of Y" is stored as "Y's R is X". Taught facts are never overwritten by inferences. Inverses ("Whose dog is Pip?") are computed at answer time. Relations come from a fixed relation table of 153 entries (each with aliases, an inverse, single- or multi-valued, and the kind of value) plus "other".
5. REASONER (ours): a question parser built as a stack of hand-written stages, each added by one past experiment (a reverse-question stage, a table stage, a yes/no reader, an n-hop chain stage, a decline-wording rewrite, ...), plus a 79,316-parameter learned lookup reasoner for multi-hop. On clean structured input it answers two-hop, reversal, abstention and single-edit multi-hop questions exactly (200/200 on an internal benchmark). The weak point is reading English, in and out.
6. MOUTH (ours, hand-made): a grammar layer that turns reply records into sentences. Grammar 1195/1205 = 99.2% under two independently checked graders; a blind judge preferred it 97 wins / 9 losses / 14 ties over the previous version. It still sometimes prints raw relation-table labels (e.g. "religion or worldview").
7. OWN-MODEL PLAN (not built yet): a ~33M-parameter own ear (8-layer width-512 bidirectional encoder, pretrained by fill-in-the-blank on simple-English stories and dialogues; heads that POINT at whole-word spans of the turn for owner and value; relation chosen from the table; a 9-way speech-act head; a fact-count head; 6 set-prediction fact slots) and an own mouth (a 28.85M decoder trained from scratch, "talker101"). Only a small plain-code "write compiler" may write to the notebook, from spans of the unchanged turn, all facts of a turn together or none. A round trip (fact -> sentence -> fact) is used for TRAINING only and is never permission to write, because it can agree with itself on a wrong fact.

MEASURED STATE OF EACH PART (fresh blind panels unless noted)
- Ear + gate (150 fresh turns): 9 scored wrong saves; 6 of those were answer-key mistakes (key said "pet", ear said "dog"), 3 were real: 2 chat typos stored inside a value (gate P(YES) 0.85 and 0.68) and 1 fact saved from a check-question with no "?" (0.37). Recall 77.9%. Threshold sweep: 19 wrong at threshold 0, 9 at 0.25, 7 at 0.7. Sentences naming several relatives: 4 of 16 facts found.
- On the development set used to choose the gate prompt and threshold, the gate let 13 of 103 wrong frames through. On 120 fresh turns from a new writer it let 63 of 65 through. So the gate barely works on fresh wording.
- A 3-question QA gate (ask "whose R is V?", "what is O's R?", "how is O related to V?" in separate prompts): 5 wrong out of 86 saved vs YES/NO 6 out of 100, but it held back 30% of true facts (bar 12%) and took 880 ms median (bar 800). Registered FAIL.
- Own-model write rules, oracle audit (a perfect reader, the planned strict write compiler): only 184 of 272 real facts (67.6%) are writable (bar 85%); 0 of 76 should-not-save facts writable.
- Casual typing (all lowercase, no apostrophes, typos) is read badly: a normaliser experiment failed and itself added 3 wrong saves.
- "our/we" is NOT the speaker (owner's ruling): the assistant must ask whose. An "ask whose" rule failed because the ear rarely hands it a group owner (14 of 30 asked, bar 27).
- Questions outside the parser's known shapes get "I didn't understand that": 40 of 51 yes/no questions were not understood.
- Replies: an honest "what can you do" list now makes 0 unsupported claims.

HOW WORK IS DONE (the rules)
- Every change is ONE sealed, pre-registered experiment: one change against a named base, predictions and pass marks fixed before the run, files sealed with SHA-256 hashes before the registered run.
- Pass/fail is decided on a blind TEST-ONLY panel written by a separate AI agent from a spec. Panels are never trained or tuned on, never quoted, and become "burned" once a builder sees items.
- A registered FAIL stays FAIL. A failed experiment gets exactly one diagnosis-driven follow-up.
- Director verifies every report: seal check, own recount from raw files, a held-out probe for every PASS.
- Fictional names only in all test and training data. No personal data. Unverified web text never goes into weights.
- The only human is the owner, a high-school senior who does not run commands; AI agents build, write panels and grade.

HARDWARE AND BUDGET
One RTX 5070 Ti (16 GB), sometimes offline; a busy shared Mac for CPU work; cloud GPU rentals within a $30 TOTAL budget. Downloading any new model needs the owner's explicit yes. A big model's GENERATED TEXT may be used as training data (stated honestly); borrowing its WEIGHTS for the final system is not allowed (borrowed parts are placeholders).

SCOPE
Only the chat assistant (ear, gate, notebook, reasoner, mouth). The owner has other projects ("small card experiments", "a village model"); do not mix them in.
=== END OF PROJECT CONTEXT ===

QUESTION 4 OF A BATCH (answer only this one): Training a small own ear on synthetic data that works on real chat

THE PROBLEM
The final ear must be the owner's own ~33M-parameter model trained from scratch. The borrowed 360M ear already struggles on fresh wording. A small model trained on generated sentences may learn the generator's templates rather than English.

DETAIL
- Planned own ear: 8-layer width-512 bidirectional encoder (about 29M) + 3.5M heads; byte-level BPE, 8,192 tokens, case kept; input = previous assistant reply + separator + this turn (<= 128 tokens). Pretraining: span-masking fill-in-the-blank on SimpleStories, TinyStories-V2 and TinyDialogues. Heads: 9-way act, fact count 0-6, 6 set-prediction fact slots (exists, owner pointer or ME/WE, relation class + cue pointer, value pointer, confidence, per-fact mode), question head.
- Frame generator already built: 200,000 training rows, 571,795 labelled spans, all spans whole-word and exact. Weaknesses found: its two difficulty levels share surface patterns; SUPPOSE and PLAN are only 1.4% of rows each.
- The owner's own 28.85M decoder (talker101), trained from scratch on 617M tokens of SimpleStories in about 3.5 hours on the RTX 5070 Ti (~49,000 tokens/s), scored 67.4% on a 10-task BLiMP grammar test (bar 70%).
- Borrowed ear v4.1 (360M, fine-tuned) on 125 fresh facts: 95 found, 30 wrong frames before the gate.
- Allowed: a big model's generated text as training data (e.g. Qwen3.8-27B writing varied chat and labelling it), stated honestly. Published: a small model trained on a big model's labels beat that big model by 7-9 F1 at named-entity recognition (UniversalNER, arXiv 2308.03279).

THE HARD QUESTION
How do I make a generator-plus-distillation data pipeline that produces an ear which generalises to wording nobody templated? Cover: how to stop template shortcuts (diversity measures, held-out generator families, adversarial writers), how much real-looking chat vs templated data, whether pretraining on stories even helps chat reading, curriculum, how to get honest pre-training estimates of fresh-wording accuracy (which held-out split predicts a blind panel?), and the smallest model size you think can reach "at most 1 wrong frame per 150 turns before any gate". Give a compute estimate for one 16 GB GPU.

WHAT I NEED BACK
1. Your diagnosis: what is really going on, and which of my explanations above is wrong or incomplete.
2. At most 4 ranked options, each with what it fixes, what it costs, and what it cannot fix.
3. The ONE experiment to run next: a single change against the current system, pass marks with exact numbers fixed in advance, the sample size and why, and the result that would prove your idea wrong. If it needs a later second step, name it but keep it separate.
4. The strongest objection to your own recommendation, and the rival you rejected.
5. Label every claim as SHOWN (published or measured), SUGGESTED (published, but in a different setting) or UNTESTED (your reasoning). Cite papers with arXiv IDs where you can, and say when you know only the abstract. Do not invent numbers or citations; say "I don't know" instead.
6. Keep this only about the chat assistant; no "small card experiments" or "village model".
7. End with a plain-language summary of 6-10 sentences that a high-school senior can follow.
```

## 5. One principled question reader instead of a stack of patches

```text
=== PROJECT CONTEXT (the same block starts every question in this batch) ===
You are advising on a research project through a plain chat. You cannot see the code, the files, or earlier chats, so everything you need is below. Where I give a number, it was measured; where I say "suggested" or "I think", it was not.

WHAT PREMONITION IS
Premonition is a personal assistant being built by a high-school senior (the owner), with AI coding agents doing the building and Claude directing and verifying. It starts knowing nothing. The user teaches it facts in plain English chat. It stores them in an explicit notebook, reasons over them (two-hop and beyond), says "I don't know" instead of guessing, and replies in fluent English. The end goal is a system on the owner's OWN architecture and OWN weights that beats an equal-size plain transformer (same data, same parameter count) on two-hop questions, reversal questions (asking the inverse of a taught fact), abstention on untaught facts, and multi-hop answers after a fact is edited (MQuAKE-style), plus a live demo for the owner's family.

HARD TARGETS
- 0 wrong notebook writes, certified below 1%. A wrong save is worse than a refusal or a clarifying question.
- Recall: at least 85% of plainly stated facts saved exactly; at most 12% of true facts held back.
- 99%+ grammatical replies, no simple mistakes, and no reply may claim something untrue about the notebook or about the assistant itself.
- Median turn time at most 800 ms.

THE PIPELINE TODAY (numbers are from sealed experiments)
1. EAR (English -> frames), BORROWED: SmolLM2-360M fine-tuned ("ear v4.1") to write one line per frame:
     TEACH | owner | relation | value      (e.g. TEACH | me | sister | Mira)
     ASK   | owner | relation              (e.g. ASK | Mira | dog)
     NONE
   A plain-code "speaker canonicaliser" maps I/me/my to the user ("me").
2. RULE BRAKE (plain code): drops frames with junk, e.g. a stored name containing a comma, or a value not found in the turn.
3. GATE, BORROWED: Qwen3.8-27B (4-bit, local on one RTX 5070 Ti 16 GB) is asked YES/NO "does this message explicitly assert this claim?" per frame; saved if P(YES) >= 0.25. The prompt wording and the 0.25 threshold were both chosen on a development set.
4. NOTEBOOK: rows owner | relation | value, e.g.  me | sister | Mira ;  Mira | dog | Pip. "X is the R of Y" is stored as "Y's R is X". Taught facts are never overwritten by inferences. Inverses ("Whose dog is Pip?") are computed at answer time. Relations come from a fixed relation table of 153 entries (each with aliases, an inverse, single- or multi-valued, and the kind of value) plus "other".
5. REASONER (ours): a question parser built as a stack of hand-written stages, each added by one past experiment (a reverse-question stage, a table stage, a yes/no reader, an n-hop chain stage, a decline-wording rewrite, ...), plus a 79,316-parameter learned lookup reasoner for multi-hop. On clean structured input it answers two-hop, reversal, abstention and single-edit multi-hop questions exactly (200/200 on an internal benchmark). The weak point is reading English, in and out.
6. MOUTH (ours, hand-made): a grammar layer that turns reply records into sentences. Grammar 1195/1205 = 99.2% under two independently checked graders; a blind judge preferred it 97 wins / 9 losses / 14 ties over the previous version. It still sometimes prints raw relation-table labels (e.g. "religion or worldview").
7. OWN-MODEL PLAN (not built yet): a ~33M-parameter own ear (8-layer width-512 bidirectional encoder, pretrained by fill-in-the-blank on simple-English stories and dialogues; heads that POINT at whole-word spans of the turn for owner and value; relation chosen from the table; a 9-way speech-act head; a fact-count head; 6 set-prediction fact slots) and an own mouth (a 28.85M decoder trained from scratch, "talker101"). Only a small plain-code "write compiler" may write to the notebook, from spans of the unchanged turn, all facts of a turn together or none. A round trip (fact -> sentence -> fact) is used for TRAINING only and is never permission to write, because it can agree with itself on a wrong fact.

MEASURED STATE OF EACH PART (fresh blind panels unless noted)
- Ear + gate (150 fresh turns): 9 scored wrong saves; 6 of those were answer-key mistakes (key said "pet", ear said "dog"), 3 were real: 2 chat typos stored inside a value (gate P(YES) 0.85 and 0.68) and 1 fact saved from a check-question with no "?" (0.37). Recall 77.9%. Threshold sweep: 19 wrong at threshold 0, 9 at 0.25, 7 at 0.7. Sentences naming several relatives: 4 of 16 facts found.
- On the development set used to choose the gate prompt and threshold, the gate let 13 of 103 wrong frames through. On 120 fresh turns from a new writer it let 63 of 65 through. So the gate barely works on fresh wording.
- A 3-question QA gate (ask "whose R is V?", "what is O's R?", "how is O related to V?" in separate prompts): 5 wrong out of 86 saved vs YES/NO 6 out of 100, but it held back 30% of true facts (bar 12%) and took 880 ms median (bar 800). Registered FAIL.
- Own-model write rules, oracle audit (a perfect reader, the planned strict write compiler): only 184 of 272 real facts (67.6%) are writable (bar 85%); 0 of 76 should-not-save facts writable.
- Casual typing (all lowercase, no apostrophes, typos) is read badly: a normaliser experiment failed and itself added 3 wrong saves.
- "our/we" is NOT the speaker (owner's ruling): the assistant must ask whose. An "ask whose" rule failed because the ear rarely hands it a group owner (14 of 30 asked, bar 27).
- Questions outside the parser's known shapes get "I didn't understand that": 40 of 51 yes/no questions were not understood.
- Replies: an honest "what can you do" list now makes 0 unsupported claims.

HOW WORK IS DONE (the rules)
- Every change is ONE sealed, pre-registered experiment: one change against a named base, predictions and pass marks fixed before the run, files sealed with SHA-256 hashes before the registered run.
- Pass/fail is decided on a blind TEST-ONLY panel written by a separate AI agent from a spec. Panels are never trained or tuned on, never quoted, and become "burned" once a builder sees items.
- A registered FAIL stays FAIL. A failed experiment gets exactly one diagnosis-driven follow-up.
- Director verifies every report: seal check, own recount from raw files, a held-out probe for every PASS.
- Fictional names only in all test and training data. No personal data. Unverified web text never goes into weights.
- The only human is the owner, a high-school senior who does not run commands; AI agents build, write panels and grade.

HARDWARE AND BUDGET
One RTX 5070 Ti (16 GB), sometimes offline; a busy shared Mac for CPU work; cloud GPU rentals within a $30 TOTAL budget. Downloading any new model needs the owner's explicit yes. A big model's GENERATED TEXT may be used as training data (stated honestly); borrowing its WEIGHTS for the final system is not allowed (borrowed parts are placeholders).

SCOPE
Only the chat assistant (ear, gate, notebook, reasoner, mouth). The owner has other projects ("small card experiments", "a village model"); do not mix them in.
=== END OF PROJECT CONTEXT ===

QUESTION 5 OF A BATCH (answer only this one): One principled question reader instead of a stack of patches

THE PROBLEM
The question side of the system grew as a stack of hand-written stages, each added by one sealed experiment. Stages run in a fixed order and the first one that fires answers. This keeps producing ordering bugs and gaps, and merging pieces from different lines breaks byte-identity checks.

MEASURED EXAMPLES
- An n-hop chain stage walks forward only from the one named person and runs before the inverse stage. After "A's spouse is V. V's spouse is W.", "Whose spouse is V?" got V's own forward fact: 16 of 16 such panel questions wrong. A guard fixed 11 of 16 (with a "(worked out backwards)" label) and left 1 wrong ("Who works for V?", a shape outside its list).
- Chain questions with multi-word names: 6 of 24 right, then 24 of 24 after a detector fix.
- Yes/no questions: 40 of 51 dev questions got "I didn't understand that"; the base parser only builds who/what/where questions; the one yes/no reader handles only "Is X's R V?" and "Is V X's R?" with one-word names.
- Recognisers built as closed lists of forms fail on new wordings: general "what can you do" questions 9/12, then 24/25 when matched by meaning; casually typed questions 16/25, then 9/25 on a fresh panel.
- A merge of three verified pieces failed its byte-identity check because two lineages worded the same "not understood" reply differently.
- On clean structured input the notebook + reasoner is exact (200/200); the losses are all in reading the question.

THE HARD QUESTION
What single representation should every question be parsed into (e.g. a small query graph or logical form over the relation table: variables, relation paths with direction, inverse, yes/no, count, list, "why"/"how do you know"), so that answering is one generic procedure and precedence bugs cannot happen? How should the parser abstain ("I didn't understand") rather than guess, with 0 wrong answers? How do I migrate from the stage stack to it one sealed single change at a time, keeping every old verified behaviour, and what test would prove the new reader is not just the old stack in disguise?

WHAT I NEED BACK
1. Your diagnosis: what is really going on, and which of my explanations above is wrong or incomplete.
2. At most 4 ranked options, each with what it fixes, what it costs, and what it cannot fix.
3. The ONE experiment to run next: a single change against the current system, pass marks with exact numbers fixed in advance, the sample size and why, and the result that would prove your idea wrong. If it needs a later second step, name it but keep it separate.
4. The strongest objection to your own recommendation, and the rival you rejected.
5. Label every claim as SHOWN (published or measured), SUGGESTED (published, but in a different setting) or UNTESTED (your reasoning). Cite papers with arXiv IDs where you can, and say when you know only the abstract. Do not invent numbers or citations; say "I don't know" instead.
6. Keep this only about the chat assistant; no "small card experiments" or "village model".
7. End with a plain-language summary of 6-10 sentences that a high-school senior can follow.
```

## 6. Trustworthy evaluation when every panel writer and grader is an AI

```text
=== PROJECT CONTEXT (the same block starts every question in this batch) ===
You are advising on a research project through a plain chat. You cannot see the code, the files, or earlier chats, so everything you need is below. Where I give a number, it was measured; where I say "suggested" or "I think", it was not.

WHAT PREMONITION IS
Premonition is a personal assistant being built by a high-school senior (the owner), with AI coding agents doing the building and Claude directing and verifying. It starts knowing nothing. The user teaches it facts in plain English chat. It stores them in an explicit notebook, reasons over them (two-hop and beyond), says "I don't know" instead of guessing, and replies in fluent English. The end goal is a system on the owner's OWN architecture and OWN weights that beats an equal-size plain transformer (same data, same parameter count) on two-hop questions, reversal questions (asking the inverse of a taught fact), abstention on untaught facts, and multi-hop answers after a fact is edited (MQuAKE-style), plus a live demo for the owner's family.

HARD TARGETS
- 0 wrong notebook writes, certified below 1%. A wrong save is worse than a refusal or a clarifying question.
- Recall: at least 85% of plainly stated facts saved exactly; at most 12% of true facts held back.
- 99%+ grammatical replies, no simple mistakes, and no reply may claim something untrue about the notebook or about the assistant itself.
- Median turn time at most 800 ms.

THE PIPELINE TODAY (numbers are from sealed experiments)
1. EAR (English -> frames), BORROWED: SmolLM2-360M fine-tuned ("ear v4.1") to write one line per frame:
     TEACH | owner | relation | value      (e.g. TEACH | me | sister | Mira)
     ASK   | owner | relation              (e.g. ASK | Mira | dog)
     NONE
   A plain-code "speaker canonicaliser" maps I/me/my to the user ("me").
2. RULE BRAKE (plain code): drops frames with junk, e.g. a stored name containing a comma, or a value not found in the turn.
3. GATE, BORROWED: Qwen3.8-27B (4-bit, local on one RTX 5070 Ti 16 GB) is asked YES/NO "does this message explicitly assert this claim?" per frame; saved if P(YES) >= 0.25. The prompt wording and the 0.25 threshold were both chosen on a development set.
4. NOTEBOOK: rows owner | relation | value, e.g.  me | sister | Mira ;  Mira | dog | Pip. "X is the R of Y" is stored as "Y's R is X". Taught facts are never overwritten by inferences. Inverses ("Whose dog is Pip?") are computed at answer time. Relations come from a fixed relation table of 153 entries (each with aliases, an inverse, single- or multi-valued, and the kind of value) plus "other".
5. REASONER (ours): a question parser built as a stack of hand-written stages, each added by one past experiment (a reverse-question stage, a table stage, a yes/no reader, an n-hop chain stage, a decline-wording rewrite, ...), plus a 79,316-parameter learned lookup reasoner for multi-hop. On clean structured input it answers two-hop, reversal, abstention and single-edit multi-hop questions exactly (200/200 on an internal benchmark). The weak point is reading English, in and out.
6. MOUTH (ours, hand-made): a grammar layer that turns reply records into sentences. Grammar 1195/1205 = 99.2% under two independently checked graders; a blind judge preferred it 97 wins / 9 losses / 14 ties over the previous version. It still sometimes prints raw relation-table labels (e.g. "religion or worldview").
7. OWN-MODEL PLAN (not built yet): a ~33M-parameter own ear (8-layer width-512 bidirectional encoder, pretrained by fill-in-the-blank on simple-English stories and dialogues; heads that POINT at whole-word spans of the turn for owner and value; relation chosen from the table; a 9-way speech-act head; a fact-count head; 6 set-prediction fact slots) and an own mouth (a 28.85M decoder trained from scratch, "talker101"). Only a small plain-code "write compiler" may write to the notebook, from spans of the unchanged turn, all facts of a turn together or none. A round trip (fact -> sentence -> fact) is used for TRAINING only and is never permission to write, because it can agree with itself on a wrong fact.

MEASURED STATE OF EACH PART (fresh blind panels unless noted)
- Ear + gate (150 fresh turns): 9 scored wrong saves; 6 of those were answer-key mistakes (key said "pet", ear said "dog"), 3 were real: 2 chat typos stored inside a value (gate P(YES) 0.85 and 0.68) and 1 fact saved from a check-question with no "?" (0.37). Recall 77.9%. Threshold sweep: 19 wrong at threshold 0, 9 at 0.25, 7 at 0.7. Sentences naming several relatives: 4 of 16 facts found.
- On the development set used to choose the gate prompt and threshold, the gate let 13 of 103 wrong frames through. On 120 fresh turns from a new writer it let 63 of 65 through. So the gate barely works on fresh wording.
- A 3-question QA gate (ask "whose R is V?", "what is O's R?", "how is O related to V?" in separate prompts): 5 wrong out of 86 saved vs YES/NO 6 out of 100, but it held back 30% of true facts (bar 12%) and took 880 ms median (bar 800). Registered FAIL.
- Own-model write rules, oracle audit (a perfect reader, the planned strict write compiler): only 184 of 272 real facts (67.6%) are writable (bar 85%); 0 of 76 should-not-save facts writable.
- Casual typing (all lowercase, no apostrophes, typos) is read badly: a normaliser experiment failed and itself added 3 wrong saves.
- "our/we" is NOT the speaker (owner's ruling): the assistant must ask whose. An "ask whose" rule failed because the ear rarely hands it a group owner (14 of 30 asked, bar 27).
- Questions outside the parser's known shapes get "I didn't understand that": 40 of 51 yes/no questions were not understood.
- Replies: an honest "what can you do" list now makes 0 unsupported claims.

HOW WORK IS DONE (the rules)
- Every change is ONE sealed, pre-registered experiment: one change against a named base, predictions and pass marks fixed before the run, files sealed with SHA-256 hashes before the registered run.
- Pass/fail is decided on a blind TEST-ONLY panel written by a separate AI agent from a spec. Panels are never trained or tuned on, never quoted, and become "burned" once a builder sees items.
- A registered FAIL stays FAIL. A failed experiment gets exactly one diagnosis-driven follow-up.
- Director verifies every report: seal check, own recount from raw files, a held-out probe for every PASS.
- Fictional names only in all test and training data. No personal data. Unverified web text never goes into weights.
- The only human is the owner, a high-school senior who does not run commands; AI agents build, write panels and grade.

HARDWARE AND BUDGET
One RTX 5070 Ti (16 GB), sometimes offline; a busy shared Mac for CPU work; cloud GPU rentals within a $30 TOTAL budget. Downloading any new model needs the owner's explicit yes. A big model's GENERATED TEXT may be used as training data (stated honestly); borrowing its WEIGHTS for the final system is not allowed (borrowed parts are placeholders).

SCOPE
Only the chat assistant (ear, gate, notebook, reasoner, mouth). The owner has other projects ("small card experiments", "a village model"); do not mix them in.
=== END OF PROJECT CONTEXT ===

QUESTION 6 OF A BATCH (answer only this one): Trustworthy evaluation when every panel writer and grader is an AI

THE PROBLEM
All test panels are written by AI agents from a spec, all builds by AI agents, most grading by AI; the only human is a high-school senior who does not run commands. I need to know when a number can be trusted, and how to certify "under 1% wrong saves" on everyday chat.

THINGS THAT WENT WRONG (all real)
- Answer keys were wrong: 6 of 9 "wrong saves" on one panel were key mistakes (key said "pet", ear said "dog"); about 40 per arm on another set were appositive facts the key left out.
- Two scorers disagreed on the same run (14/40 vs 23/40); the difference was never fully resolved.
- A builder's own matcher set the denominator, so its bar could not fail; the director's recount turned a claimed PASS into a FAIL by one item.
- Two LLM grammar graders marked all 1205 replies "ok"; they were ruled invalid, and a planted-mistake check (graders must catch at least 36 of 40 planted errors) was added after the fact.
- Panels get burned: a builder pushed raw panel rows; the director once quoted 3 panel items; a panel writer read an older panel's items.
- The director named the wrong base in a brief, so the panel could not show the bug the experiment targeted.
- Panels are written by one writer with fixed family quotas, so they are not a random sample of real chat.
- An earlier outside answer proposed: certify on 600 independently sampled turns, pass if at most 1 has a wrong save (upper bound about 0.93% at level 0.025); certify recall with at least 150 facts and a lower confidence bound >= 85%. The open part is WHERE independent everyday turns come from.

THE HARD QUESTION
Design an evaluation system that stays honest with AI writers and AI graders: where representative test turns come from (several different writer models? a small amount of the owner's own chat, with fictional names swapped in? a generative model of chat topics?), how to audit answer keys, how to validate graders (planted errors, agreement statistics), how to track panel burn, who sets denominators, and which of these checks give the most trust per unit of effort. Say how to measure how UNREPRESENTATIVE a synthetic panel is. Keep the certification maths short; the question is the data and the process.

WHAT I NEED BACK
1. Your diagnosis: what is really going on, and which of my explanations above is wrong or incomplete.
2. At most 4 ranked options, each with what it fixes, what it costs, and what it cannot fix.
3. The ONE experiment to run next: a single change against the current system, pass marks with exact numbers fixed in advance, the sample size and why, and the result that would prove your idea wrong. If it needs a later second step, name it but keep it separate.
4. The strongest objection to your own recommendation, and the rival you rejected.
5. Label every claim as SHOWN (published or measured), SUGGESTED (published, but in a different setting) or UNTESTED (your reasoning). Cite papers with arXiv IDs where you can, and say when you know only the abstract. Do not invent numbers or citations; say "I don't know" instead.
6. Keep this only about the chat assistant; no "small card experiments" or "village model".
7. End with a plain-language summary of 6-10 sentences that a high-school senior can follow.
```

## 7. Reading several facts, appositives and pronouns in one sentence

```text
=== PROJECT CONTEXT (the same block starts every question in this batch) ===
You are advising on a research project through a plain chat. You cannot see the code, the files, or earlier chats, so everything you need is below. Where I give a number, it was measured; where I say "suggested" or "I think", it was not.

WHAT PREMONITION IS
Premonition is a personal assistant being built by a high-school senior (the owner), with AI coding agents doing the building and Claude directing and verifying. It starts knowing nothing. The user teaches it facts in plain English chat. It stores them in an explicit notebook, reasons over them (two-hop and beyond), says "I don't know" instead of guessing, and replies in fluent English. The end goal is a system on the owner's OWN architecture and OWN weights that beats an equal-size plain transformer (same data, same parameter count) on two-hop questions, reversal questions (asking the inverse of a taught fact), abstention on untaught facts, and multi-hop answers after a fact is edited (MQuAKE-style), plus a live demo for the owner's family.

HARD TARGETS
- 0 wrong notebook writes, certified below 1%. A wrong save is worse than a refusal or a clarifying question.
- Recall: at least 85% of plainly stated facts saved exactly; at most 12% of true facts held back.
- 99%+ grammatical replies, no simple mistakes, and no reply may claim something untrue about the notebook or about the assistant itself.
- Median turn time at most 800 ms.

THE PIPELINE TODAY (numbers are from sealed experiments)
1. EAR (English -> frames), BORROWED: SmolLM2-360M fine-tuned ("ear v4.1") to write one line per frame:
     TEACH | owner | relation | value      (e.g. TEACH | me | sister | Mira)
     ASK   | owner | relation              (e.g. ASK | Mira | dog)
     NONE
   A plain-code "speaker canonicaliser" maps I/me/my to the user ("me").
2. RULE BRAKE (plain code): drops frames with junk, e.g. a stored name containing a comma, or a value not found in the turn.
3. GATE, BORROWED: Qwen3.8-27B (4-bit, local on one RTX 5070 Ti 16 GB) is asked YES/NO "does this message explicitly assert this claim?" per frame; saved if P(YES) >= 0.25. The prompt wording and the 0.25 threshold were both chosen on a development set.
4. NOTEBOOK: rows owner | relation | value, e.g.  me | sister | Mira ;  Mira | dog | Pip. "X is the R of Y" is stored as "Y's R is X". Taught facts are never overwritten by inferences. Inverses ("Whose dog is Pip?") are computed at answer time. Relations come from a fixed relation table of 153 entries (each with aliases, an inverse, single- or multi-valued, and the kind of value) plus "other".
5. REASONER (ours): a question parser built as a stack of hand-written stages, each added by one past experiment (a reverse-question stage, a table stage, a yes/no reader, an n-hop chain stage, a decline-wording rewrite, ...), plus a 79,316-parameter learned lookup reasoner for multi-hop. On clean structured input it answers two-hop, reversal, abstention and single-edit multi-hop questions exactly (200/200 on an internal benchmark). The weak point is reading English, in and out.
6. MOUTH (ours, hand-made): a grammar layer that turns reply records into sentences. Grammar 1195/1205 = 99.2% under two independently checked graders; a blind judge preferred it 97 wins / 9 losses / 14 ties over the previous version. It still sometimes prints raw relation-table labels (e.g. "religion or worldview").
7. OWN-MODEL PLAN (not built yet): a ~33M-parameter own ear (8-layer width-512 bidirectional encoder, pretrained by fill-in-the-blank on simple-English stories and dialogues; heads that POINT at whole-word spans of the turn for owner and value; relation chosen from the table; a 9-way speech-act head; a fact-count head; 6 set-prediction fact slots) and an own mouth (a 28.85M decoder trained from scratch, "talker101"). Only a small plain-code "write compiler" may write to the notebook, from spans of the unchanged turn, all facts of a turn together or none. A round trip (fact -> sentence -> fact) is used for TRAINING only and is never permission to write, because it can agree with itself on a wrong fact.

MEASURED STATE OF EACH PART (fresh blind panels unless noted)
- Ear + gate (150 fresh turns): 9 scored wrong saves; 6 of those were answer-key mistakes (key said "pet", ear said "dog"), 3 were real: 2 chat typos stored inside a value (gate P(YES) 0.85 and 0.68) and 1 fact saved from a check-question with no "?" (0.37). Recall 77.9%. Threshold sweep: 19 wrong at threshold 0, 9 at 0.25, 7 at 0.7. Sentences naming several relatives: 4 of 16 facts found.
- On the development set used to choose the gate prompt and threshold, the gate let 13 of 103 wrong frames through. On 120 fresh turns from a new writer it let 63 of 65 through. So the gate barely works on fresh wording.
- A 3-question QA gate (ask "whose R is V?", "what is O's R?", "how is O related to V?" in separate prompts): 5 wrong out of 86 saved vs YES/NO 6 out of 100, but it held back 30% of true facts (bar 12%) and took 880 ms median (bar 800). Registered FAIL.
- Own-model write rules, oracle audit (a perfect reader, the planned strict write compiler): only 184 of 272 real facts (67.6%) are writable (bar 85%); 0 of 76 should-not-save facts writable.
- Casual typing (all lowercase, no apostrophes, typos) is read badly: a normaliser experiment failed and itself added 3 wrong saves.
- "our/we" is NOT the speaker (owner's ruling): the assistant must ask whose. An "ask whose" rule failed because the ear rarely hands it a group owner (14 of 30 asked, bar 27).
- Questions outside the parser's known shapes get "I didn't understand that": 40 of 51 yes/no questions were not understood.
- Replies: an honest "what can you do" list now makes 0 unsupported claims.

HOW WORK IS DONE (the rules)
- Every change is ONE sealed, pre-registered experiment: one change against a named base, predictions and pass marks fixed before the run, files sealed with SHA-256 hashes before the registered run.
- Pass/fail is decided on a blind TEST-ONLY panel written by a separate AI agent from a spec. Panels are never trained or tuned on, never quoted, and become "burned" once a builder sees items.
- A registered FAIL stays FAIL. A failed experiment gets exactly one diagnosis-driven follow-up.
- Director verifies every report: seal check, own recount from raw files, a held-out probe for every PASS.
- Fictional names only in all test and training data. No personal data. Unverified web text never goes into weights.
- The only human is the owner, a high-school senior who does not run commands; AI agents build, write panels and grade.

HARDWARE AND BUDGET
One RTX 5070 Ti (16 GB), sometimes offline; a busy shared Mac for CPU work; cloud GPU rentals within a $30 TOTAL budget. Downloading any new model needs the owner's explicit yes. A big model's GENERATED TEXT may be used as training data (stated honestly); borrowing its WEIGHTS for the final system is not allowed (borrowed parts are placeholders).

SCOPE
Only the chat assistant (ear, gate, notebook, reasoner, mouth). The owner has other projects ("small card experiments", "a village model"); do not mix them in.
=== END OF PROJECT CONTEXT ===

QUESTION 7 OF A BATCH (answer only this one): Reading several facts, appositives and pronouns in one sentence

THE PROBLEM
Recall is stuck below the 85% bar mostly because sentences with several facts, lists, appositives and pronouns are read badly, and the all-or-nothing write rule turns one unreadable fact into zero saved facts.

MEASURED
- Sentences naming several relatives: 4 of 16 facts found. Recall on the fresh panel 77.9% (about 82.8% if the 6 answer-key mistakes are counted as hits).
- Pick-1-of-4 rival readings: on 13 of 14 plural frames it picked the reading with the OTHER name.
- A live chat probe: two facts in one sentence saved nothing.
- Not saved: appositives ("Nell, my neighbour, works at Tolby Mill"), "moved to", a company name containing a comma (refused as two facts).
- A pronoun bound to the wrong person was a real wrong save: "Ada's son is Bo and he lives in Rook" saved "Ada lives in Rook".
- The ear writes frames one after another as text; the own-model plan uses 6 set-prediction slots with a fact-count head.

THE HARD QUESTION
How should coordination ("Mira and Tal are my sisters", "my sisters are Mira, Tal and June"), distributive vs collective readings ("Mira and Tal own a bakery"), appositives, relative clauses and pronoun binding be handled so that recall rises without new wrong saves? Should the ear emit a small structure (e.g. a coordination group node) that plain code distributes, rather than flat facts? Should a turn with one unreadable fact save the readable ones (partial write) or none, and how does that interact with correction turns? What training data covers these without memorising templates? Give one sealed experiment with pass marks for the family that pays most.

WHAT I NEED BACK
1. Your diagnosis: what is really going on, and which of my explanations above is wrong or incomplete.
2. At most 4 ranked options, each with what it fixes, what it costs, and what it cannot fix.
3. The ONE experiment to run next: a single change against the current system, pass marks with exact numbers fixed in advance, the sample size and why, and the result that would prove your idea wrong. If it needs a later second step, name it but keep it separate.
4. The strongest objection to your own recommendation, and the rival you rejected.
5. Label every claim as SHOWN (published or measured), SUGGESTED (published, but in a different setting) or UNTESTED (your reasoning). Cite papers with arXiv IDs where you can, and say when you know only the abstract. Do not invent numbers or citations; say "I don't know" instead.
6. Keep this only about the chat assistant; no "small card experiments" or "village model".
7. End with a plain-language summary of 6-10 sentences that a high-school senior can follow.
```

## 8. An own mouth that is fluent, faithful and 99% grammatical at about 30M parameters

```text
=== PROJECT CONTEXT (the same block starts every question in this batch) ===
You are advising on a research project through a plain chat. You cannot see the code, the files, or earlier chats, so everything you need is below. Where I give a number, it was measured; where I say "suggested" or "I think", it was not.

WHAT PREMONITION IS
Premonition is a personal assistant being built by a high-school senior (the owner), with AI coding agents doing the building and Claude directing and verifying. It starts knowing nothing. The user teaches it facts in plain English chat. It stores them in an explicit notebook, reasons over them (two-hop and beyond), says "I don't know" instead of guessing, and replies in fluent English. The end goal is a system on the owner's OWN architecture and OWN weights that beats an equal-size plain transformer (same data, same parameter count) on two-hop questions, reversal questions (asking the inverse of a taught fact), abstention on untaught facts, and multi-hop answers after a fact is edited (MQuAKE-style), plus a live demo for the owner's family.

HARD TARGETS
- 0 wrong notebook writes, certified below 1%. A wrong save is worse than a refusal or a clarifying question.
- Recall: at least 85% of plainly stated facts saved exactly; at most 12% of true facts held back.
- 99%+ grammatical replies, no simple mistakes, and no reply may claim something untrue about the notebook or about the assistant itself.
- Median turn time at most 800 ms.

THE PIPELINE TODAY (numbers are from sealed experiments)
1. EAR (English -> frames), BORROWED: SmolLM2-360M fine-tuned ("ear v4.1") to write one line per frame:
     TEACH | owner | relation | value      (e.g. TEACH | me | sister | Mira)
     ASK   | owner | relation              (e.g. ASK | Mira | dog)
     NONE
   A plain-code "speaker canonicaliser" maps I/me/my to the user ("me").
2. RULE BRAKE (plain code): drops frames with junk, e.g. a stored name containing a comma, or a value not found in the turn.
3. GATE, BORROWED: Qwen3.8-27B (4-bit, local on one RTX 5070 Ti 16 GB) is asked YES/NO "does this message explicitly assert this claim?" per frame; saved if P(YES) >= 0.25. The prompt wording and the 0.25 threshold were both chosen on a development set.
4. NOTEBOOK: rows owner | relation | value, e.g.  me | sister | Mira ;  Mira | dog | Pip. "X is the R of Y" is stored as "Y's R is X". Taught facts are never overwritten by inferences. Inverses ("Whose dog is Pip?") are computed at answer time. Relations come from a fixed relation table of 153 entries (each with aliases, an inverse, single- or multi-valued, and the kind of value) plus "other".
5. REASONER (ours): a question parser built as a stack of hand-written stages, each added by one past experiment (a reverse-question stage, a table stage, a yes/no reader, an n-hop chain stage, a decline-wording rewrite, ...), plus a 79,316-parameter learned lookup reasoner for multi-hop. On clean structured input it answers two-hop, reversal, abstention and single-edit multi-hop questions exactly (200/200 on an internal benchmark). The weak point is reading English, in and out.
6. MOUTH (ours, hand-made): a grammar layer that turns reply records into sentences. Grammar 1195/1205 = 99.2% under two independently checked graders; a blind judge preferred it 97 wins / 9 losses / 14 ties over the previous version. It still sometimes prints raw relation-table labels (e.g. "religion or worldview").
7. OWN-MODEL PLAN (not built yet): a ~33M-parameter own ear (8-layer width-512 bidirectional encoder, pretrained by fill-in-the-blank on simple-English stories and dialogues; heads that POINT at whole-word spans of the turn for owner and value; relation chosen from the table; a 9-way speech-act head; a fact-count head; 6 set-prediction fact slots) and an own mouth (a 28.85M decoder trained from scratch, "talker101"). Only a small plain-code "write compiler" may write to the notebook, from spans of the unchanged turn, all facts of a turn together or none. A round trip (fact -> sentence -> fact) is used for TRAINING only and is never permission to write, because it can agree with itself on a wrong fact.

MEASURED STATE OF EACH PART (fresh blind panels unless noted)
- Ear + gate (150 fresh turns): 9 scored wrong saves; 6 of those were answer-key mistakes (key said "pet", ear said "dog"), 3 were real: 2 chat typos stored inside a value (gate P(YES) 0.85 and 0.68) and 1 fact saved from a check-question with no "?" (0.37). Recall 77.9%. Threshold sweep: 19 wrong at threshold 0, 9 at 0.25, 7 at 0.7. Sentences naming several relatives: 4 of 16 facts found.
- On the development set used to choose the gate prompt and threshold, the gate let 13 of 103 wrong frames through. On 120 fresh turns from a new writer it let 63 of 65 through. So the gate barely works on fresh wording.
- A 3-question QA gate (ask "whose R is V?", "what is O's R?", "how is O related to V?" in separate prompts): 5 wrong out of 86 saved vs YES/NO 6 out of 100, but it held back 30% of true facts (bar 12%) and took 880 ms median (bar 800). Registered FAIL.
- Own-model write rules, oracle audit (a perfect reader, the planned strict write compiler): only 184 of 272 real facts (67.6%) are writable (bar 85%); 0 of 76 should-not-save facts writable.
- Casual typing (all lowercase, no apostrophes, typos) is read badly: a normaliser experiment failed and itself added 3 wrong saves.
- "our/we" is NOT the speaker (owner's ruling): the assistant must ask whose. An "ask whose" rule failed because the ear rarely hands it a group owner (14 of 30 asked, bar 27).
- Questions outside the parser's known shapes get "I didn't understand that": 40 of 51 yes/no questions were not understood.
- Replies: an honest "what can you do" list now makes 0 unsupported claims.

HOW WORK IS DONE (the rules)
- Every change is ONE sealed, pre-registered experiment: one change against a named base, predictions and pass marks fixed before the run, files sealed with SHA-256 hashes before the registered run.
- Pass/fail is decided on a blind TEST-ONLY panel written by a separate AI agent from a spec. Panels are never trained or tuned on, never quoted, and become "burned" once a builder sees items.
- A registered FAIL stays FAIL. A failed experiment gets exactly one diagnosis-driven follow-up.
- Director verifies every report: seal check, own recount from raw files, a held-out probe for every PASS.
- Fictional names only in all test and training data. No personal data. Unverified web text never goes into weights.
- The only human is the owner, a high-school senior who does not run commands; AI agents build, write panels and grade.

HARDWARE AND BUDGET
One RTX 5070 Ti (16 GB), sometimes offline; a busy shared Mac for CPU work; cloud GPU rentals within a $30 TOTAL budget. Downloading any new model needs the owner's explicit yes. A big model's GENERATED TEXT may be used as training data (stated honestly); borrowing its WEIGHTS for the final system is not allowed (borrowed parts are placeholders).

SCOPE
Only the chat assistant (ear, gate, notebook, reasoner, mouth). The owner has other projects ("small card experiments", "a village model"); do not mix them in.
=== END OF PROJECT CONTEXT ===

QUESTION 8 OF A BATCH (answer only this one): An own mouth that is fluent, faithful and 99% grammatical at about 30M parameters

THE PROBLEM
The final mouth must be the owner's own weights. Today's best mouth is hand-made grammar code (99.2% grammatical, preferred by a blind judge) but it is rigid, prints raw relation labels sometimes, and cannot do small talk well. The own learned decoder is not yet good enough.

MEASURED
- talker101 (own 28.85M decoder, from scratch, 617M tokens of SimpleStories, ~3.5 h on the 5070 Ti): validation loss passed; BLiMP-10 grammar 67.4% (bar 70%): registered FAIL.
- talker120b (talker101 fine-tuned to speak from reply records): 172 of 500 replies unfaithful to the record before a "brake"; 0/500 after the brake. Names got cut up ("Fara" for "Farah") because the copy mechanism copied word pieces, not whole names.
- Hand grammar layer: 1195/1205 = 99.2% grammatical under two graders that each caught at least 38 of 40 planted mistakes; blind judge 97 wins / 9 losses / 14 ties vs the previous version; the only flagged defect is raw relation labels such as "language of work or name".
- The reply record is structured: act (answer / abstain / confirm-save / decline / clarify / small talk), the facts used, whether the answer was worked out backwards, and fixed honest texts where needed.
- Small talk: greetings and closings fit on 31 of 35 items with fixed replies.

THE HARD QUESTION
What architecture and training plan gets a ~30M own model to at least 99% grammatical, 100% faithful (every name and fact in a reply is in the record), and natural small talk? Options include: a learned choice among grammar-layer templates, whole-name slot tokens with constrained decoding, a learned surface realiser trained on the hand layer's own outputs plus paraphrases (distillation), plan-then-realise, or keeping the hand layer and learning only the small-talk part. Is 99% even plausible at 30M, and what would show it is not? How should grammar be graded reliably by AI graders?

WHAT I NEED BACK
1. Your diagnosis: what is really going on, and which of my explanations above is wrong or incomplete.
2. At most 4 ranked options, each with what it fixes, what it costs, and what it cannot fix.
3. The ONE experiment to run next: a single change against the current system, pass marks with exact numbers fixed in advance, the sample size and why, and the result that would prove your idea wrong. If it needs a later second step, name it but keep it separate.
4. The strongest objection to your own recommendation, and the rival you rejected.
5. Label every claim as SHOWN (published or measured), SUGGESTED (published, but in a different setting) or UNTESTED (your reasoning). Cite papers with arXiv IDs where you can, and say when you know only the abstract. Do not invent numbers or citations; say "I don't know" instead.
6. Keep this only about the chat assistant; no "small card experiments" or "village model".
7. End with a plain-language summary of 6-10 sentences that a high-school senior can follow.
```

## 9. Corrections, retractions and facts that change over time

```text
=== PROJECT CONTEXT (the same block starts every question in this batch) ===
You are advising on a research project through a plain chat. You cannot see the code, the files, or earlier chats, so everything you need is below. Where I give a number, it was measured; where I say "suggested" or "I think", it was not.

WHAT PREMONITION IS
Premonition is a personal assistant being built by a high-school senior (the owner), with AI coding agents doing the building and Claude directing and verifying. It starts knowing nothing. The user teaches it facts in plain English chat. It stores them in an explicit notebook, reasons over them (two-hop and beyond), says "I don't know" instead of guessing, and replies in fluent English. The end goal is a system on the owner's OWN architecture and OWN weights that beats an equal-size plain transformer (same data, same parameter count) on two-hop questions, reversal questions (asking the inverse of a taught fact), abstention on untaught facts, and multi-hop answers after a fact is edited (MQuAKE-style), plus a live demo for the owner's family.

HARD TARGETS
- 0 wrong notebook writes, certified below 1%. A wrong save is worse than a refusal or a clarifying question.
- Recall: at least 85% of plainly stated facts saved exactly; at most 12% of true facts held back.
- 99%+ grammatical replies, no simple mistakes, and no reply may claim something untrue about the notebook or about the assistant itself.
- Median turn time at most 800 ms.

THE PIPELINE TODAY (numbers are from sealed experiments)
1. EAR (English -> frames), BORROWED: SmolLM2-360M fine-tuned ("ear v4.1") to write one line per frame:
     TEACH | owner | relation | value      (e.g. TEACH | me | sister | Mira)
     ASK   | owner | relation              (e.g. ASK | Mira | dog)
     NONE
   A plain-code "speaker canonicaliser" maps I/me/my to the user ("me").
2. RULE BRAKE (plain code): drops frames with junk, e.g. a stored name containing a comma, or a value not found in the turn.
3. GATE, BORROWED: Qwen3.8-27B (4-bit, local on one RTX 5070 Ti 16 GB) is asked YES/NO "does this message explicitly assert this claim?" per frame; saved if P(YES) >= 0.25. The prompt wording and the 0.25 threshold were both chosen on a development set.
4. NOTEBOOK: rows owner | relation | value, e.g.  me | sister | Mira ;  Mira | dog | Pip. "X is the R of Y" is stored as "Y's R is X". Taught facts are never overwritten by inferences. Inverses ("Whose dog is Pip?") are computed at answer time. Relations come from a fixed relation table of 153 entries (each with aliases, an inverse, single- or multi-valued, and the kind of value) plus "other".
5. REASONER (ours): a question parser built as a stack of hand-written stages, each added by one past experiment (a reverse-question stage, a table stage, a yes/no reader, an n-hop chain stage, a decline-wording rewrite, ...), plus a 79,316-parameter learned lookup reasoner for multi-hop. On clean structured input it answers two-hop, reversal, abstention and single-edit multi-hop questions exactly (200/200 on an internal benchmark). The weak point is reading English, in and out.
6. MOUTH (ours, hand-made): a grammar layer that turns reply records into sentences. Grammar 1195/1205 = 99.2% under two independently checked graders; a blind judge preferred it 97 wins / 9 losses / 14 ties over the previous version. It still sometimes prints raw relation-table labels (e.g. "religion or worldview").
7. OWN-MODEL PLAN (not built yet): a ~33M-parameter own ear (8-layer width-512 bidirectional encoder, pretrained by fill-in-the-blank on simple-English stories and dialogues; heads that POINT at whole-word spans of the turn for owner and value; relation chosen from the table; a 9-way speech-act head; a fact-count head; 6 set-prediction fact slots) and an own mouth (a 28.85M decoder trained from scratch, "talker101"). Only a small plain-code "write compiler" may write to the notebook, from spans of the unchanged turn, all facts of a turn together or none. A round trip (fact -> sentence -> fact) is used for TRAINING only and is never permission to write, because it can agree with itself on a wrong fact.

MEASURED STATE OF EACH PART (fresh blind panels unless noted)
- Ear + gate (150 fresh turns): 9 scored wrong saves; 6 of those were answer-key mistakes (key said "pet", ear said "dog"), 3 were real: 2 chat typos stored inside a value (gate P(YES) 0.85 and 0.68) and 1 fact saved from a check-question with no "?" (0.37). Recall 77.9%. Threshold sweep: 19 wrong at threshold 0, 9 at 0.25, 7 at 0.7. Sentences naming several relatives: 4 of 16 facts found.
- On the development set used to choose the gate prompt and threshold, the gate let 13 of 103 wrong frames through. On 120 fresh turns from a new writer it let 63 of 65 through. So the gate barely works on fresh wording.
- A 3-question QA gate (ask "whose R is V?", "what is O's R?", "how is O related to V?" in separate prompts): 5 wrong out of 86 saved vs YES/NO 6 out of 100, but it held back 30% of true facts (bar 12%) and took 880 ms median (bar 800). Registered FAIL.
- Own-model write rules, oracle audit (a perfect reader, the planned strict write compiler): only 184 of 272 real facts (67.6%) are writable (bar 85%); 0 of 76 should-not-save facts writable.
- Casual typing (all lowercase, no apostrophes, typos) is read badly: a normaliser experiment failed and itself added 3 wrong saves.
- "our/we" is NOT the speaker (owner's ruling): the assistant must ask whose. An "ask whose" rule failed because the ear rarely hands it a group owner (14 of 30 asked, bar 27).
- Questions outside the parser's known shapes get "I didn't understand that": 40 of 51 yes/no questions were not understood.
- Replies: an honest "what can you do" list now makes 0 unsupported claims.

HOW WORK IS DONE (the rules)
- Every change is ONE sealed, pre-registered experiment: one change against a named base, predictions and pass marks fixed before the run, files sealed with SHA-256 hashes before the registered run.
- Pass/fail is decided on a blind TEST-ONLY panel written by a separate AI agent from a spec. Panels are never trained or tuned on, never quoted, and become "burned" once a builder sees items.
- A registered FAIL stays FAIL. A failed experiment gets exactly one diagnosis-driven follow-up.
- Director verifies every report: seal check, own recount from raw files, a held-out probe for every PASS.
- Fictional names only in all test and training data. No personal data. Unverified web text never goes into weights.
- The only human is the owner, a high-school senior who does not run commands; AI agents build, write panels and grade.

HARDWARE AND BUDGET
One RTX 5070 Ti (16 GB), sometimes offline; a busy shared Mac for CPU work; cloud GPU rentals within a $30 TOTAL budget. Downloading any new model needs the owner's explicit yes. A big model's GENERATED TEXT may be used as training data (stated honestly); borrowing its WEIGHTS for the final system is not allowed (borrowed parts are placeholders).

SCOPE
Only the chat assistant (ear, gate, notebook, reasoner, mouth). The owner has other projects ("small card experiments", "a village model"); do not mix them in.
=== END OF PROJECT CONTEXT ===

QUESTION 9 OF A BATCH (answer only this one): Corrections, retractions and facts that change over time

THE PROBLEM
Users correct themselves, retract facts, and facts change (people move, change jobs). The notebook must update without wrong saves, keep taught facts separate from inferences, and still answer multi-hop questions correctly after an edit (MQuAKE-style).

MEASURED
- "Ana's cat is Fig, not Moss" is refused today (no DENY frames in the ear); a planned change adds DENY frames and correction pairs so it removes Moss and saves Fig.
- A correction piece scored 54/80 on a corrections panel with 0 false claims and 0 junk writes. On a fresh 96-item corrections panel the current base (without the correction pieces merged yet) got 34/96 right, 48 wrong values, 9 junk writes, 4 false claims.
- "Forget where Ana lives" was parsed with "where Ana" as a name.
- "Ada moved to Tolby" is not saved at all.
- The notebook keeps one current value for single-valued relations (e.g. mother, lives in) and a set for multi-valued ones (e.g. sister). The reasoner answers single-edit multi-hop questions exactly on clean input.
- Earlier honesty bug: "I do not know that from what you taught me" was said about facts that HAD been taught and then retracted.

THE HARD QUESTION
Design the correction model: how to store history (valid time? a superseded flag?), how to tell a correction from an extra value for multi-valued relations ("Mira's sister is June" when Tal is already her sister), how to handle "No, Milan." answering the assistant's previous reply, retraction vs denial, "used to", hypotheticals, and what the assistant should say about a fact that was changed ("Ada lived in Rook until you told me she moved"). What should the reasoner do on multi-hop after an edit when an intermediate fact is stale? Give the sealed experiment order and pass marks for the first two pieces.

WHAT I NEED BACK
1. Your diagnosis: what is really going on, and which of my explanations above is wrong or incomplete.
2. At most 4 ranked options, each with what it fixes, what it costs, and what it cannot fix.
3. The ONE experiment to run next: a single change against the current system, pass marks with exact numbers fixed in advance, the sample size and why, and the result that would prove your idea wrong. If it needs a later second step, name it but keep it separate.
4. The strongest objection to your own recommendation, and the rival you rejected.
5. Label every claim as SHOWN (published or measured), SUGGESTED (published, but in a different setting) or UNTESTED (your reasoning). Cite papers with arXiv IDs where you can, and say when you know only the abstract. Do not invent numbers or citations; say "I don't know" instead.
6. Keep this only about the chat assistant; no "small card experiments" or "village model".
7. End with a plain-language summary of 6-10 sentences that a high-school senior can follow.
```

## 10. Casual typing: lowercase, no apostrophes, typos, without silently changing names

```text
=== PROJECT CONTEXT (the same block starts every question in this batch) ===
You are advising on a research project through a plain chat. You cannot see the code, the files, or earlier chats, so everything you need is below. Where I give a number, it was measured; where I say "suggested" or "I think", it was not.

WHAT PREMONITION IS
Premonition is a personal assistant being built by a high-school senior (the owner), with AI coding agents doing the building and Claude directing and verifying. It starts knowing nothing. The user teaches it facts in plain English chat. It stores them in an explicit notebook, reasons over them (two-hop and beyond), says "I don't know" instead of guessing, and replies in fluent English. The end goal is a system on the owner's OWN architecture and OWN weights that beats an equal-size plain transformer (same data, same parameter count) on two-hop questions, reversal questions (asking the inverse of a taught fact), abstention on untaught facts, and multi-hop answers after a fact is edited (MQuAKE-style), plus a live demo for the owner's family.

HARD TARGETS
- 0 wrong notebook writes, certified below 1%. A wrong save is worse than a refusal or a clarifying question.
- Recall: at least 85% of plainly stated facts saved exactly; at most 12% of true facts held back.
- 99%+ grammatical replies, no simple mistakes, and no reply may claim something untrue about the notebook or about the assistant itself.
- Median turn time at most 800 ms.

THE PIPELINE TODAY (numbers are from sealed experiments)
1. EAR (English -> frames), BORROWED: SmolLM2-360M fine-tuned ("ear v4.1") to write one line per frame:
     TEACH | owner | relation | value      (e.g. TEACH | me | sister | Mira)
     ASK   | owner | relation              (e.g. ASK | Mira | dog)
     NONE
   A plain-code "speaker canonicaliser" maps I/me/my to the user ("me").
2. RULE BRAKE (plain code): drops frames with junk, e.g. a stored name containing a comma, or a value not found in the turn.
3. GATE, BORROWED: Qwen3.8-27B (4-bit, local on one RTX 5070 Ti 16 GB) is asked YES/NO "does this message explicitly assert this claim?" per frame; saved if P(YES) >= 0.25. The prompt wording and the 0.25 threshold were both chosen on a development set.
4. NOTEBOOK: rows owner | relation | value, e.g.  me | sister | Mira ;  Mira | dog | Pip. "X is the R of Y" is stored as "Y's R is X". Taught facts are never overwritten by inferences. Inverses ("Whose dog is Pip?") are computed at answer time. Relations come from a fixed relation table of 153 entries (each with aliases, an inverse, single- or multi-valued, and the kind of value) plus "other".
5. REASONER (ours): a question parser built as a stack of hand-written stages, each added by one past experiment (a reverse-question stage, a table stage, a yes/no reader, an n-hop chain stage, a decline-wording rewrite, ...), plus a 79,316-parameter learned lookup reasoner for multi-hop. On clean structured input it answers two-hop, reversal, abstention and single-edit multi-hop questions exactly (200/200 on an internal benchmark). The weak point is reading English, in and out.
6. MOUTH (ours, hand-made): a grammar layer that turns reply records into sentences. Grammar 1195/1205 = 99.2% under two independently checked graders; a blind judge preferred it 97 wins / 9 losses / 14 ties over the previous version. It still sometimes prints raw relation-table labels (e.g. "religion or worldview").
7. OWN-MODEL PLAN (not built yet): a ~33M-parameter own ear (8-layer width-512 bidirectional encoder, pretrained by fill-in-the-blank on simple-English stories and dialogues; heads that POINT at whole-word spans of the turn for owner and value; relation chosen from the table; a 9-way speech-act head; a fact-count head; 6 set-prediction fact slots) and an own mouth (a 28.85M decoder trained from scratch, "talker101"). Only a small plain-code "write compiler" may write to the notebook, from spans of the unchanged turn, all facts of a turn together or none. A round trip (fact -> sentence -> fact) is used for TRAINING only and is never permission to write, because it can agree with itself on a wrong fact.

MEASURED STATE OF EACH PART (fresh blind panels unless noted)
- Ear + gate (150 fresh turns): 9 scored wrong saves; 6 of those were answer-key mistakes (key said "pet", ear said "dog"), 3 were real: 2 chat typos stored inside a value (gate P(YES) 0.85 and 0.68) and 1 fact saved from a check-question with no "?" (0.37). Recall 77.9%. Threshold sweep: 19 wrong at threshold 0, 9 at 0.25, 7 at 0.7. Sentences naming several relatives: 4 of 16 facts found.
- On the development set used to choose the gate prompt and threshold, the gate let 13 of 103 wrong frames through. On 120 fresh turns from a new writer it let 63 of 65 through. So the gate barely works on fresh wording.
- A 3-question QA gate (ask "whose R is V?", "what is O's R?", "how is O related to V?" in separate prompts): 5 wrong out of 86 saved vs YES/NO 6 out of 100, but it held back 30% of true facts (bar 12%) and took 880 ms median (bar 800). Registered FAIL.
- Own-model write rules, oracle audit (a perfect reader, the planned strict write compiler): only 184 of 272 real facts (67.6%) are writable (bar 85%); 0 of 76 should-not-save facts writable.
- Casual typing (all lowercase, no apostrophes, typos) is read badly: a normaliser experiment failed and itself added 3 wrong saves.
- "our/we" is NOT the speaker (owner's ruling): the assistant must ask whose. An "ask whose" rule failed because the ear rarely hands it a group owner (14 of 30 asked, bar 27).
- Questions outside the parser's known shapes get "I didn't understand that": 40 of 51 yes/no questions were not understood.
- Replies: an honest "what can you do" list now makes 0 unsupported claims.

HOW WORK IS DONE (the rules)
- Every change is ONE sealed, pre-registered experiment: one change against a named base, predictions and pass marks fixed before the run, files sealed with SHA-256 hashes before the registered run.
- Pass/fail is decided on a blind TEST-ONLY panel written by a separate AI agent from a spec. Panels are never trained or tuned on, never quoted, and become "burned" once a builder sees items.
- A registered FAIL stays FAIL. A failed experiment gets exactly one diagnosis-driven follow-up.
- Director verifies every report: seal check, own recount from raw files, a held-out probe for every PASS.
- Fictional names only in all test and training data. No personal data. Unverified web text never goes into weights.
- The only human is the owner, a high-school senior who does not run commands; AI agents build, write panels and grade.

HARDWARE AND BUDGET
One RTX 5070 Ti (16 GB), sometimes offline; a busy shared Mac for CPU work; cloud GPU rentals within a $30 TOTAL budget. Downloading any new model needs the owner's explicit yes. A big model's GENERATED TEXT may be used as training data (stated honestly); borrowing its WEIGHTS for the final system is not allowed (borrowed parts are placeholders).

SCOPE
Only the chat assistant (ear, gate, notebook, reasoner, mouth). The owner has other projects ("small card experiments", "a village model"); do not mix them in.
=== END OF PROJECT CONTEXT ===

QUESTION 10 OF A BATCH (answer only this one): Casual typing: lowercase, no apostrophes, typos, without silently changing names

THE PROBLEM
Real people type "whats ana cat called" and "my sisters name is mira stil". The system reads casual typing badly, and a "fix the typing first" normaliser made things worse.

MEASURED
- A live chat probe: lowercase / no-apostrophe typing 0 of 7 right.
- A casual-typing normaliser (run before the reader): casual turns exact 14-23 of 40 (two scorers disagree) vs 0-6 of 40 without it (bar 30); lowercase questions 0 of 15; and it ADDED 3 wrong saves (a rule that kept a trailing "s" stored names like "Benos"). Registered FAIL.
- A reader for casually typed questions: 9 of 25 answered on a fresh panel; 12 of the 16 misses dropped the possessive entirely ("whats ana cat name").
- 2 of the 3 real wrong saves on the main fresh panel were typos stored inside a value, with gate P(YES) 0.85 and 0.68. A mixed-case typo guard exists but lets all-lowercase text through.
- Rules: an unfamiliar spelling is a reason to ask, not evidence the value is false; never silently correct a name; keep the original text.

THE HARD QUESTION
How should a reader handle case-less text where names and ordinary words collide ("rose", "will", "mark", "may", "bill")? When should it ask "Did you mean ...?" and how often is acceptable? Is a normaliser in front of the reader ever the right design, or should the reader be trained on casual text directly? How do I tell a typo in a NEW name (unknowable) from a typo in a KNOWN name (fixable with confirmation)? One sealed experiment with pass marks, including the wrong-save bar.

WHAT I NEED BACK
1. Your diagnosis: what is really going on, and which of my explanations above is wrong or incomplete.
2. At most 4 ranked options, each with what it fixes, what it costs, and what it cannot fix.
3. The ONE experiment to run next: a single change against the current system, pass marks with exact numbers fixed in advance, the sample size and why, and the result that would prove your idea wrong. If it needs a later second step, name it but keep it separate.
4. The strongest objection to your own recommendation, and the rival you rejected.
5. Label every claim as SHOWN (published or measured), SUGGESTED (published, but in a different setting) or UNTESTED (your reasoning). Cite papers with arXiv IDs where you can, and say when you know only the abstract. Do not invent numbers or citations; say "I don't know" instead.
6. Keep this only about the chat assistant; no "small card experiments" or "village model".
7. End with a plain-language summary of 6-10 sentences that a high-school senior can follow.
```

## 11. Proving the design beats an equal-size plain transformer, fairly

```text
=== PROJECT CONTEXT (the same block starts every question in this batch) ===
You are advising on a research project through a plain chat. You cannot see the code, the files, or earlier chats, so everything you need is below. Where I give a number, it was measured; where I say "suggested" or "I think", it was not.

WHAT PREMONITION IS
Premonition is a personal assistant being built by a high-school senior (the owner), with AI coding agents doing the building and Claude directing and verifying. It starts knowing nothing. The user teaches it facts in plain English chat. It stores them in an explicit notebook, reasons over them (two-hop and beyond), says "I don't know" instead of guessing, and replies in fluent English. The end goal is a system on the owner's OWN architecture and OWN weights that beats an equal-size plain transformer (same data, same parameter count) on two-hop questions, reversal questions (asking the inverse of a taught fact), abstention on untaught facts, and multi-hop answers after a fact is edited (MQuAKE-style), plus a live demo for the owner's family.

HARD TARGETS
- 0 wrong notebook writes, certified below 1%. A wrong save is worse than a refusal or a clarifying question.
- Recall: at least 85% of plainly stated facts saved exactly; at most 12% of true facts held back.
- 99%+ grammatical replies, no simple mistakes, and no reply may claim something untrue about the notebook or about the assistant itself.
- Median turn time at most 800 ms.

THE PIPELINE TODAY (numbers are from sealed experiments)
1. EAR (English -> frames), BORROWED: SmolLM2-360M fine-tuned ("ear v4.1") to write one line per frame:
     TEACH | owner | relation | value      (e.g. TEACH | me | sister | Mira)
     ASK   | owner | relation              (e.g. ASK | Mira | dog)
     NONE
   A plain-code "speaker canonicaliser" maps I/me/my to the user ("me").
2. RULE BRAKE (plain code): drops frames with junk, e.g. a stored name containing a comma, or a value not found in the turn.
3. GATE, BORROWED: Qwen3.8-27B (4-bit, local on one RTX 5070 Ti 16 GB) is asked YES/NO "does this message explicitly assert this claim?" per frame; saved if P(YES) >= 0.25. The prompt wording and the 0.25 threshold were both chosen on a development set.
4. NOTEBOOK: rows owner | relation | value, e.g.  me | sister | Mira ;  Mira | dog | Pip. "X is the R of Y" is stored as "Y's R is X". Taught facts are never overwritten by inferences. Inverses ("Whose dog is Pip?") are computed at answer time. Relations come from a fixed relation table of 153 entries (each with aliases, an inverse, single- or multi-valued, and the kind of value) plus "other".
5. REASONER (ours): a question parser built as a stack of hand-written stages, each added by one past experiment (a reverse-question stage, a table stage, a yes/no reader, an n-hop chain stage, a decline-wording rewrite, ...), plus a 79,316-parameter learned lookup reasoner for multi-hop. On clean structured input it answers two-hop, reversal, abstention and single-edit multi-hop questions exactly (200/200 on an internal benchmark). The weak point is reading English, in and out.
6. MOUTH (ours, hand-made): a grammar layer that turns reply records into sentences. Grammar 1195/1205 = 99.2% under two independently checked graders; a blind judge preferred it 97 wins / 9 losses / 14 ties over the previous version. It still sometimes prints raw relation-table labels (e.g. "religion or worldview").
7. OWN-MODEL PLAN (not built yet): a ~33M-parameter own ear (8-layer width-512 bidirectional encoder, pretrained by fill-in-the-blank on simple-English stories and dialogues; heads that POINT at whole-word spans of the turn for owner and value; relation chosen from the table; a 9-way speech-act head; a fact-count head; 6 set-prediction fact slots) and an own mouth (a 28.85M decoder trained from scratch, "talker101"). Only a small plain-code "write compiler" may write to the notebook, from spans of the unchanged turn, all facts of a turn together or none. A round trip (fact -> sentence -> fact) is used for TRAINING only and is never permission to write, because it can agree with itself on a wrong fact.

MEASURED STATE OF EACH PART (fresh blind panels unless noted)
- Ear + gate (150 fresh turns): 9 scored wrong saves; 6 of those were answer-key mistakes (key said "pet", ear said "dog"), 3 were real: 2 chat typos stored inside a value (gate P(YES) 0.85 and 0.68) and 1 fact saved from a check-question with no "?" (0.37). Recall 77.9%. Threshold sweep: 19 wrong at threshold 0, 9 at 0.25, 7 at 0.7. Sentences naming several relatives: 4 of 16 facts found.
- On the development set used to choose the gate prompt and threshold, the gate let 13 of 103 wrong frames through. On 120 fresh turns from a new writer it let 63 of 65 through. So the gate barely works on fresh wording.
- A 3-question QA gate (ask "whose R is V?", "what is O's R?", "how is O related to V?" in separate prompts): 5 wrong out of 86 saved vs YES/NO 6 out of 100, but it held back 30% of true facts (bar 12%) and took 880 ms median (bar 800). Registered FAIL.
- Own-model write rules, oracle audit (a perfect reader, the planned strict write compiler): only 184 of 272 real facts (67.6%) are writable (bar 85%); 0 of 76 should-not-save facts writable.
- Casual typing (all lowercase, no apostrophes, typos) is read badly: a normaliser experiment failed and itself added 3 wrong saves.
- "our/we" is NOT the speaker (owner's ruling): the assistant must ask whose. An "ask whose" rule failed because the ear rarely hands it a group owner (14 of 30 asked, bar 27).
- Questions outside the parser's known shapes get "I didn't understand that": 40 of 51 yes/no questions were not understood.
- Replies: an honest "what can you do" list now makes 0 unsupported claims.

HOW WORK IS DONE (the rules)
- Every change is ONE sealed, pre-registered experiment: one change against a named base, predictions and pass marks fixed before the run, files sealed with SHA-256 hashes before the registered run.
- Pass/fail is decided on a blind TEST-ONLY panel written by a separate AI agent from a spec. Panels are never trained or tuned on, never quoted, and become "burned" once a builder sees items.
- A registered FAIL stays FAIL. A failed experiment gets exactly one diagnosis-driven follow-up.
- Director verifies every report: seal check, own recount from raw files, a held-out probe for every PASS.
- Fictional names only in all test and training data. No personal data. Unverified web text never goes into weights.
- The only human is the owner, a high-school senior who does not run commands; AI agents build, write panels and grade.

HARDWARE AND BUDGET
One RTX 5070 Ti (16 GB), sometimes offline; a busy shared Mac for CPU work; cloud GPU rentals within a $30 TOTAL budget. Downloading any new model needs the owner's explicit yes. A big model's GENERATED TEXT may be used as training data (stated honestly); borrowing its WEIGHTS for the final system is not allowed (borrowed parts are placeholders).

SCOPE
Only the chat assistant (ear, gate, notebook, reasoner, mouth). The owner has other projects ("small card experiments", "a village model"); do not mix them in.
=== END OF PROJECT CONTEXT ===

QUESTION 11 OF A BATCH (answer only this one): Proving the design beats an equal-size plain transformer, fairly

THE PROBLEM
The project's headline claim is that this design (reader + explicit notebook + small reasoner + mouth) beats an equal-size plain transformer on two-hop, reversal, abstention and MQuAKE-style edit questions. A skeptic will say "of course, you gave it a database". I need a comparison that is fair and whose win means something.

DETAIL
- The notebook + reasoner is exact on clean structured input (200/200). The risk is all in reading English.
- Planned baselines: (a) a plain decoder transformer of the same audited parameter count (about 33M), same pretraining data and same compute; (b) the same with retrieval over the chat history (MeLLo-style); (c) the same model given the same notebook, so "it's just the database" gets a number.
- A comparison benchmark has been written and sealed: 5 x 500 fictional "worlds" (each a chat where facts are taught, then questions asked), marked test-only.
- An earlier review found a bias in an older comparison: the plain model's prompt had no fact order and no "newer wins" rule, and a bare "not" as the abstain marker. The reversal rows of an older benchmark had the answer inside the question.
- Budget: $30 total for rentals; one 16 GB GPU.

THE HARD QUESTION
What set of baselines, tuning budgets, data parity rules and metrics makes the win meaningful? What claims are legitimate if the design wins only with the notebook (and is that the point, not a flaw)? How should reading errors be separated from reasoning wins (e.g. report with gold frames and with the real ear)? How big must each test be for the differences to be real, and what result would show the design does NOT beat the baseline? Also: what 5-minute live demo for a non-technical family audience shows the difference honestly?

WHAT I NEED BACK
1. Your diagnosis: what is really going on, and which of my explanations above is wrong or incomplete.
2. At most 4 ranked options, each with what it fixes, what it costs, and what it cannot fix.
3. The ONE experiment to run next: a single change against the current system, pass marks with exact numbers fixed in advance, the sample size and why, and the result that would prove your idea wrong. If it needs a later second step, name it but keep it separate.
4. The strongest objection to your own recommendation, and the rival you rejected.
5. Label every claim as SHOWN (published or measured), SUGGESTED (published, but in a different setting) or UNTESTED (your reasoning). Cite papers with arXiv IDs where you can, and say when you know only the abstract. Do not invent numbers or citations; say "I don't know" instead.
6. Keep this only about the chat assistant; no "small card experiments" or "village model".
7. End with a plain-language summary of 6-10 sentences that a high-school senior can follow.
```

## 12. "Our" and "we": group owners in a person-by-person notebook

```text
=== PROJECT CONTEXT (the same block starts every question in this batch) ===
You are advising on a research project through a plain chat. You cannot see the code, the files, or earlier chats, so everything you need is below. Where I give a number, it was measured; where I say "suggested" or "I think", it was not.

WHAT PREMONITION IS
Premonition is a personal assistant being built by a high-school senior (the owner), with AI coding agents doing the building and Claude directing and verifying. It starts knowing nothing. The user teaches it facts in plain English chat. It stores them in an explicit notebook, reasons over them (two-hop and beyond), says "I don't know" instead of guessing, and replies in fluent English. The end goal is a system on the owner's OWN architecture and OWN weights that beats an equal-size plain transformer (same data, same parameter count) on two-hop questions, reversal questions (asking the inverse of a taught fact), abstention on untaught facts, and multi-hop answers after a fact is edited (MQuAKE-style), plus a live demo for the owner's family.

HARD TARGETS
- 0 wrong notebook writes, certified below 1%. A wrong save is worse than a refusal or a clarifying question.
- Recall: at least 85% of plainly stated facts saved exactly; at most 12% of true facts held back.
- 99%+ grammatical replies, no simple mistakes, and no reply may claim something untrue about the notebook or about the assistant itself.
- Median turn time at most 800 ms.

THE PIPELINE TODAY (numbers are from sealed experiments)
1. EAR (English -> frames), BORROWED: SmolLM2-360M fine-tuned ("ear v4.1") to write one line per frame:
     TEACH | owner | relation | value      (e.g. TEACH | me | sister | Mira)
     ASK   | owner | relation              (e.g. ASK | Mira | dog)
     NONE
   A plain-code "speaker canonicaliser" maps I/me/my to the user ("me").
2. RULE BRAKE (plain code): drops frames with junk, e.g. a stored name containing a comma, or a value not found in the turn.
3. GATE, BORROWED: Qwen3.8-27B (4-bit, local on one RTX 5070 Ti 16 GB) is asked YES/NO "does this message explicitly assert this claim?" per frame; saved if P(YES) >= 0.25. The prompt wording and the 0.25 threshold were both chosen on a development set.
4. NOTEBOOK: rows owner | relation | value, e.g.  me | sister | Mira ;  Mira | dog | Pip. "X is the R of Y" is stored as "Y's R is X". Taught facts are never overwritten by inferences. Inverses ("Whose dog is Pip?") are computed at answer time. Relations come from a fixed relation table of 153 entries (each with aliases, an inverse, single- or multi-valued, and the kind of value) plus "other".
5. REASONER (ours): a question parser built as a stack of hand-written stages, each added by one past experiment (a reverse-question stage, a table stage, a yes/no reader, an n-hop chain stage, a decline-wording rewrite, ...), plus a 79,316-parameter learned lookup reasoner for multi-hop. On clean structured input it answers two-hop, reversal, abstention and single-edit multi-hop questions exactly (200/200 on an internal benchmark). The weak point is reading English, in and out.
6. MOUTH (ours, hand-made): a grammar layer that turns reply records into sentences. Grammar 1195/1205 = 99.2% under two independently checked graders; a blind judge preferred it 97 wins / 9 losses / 14 ties over the previous version. It still sometimes prints raw relation-table labels (e.g. "religion or worldview").
7. OWN-MODEL PLAN (not built yet): a ~33M-parameter own ear (8-layer width-512 bidirectional encoder, pretrained by fill-in-the-blank on simple-English stories and dialogues; heads that POINT at whole-word spans of the turn for owner and value; relation chosen from the table; a 9-way speech-act head; a fact-count head; 6 set-prediction fact slots) and an own mouth (a 28.85M decoder trained from scratch, "talker101"). Only a small plain-code "write compiler" may write to the notebook, from spans of the unchanged turn, all facts of a turn together or none. A round trip (fact -> sentence -> fact) is used for TRAINING only and is never permission to write, because it can agree with itself on a wrong fact.

MEASURED STATE OF EACH PART (fresh blind panels unless noted)
- Ear + gate (150 fresh turns): 9 scored wrong saves; 6 of those were answer-key mistakes (key said "pet", ear said "dog"), 3 were real: 2 chat typos stored inside a value (gate P(YES) 0.85 and 0.68) and 1 fact saved from a check-question with no "?" (0.37). Recall 77.9%. Threshold sweep: 19 wrong at threshold 0, 9 at 0.25, 7 at 0.7. Sentences naming several relatives: 4 of 16 facts found.
- On the development set used to choose the gate prompt and threshold, the gate let 13 of 103 wrong frames through. On 120 fresh turns from a new writer it let 63 of 65 through. So the gate barely works on fresh wording.
- A 3-question QA gate (ask "whose R is V?", "what is O's R?", "how is O related to V?" in separate prompts): 5 wrong out of 86 saved vs YES/NO 6 out of 100, but it held back 30% of true facts (bar 12%) and took 880 ms median (bar 800). Registered FAIL.
- Own-model write rules, oracle audit (a perfect reader, the planned strict write compiler): only 184 of 272 real facts (67.6%) are writable (bar 85%); 0 of 76 should-not-save facts writable.
- Casual typing (all lowercase, no apostrophes, typos) is read badly: a normaliser experiment failed and itself added 3 wrong saves.
- "our/we" is NOT the speaker (owner's ruling): the assistant must ask whose. An "ask whose" rule failed because the ear rarely hands it a group owner (14 of 30 asked, bar 27).
- Questions outside the parser's known shapes get "I didn't understand that": 40 of 51 yes/no questions were not understood.
- Replies: an honest "what can you do" list now makes 0 unsupported claims.

HOW WORK IS DONE (the rules)
- Every change is ONE sealed, pre-registered experiment: one change against a named base, predictions and pass marks fixed before the run, files sealed with SHA-256 hashes before the registered run.
- Pass/fail is decided on a blind TEST-ONLY panel written by a separate AI agent from a spec. Panels are never trained or tuned on, never quoted, and become "burned" once a builder sees items.
- A registered FAIL stays FAIL. A failed experiment gets exactly one diagnosis-driven follow-up.
- Director verifies every report: seal check, own recount from raw files, a held-out probe for every PASS.
- Fictional names only in all test and training data. No personal data. Unverified web text never goes into weights.
- The only human is the owner, a high-school senior who does not run commands; AI agents build, write panels and grade.

HARDWARE AND BUDGET
One RTX 5070 Ti (16 GB), sometimes offline; a busy shared Mac for CPU work; cloud GPU rentals within a $30 TOTAL budget. Downloading any new model needs the owner's explicit yes. A big model's GENERATED TEXT may be used as training data (stated honestly); borrowing its WEIGHTS for the final system is not allowed (borrowed parts are placeholders).

SCOPE
Only the chat assistant (ear, gate, notebook, reasoner, mouth). The owner has other projects ("small card experiments", "a village model"); do not mix them in.
=== END OF PROJECT CONTEXT ===

QUESTION 12 OF A BATCH (answer only this one): "Our" and "we": group owners in a person-by-person notebook

THE PROBLEM
The owner ruled that "our dog is Pip" is NOT the speaker's fact: the assistant should ask whose, unless the group is known. The notebook stores owner | relation | value with single owners.

MEASURED
- A rule "if the ear's owner is a group word, ask whose": it fired on 23 of 23 group owners it saw, but the ear handed it a group owner on too few turns. Group-owner turns asked whose 14/30 (bar 27); mixed turns exactly right 5/15 (bar 12); 0 new wrong saves. On 16 group turns the ear read the owner some other way (10) or the brake dropped the frame (6).
- A text-level check before the ear (ask whose if the turn names a thing owned by our/we/us): on development turns it asked on 46 of 46 group turns with 0 false asks in 53; its registered run is not finished.
- "we/our" also appears where it is not ownership: "we went to Tolby", "our meeting is at 3", "we're fine".

THE HARD QUESTION
How should groups be represented (a named group entity like "household", a set of people, or a shared-owner flag), how should the assistant ask whose with the fewest questions ("our dog" asked once, then remembered?), how should questions about group facts be answered ("Whose dog is Pip?"), and how should the reader decide that "we/our" is about ownership at all? What wrong saves can the group model itself create? One sealed experiment with pass marks.

WHAT I NEED BACK
1. Your diagnosis: what is really going on, and which of my explanations above is wrong or incomplete.
2. At most 4 ranked options, each with what it fixes, what it costs, and what it cannot fix.
3. The ONE experiment to run next: a single change against the current system, pass marks with exact numbers fixed in advance, the sample size and why, and the result that would prove your idea wrong. If it needs a later second step, name it but keep it separate.
4. The strongest objection to your own recommendation, and the rival you rejected.
5. Label every claim as SHOWN (published or measured), SUGGESTED (published, but in a different setting) or UNTESTED (your reasoning). Cite papers with arXiv IDs where you can, and say when you know only the abstract. Do not invent numbers or citations; say "I don't know" instead.
6. Keep this only about the chat assistant; no "small card experiments" or "village model".
7. End with a plain-language summary of 6-10 sentences that a high-school senior can follow.
```

## 13. Every sentence the assistant says must be true

```text
=== PROJECT CONTEXT (the same block starts every question in this batch) ===
You are advising on a research project through a plain chat. You cannot see the code, the files, or earlier chats, so everything you need is below. Where I give a number, it was measured; where I say "suggested" or "I think", it was not.

WHAT PREMONITION IS
Premonition is a personal assistant being built by a high-school senior (the owner), with AI coding agents doing the building and Claude directing and verifying. It starts knowing nothing. The user teaches it facts in plain English chat. It stores them in an explicit notebook, reasons over them (two-hop and beyond), says "I don't know" instead of guessing, and replies in fluent English. The end goal is a system on the owner's OWN architecture and OWN weights that beats an equal-size plain transformer (same data, same parameter count) on two-hop questions, reversal questions (asking the inverse of a taught fact), abstention on untaught facts, and multi-hop answers after a fact is edited (MQuAKE-style), plus a live demo for the owner's family.

HARD TARGETS
- 0 wrong notebook writes, certified below 1%. A wrong save is worse than a refusal or a clarifying question.
- Recall: at least 85% of plainly stated facts saved exactly; at most 12% of true facts held back.
- 99%+ grammatical replies, no simple mistakes, and no reply may claim something untrue about the notebook or about the assistant itself.
- Median turn time at most 800 ms.

THE PIPELINE TODAY (numbers are from sealed experiments)
1. EAR (English -> frames), BORROWED: SmolLM2-360M fine-tuned ("ear v4.1") to write one line per frame:
     TEACH | owner | relation | value      (e.g. TEACH | me | sister | Mira)
     ASK   | owner | relation              (e.g. ASK | Mira | dog)
     NONE
   A plain-code "speaker canonicaliser" maps I/me/my to the user ("me").
2. RULE BRAKE (plain code): drops frames with junk, e.g. a stored name containing a comma, or a value not found in the turn.
3. GATE, BORROWED: Qwen3.8-27B (4-bit, local on one RTX 5070 Ti 16 GB) is asked YES/NO "does this message explicitly assert this claim?" per frame; saved if P(YES) >= 0.25. The prompt wording and the 0.25 threshold were both chosen on a development set.
4. NOTEBOOK: rows owner | relation | value, e.g.  me | sister | Mira ;  Mira | dog | Pip. "X is the R of Y" is stored as "Y's R is X". Taught facts are never overwritten by inferences. Inverses ("Whose dog is Pip?") are computed at answer time. Relations come from a fixed relation table of 153 entries (each with aliases, an inverse, single- or multi-valued, and the kind of value) plus "other".
5. REASONER (ours): a question parser built as a stack of hand-written stages, each added by one past experiment (a reverse-question stage, a table stage, a yes/no reader, an n-hop chain stage, a decline-wording rewrite, ...), plus a 79,316-parameter learned lookup reasoner for multi-hop. On clean structured input it answers two-hop, reversal, abstention and single-edit multi-hop questions exactly (200/200 on an internal benchmark). The weak point is reading English, in and out.
6. MOUTH (ours, hand-made): a grammar layer that turns reply records into sentences. Grammar 1195/1205 = 99.2% under two independently checked graders; a blind judge preferred it 97 wins / 9 losses / 14 ties over the previous version. It still sometimes prints raw relation-table labels (e.g. "religion or worldview").
7. OWN-MODEL PLAN (not built yet): a ~33M-parameter own ear (8-layer width-512 bidirectional encoder, pretrained by fill-in-the-blank on simple-English stories and dialogues; heads that POINT at whole-word spans of the turn for owner and value; relation chosen from the table; a 9-way speech-act head; a fact-count head; 6 set-prediction fact slots) and an own mouth (a 28.85M decoder trained from scratch, "talker101"). Only a small plain-code "write compiler" may write to the notebook, from spans of the unchanged turn, all facts of a turn together or none. A round trip (fact -> sentence -> fact) is used for TRAINING only and is never permission to write, because it can agree with itself on a wrong fact.

MEASURED STATE OF EACH PART (fresh blind panels unless noted)
- Ear + gate (150 fresh turns): 9 scored wrong saves; 6 of those were answer-key mistakes (key said "pet", ear said "dog"), 3 were real: 2 chat typos stored inside a value (gate P(YES) 0.85 and 0.68) and 1 fact saved from a check-question with no "?" (0.37). Recall 77.9%. Threshold sweep: 19 wrong at threshold 0, 9 at 0.25, 7 at 0.7. Sentences naming several relatives: 4 of 16 facts found.
- On the development set used to choose the gate prompt and threshold, the gate let 13 of 103 wrong frames through. On 120 fresh turns from a new writer it let 63 of 65 through. So the gate barely works on fresh wording.
- A 3-question QA gate (ask "whose R is V?", "what is O's R?", "how is O related to V?" in separate prompts): 5 wrong out of 86 saved vs YES/NO 6 out of 100, but it held back 30% of true facts (bar 12%) and took 880 ms median (bar 800). Registered FAIL.
- Own-model write rules, oracle audit (a perfect reader, the planned strict write compiler): only 184 of 272 real facts (67.6%) are writable (bar 85%); 0 of 76 should-not-save facts writable.
- Casual typing (all lowercase, no apostrophes, typos) is read badly: a normaliser experiment failed and itself added 3 wrong saves.
- "our/we" is NOT the speaker (owner's ruling): the assistant must ask whose. An "ask whose" rule failed because the ear rarely hands it a group owner (14 of 30 asked, bar 27).
- Questions outside the parser's known shapes get "I didn't understand that": 40 of 51 yes/no questions were not understood.
- Replies: an honest "what can you do" list now makes 0 unsupported claims.

HOW WORK IS DONE (the rules)
- Every change is ONE sealed, pre-registered experiment: one change against a named base, predictions and pass marks fixed before the run, files sealed with SHA-256 hashes before the registered run.
- Pass/fail is decided on a blind TEST-ONLY panel written by a separate AI agent from a spec. Panels are never trained or tuned on, never quoted, and become "burned" once a builder sees items.
- A registered FAIL stays FAIL. A failed experiment gets exactly one diagnosis-driven follow-up.
- Director verifies every report: seal check, own recount from raw files, a held-out probe for every PASS.
- Fictional names only in all test and training data. No personal data. Unverified web text never goes into weights.
- The only human is the owner, a high-school senior who does not run commands; AI agents build, write panels and grade.

HARDWARE AND BUDGET
One RTX 5070 Ti (16 GB), sometimes offline; a busy shared Mac for CPU work; cloud GPU rentals within a $30 TOTAL budget. Downloading any new model needs the owner's explicit yes. A big model's GENERATED TEXT may be used as training data (stated honestly); borrowing its WEIGHTS for the final system is not allowed (borrowed parts are placeholders).

SCOPE
Only the chat assistant (ear, gate, notebook, reasoner, mouth). The owner has other projects ("small card experiments", "a village model"); do not mix them in.
=== END OF PROJECT CONTEXT ===

QUESTION 13 OF A BATCH (answer only this one): Every sentence the assistant says must be true

THE PROBLEM
Beyond wrong saves, replies can be untrue: about the notebook ("I don't know that" when it was taught), or about the assistant ("I can give sources" when it cannot). The system must never claim something it cannot back up, while still being helpful and natural.

MEASURED
- An earlier "What can you do?" answer listed skills that had never been tested. A fixed honest ability text now makes 0 unsupported claims; every claim in it matches measured dev evidence (saving 8/8, one-step questions 8/8, two-step boss chains 10/10, "No, ..." corrections 8/8, "Forget X's R." 8/8, abstaining 8/8; sources 0/8, so it says it cannot give sources yet). Recognising ability questions by a closed list of forms got 9/12; by meaning 24/25.
- "I do not know that from what you taught me" was said about taught facts in 2 dev cases; the current wording is "I didn't understand that question", which is true when the parser failed.
- Answers worked out backwards now say "(worked out backwards)".
- "Can you ...?" requests get honest declines but no help.

THE HARD QUESTION
Design a claim-provenance rule for replies: every sentence is either (a) a notebook row or a derivation from rows, (b) a measured ability with its evidence, (c) a fixed social phrase, or (d) an honest statement of a failure the system can actually detect. How do I enforce this when the mouth becomes a learned model? How can the system tell "not taught" from "taught but I failed to read your question" from "taught then retracted"? How should uncertainty be phrased so a non-technical user trusts it correctly? One sealed experiment with pass marks.

WHAT I NEED BACK
1. Your diagnosis: what is really going on, and which of my explanations above is wrong or incomplete.
2. At most 4 ranked options, each with what it fixes, what it costs, and what it cannot fix.
3. The ONE experiment to run next: a single change against the current system, pass marks with exact numbers fixed in advance, the sample size and why, and the result that would prove your idea wrong. If it needs a later second step, name it but keep it separate.
4. The strongest objection to your own recommendation, and the rival you rejected.
5. Label every claim as SHOWN (published or measured), SUGGESTED (published, but in a different setting) or UNTESTED (your reasoning). Cite papers with arXiv IDs where you can, and say when you know only the abstract. Do not invent numbers or citations; say "I don't know" instead.
6. Keep this only about the chat assistant; no "small card experiments" or "village model".
7. End with a plain-language summary of 6-10 sentences that a high-school senior can follow.
```

## 14. A relation vocabulary that can grow without wrong saves

```text
=== PROJECT CONTEXT (the same block starts every question in this batch) ===
You are advising on a research project through a plain chat. You cannot see the code, the files, or earlier chats, so everything you need is below. Where I give a number, it was measured; where I say "suggested" or "I think", it was not.

WHAT PREMONITION IS
Premonition is a personal assistant being built by a high-school senior (the owner), with AI coding agents doing the building and Claude directing and verifying. It starts knowing nothing. The user teaches it facts in plain English chat. It stores them in an explicit notebook, reasons over them (two-hop and beyond), says "I don't know" instead of guessing, and replies in fluent English. The end goal is a system on the owner's OWN architecture and OWN weights that beats an equal-size plain transformer (same data, same parameter count) on two-hop questions, reversal questions (asking the inverse of a taught fact), abstention on untaught facts, and multi-hop answers after a fact is edited (MQuAKE-style), plus a live demo for the owner's family.

HARD TARGETS
- 0 wrong notebook writes, certified below 1%. A wrong save is worse than a refusal or a clarifying question.
- Recall: at least 85% of plainly stated facts saved exactly; at most 12% of true facts held back.
- 99%+ grammatical replies, no simple mistakes, and no reply may claim something untrue about the notebook or about the assistant itself.
- Median turn time at most 800 ms.

THE PIPELINE TODAY (numbers are from sealed experiments)
1. EAR (English -> frames), BORROWED: SmolLM2-360M fine-tuned ("ear v4.1") to write one line per frame:
     TEACH | owner | relation | value      (e.g. TEACH | me | sister | Mira)
     ASK   | owner | relation              (e.g. ASK | Mira | dog)
     NONE
   A plain-code "speaker canonicaliser" maps I/me/my to the user ("me").
2. RULE BRAKE (plain code): drops frames with junk, e.g. a stored name containing a comma, or a value not found in the turn.
3. GATE, BORROWED: Qwen3.8-27B (4-bit, local on one RTX 5070 Ti 16 GB) is asked YES/NO "does this message explicitly assert this claim?" per frame; saved if P(YES) >= 0.25. The prompt wording and the 0.25 threshold were both chosen on a development set.
4. NOTEBOOK: rows owner | relation | value, e.g.  me | sister | Mira ;  Mira | dog | Pip. "X is the R of Y" is stored as "Y's R is X". Taught facts are never overwritten by inferences. Inverses ("Whose dog is Pip?") are computed at answer time. Relations come from a fixed relation table of 153 entries (each with aliases, an inverse, single- or multi-valued, and the kind of value) plus "other".
5. REASONER (ours): a question parser built as a stack of hand-written stages, each added by one past experiment (a reverse-question stage, a table stage, a yes/no reader, an n-hop chain stage, a decline-wording rewrite, ...), plus a 79,316-parameter learned lookup reasoner for multi-hop. On clean structured input it answers two-hop, reversal, abstention and single-edit multi-hop questions exactly (200/200 on an internal benchmark). The weak point is reading English, in and out.
6. MOUTH (ours, hand-made): a grammar layer that turns reply records into sentences. Grammar 1195/1205 = 99.2% under two independently checked graders; a blind judge preferred it 97 wins / 9 losses / 14 ties over the previous version. It still sometimes prints raw relation-table labels (e.g. "religion or worldview").
7. OWN-MODEL PLAN (not built yet): a ~33M-parameter own ear (8-layer width-512 bidirectional encoder, pretrained by fill-in-the-blank on simple-English stories and dialogues; heads that POINT at whole-word spans of the turn for owner and value; relation chosen from the table; a 9-way speech-act head; a fact-count head; 6 set-prediction fact slots) and an own mouth (a 28.85M decoder trained from scratch, "talker101"). Only a small plain-code "write compiler" may write to the notebook, from spans of the unchanged turn, all facts of a turn together or none. A round trip (fact -> sentence -> fact) is used for TRAINING only and is never permission to write, because it can agree with itself on a wrong fact.

MEASURED STATE OF EACH PART (fresh blind panels unless noted)
- Ear + gate (150 fresh turns): 9 scored wrong saves; 6 of those were answer-key mistakes (key said "pet", ear said "dog"), 3 were real: 2 chat typos stored inside a value (gate P(YES) 0.85 and 0.68) and 1 fact saved from a check-question with no "?" (0.37). Recall 77.9%. Threshold sweep: 19 wrong at threshold 0, 9 at 0.25, 7 at 0.7. Sentences naming several relatives: 4 of 16 facts found.
- On the development set used to choose the gate prompt and threshold, the gate let 13 of 103 wrong frames through. On 120 fresh turns from a new writer it let 63 of 65 through. So the gate barely works on fresh wording.
- A 3-question QA gate (ask "whose R is V?", "what is O's R?", "how is O related to V?" in separate prompts): 5 wrong out of 86 saved vs YES/NO 6 out of 100, but it held back 30% of true facts (bar 12%) and took 880 ms median (bar 800). Registered FAIL.
- Own-model write rules, oracle audit (a perfect reader, the planned strict write compiler): only 184 of 272 real facts (67.6%) are writable (bar 85%); 0 of 76 should-not-save facts writable.
- Casual typing (all lowercase, no apostrophes, typos) is read badly: a normaliser experiment failed and itself added 3 wrong saves.
- "our/we" is NOT the speaker (owner's ruling): the assistant must ask whose. An "ask whose" rule failed because the ear rarely hands it a group owner (14 of 30 asked, bar 27).
- Questions outside the parser's known shapes get "I didn't understand that": 40 of 51 yes/no questions were not understood.
- Replies: an honest "what can you do" list now makes 0 unsupported claims.

HOW WORK IS DONE (the rules)
- Every change is ONE sealed, pre-registered experiment: one change against a named base, predictions and pass marks fixed before the run, files sealed with SHA-256 hashes before the registered run.
- Pass/fail is decided on a blind TEST-ONLY panel written by a separate AI agent from a spec. Panels are never trained or tuned on, never quoted, and become "burned" once a builder sees items.
- A registered FAIL stays FAIL. A failed experiment gets exactly one diagnosis-driven follow-up.
- Director verifies every report: seal check, own recount from raw files, a held-out probe for every PASS.
- Fictional names only in all test and training data. No personal data. Unverified web text never goes into weights.
- The only human is the owner, a high-school senior who does not run commands; AI agents build, write panels and grade.

HARDWARE AND BUDGET
One RTX 5070 Ti (16 GB), sometimes offline; a busy shared Mac for CPU work; cloud GPU rentals within a $30 TOTAL budget. Downloading any new model needs the owner's explicit yes. A big model's GENERATED TEXT may be used as training data (stated honestly); borrowing its WEIGHTS for the final system is not allowed (borrowed parts are placeholders).

SCOPE
Only the chat assistant (ear, gate, notebook, reasoner, mouth). The owner has other projects ("small card experiments", "a village model"); do not mix them in.
=== END OF PROJECT CONTEXT ===

QUESTION 14 OF A BATCH (answer only this one): A relation vocabulary that can grow without wrong saves

THE PROBLEM
Facts must use one of 153 relations in a fixed table (each with aliases, an inverse, single or multi-valued, and the kind of value). Real chat uses relations that are not in the table, verb phrases instead of nouns, and relations whose inverse depends on unknown information.

MEASURED AND KNOWN
- In the oracle audit, 12 of 272 real facts used a relation not in the table, and 59 had no relation cue word (verb facts like "works at", "moved to" are among them).
- Replies sometimes print raw table labels ("religion or worldview", "language of work or name").
- Yes/no answers may only say "No" for single-valued relations.
- "Who is Ada's child?" works because "mother" has an inverse; inverses like "Bo's parent" lose gender and number.
- The table once scored "dog" as wrong against a key of "pet"; the table must say which relation names are narrower than others.
- Open question for the owner: may the automatic "sleep" consolidation learn new relation words?

THE HARD QUESTION
How should a new relation enter the system: asked of the user ("What is 'godmother' — like mother?"), learned from repeated use, or stored as OTHER:<words> with limited reasoning? Which properties (inverse, cardinality, value type, narrower/broader, symmetric, transitive) must be known before a relation can be used in multi-hop or yes/no answers, and which can be safely unknown? How do verb facts map to relations without wrong saves? One sealed experiment with pass marks.

WHAT I NEED BACK
1. Your diagnosis: what is really going on, and which of my explanations above is wrong or incomplete.
2. At most 4 ranked options, each with what it fixes, what it costs, and what it cannot fix.
3. The ONE experiment to run next: a single change against the current system, pass marks with exact numbers fixed in advance, the sample size and why, and the result that would prove your idea wrong. If it needs a later second step, name it but keep it separate.
4. The strongest objection to your own recommendation, and the rival you rejected.
5. Label every claim as SHOWN (published or measured), SUGGESTED (published, but in a different setting) or UNTESTED (your reasoning). Cite papers with arXiv IDs where you can, and say when you know only the abstract. Do not invent numbers or citations; say "I don't know" instead.
6. Keep this only about the chat assistant; no "small card experiments" or "village model".
7. End with a plain-language summary of 6-10 sentences that a high-school senior can follow.
```

## 15. Combining many verified single changes into one base

```text
=== PROJECT CONTEXT (the same block starts every question in this batch) ===
You are advising on a research project through a plain chat. You cannot see the code, the files, or earlier chats, so everything you need is below. Where I give a number, it was measured; where I say "suggested" or "I think", it was not.

WHAT PREMONITION IS
Premonition is a personal assistant being built by a high-school senior (the owner), with AI coding agents doing the building and Claude directing and verifying. It starts knowing nothing. The user teaches it facts in plain English chat. It stores them in an explicit notebook, reasons over them (two-hop and beyond), says "I don't know" instead of guessing, and replies in fluent English. The end goal is a system on the owner's OWN architecture and OWN weights that beats an equal-size plain transformer (same data, same parameter count) on two-hop questions, reversal questions (asking the inverse of a taught fact), abstention on untaught facts, and multi-hop answers after a fact is edited (MQuAKE-style), plus a live demo for the owner's family.

HARD TARGETS
- 0 wrong notebook writes, certified below 1%. A wrong save is worse than a refusal or a clarifying question.
- Recall: at least 85% of plainly stated facts saved exactly; at most 12% of true facts held back.
- 99%+ grammatical replies, no simple mistakes, and no reply may claim something untrue about the notebook or about the assistant itself.
- Median turn time at most 800 ms.

THE PIPELINE TODAY (numbers are from sealed experiments)
1. EAR (English -> frames), BORROWED: SmolLM2-360M fine-tuned ("ear v4.1") to write one line per frame:
     TEACH | owner | relation | value      (e.g. TEACH | me | sister | Mira)
     ASK   | owner | relation              (e.g. ASK | Mira | dog)
     NONE
   A plain-code "speaker canonicaliser" maps I/me/my to the user ("me").
2. RULE BRAKE (plain code): drops frames with junk, e.g. a stored name containing a comma, or a value not found in the turn.
3. GATE, BORROWED: Qwen3.8-27B (4-bit, local on one RTX 5070 Ti 16 GB) is asked YES/NO "does this message explicitly assert this claim?" per frame; saved if P(YES) >= 0.25. The prompt wording and the 0.25 threshold were both chosen on a development set.
4. NOTEBOOK: rows owner | relation | value, e.g.  me | sister | Mira ;  Mira | dog | Pip. "X is the R of Y" is stored as "Y's R is X". Taught facts are never overwritten by inferences. Inverses ("Whose dog is Pip?") are computed at answer time. Relations come from a fixed relation table of 153 entries (each with aliases, an inverse, single- or multi-valued, and the kind of value) plus "other".
5. REASONER (ours): a question parser built as a stack of hand-written stages, each added by one past experiment (a reverse-question stage, a table stage, a yes/no reader, an n-hop chain stage, a decline-wording rewrite, ...), plus a 79,316-parameter learned lookup reasoner for multi-hop. On clean structured input it answers two-hop, reversal, abstention and single-edit multi-hop questions exactly (200/200 on an internal benchmark). The weak point is reading English, in and out.
6. MOUTH (ours, hand-made): a grammar layer that turns reply records into sentences. Grammar 1195/1205 = 99.2% under two independently checked graders; a blind judge preferred it 97 wins / 9 losses / 14 ties over the previous version. It still sometimes prints raw relation-table labels (e.g. "religion or worldview").
7. OWN-MODEL PLAN (not built yet): a ~33M-parameter own ear (8-layer width-512 bidirectional encoder, pretrained by fill-in-the-blank on simple-English stories and dialogues; heads that POINT at whole-word spans of the turn for owner and value; relation chosen from the table; a 9-way speech-act head; a fact-count head; 6 set-prediction fact slots) and an own mouth (a 28.85M decoder trained from scratch, "talker101"). Only a small plain-code "write compiler" may write to the notebook, from spans of the unchanged turn, all facts of a turn together or none. A round trip (fact -> sentence -> fact) is used for TRAINING only and is never permission to write, because it can agree with itself on a wrong fact.

MEASURED STATE OF EACH PART (fresh blind panels unless noted)
- Ear + gate (150 fresh turns): 9 scored wrong saves; 6 of those were answer-key mistakes (key said "pet", ear said "dog"), 3 were real: 2 chat typos stored inside a value (gate P(YES) 0.85 and 0.68) and 1 fact saved from a check-question with no "?" (0.37). Recall 77.9%. Threshold sweep: 19 wrong at threshold 0, 9 at 0.25, 7 at 0.7. Sentences naming several relatives: 4 of 16 facts found.
- On the development set used to choose the gate prompt and threshold, the gate let 13 of 103 wrong frames through. On 120 fresh turns from a new writer it let 63 of 65 through. So the gate barely works on fresh wording.
- A 3-question QA gate (ask "whose R is V?", "what is O's R?", "how is O related to V?" in separate prompts): 5 wrong out of 86 saved vs YES/NO 6 out of 100, but it held back 30% of true facts (bar 12%) and took 880 ms median (bar 800). Registered FAIL.
- Own-model write rules, oracle audit (a perfect reader, the planned strict write compiler): only 184 of 272 real facts (67.6%) are writable (bar 85%); 0 of 76 should-not-save facts writable.
- Casual typing (all lowercase, no apostrophes, typos) is read badly: a normaliser experiment failed and itself added 3 wrong saves.
- "our/we" is NOT the speaker (owner's ruling): the assistant must ask whose. An "ask whose" rule failed because the ear rarely hands it a group owner (14 of 30 asked, bar 27).
- Questions outside the parser's known shapes get "I didn't understand that": 40 of 51 yes/no questions were not understood.
- Replies: an honest "what can you do" list now makes 0 unsupported claims.

HOW WORK IS DONE (the rules)
- Every change is ONE sealed, pre-registered experiment: one change against a named base, predictions and pass marks fixed before the run, files sealed with SHA-256 hashes before the registered run.
- Pass/fail is decided on a blind TEST-ONLY panel written by a separate AI agent from a spec. Panels are never trained or tuned on, never quoted, and become "burned" once a builder sees items.
- A registered FAIL stays FAIL. A failed experiment gets exactly one diagnosis-driven follow-up.
- Director verifies every report: seal check, own recount from raw files, a held-out probe for every PASS.
- Fictional names only in all test and training data. No personal data. Unverified web text never goes into weights.
- The only human is the owner, a high-school senior who does not run commands; AI agents build, write panels and grade.

HARDWARE AND BUDGET
One RTX 5070 Ti (16 GB), sometimes offline; a busy shared Mac for CPU work; cloud GPU rentals within a $30 TOTAL budget. Downloading any new model needs the owner's explicit yes. A big model's GENERATED TEXT may be used as training data (stated honestly); borrowing its WEIGHTS for the final system is not allowed (borrowed parts are placeholders).

SCOPE
Only the chat assistant (ear, gate, notebook, reasoner, mouth). The owner has other projects ("small card experiments", "a village model"); do not mix them in.
=== END OF PROJECT CONTEXT ===

QUESTION 15 OF A BATCH (answer only this one): Combining many verified single changes into one base

THE PROBLEM
Several lines of work each produce single-change experiments on their own base (a question-reading line, a correction line, a reply-wording line, an ear line). Each piece is verified alone. Combining them is where things break, and every combination seems to need a new blind panel.

MEASURED
- A merge of three verified pieces failed its byte-identity check on 15 rows: every difference was reply wording (one lineage said "I do not know that from what you taught me", the other "I didn't understand that question"), stores identical. A second merge is now being tried with the old panels as regression checks only and a fresh blind panel for the claim.
- An experiment was built on the wrong base, so its panel could not show the bug it targeted (the bug lived in a stage that base did not have).
- Panels burn quickly: after a merge's builder pushed raw panel rows, three panels became regression-only.
- Pieces waiting to be merged include: openers, corrections, the backwards label, honest reply texts, the comma guard, the chain-subject fix.

THE HARD QUESTION
What process lets many single-change pieces be combined with confidence and without burning a fresh blind panel every time? Consider: declaring each piece's "footprint" (which reply fields and store rows it may change) and checking merges mechanically against the union of footprints; interaction tests only where footprints overlap; a single canonical wording table; a fixed regression suite that is allowed to be seen; and when a merge truly needs fresh blind evidence. What would show this process lets a real regression through?

WHAT I NEED BACK
1. Your diagnosis: what is really going on, and which of my explanations above is wrong or incomplete.
2. At most 4 ranked options, each with what it fixes, what it costs, and what it cannot fix.
3. The ONE experiment to run next: a single change against the current system, pass marks with exact numbers fixed in advance, the sample size and why, and the result that would prove your idea wrong. If it needs a later second step, name it but keep it separate.
4. The strongest objection to your own recommendation, and the rival you rejected.
5. Label every claim as SHOWN (published or measured), SUGGESTED (published, but in a different setting) or UNTESTED (your reasoning). Cite papers with arXiv IDs where you can, and say when you know only the abstract. Do not invent numbers or citations; say "I don't know" instead.
6. Keep this only about the chat assistant; no "small card experiments" or "village model".
7. End with a plain-language summary of 6-10 sentences that a high-school senior can follow.
```

## 16. Speed: a 5% time bar measured on a busy machine, and a 27B gate per fact

```text
=== PROJECT CONTEXT (the same block starts every question in this batch) ===
You are advising on a research project through a plain chat. You cannot see the code, the files, or earlier chats, so everything you need is below. Where I give a number, it was measured; where I say "suggested" or "I think", it was not.

WHAT PREMONITION IS
Premonition is a personal assistant being built by a high-school senior (the owner), with AI coding agents doing the building and Claude directing and verifying. It starts knowing nothing. The user teaches it facts in plain English chat. It stores them in an explicit notebook, reasons over them (two-hop and beyond), says "I don't know" instead of guessing, and replies in fluent English. The end goal is a system on the owner's OWN architecture and OWN weights that beats an equal-size plain transformer (same data, same parameter count) on two-hop questions, reversal questions (asking the inverse of a taught fact), abstention on untaught facts, and multi-hop answers after a fact is edited (MQuAKE-style), plus a live demo for the owner's family.

HARD TARGETS
- 0 wrong notebook writes, certified below 1%. A wrong save is worse than a refusal or a clarifying question.
- Recall: at least 85% of plainly stated facts saved exactly; at most 12% of true facts held back.
- 99%+ grammatical replies, no simple mistakes, and no reply may claim something untrue about the notebook or about the assistant itself.
- Median turn time at most 800 ms.

THE PIPELINE TODAY (numbers are from sealed experiments)
1. EAR (English -> frames), BORROWED: SmolLM2-360M fine-tuned ("ear v4.1") to write one line per frame:
     TEACH | owner | relation | value      (e.g. TEACH | me | sister | Mira)
     ASK   | owner | relation              (e.g. ASK | Mira | dog)
     NONE
   A plain-code "speaker canonicaliser" maps I/me/my to the user ("me").
2. RULE BRAKE (plain code): drops frames with junk, e.g. a stored name containing a comma, or a value not found in the turn.
3. GATE, BORROWED: Qwen3.8-27B (4-bit, local on one RTX 5070 Ti 16 GB) is asked YES/NO "does this message explicitly assert this claim?" per frame; saved if P(YES) >= 0.25. The prompt wording and the 0.25 threshold were both chosen on a development set.
4. NOTEBOOK: rows owner | relation | value, e.g.  me | sister | Mira ;  Mira | dog | Pip. "X is the R of Y" is stored as "Y's R is X". Taught facts are never overwritten by inferences. Inverses ("Whose dog is Pip?") are computed at answer time. Relations come from a fixed relation table of 153 entries (each with aliases, an inverse, single- or multi-valued, and the kind of value) plus "other".
5. REASONER (ours): a question parser built as a stack of hand-written stages, each added by one past experiment (a reverse-question stage, a table stage, a yes/no reader, an n-hop chain stage, a decline-wording rewrite, ...), plus a 79,316-parameter learned lookup reasoner for multi-hop. On clean structured input it answers two-hop, reversal, abstention and single-edit multi-hop questions exactly (200/200 on an internal benchmark). The weak point is reading English, in and out.
6. MOUTH (ours, hand-made): a grammar layer that turns reply records into sentences. Grammar 1195/1205 = 99.2% under two independently checked graders; a blind judge preferred it 97 wins / 9 losses / 14 ties over the previous version. It still sometimes prints raw relation-table labels (e.g. "religion or worldview").
7. OWN-MODEL PLAN (not built yet): a ~33M-parameter own ear (8-layer width-512 bidirectional encoder, pretrained by fill-in-the-blank on simple-English stories and dialogues; heads that POINT at whole-word spans of the turn for owner and value; relation chosen from the table; a 9-way speech-act head; a fact-count head; 6 set-prediction fact slots) and an own mouth (a 28.85M decoder trained from scratch, "talker101"). Only a small plain-code "write compiler" may write to the notebook, from spans of the unchanged turn, all facts of a turn together or none. A round trip (fact -> sentence -> fact) is used for TRAINING only and is never permission to write, because it can agree with itself on a wrong fact.

MEASURED STATE OF EACH PART (fresh blind panels unless noted)
- Ear + gate (150 fresh turns): 9 scored wrong saves; 6 of those were answer-key mistakes (key said "pet", ear said "dog"), 3 were real: 2 chat typos stored inside a value (gate P(YES) 0.85 and 0.68) and 1 fact saved from a check-question with no "?" (0.37). Recall 77.9%. Threshold sweep: 19 wrong at threshold 0, 9 at 0.25, 7 at 0.7. Sentences naming several relatives: 4 of 16 facts found.
- On the development set used to choose the gate prompt and threshold, the gate let 13 of 103 wrong frames through. On 120 fresh turns from a new writer it let 63 of 65 through. So the gate barely works on fresh wording.
- A 3-question QA gate (ask "whose R is V?", "what is O's R?", "how is O related to V?" in separate prompts): 5 wrong out of 86 saved vs YES/NO 6 out of 100, but it held back 30% of true facts (bar 12%) and took 880 ms median (bar 800). Registered FAIL.
- Own-model write rules, oracle audit (a perfect reader, the planned strict write compiler): only 184 of 272 real facts (67.6%) are writable (bar 85%); 0 of 76 should-not-save facts writable.
- Casual typing (all lowercase, no apostrophes, typos) is read badly: a normaliser experiment failed and itself added 3 wrong saves.
- "our/we" is NOT the speaker (owner's ruling): the assistant must ask whose. An "ask whose" rule failed because the ear rarely hands it a group owner (14 of 30 asked, bar 27).
- Questions outside the parser's known shapes get "I didn't understand that": 40 of 51 yes/no questions were not understood.
- Replies: an honest "what can you do" list now makes 0 unsupported claims.

HOW WORK IS DONE (the rules)
- Every change is ONE sealed, pre-registered experiment: one change against a named base, predictions and pass marks fixed before the run, files sealed with SHA-256 hashes before the registered run.
- Pass/fail is decided on a blind TEST-ONLY panel written by a separate AI agent from a spec. Panels are never trained or tuned on, never quoted, and become "burned" once a builder sees items.
- A registered FAIL stays FAIL. A failed experiment gets exactly one diagnosis-driven follow-up.
- Director verifies every report: seal check, own recount from raw files, a held-out probe for every PASS.
- Fictional names only in all test and training data. No personal data. Unverified web text never goes into weights.
- The only human is the owner, a high-school senior who does not run commands; AI agents build, write panels and grade.

HARDWARE AND BUDGET
One RTX 5070 Ti (16 GB), sometimes offline; a busy shared Mac for CPU work; cloud GPU rentals within a $30 TOTAL budget. Downloading any new model needs the owner's explicit yes. A big model's GENERATED TEXT may be used as training data (stated honestly); borrowing its WEIGHTS for the final system is not allowed (borrowed parts are placeholders).

SCOPE
Only the chat assistant (ear, gate, notebook, reasoner, mouth). The owner has other projects ("small card experiments", "a village model"); do not mix them in.
=== END OF PROJECT CONTEXT ===

QUESTION 16 OF A BATCH (answer only this one): Speed: a 5% time bar measured on a busy machine, and a 27B gate per fact

THE PROBLEM
Two speed problems. (1) Measurement: a new mouth passed every quality mark but failed its speed mark (+8.1% total suite time vs a 5% bar), measured on a busy shared Mac where run-to-run spread was larger than the gap; a quiet re-measure was allowed but the Mac was never quiet in 5 hours, so the FAIL stands. (2) Budget: the gate runs a 4-bit 27B model once per fact (YES/NO) or three times (QA), and the QA version's median turn time was 880 ms against an 800 ms bar.

DETAIL
- Per-turn latency of the new mouth passed; only the whole-suite wall-clock mark failed.
- The gate runs via a llama.cpp server on the RTX 5070 Ti (16 GB), parallel 1, 4096 context, 8-bit KV cache.
- Turns carry 0-4 facts; slow turns are the multi-fact ones.

THE HARD QUESTION
(1) What speed-measurement protocol gives a trustworthy "within 5%" verdict on a noisy shared machine (paired interleaved runs, CPU time vs wall time, instruction counts, confidence intervals, how many repeats), and how should a speed bar be written in the first place? (2) How can a per-fact 27B check fit an 800 ms median: prompt-prefix caching, batching all of a turn's questions into one call, scoring with a single forward pass of logits, a smaller model first with the 27B only on risky frames, or speculative decoding? Give the expected milliseconds for each with your assumptions, and one sealed experiment with pass marks.

WHAT I NEED BACK
1. Your diagnosis: what is really going on, and which of my explanations above is wrong or incomplete.
2. At most 4 ranked options, each with what it fixes, what it costs, and what it cannot fix.
3. The ONE experiment to run next: a single change against the current system, pass marks with exact numbers fixed in advance, the sample size and why, and the result that would prove your idea wrong. If it needs a later second step, name it but keep it separate.
4. The strongest objection to your own recommendation, and the rival you rejected.
5. Label every claim as SHOWN (published or measured), SUGGESTED (published, but in a different setting) or UNTESTED (your reasoning). Cite papers with arXiv IDs where you can, and say when you know only the abstract. Do not invent numbers or citations; say "I don't know" instead.
6. Keep this only about the chat assistant; no "small card experiments" or "village model".
7. End with a plain-language summary of 6-10 sentences that a high-school senior can follow.
```

## 17. What should "sleep" do in a system with an explicit notebook?

```text
=== PROJECT CONTEXT (the same block starts every question in this batch) ===
You are advising on a research project through a plain chat. You cannot see the code, the files, or earlier chats, so everything you need is below. Where I give a number, it was measured; where I say "suggested" or "I think", it was not.

WHAT PREMONITION IS
Premonition is a personal assistant being built by a high-school senior (the owner), with AI coding agents doing the building and Claude directing and verifying. It starts knowing nothing. The user teaches it facts in plain English chat. It stores them in an explicit notebook, reasons over them (two-hop and beyond), says "I don't know" instead of guessing, and replies in fluent English. The end goal is a system on the owner's OWN architecture and OWN weights that beats an equal-size plain transformer (same data, same parameter count) on two-hop questions, reversal questions (asking the inverse of a taught fact), abstention on untaught facts, and multi-hop answers after a fact is edited (MQuAKE-style), plus a live demo for the owner's family.

HARD TARGETS
- 0 wrong notebook writes, certified below 1%. A wrong save is worse than a refusal or a clarifying question.
- Recall: at least 85% of plainly stated facts saved exactly; at most 12% of true facts held back.
- 99%+ grammatical replies, no simple mistakes, and no reply may claim something untrue about the notebook or about the assistant itself.
- Median turn time at most 800 ms.

THE PIPELINE TODAY (numbers are from sealed experiments)
1. EAR (English -> frames), BORROWED: SmolLM2-360M fine-tuned ("ear v4.1") to write one line per frame:
     TEACH | owner | relation | value      (e.g. TEACH | me | sister | Mira)
     ASK   | owner | relation              (e.g. ASK | Mira | dog)
     NONE
   A plain-code "speaker canonicaliser" maps I/me/my to the user ("me").
2. RULE BRAKE (plain code): drops frames with junk, e.g. a stored name containing a comma, or a value not found in the turn.
3. GATE, BORROWED: Qwen3.8-27B (4-bit, local on one RTX 5070 Ti 16 GB) is asked YES/NO "does this message explicitly assert this claim?" per frame; saved if P(YES) >= 0.25. The prompt wording and the 0.25 threshold were both chosen on a development set.
4. NOTEBOOK: rows owner | relation | value, e.g.  me | sister | Mira ;  Mira | dog | Pip. "X is the R of Y" is stored as "Y's R is X". Taught facts are never overwritten by inferences. Inverses ("Whose dog is Pip?") are computed at answer time. Relations come from a fixed relation table of 153 entries (each with aliases, an inverse, single- or multi-valued, and the kind of value) plus "other".
5. REASONER (ours): a question parser built as a stack of hand-written stages, each added by one past experiment (a reverse-question stage, a table stage, a yes/no reader, an n-hop chain stage, a decline-wording rewrite, ...), plus a 79,316-parameter learned lookup reasoner for multi-hop. On clean structured input it answers two-hop, reversal, abstention and single-edit multi-hop questions exactly (200/200 on an internal benchmark). The weak point is reading English, in and out.
6. MOUTH (ours, hand-made): a grammar layer that turns reply records into sentences. Grammar 1195/1205 = 99.2% under two independently checked graders; a blind judge preferred it 97 wins / 9 losses / 14 ties over the previous version. It still sometimes prints raw relation-table labels (e.g. "religion or worldview").
7. OWN-MODEL PLAN (not built yet): a ~33M-parameter own ear (8-layer width-512 bidirectional encoder, pretrained by fill-in-the-blank on simple-English stories and dialogues; heads that POINT at whole-word spans of the turn for owner and value; relation chosen from the table; a 9-way speech-act head; a fact-count head; 6 set-prediction fact slots) and an own mouth (a 28.85M decoder trained from scratch, "talker101"). Only a small plain-code "write compiler" may write to the notebook, from spans of the unchanged turn, all facts of a turn together or none. A round trip (fact -> sentence -> fact) is used for TRAINING only and is never permission to write, because it can agree with itself on a wrong fact.

MEASURED STATE OF EACH PART (fresh blind panels unless noted)
- Ear + gate (150 fresh turns): 9 scored wrong saves; 6 of those were answer-key mistakes (key said "pet", ear said "dog"), 3 were real: 2 chat typos stored inside a value (gate P(YES) 0.85 and 0.68) and 1 fact saved from a check-question with no "?" (0.37). Recall 77.9%. Threshold sweep: 19 wrong at threshold 0, 9 at 0.25, 7 at 0.7. Sentences naming several relatives: 4 of 16 facts found.
- On the development set used to choose the gate prompt and threshold, the gate let 13 of 103 wrong frames through. On 120 fresh turns from a new writer it let 63 of 65 through. So the gate barely works on fresh wording.
- A 3-question QA gate (ask "whose R is V?", "what is O's R?", "how is O related to V?" in separate prompts): 5 wrong out of 86 saved vs YES/NO 6 out of 100, but it held back 30% of true facts (bar 12%) and took 880 ms median (bar 800). Registered FAIL.
- Own-model write rules, oracle audit (a perfect reader, the planned strict write compiler): only 184 of 272 real facts (67.6%) are writable (bar 85%); 0 of 76 should-not-save facts writable.
- Casual typing (all lowercase, no apostrophes, typos) is read badly: a normaliser experiment failed and itself added 3 wrong saves.
- "our/we" is NOT the speaker (owner's ruling): the assistant must ask whose. An "ask whose" rule failed because the ear rarely hands it a group owner (14 of 30 asked, bar 27).
- Questions outside the parser's known shapes get "I didn't understand that": 40 of 51 yes/no questions were not understood.
- Replies: an honest "what can you do" list now makes 0 unsupported claims.

HOW WORK IS DONE (the rules)
- Every change is ONE sealed, pre-registered experiment: one change against a named base, predictions and pass marks fixed before the run, files sealed with SHA-256 hashes before the registered run.
- Pass/fail is decided on a blind TEST-ONLY panel written by a separate AI agent from a spec. Panels are never trained or tuned on, never quoted, and become "burned" once a builder sees items.
- A registered FAIL stays FAIL. A failed experiment gets exactly one diagnosis-driven follow-up.
- Director verifies every report: seal check, own recount from raw files, a held-out probe for every PASS.
- Fictional names only in all test and training data. No personal data. Unverified web text never goes into weights.
- The only human is the owner, a high-school senior who does not run commands; AI agents build, write panels and grade.

HARDWARE AND BUDGET
One RTX 5070 Ti (16 GB), sometimes offline; a busy shared Mac for CPU work; cloud GPU rentals within a $30 TOTAL budget. Downloading any new model needs the owner's explicit yes. A big model's GENERATED TEXT may be used as training data (stated honestly); borrowing its WEIGHTS for the final system is not allowed (borrowed parts are placeholders).

SCOPE
Only the chat assistant (ear, gate, notebook, reasoner, mouth). The owner has other projects ("small card experiments", "a village model"); do not mix them in.
=== END OF PROJECT CONTEXT ===

QUESTION 17 OF A BATCH (answer only this one): What should "sleep" do in a system with an explicit notebook?

THE PROBLEM
The design includes a SLEEP mode: automatic, mathematical consolidation between conversations (replay, rank-limited weight updates, "harden before gate"); the model never proposes rules or chooses what to store. But with an explicit notebook holding the facts, it is unclear what sleep should learn, and a review found the current sleep "merge" mark is a no-op (it cannot fail).

DETAIL
- Facts live in the notebook, not in weights; taught facts are never overwritten by inferences.
- Candidates for what sleep could change: the ear adapting to this user's typing and phrasing, new relation words, the mouth's word choice, compressing or indexing the notebook, precomputing inverses and chains.
- Every change to the ear risks new wrong saves; any change must pass the same wrong-save bar.
- Open question for the owner: may sleep learn relation words?

THE HARD QUESTION
Give a precise definition of what sleep should do here, what it must never do, and how to test that it helps without letting wrong saves in (for example, a user-specific ear adapter trained on turns the user later confirmed, with a frozen gate). Is continual adaptation safe at all under a "0 wrong saves" target, and what published work on continual learning, replay and forgetting applies? One sealed experiment with pass marks, including a mark that can actually fail.

WHAT I NEED BACK
1. Your diagnosis: what is really going on, and which of my explanations above is wrong or incomplete.
2. At most 4 ranked options, each with what it fixes, what it costs, and what it cannot fix.
3. The ONE experiment to run next: a single change against the current system, pass marks with exact numbers fixed in advance, the sample size and why, and the result that would prove your idea wrong. If it needs a later second step, name it but keep it separate.
4. The strongest objection to your own recommendation, and the rival you rejected.
5. Label every claim as SHOWN (published or measured), SUGGESTED (published, but in a different setting) or UNTESTED (your reasoning). Cite papers with arXiv IDs where you can, and say when you know only the abstract. Do not invent numbers or citations; say "I don't know" instead.
6. Keep this only about the chat assistant; no "small card experiments" or "village model".
7. End with a plain-language summary of 6-10 sentences that a high-school senior can follow.
```

## 18. A safe "thinking" mode that uses the web without polluting the notebook

```text
=== PROJECT CONTEXT (the same block starts every question in this batch) ===
You are advising on a research project through a plain chat. You cannot see the code, the files, or earlier chats, so everything you need is below. Where I give a number, it was measured; where I say "suggested" or "I think", it was not.

WHAT PREMONITION IS
Premonition is a personal assistant being built by a high-school senior (the owner), with AI coding agents doing the building and Claude directing and verifying. It starts knowing nothing. The user teaches it facts in plain English chat. It stores them in an explicit notebook, reasons over them (two-hop and beyond), says "I don't know" instead of guessing, and replies in fluent English. The end goal is a system on the owner's OWN architecture and OWN weights that beats an equal-size plain transformer (same data, same parameter count) on two-hop questions, reversal questions (asking the inverse of a taught fact), abstention on untaught facts, and multi-hop answers after a fact is edited (MQuAKE-style), plus a live demo for the owner's family.

HARD TARGETS
- 0 wrong notebook writes, certified below 1%. A wrong save is worse than a refusal or a clarifying question.
- Recall: at least 85% of plainly stated facts saved exactly; at most 12% of true facts held back.
- 99%+ grammatical replies, no simple mistakes, and no reply may claim something untrue about the notebook or about the assistant itself.
- Median turn time at most 800 ms.

THE PIPELINE TODAY (numbers are from sealed experiments)
1. EAR (English -> frames), BORROWED: SmolLM2-360M fine-tuned ("ear v4.1") to write one line per frame:
     TEACH | owner | relation | value      (e.g. TEACH | me | sister | Mira)
     ASK   | owner | relation              (e.g. ASK | Mira | dog)
     NONE
   A plain-code "speaker canonicaliser" maps I/me/my to the user ("me").
2. RULE BRAKE (plain code): drops frames with junk, e.g. a stored name containing a comma, or a value not found in the turn.
3. GATE, BORROWED: Qwen3.8-27B (4-bit, local on one RTX 5070 Ti 16 GB) is asked YES/NO "does this message explicitly assert this claim?" per frame; saved if P(YES) >= 0.25. The prompt wording and the 0.25 threshold were both chosen on a development set.
4. NOTEBOOK: rows owner | relation | value, e.g.  me | sister | Mira ;  Mira | dog | Pip. "X is the R of Y" is stored as "Y's R is X". Taught facts are never overwritten by inferences. Inverses ("Whose dog is Pip?") are computed at answer time. Relations come from a fixed relation table of 153 entries (each with aliases, an inverse, single- or multi-valued, and the kind of value) plus "other".
5. REASONER (ours): a question parser built as a stack of hand-written stages, each added by one past experiment (a reverse-question stage, a table stage, a yes/no reader, an n-hop chain stage, a decline-wording rewrite, ...), plus a 79,316-parameter learned lookup reasoner for multi-hop. On clean structured input it answers two-hop, reversal, abstention and single-edit multi-hop questions exactly (200/200 on an internal benchmark). The weak point is reading English, in and out.
6. MOUTH (ours, hand-made): a grammar layer that turns reply records into sentences. Grammar 1195/1205 = 99.2% under two independently checked graders; a blind judge preferred it 97 wins / 9 losses / 14 ties over the previous version. It still sometimes prints raw relation-table labels (e.g. "religion or worldview").
7. OWN-MODEL PLAN (not built yet): a ~33M-parameter own ear (8-layer width-512 bidirectional encoder, pretrained by fill-in-the-blank on simple-English stories and dialogues; heads that POINT at whole-word spans of the turn for owner and value; relation chosen from the table; a 9-way speech-act head; a fact-count head; 6 set-prediction fact slots) and an own mouth (a 28.85M decoder trained from scratch, "talker101"). Only a small plain-code "write compiler" may write to the notebook, from spans of the unchanged turn, all facts of a turn together or none. A round trip (fact -> sentence -> fact) is used for TRAINING only and is never permission to write, because it can agree with itself on a wrong fact.

MEASURED STATE OF EACH PART (fresh blind panels unless noted)
- Ear + gate (150 fresh turns): 9 scored wrong saves; 6 of those were answer-key mistakes (key said "pet", ear said "dog"), 3 were real: 2 chat typos stored inside a value (gate P(YES) 0.85 and 0.68) and 1 fact saved from a check-question with no "?" (0.37). Recall 77.9%. Threshold sweep: 19 wrong at threshold 0, 9 at 0.25, 7 at 0.7. Sentences naming several relatives: 4 of 16 facts found.
- On the development set used to choose the gate prompt and threshold, the gate let 13 of 103 wrong frames through. On 120 fresh turns from a new writer it let 63 of 65 through. So the gate barely works on fresh wording.
- A 3-question QA gate (ask "whose R is V?", "what is O's R?", "how is O related to V?" in separate prompts): 5 wrong out of 86 saved vs YES/NO 6 out of 100, but it held back 30% of true facts (bar 12%) and took 880 ms median (bar 800). Registered FAIL.
- Own-model write rules, oracle audit (a perfect reader, the planned strict write compiler): only 184 of 272 real facts (67.6%) are writable (bar 85%); 0 of 76 should-not-save facts writable.
- Casual typing (all lowercase, no apostrophes, typos) is read badly: a normaliser experiment failed and itself added 3 wrong saves.
- "our/we" is NOT the speaker (owner's ruling): the assistant must ask whose. An "ask whose" rule failed because the ear rarely hands it a group owner (14 of 30 asked, bar 27).
- Questions outside the parser's known shapes get "I didn't understand that": 40 of 51 yes/no questions were not understood.
- Replies: an honest "what can you do" list now makes 0 unsupported claims.

HOW WORK IS DONE (the rules)
- Every change is ONE sealed, pre-registered experiment: one change against a named base, predictions and pass marks fixed before the run, files sealed with SHA-256 hashes before the registered run.
- Pass/fail is decided on a blind TEST-ONLY panel written by a separate AI agent from a spec. Panels are never trained or tuned on, never quoted, and become "burned" once a builder sees items.
- A registered FAIL stays FAIL. A failed experiment gets exactly one diagnosis-driven follow-up.
- Director verifies every report: seal check, own recount from raw files, a held-out probe for every PASS.
- Fictional names only in all test and training data. No personal data. Unverified web text never goes into weights.
- The only human is the owner, a high-school senior who does not run commands; AI agents build, write panels and grade.

HARDWARE AND BUDGET
One RTX 5070 Ti (16 GB), sometimes offline; a busy shared Mac for CPU work; cloud GPU rentals within a $30 TOTAL budget. Downloading any new model needs the owner's explicit yes. A big model's GENERATED TEXT may be used as training data (stated honestly); borrowing its WEIGHTS for the final system is not allowed (borrowed parts are placeholders).

SCOPE
Only the chat assistant (ear, gate, notebook, reasoner, mouth). The owner has other projects ("small card experiments", "a village model"); do not mix them in.
=== END OF PROJECT CONTEXT ===

QUESTION 18 OF A BATCH (answer only this one): A safe "thinking" mode that uses the web without polluting the notebook

THE PROBLEM
The design includes a THINKING mode where the assistant may search the web to answer general questions. Rules: web results are quarantined; a fact needs two independent sites to be trusted; unverified web text never goes into weights; personal facts (about the user and people they know) are never web-searched. Nothing of this mode is built yet; "gives sources" scored 0 of 8 in a capability check.

THE HARD QUESTION
Design the quarantine: how web-derived facts are stored separately from taught facts, how answers mix them ("You told me X; the web says Y"), what "two independent sites" should mean in practice (mirrors and copies are common), how to stop a web fact about a common name from attaching to a person the user taught ("Ada" the user's sister vs a famous Ada), how to cite, and what must never happen. Keep it buildable by AI agents with plain code plus the existing small models. One sealed experiment with pass marks.

WHAT I NEED BACK
1. Your diagnosis: what is really going on, and which of my explanations above is wrong or incomplete.
2. At most 4 ranked options, each with what it fixes, what it costs, and what it cannot fix.
3. The ONE experiment to run next: a single change against the current system, pass marks with exact numbers fixed in advance, the sample size and why, and the result that would prove your idea wrong. If it needs a later second step, name it but keep it separate.
4. The strongest objection to your own recommendation, and the rival you rejected.
5. Label every claim as SHOWN (published or measured), SUGGESTED (published, but in a different setting) or UNTESTED (your reasoning). Cite papers with arXiv IDs where you can, and say when you know only the abstract. Do not invent numbers or citations; say "I don't know" instead.
6. Keep this only about the chat assistant; no "small card experiments" or "village model".
7. End with a plain-language summary of 6-10 sentences that a high-school senior can follow.
```
