# dir-s5 PASSMARKS: can the plain 1.2B talker read the right notes? (sealed before any run; written 2026-09-29 02:12 UTC)

Test 5 of the lead sweep (design/research/lead-sweep-2026-09-29/SYNTHESIS.md section 3, item 5). Inference only, no training.
Reader = LFM2.5-1.2B-Instruct @0f604ada, plain, greedy. Kept apart from the maze cards and the village model: no maze number is claimed or compared.

## The data guard (proved, not promised)
- Dev slice: 100 questions of LongMemEval-S (HF xiaowu0162/longmemeval-cleaned, `longmemeval_s_cleaned.json`, sha256 d6f21ea9...a3c678, checked against HF's own hash). Picked by `scripts/claude_dir_s5_slice.py` by id and type only (no text read): 23 multi-session, 23 temporal, 14 knowledge-update, 13 single-session-user, 11 assistant, 10 preference, plus 6 abstention ids taken first from all 30. Result by type: temporal 26, multi 25, KU 15, user 13, assistant 11, preference 10 (six of those are the abstention ids).
- `dev100.ids.txt` (ids + type, no text) hash 00bb9f9e...efe2 in `SEAL-slice.sha256.txt`. `check` recomputes it from the data.
- Disjoint from earlier dev slices: shown. No earlier LongMemEval slice exists: every earlier file (bm-390/391/397t/398*, y1r, lis319, rd378/371) says LongMemEval was "untouched"; and a whole-word search of the whole repo for all 100 ids finds no hit outside this folder.
- The final set = the other 400 questions (id-list hash 9b3849ed...b532eb3f35, ids not stored). Nothing here keeps, reads or scores them; the job loads all 500 from the file only to pick out the 100 by id. Suggested (Ben decides): report the final on the 400, with these 100 removed from headline numbers.
- Question, answer and reply text stay in the job's scratch folder on BensPC, not in git. Only counts and per-question 0/1 flags are pushed. Nobody reads per-question text after this seal.

## Arms (one change: what the reader is given; same model, system prompt, greedy decoding)
- closed: no material.  oracle: the evidence sessions only, whole.  plain: the latest whole-haystack text that fits 24,000 tokens (the plain long-context twin).
- raw10: the top-10 rounds (a round = one user turn + the next assistant turn) by the stack's frozen MiniLM-L6-v2 cosine to the question, 128 word pieces, shown in time order with the chat date.
- notes10: the SAME 10 rounds, each turned into one short fact note (at most 30 words) by the same 1.2B, which never sees the question. No Claude-written text anywhere; note writing is the talker's own work.
- Not run here (untested): a stronger embedder (M1), an "I don't know" gate (M3). Retriever is fixed at MiniLM so notes vs raw is the only difference.

## Two readings of every answer; the verdict needs both
- AUTO: normalised containment (gold in reply, or all content words when the gold has 5 or fewer) and, for the 6 abstention ids, an "I don't know"-type phrase. Preference questions (10) and gold answers longer than 12 words (5) cannot be scored this way: AUTO has n = 85 and its bars are scaled by 85/100 and rounded up.
- JUDGE: the same 1.2B as a yes/no judge with the LongMemEval judge prompts (temporal off-by-one, knowledge-update, preference rubric, abstention). Self-judging is a bias, so it is gated: on 100 questions, the gold answer given as the reply must be judged "yes" on at least 90, and another question's gold (same type) given as the reply must be judged "yes" on at most 10. If the gate fails, JUDGE is dropped and the verdict is labelled AUTO-only, low confidence (never claimed as a pass).
- A pass/wrong call stands only if both readings agree; otherwise it is "not shown".

## Marks (n = 100 for JUDGE; AUTO scaled as above)
PASS (both must hold): 
- P1 oracle correct on at least 50 of 100;
- P2 notes10 minus raw10 at least +10 of 100 correct AND exact paired McNemar p < 0.05 on the same 100.
WRONG:
- W1 oracle under 30 of 100. Then the reader is the limit: item 6 needs a bigger or trained reader before any retriever work.
- W2 raw10 correct count above oracle correct count (brief's rule: the reader likes distractors or the data is off; recheck, no claim).
- Control: closed-book above 10 of 100 means the questions leak or the scorer is too loose: verdict void.
Anything else (oracle 30-49, or P1 without P2, or the readings disagree): "not shown", with the counts reported. A decisive answer = PASS or W1.
What it decides: whether item 6 is a retriever job or a reader job.

## MARKS SELF-CHECK (thread-helper-common.md), one line each
1. Bars above noise: n = 100 gives a binomial sd of about 5 points at 50% (computed, not measured). The oracle bar of 50 is a threshold, not a difference; the +10 bar is about 2 sd and is paired with McNemar. Run-to-run noise: none from sampling (greedy, retrieval fixed); a rerun of 10 oracle answers must repeat exactly and the count is reported. Judge noise is what the calibration gate measures.
2. "Every seed" reading: there are no random seeds (all steps deterministic), so the analogue is "both readings": rejection (W1) and pass need AUTO and JUDGE to agree, else "not shown".
3. Fair comparator: notes10 is compared with raw10 over the identical 10 rounds (the higher of the loops that apply; plain and oracle are reported beside them, not used as the comparator).
4. A row a plain net cannot pass: closed-book (same model, no notes) must stay at or under 10 of 100; plain long-context twin is reported beside. A model with no access to the right material cannot reach oracle 50. Memorising the questions is checked by the closed-book row, since the model was not trained on them.
5. F_few (k = 1..64): not applicable. This is a reader test with no few-example adaptation; I do not claim any F_eq or F_few number.
6. Sleep gates: not applicable (no sleep draws).

## Cost and place
Under 1 hour on BensPC's 5070 Ti (estimate; not measured): retrieval about 25,000 short texts, about 1,000 notes, 500 answers (plain up to 24,000 tokens each), about 700 judge calls. $0, no rental, no downloads except the dataset file (277 MB, dataset not a model, sha-pinned; exit 75 if the PC cannot reach HuggingFace).
Untested: `run` needs torch and the model, which the box that wrote it does not have. The job runs a 3-question smoke first.
