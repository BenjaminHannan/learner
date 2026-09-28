# vread2 pass marks: does crediting any copy of the owner's name fix the vector reader's low backref confidence?

Vector-reader thread. Written 2026-09-28T02:14:42Z, before any training. The task came from Ben's overnight prompt
(reviews/chat-prompt-vread-name-credit-2026-09-28.md), which follows Astra's read-only diagnosis of the vread backref
gap. This is a practice test on fresh Luna chats. Nothing joins the build without Ben's yes on the result. This test
is about the vector reader only. It is kept apart from the small card experiments and the village model.

## The one change
- **Arm A** is vread's vector reader, retrained as it was run. `scripts/claude_vread2_model.py` calls
  `scripts/claude_vread_model.py` unchanged:
  - VReader, card_loss, decode, all_right, targets and the frozen 1B encoder;
  - layer 12, rounds 0-6 free and 1-3 graded, fp32 with TF32 off, AdamW lr 3e-4, batch 32, 4,000 steps;
  - the same 11,217 train rows (vread's sealed chunk 1-10 pack; `claude_vread_data.py unpack` checks every sha256).

  Shown on CPU before this commit: after 3 steps (batch 4, seed 327), arm A's weights are bit-identical to those of
  `claude_vread_model.py train`.
- **Arm B** is the same reader with the owner pointer credited for any copy of the right name:
  - **Training loss.** Owner start = −log of the total start probability over every copy of the labelled owner
    name. Owner end = −log of the total end probability over those copies' ends.
  - **Stop target.** The stop head learns "every card cell is exactly right". For B, an owner counts as right when
    its (start, end) is any copy. This is the same credit applied where the owner pointer is graded. Without it the
    stop target would call B's own correct choices wrong, which would change B's number of rounds. Declared now.
  - **Read time.** The owner start and end probabilities are the totals over the copies whose text equals the
    chosen span. The chosen span always counts, even when it is not a whole-word copy.
  - Nothing else differs.
- **A copy of a name** is every whole-word, exact-case occurrence of the name in the turn, the previous reply or the
  earlier-turn lines of the prompt, found with the label search's own pattern (`claude_vread_data.occurrences`),
  whose tokens decode to exactly the name (`claude_vread2_data.copies`). The label's pointer is the newest copy and is
  always among them.
  - Shown before this commit: 6,594 of 6,594 named-owner train cards have their label pointer among their copies,
    and every copy decodes to the owner text.
  - 3,936 of those 6,594 cards have 2 or more copies.
- **Two seeds.** Each seed trains one A and one B from the same initial weights, on the same batches and round
  counts, sharing the 1B forward pass:
  - seed 327 is vread's own (initial weights 327, batches 328);
  - seed 331 is the second.

  That gives 4 checkpoints: A-s327, B-s327, A-s331, B-s331. Every card keeps all 7 probabilities (exist decision,
  state, relation, owner start, owner end, value start, value end). Its conf is the lowest of the 7, with B's copy
  totals for B.
- **Checkpoints.** All 4 are copied back and their sha256 checked against the rental's manifest before the
  instance is destroyed.
- **Save bars.** Each checkpoint gets its own save bar from vread's calibration slice (1,230 rows), using
  `claude_vread_score.choose_bar` unchanged: the lowest grid value with wrong saves at most 0.5% of saves (main
  rule). `bar.json` is committed before any fresh read is opened.

## Fresh data (`data/`, built by `scripts/claude_vread2_data.py build`)
- **How it was built.** All kept rows of Luna chunks 11, 12 and 13 from origin/builder-outbox
  (`artifacts/claude-lis320-20260926/full-luna/chunkK/raw.new.jsonl.gz`). The unchanged vread data code ran its
  clean, seeds and code checks over chunks 1-13 joined in chunk order. Only the chunk list is set.
- **Checks.**
  - Chunks 1-10 give back exactly vread's 13,891 kept rows (same ids).
  - 0 of 948 fresh dialogs are in vread's pack.
  - 0 fresh rows were dropped for an unmapped span.
- **Size.** 6,483 rows and 6,774 cards. Every row is Luna-worded with a code label, and none is Claude-written.
- **Use.** Never trained on. Each checkpoint reads the fresh set once, and it is scored once. No blind panel
  (readpanel320 or any other) is opened.
- **Gold-only counts (label counts, no read):**
  - 538 backref cards, all current;
  - by how often the owner's name appears: 237 once, 151 twice and 150 three or more times.

## Definitions (`scripts/claude_vread2_score.py`)
- **Matched card.** In a backref row, each emitted card (any confidence) takes the first unused gold card with the
  same relation and state. It prefers a gold card equal in all four fields. This is how the pointer check in
  `claude_vread_score.score` pairs cards.
- **Right-owner card.** A matched card whose owner equals the gold owner (lower-cased).
- **Low.** Card conf < 0.97.
- **Bins.** Each card goes in the bin of its gold owner's number of copies: 1, 2 or 3+. Cards whose gold owner is
  "me" are left out.
- **Below-0.97 share of a bin.** Low right-owner cards ÷ right-owner cards in that bin, as an exact percent (no
  rounding). A bin with no right-owner cards has no share, and any mark that needs it is not met.
- **Backref right saves and backref wrong saves at 0.97.** `claude_vread_score.score` on the backref rows under the
  history rule at bar 0.97: `family backref:right` and `wrong_saves`.
- **Wrong turns.** `claude_vread_score.score` on the whole fresh set, main rule, at the checkpoint's own bar.

## Marks
**Validity.** The result is INCONCLUSIVE unless all of these hold:
- at least 200 backref cards, and at least 60 whose owner name appears 3+ times (gold counts above: 538 and 150,
  met);
- in both seeds, arm A repeats the dev pattern: A's below-0.97 share for 3+ copies is at least 25 points above its
  share for 1 copy.

**Pass.** B against A at the same seed. All three marks must hold in both seeds:

| Mark | Bar |
|---|---|
| M1 | B's below-0.97 share for 3+ copies ≤ B's share for 1 copy + 10 points |
| M2 | B's backref right saves at 0.97 (history rule) ≥ A's + 5% of the backref cards (+26.9 with 538 cards) |
| M3 | B's wrong turns (whole fresh set, main rule, own bar) ≤ A's + 2, AND B's backref wrong saves at 0.97 ≤ A's + 2 |

**Proved wrong.** A repeats the pattern (validity holds), but B's below-0.97 share for 3+ copies stays within 10
points of A's (|B − A| ≤ 10) in both seeds. Then splitting probability across copies of a name is not the cause.

**Verdict.** INCONCLUSIVE if validity fails; else PASS if M1-M3 hold in both seeds; else "FAIL (proved wrong)" if
the proved-wrong condition holds; else FAIL.

## Report only (no bar)
- **Wrong person.** Matched backref cards whose owner is another name, not "me". Reported:
  - over all matched backref cards;
  - over those whose prompt also names a rival person: a different person name from the dialog's gold cards (non-me
    owners, and values of person relations) with a whole-word copy in the prompt;
  - how many of the wrong owners start after the gold name's newest copy.

  This change should not move it.
- **Which probability is lowest.** Which of the 7 probabilities is lowest on low cards:
  - on right-owner backref cards;
  - on every card of the fresh set.
- **Other counts:** right and wrong saves (main rule, own bar), backref counts at the own bar, each checkpoint's
  bar, mean rounds, and the training logs.

## Definition check on vread's old dev reads (disclosed; dev is already used, and this changes no mark)
Before this commit, the bins above were applied to vread's dev reads (`run/out/vec_dev_reads.jsonl`) to check that
they measure what the diagnosis measured. The vector reader's right-owner backref cards below 0.97 were:
- 19 of 30 for names with 3+ copies (the diagnosis's figure);
- 11 of 40 for 2 copies;
- 8 of 49 for 1 copy.

Its wrong-person count with a rival named was 16, also the diagnosis's figure.

## Order
1. This commit: data, model and scoring code, and marks. The rental control script is not in this commit (see
   below).
2. One rental job, capped at $4, on an RTX 4090 like vread's. The job:
   - runs the checks (gradient, pointer and copy checks);
   - trains the two seeds side by side;
   - has each checkpoint read the calibration slice and the fresh set.
3. Copy-back with sha256 checks of every checkpoint and result file. Then destroy the instance, or stop it if the
   check fails.
4. `bar.json` from the calibration reads, committed.
5. The fresh set is scored once, then `verdict`.
6. A separate subagent recounts blind, from the score files and this file only.
