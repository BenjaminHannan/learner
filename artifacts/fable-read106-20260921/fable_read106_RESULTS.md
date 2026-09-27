# RESULTS — Exp 106: first reading-ladder score (TEST, inference only)

**Result: the safety bar FAILED in 4 of 9 ears/seeds, and no ear read a single
fact correctly.** Rung-1 tape wrote 1–2 wrong triples per seed (all 3 seeds
FAIL); bigru wrote 1 wrong triple in seed 4302 (FAIL) and nothing in 4301/4303
(vacuous PASS). Rung-2 wrote nothing at all in any seed (vacuous PASS) and
recalled 0/312. Every seed reported separately, never averaged.

## 1. What ran

400 sealed reading94 sentences through 9 frozen ears on Mac CPU (39 s,
OMP=1): rung-1 tape/bigru × 4301/4302/4303 behind the exp-76 certified gate
(tau tape 0.088756, bigru 0.30286); rung-2 × 4701/4702/4703 behind each seed's
own sealed tau (0.9484/0.8766/0.9548). New files only, all `fable_read106_`:
`scripts/fable_read106_score.py`,
`artifacts/fable-read106-20260921/` (PASSMARKS.md, SEAL.sha256.txt,
`fable_read106_results.json`, `fable_read106_results_sentences.json`, this file),
`design/v3/30-modes/106-reading-ladder-first-score-muse.md`.
All checkpoints loaded on CPU in seconds; nothing skipped.

## 2. Marks (integers, per ears/seed)

R1 = wrong/writes ≤ 1% (GATED). R2 = correct/312 (recall, reported).
R3 = writes on the 245 NO_FACT sentences (reported).

| ears/seed | writes | wrong | R1 | correct (R2) | R3 NO_FACT writes |
|---|---|---|---|---|---|
| rung1-tape-4301 | 1 | 1 | **FAIL** (100%) | 0/312 | 1 |
| rung1-tape-4302 | 2 | 2 | **FAIL** (100%) | 0/312 | 1 |
| rung1-tape-4303 | 1 | 1 | **FAIL** (100%) | 0/312 | 0 |
| rung1-bigru-4301 | 0 | 0 | PASS (vacuous) | 0/312 | 0 |
| rung1-bigru-4302 | 1 | 1 | **FAIL** (100%) | 0/312 | 1 |
| rung1-bigru-4303 | 0 | 0 | PASS (vacuous) | 0/312 | 0 |
| rung2-c-4701 | 0 | 0 | PASS (vacuous) | 0/312 | 0 |
| rung2-c-4702 | 0 | 0 | PASS (vacuous) | 0/312 | 0 |
| rung2-c-4703 | 0 | 0 | PASS (vacuous) | 0/312 | 0 |

## 3. Every wrong write, verbatim (5 total — this is the whole top-10 list)

1. tape-4301 + tape-4302, `This is much like a typewriter.` (gold NO_FACT):
   wrote `('', 'typewriter', '')` — degenerate empty-relation write.
2. bigru-4302, `It is also one of the States of Germany.` (gold NO_FACT,
   vague pronoun): wrote `('', 'germany', '')` — same degenerate shape.
3. tape-4302 + tape-4303, `Saint-Paul-en-Jarez is a town in France.` (gold:
   `located in the administrative territorial entity | saint-paul-en-jarez |
   france`): wrote `('city', 'saint-paul-en-jarez', 'france')` — subject and
   object exactly right, relation in the toy namespace (`city`) instead of the
   gold string. Wrong under the sealed rule; a near-miss, not a hallucination.

## 4. How often each ear spoke (R4; CLARIFY = 0 everywhere — no decoder emits it)

- tape-4301: REPHRASE 398, EXECUTE 1, ECHO 1 (87 unencodable: >8 opaque words).
- tape-4302: REPHRASE 395, EXECUTE 2, ECHO 3 (87 unencodable).
- tape-4303: REPHRASE 399, EXECUTE 1, ECHO 0 (87 unencodable).
- bigru-4301: REPHRASE 395, EXECUTE 0, ECHO 5 (87 unencodable).
- bigru-4302: REPHRASE 398, EXECUTE 1, ECHO 1 (87 unencodable).
- bigru-4303: REPHRASE 400, EXECUTE 0, ECHO 0 (87 unencodable).
- rung2-4701: REPHRASE 398, EXECUTE 0, ECHO 2 (raw acts: STATE 276, NO_FACT 124).
- rung2-4702: REPHRASE 396, EXECUTE 0, ECHO 4 (raw acts: STATE 306, NO_FACT 94).
- rung2-4703: REPHRASE 398, EXECUTE 0, ECHO 2 (raw acts: STATE 288, NO_FACT 110,
  UNSURE 2).

Rung-2 proposes STATE frames on ~70% of sentences but every one dies at the
0.88–0.95 write gate or the brakes — same choke seen on WebRED in exp 47.

## 5. Reproduce (exact)

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B \
  scripts/fable_read106_score.py --snapshot <scibert-snapshot> \
  --out artifacts/fable-read106-20260921/fable_read106_results.json
shasum -a 256 artifacts/fable-read106-20260921/PASSMARKS.md  # must equal SEAL
```

## 6. Deviations

- D1: fixed a batching bug in my own scorer before the run (iterate the pack
  list via the sealed `run_ear` instead of indexing it as a dict). Same sealed
  decode/verdict path; no threshold or rule changed.
- D2: the crashed first launch (that bug) wrote no output and ran after the
  seal; the registered run is the single clean 39 s run above.
- D3: 0/0 R1 outcomes labelled VACUOUS, not hidden.

## 7. Predictions (ledger P106.1–P106.4): 2/4 TRUE

P106.1 FALSE (rung-1 wrote 5 times, not 0) | 0.7225. P106.2 TRUE (rung-2:
0/0/0 writes, ≤ 5) | 0.0625. P106.3 FALSE (4 R1 FAILs) | 0.8100. P106.4 TRUE
(recall 0/312 everywhere, < 5%) | 0.0400.

## 8. What it means / What it does not mean

- Means: on real simple-English text the old ears either stay silent (rung-2,
  bigru-4301/4303: 0 writes) or write rarely and wrongly (tape + bigru-4302:
  5 writes, 5 wrong, 0/312 recalled). The write gates do not save rung-1: the
  failures slipped through at high confidence, not at the margin.
- Does not mean: the ears "understand nothing" or that rung-2's silence is
  safe by design — 5 vacuous passes are absence of writing, not proof of
  restraint; and write #3 shows a relation-namespace mismatch, a scoring
  subtlety for the next ladder step, not a hallucination.

Questions for Ben: none — measurement only, per plan.
