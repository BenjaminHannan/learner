# 8b handoff (2026-10-08, 12:55 PM ET)

For whoever finishes this: Ben, a local Claude Code session, or the roadmap thread. Branch `claude/nice-lamport-al1gwo`, PR
BenjaminHannan/learner#52. Read `design/8b-gemma-growth-2026-10-08.md` (sections 1-7) first. The marks there were fixed before any run.
Do not change them.

## The task (Ben's brief)

B2 (looped thinker) doesn't get better from 3M to 10M (+0.49 pooled-5) while PT gains +3.77 and the plain LLM +15.77. Diagnose why with
cheap ablations, propose at most 3 fixes built on an EmbeddingGemma input, run the cheapest decisive test, and say whether the 30M rung
(~$42) is worth it. Hard rules: the Gemma embedder is the main input; our thinker stays and must drive; everything inside the model
is learned; no truncated targets; data = TEACH rows + FineWeb-Edu only; marks before runs; >= 6 paired seeds for a claim; count
borrowed parts; ask Ben before spending over ~$40 in total. Times in ET.

## What is done

- **Diagnosis** (section 1, from saved 8a results; `g8b/analysis/free_ablations.txt`). B2's 3M and 10M training-loss curves are the
  same curve from step 1k on, so the extra size never reaches the loss. The calculator families are saturated. On the other 20
  families (62%, room to grow) B2 gains +0.57, PT +3.14. There the talker answers from the shallow letter reader: 2 rounds are
  enough, and removing the word-content keys collapses those families. The rule families have no program targets (their worked
  steps are labels), so their numbers come from the parallel GEN letters.
- **Bug** (addendum B): `caps.apply()` never patched the lazily imported Ledger. **Every 8a B2 run, and 8a-G's EGE arm, used 9
  register tokens instead of 36 and GEN targets cut to 8 letters.** Plain arms and scored dev rows are unaffected. Fixed in
  `g8b/overlay/custom_io/g8a/caps.py`. **Tell the roadmap thread** (8a-G, `claude/project-thread-yha868`); its build branch
  `claude/project-thread-f1to6a` still has the bug at 612f5c5b0.
- **Fixes:** (1) EGE = Gemma before the letter window (8a-G runs it with the bug; here **EGE36**, fixed); (2) Gemma feeds only the
  thinker (EGK route; unstable before, not run); (3) **EGA36** = EGE36 + `gen_ar`, the thinker writes GEN answers letter by letter with
  its own blocks. `g8b/tests/test_gen_ar.py` passes 8/8.
- **Screen running:** EGE36 and EGA36, 3M and 10M, seeds 400/401, 8 RTX 5090 boxes. Go / stop rules in addendum B (section 6).

## Boxes (`g8b/boxes.json`; live = no `status` field)

| box | arm | rung | seed | started (ET) | expected done (ET, rough) |
|---|---|---|---|---|---|
| 54872786 | EGA36 | 3M | 400 | 12:09 PM | 2:30-4 PM |
| 54872791 | EGA36 | 3M | 401 | 12:05 PM | 2:30-4 PM |
| 54880790 | EGE36 | 3M | 400 | 12:51 PM | 3:30-5 PM |
| 54872795 | EGE36 | 3M | 401 | 12:11 PM | 2:30-4 PM |
| 54878149 | EGA36 | 10M | 400 | 12:41 PM | 6-10 PM (cap 9.5 h from 12:30) |
| 54878150 | EGA36 | 10M | 401 | 12:43 PM | 6-10 PM |
| 54878158 | EGE36 | 10M | 400 | ~12:50 PM | 6-10 PM |
| 54878159 | EGE36 | 10M | 401 | 12:46 PM | 6-10 PM |

The 10M arms use `--accum B2=2` (44 thinker tokens did not fit 32 GB; addendum C). Training output only appears in the log when a run
ends. Spend so far is about $6, expected total about $26.

## How to finish

Follow "If this session stops" in `g8b/README.md`: tail, collect, **destroy every box once collected** (they bill until destroyed),
then the readout. Off the cloud session, set `VAST_API_KEY` in your environment first. `g8b/vast8b.py` sends it itself; never put it
in a file or chat. A ~900-byte `8a-...-B2` block means the run died; collect it and read its `stdout.events.txt` (the out-of-memory
case looked like that).

Then:
1. `ARM=EGE36 python g8b/analysis/screen_readout.py results/8b/EGE36 <8a-ladder>` and
   `python g8b/analysis/screen_readout.py results/8b/EGA36 <8a-ladder> --ctl results/8b/EGE36`. Add 8a-G's results dir as the third
   argument if they have landed (it switches the yardstick to G-PT, the fair one).
2. Write `results/8b/README.md`: each arm's gain, the go / stop verdict, guards, the training-loss gap, the rule-family changes, and
   sizes with EmbeddingGemma counted. Label every claim shown / suggested / untested. Add a plain-language summary for Ben.
3. Answer the brief: did either fix beat the plain model's gain (2-seed screen; Ben's mark needs 6 seeds)? 30M: recommend it only
   if an arm passes against PT on 6 seeds (section 3); otherwise no.
4. If an arm says **go**: seeds 402-405 at both rungs plus LLM-10M seed 404 (missing in 8a), about $25-30. Check the total against
   Ben's $40 line and ask him first.
5. Commit to this branch and update the PR.

## Prompt for a local Claude Code session (run it in the learner checkout)

"Check out `claude/nice-lamport-al1gwo`, read `g8b/HANDOFF.md` and `design/8b-gemma-growth-2026-10-08.md`, and finish the 8b screen as
the handoff says. My Vast key is in VAST_API_KEY (don't print it). Don't change any mark; destroy each box after collecting it; ask
me before any spend that would take the 8b total over $40."

## UPDATE 2:35 PM ET: all eight screen runs were killed by Vast (credit ran out)

At 2:27 PM ET every box showed `exited`, Vast credit was 0 and the balance -$0.71 (`balance_threshold` -0.01). Credit was $3.68 at 12:55 PM
with about 13 boxes up (my 8 at ~$0.6/h plus the roadmap thread's 8a-G boxes), so it ran out within roughly an hour. Vast stopped the roadmap
thread's boxes too (g8G-3M-s400/s401, g8G-10M-s400/s401, cio-t1c2). Nothing from the screen was saved: `train.py` writes a checkpoint only
at the end and the result only after the run, so a restart means step 0. The table above is void; every box is `exited` and not yet destroyed.
To redo the screen: top up Vast credit (the account's autobill did not trigger), then relaunch the eight jobs from `g8b/boxes.json`
with the same commit and env (3M: MAXH 6; 10M: ACCUM=2, MAXH 9.5), about $26. **Check `credit` before launching and again every hour.**
