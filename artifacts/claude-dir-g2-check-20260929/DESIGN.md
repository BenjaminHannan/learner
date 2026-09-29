# dir-g2 design: train the check head to tell right from wrong (G builder thread, 2026-09-29)

Labels: SHOWN = read from a file. SUGGESTED = reasoned. UNTESTED = nobody has run it. Nothing of G2 has run; no code exists yet. Marks: PASSMARKS.md (written first).
Parent: test G (`artifacts/claude-dir-g-search-20260928/`, result `artifacts/claude-dir-g-build-20260928/RESULT.md`): "candidates fine, check not".

## 1. Plain summary
G's four tries are good (each stream 11 to 19 of 300, against 4 for one stream), and an oracle that picks the right try gets 42 and 33. The net's own "is this right?" head picks only 30 and 24. This is the "blurt many tries, filter with a checker" idea from Ben's creative model: the tries exist, so train the checker. One change: retrain only the check head, with labels from an exact code checker on the net's own tries, leaving the reasoner frozen.

## 2. What is known (SHOWN, G RESULT.md, runs/g-s13, g-s14)
S_pick 30, 24; S_rand mean 16.25, 13.0; S_any (4 streams at own stop) 42, 33; one stream with an any-of-48-rounds oracle 37, 35; any stream any round 90, 94; practice exactness per stream 0.19 to 0.31.
The head that picked: `Net.halt = Linear(512, 1)` on `ln_out(h).mean(1)` (`claude_rsn358a_run.py:83,107`), trained with target "this round's answer equals the stored answer" (`:298`). With a median of 22 valid answers per hand (DIAGNOSIS.md, SHOWN) this label calls many right answers wrong (SUGGESTED as one reason it picks badly).

## 3. The change (one)
Retrain the halt head only. The net (all weights, the 4 start vectors) is frozen, sha256 unchanged.
- Head: same shape as the sealed head, a fresh Linear(512, 1) on the same input (the mean over cells of ln_out(state)). Nothing bigger (a bigger head is a second change).
- Data: the net's own tries. Practice items are run through all 4 streams for 48 rounds; for each (item, stream) 6 rounds are drawn at random; the example is (pooled state at that round, label). Label = 1 if the exact code checker (`claude_rsn358a_envs.check`, any valid answer counts) accepts the answer decoded from that state, else 0. Items: 24,000 wide-pool numbers4 (hand, target) pairs, 6,000 sums4, 6,000 grids5 (fresh generators, own seeds), plus a separate 3,000-pair numbers4 dev set (not used for head training). All kinds stay in so the head is never told the kind; the checker is used only to make training labels, never at test.
- Test-time use (the pick): the sealed stop rule per stream is unchanged (it uses the OLD head, so every net's four answers at their stops are exactly G's); the new head's probability at each stream's stop picks among the 4 (highest wins, ties lowest index). Only the pick changes, so S_any and S_rand are identical to G's by construction and the comparison is paired.
- Reported only (not judged): P192, the new head's argmax over all 4 streams x 48 rounds (what a checker could unlock, ceiling 90 and 94); and "full swap" (new head also drives the stop rule).

## 4. Deviation from DESIGN.md section 6 (stated)
G's section 6 wrote "corruptions of stored answers (swap or replace answer tokens)". The halt head reads the loop's state, not an answer string, so a corrupted string cannot be shown to it without writing answers back into the input (a verifier mode: new input format, bigger change, not done here). What the head must reject at test are the net's own wrong tries, so those are the negatives (on-distribution, code-labelled, no text Claude wrote). Corrupted-answer verifier mode stays as the next fallback (own test).

## 5. Why it might not work (SUGGESTED)
- A linear read of a mean-pooled state may be unable to tell 17 x 3 - 27 from a near miss: judging needs arithmetic. Then the head learns cues (stream, round, confidence) and the pick stays near S_rand. The shuffled-label control and the dev AUC separate "head learned something" from "cue".
- The head trains on practice items (net right about 25% of the time) and is applied to held-out hands (net right about 5 to 10%): a shift. The pick only needs the ranking across 4 streams of one item, which shifts less (SUGGESTED, UNTESTED).
- The gain is capped at S_any: 12 more on seed 13, 9 more on seed 14 (SHOWN arithmetic).

## 6. Cost and where it runs (SUGGESTED, from timings in RUN-NOTE.md)
G nets took 97 minutes each for about 1.6 billion row-rounds (60,000 steps x 1,024 rows x about 8.5 rounds x 3 for backward); features for G2 are about 6 million forward row-rounds (SUGGESTED about 0.4% of that). GPU: minutes. CPU: about 1 to 2 hours on a 10-core Mac (UNTESTED, from this box's 16.7 s per 1,024-row step). Weights: `final.pt` of both nets are on Ben's Mac (`~/premonition-models/dirg/`) and BensPC, not in git (25.8 MB each).

## 7. What to build (new files, prefix claude_dir_g2_)
`scripts/claude_dir_g2_run.py` (imports the G runner and the sealed chain): `feats` (train and dev features, no test file), `train-head --seed S [--shuffle]`, `eval` (test items once per head file: S_pick_new, S_rand, S_any, P192, full swap, old-pick recompute for the reproduction check), `selftest` (CPU: the old head's recomputed pick equals `stream_rounds`-based pick on fixed items; label function; shuffle), `queue-dir-g2-*.md`.
