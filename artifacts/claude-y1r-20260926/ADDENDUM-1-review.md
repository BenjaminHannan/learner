# y1r addendum 1: the Thread manager's pre-run review (Answering-from-memory thread, 2026-09-26 19:48 UTC, before any real run; sealed in SEAL-y1r-add1.sha256.txt)

The Thread manager reviewed PLAN.md (8a900b659) at 19:39 UTC and asked for three additions. The marks, predictions
and the one change do not move.

1. **No choice is made on LoCoMo.** The recipe is fixed: 2 epochs, the final weights, no checkpoint or epoch
   selection. If any choice is ever needed, it is made on the GLM practice-dev pairs (items_dev), never on LoCoMo.
   LoCoMo is only scored.
2. **One run, on what the gate passes.** y1r runs once, after y1t's top-up (ADDENDUM-3) and the data gate
   (GATE-data.md with GATE-ADDENDUM-1), on exactly the filtered items_train and items_dev the gate result names.
   RESULTS reports the pair count. There is no second run to keep the better one.
3. **Control row, report only: shuffled pairs.**
   - scripts/claude_y1r_control.py shuffle (seed 4037) moves every query to a pair from another chat; positives
     and negatives stay where they are.
   - The same MiniLM is trained with the same sealed command and recipe on those pairs (arm C), and scored with
     the same LoCoMo run.
   - If arm C gains about as much as arm R over arm U, the gain is adaptation to the text format, not learning
     what a question points to. RESULTS says so in words; the stage-1 mark is still R minus U.

Also agreed with Benchmarks (bm-398u, 19:28 UTC), report only: stage 1 also writes the finding counts (any and all
evidence in the top 20) for arms U, R and C on rd-378L's 759 questions (LoCoMo conversations 0-4, categories 1-4,
ranked_turns.jsonl order), so y1r sits beside bm-398u's reranker. y1r's k stays 20: it changes the ranking, not a
rerank of store B's top 20. Stage 2's decision stays on bm-398d's 297 sample, as sealed.

Order of the run: sha256sum -c SEAL-y1r and SEAL-y1r-add1; selftests; pairs (train, dev); control shuffle; train R;
train C; locomo U, R, C in one session.
