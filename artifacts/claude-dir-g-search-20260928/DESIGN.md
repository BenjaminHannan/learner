# dir-g design: search inside the thought (helper G, 2026-09-28)

Labels: SHOWN = read from code or files here. SUGGESTED = reasoned. UNTESTED = nobody has run it. Nothing was run; no code was written.
Marks: PASSMARKS.md (written first). Prior work: SURVEY.md. Ben's rules: reasoner learned, never told the puzzle kind, one change per test.

## 1. Plain summary
The loop thinks in rounds but every round refines one line of thought, and it settles. Idea: start the loop from 4 different learned starting states (four "tries"), train it so the tries differ, and let the net's own "is this right?" head (the halt head it already has) choose. One change, about 2,000 extra weights, no puzzle-specific code. It is a fair test of search only if the check head can tell right from wrong on hands it never saw; the test reads that separately from whether the tries are any good.

## 2. Where it sits (SHOWN from code)
- Loop state: `h` of shape [batch, cells, d]; `Net.loop_train` starts `h = zeros_like(e)`, runs `total-k` no-grad rounds then `k` graded rounds; each graded round gives token logits and a halt logit (`scripts/claude_rsn358a_run.py:116-141`).
- Loss: cross-entropy on the stored answer at each graded round, mean, plus 0.5 x halt BCE where the halt target is "this round's answer equals the stored answer" (`:176-181`, `:291-301`). Test: up to 48 rounds, stop at the first round with halt p > 0.5, else the most confident round (`:228-250`).
- Diagnosis (SHOWN): extra rounds do not help numbers4 (0 to 3 of 300 at every round count), the answer changes over rounds without getting nearer to a valid one (DIAGNOSIS.md section 1, "Loop thinking time"). So "more rounds" is not search; different starts is the smallest way to get different lines.

## 3. The change (one)
1. K = 4 learned start vectors s_1..s_4, each [d], added as the initial state: `h_k = s_k` broadcast over cells (instead of zeros). Init: small random, different per stream. All streams share every other weight. Extra weights: 4 x d (about 2,000 at d = 512), under 0.05% of a 6.3 M net.
2. Training: run the K streams as K copies of the batch through the same rounds (same `total`, `k` draw for all). For each item, take the stream with the lowest mean graded-round CE (selection detached); the token loss is that stream's CE at weight 1 plus the other three at weight 0.05 each (winner-take-all with a small leak so no stream dies). Halt BCE is applied to all K streams (each against its own exactness), same 0.5 weight, averaged.
3. Test: each stream stops by the sealed rule; the answer is the stream whose halt probability at its stop is highest.
Why these are one change, not three: the start vectors alone would collapse to one answer without the winner-take-all loss, and picking is meaningless without both; together they are the smallest thing that can be called "try several, keep the one that checks out". Read-only splits (no extra training) separate them: S_rand, S_any, S_pick in PASSMARKS.md.
Kind-blind (SHOWN by construction): the env embedding stays fixed at 0 as in 358u; no stream sees any kind label; the pick uses only the net's own halt output; no checker or solver at test time.
K = 1 with s_1 = 0 must reproduce the sealed loop exactly (V2 selftest).

## 4. Why I expect it to be hard (SUGGESTED)
- Winner-take-all on a lookup task: each stream can memorise the same 1,062 (or 36,782) items and the streams agree on practice, so held-out diversity may come from nothing but noise. V4 (D >= 2.0 on held-out) catches "streams did not diverge".
- The halt head's label is "equals the stored answer", so a valid alternative answer is labelled "wrong". With median 22 valid answers per hand (DIAGNOSIS.md, cause 3) the head learns to recognise the stored style, not validity. This makes the pick weaker than it could be. H2's fallback (any-valid targets and halt) fixes exactly that, which is why G should run on top of it if it was read first (PASSMARKS.md Entry).
- The head must evaluate an arithmetic expression to judge a candidate. Nothing else in training teaches that. It is easier than producing one (checking is easier than finding, SUGGESTED) but untested for this net.

## 5. Decomposition the run gives for free (no extra training)
From the same trained nets: S_any (oracle) vs S_pick vs S_rand separates "candidates" from "check". Also reported: practice exactness, D, and the old 48-round any-round count as the more-thinking-time control (SHOWN in `evaluate`: `right_at_any_round`). Same-compute control: the one-stream baseline given its own 48 rounds is already the sealed test. Training compute is about 4x per step (UNTESTED estimate): H2 costs about $0.5 and 70 min for 4 nets on one RTX 5090 (DIAGNOSIS.md), so G is roughly 4 to 5 hours and $2 to $2.5 for the same 4 nets, under the $4 job cap. Check with a 200-step timing run first. The Director decides on release.

## 6. Fallbacks (not bundled, each its own test with its own marks)
- Check-head training: if the marks give "candidates fine, check not", train the halt head on code-made corruptions of stored answers (swap or replace answer tokens; label by exact match). Code-made data, kind-blind.
- Stream of Search style: solver-written search traces as targets (SURVEY.md #2). Large change, kind-specific data, last resort.
- Expert iteration: sample K tries, keep the ones the exact checker accepts, train on them. Needs a sampler; larger.

## 7. What to build (for the builder, prefix claude_dir_g_, new files only)
- `claude_dir_g_run.py` (torch): import sealed 358u run module, subclass `Net` with `starts = Parameter(K, d)`, override `loop_train`, `loop_rounds`; a new training step with the loss in section 3; commands `train`, `eval` (adds S_pick, S_rand, S_any, D), `selftest` (V2, CPU, K=1 equality), `timing`.
- `claude_dir_g_floor.py` (pure python): F4 from the diagnosis's strategies A to C, reuse `claude_numbers_diag_answers.py`.
- `queue-g-a.md`: 4 nets, STATUS: HELD, same format as the H2 queue jobs, first step checks sha256 of PASSMARKS.md and scripts. GPU: BensPC or vast (cap $4), Director's call.
Not done here: none of these exist yet, and torch is not on this box.

## 8. Risks and what remains
- Nothing has run; every performance statement above is a guess.
- Literature notes are partly RECALLED (SURVEY.md labels each row).
- Ordering risk: G is only well posed after H2 (and probably its any-valid fallback) is read. Entry rule in PASSMARKS.md.
- Not decided by me, sent to the Director as options: run G before the any-valid fallback (cheaper, weaker head label) or after (my recommendation).
