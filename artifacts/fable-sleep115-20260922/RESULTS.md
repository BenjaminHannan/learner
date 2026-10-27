# Exp 115 RESULTS — sleep scale ladder: breaking point L4

Exp 104 installed one relation in one sleep. I scaled it rung by rung
(L1: 3 relations, 1 sleep; L2: 2 sleep cycles; L3: 3-hop word alone;
L4: 400 turns, 5 sleeps, 5 relations; L5: + kill-9). New files only:
a 3-word episode feed + per-word bridge into the live reasoner77, an
ears wrap forcing entity-valued teaches for chain hops, and a ladder
driver. Everything ran through the daemon mailbox.

## Marks (every seed reported, never averaged)

| mark | L1 s1/s2/s3 | L2 s1/s2/s3 | L3 s1/s2/s3 | L4 s1/s2(/s3) |
|---|---|---|---|---|
| installs == requested | 3/3/3 | 1+2 / 1+2 / 1+2 | 1/1/1 | 3,3 (of 5) |
| OOF / agreement per installed word | 1.00/1.00 x9 | 1.00/1.00 x9 | 1.00/1.00 x3 | 1.00/1.00 x6 |
| wrong installs | 0/0/0 | 0/0/0 | 0/0/0 | 0/0 |
| NEW-people probes per installed word | 5/5 x3 seeds | 5/5 x3 (incl. A after sleep 2) | 5/5 x3 | 5/5 x3 words |
| extra-relation probes (L4 only) | — | — | — | 0/5 + 5 abstain, 0 wrong, both seeds |
| probe records sleep-derived | 15/15 x3 | 15/15 x3 | 5/5 x3 | 15/15, both seeds |
| taught intact / dupes / overwrites | 150/150, 0, 0 (x3) | 150/150, 0, 0 (x3) | 75/75, 0, 0 (x3) | 225/225, 0, 0 (both) |
| sleep wall-clock (s) | 30/31/29 | 69+18 / 70+16 / 71+19 | 5/6/4 | s1: 74, 341, 37, 0, 0; s2: 415, 245, 19, 0, 0 |
| rung verdict | PASS | PASS | PASS | FAIL (breaking point) |

L4 seed 3: incomplete (141/400 turns, 1 sleep @70 s) when the wave clock
ran out; not scored. The rung verdict rests on seeds 1-2, which both fail
the "5 relations installed, 5/5 probes each" marks. L5 never ran (stop rule).

## What happened

L1's one sleep installed all three words (20 episodes each, gate 1.00/1.00,
routings [1,1]/[3,4]/[1,5,7]) in ~30 s and answered 15/15 strangers.
L2 installed A in sleep 1, B+C in sleep 2 (same-dir restart between), and A
still answered 5/5 after sleep 2: no forgetting. L3 installed the 3-hop
word alone in ~5 s, 5/5. L4 installed w0/w1/w2 in sleeps 1-3, then asked
20 questions each for boss_of_father and teacher_of_spouse: the wrapper
queued zero episodes (no word slot exists — R44 has exactly 3), both sleeps
were instant no-ops, and all 10 probes honestly abstained, 0 wrong.
The previous three installs stayed 5/5 throughout; taught facts never lost.

## Findings / deviations

1. My pre-registered latency model was wrong: multi-word sleeps took
   5-37 s, not ~70 s/word (P115.3/P115.4 scored FALSE). Single-word sleeps
   varied 5-415 s across identical code — other agents share this Mac, so
   contention, not the recipe, dominates wall-clock. L4's 341/415/245 s
   sleeps also miss the 120 s mark, but the rung fails structurally first.
2. Drive bugfix before the registered wave: truth keys used "best friend"
   (space) vs stored "best_friend" (scratchpad smoke showed 125/150).
   Fixed, resealed (new SEAL hashes), then registered. No registered run
   was ever re-run.
3. The brief's example relations (paternal uncle, cousin) are not
   expressible: R44 has no brother/sister/child skills. L1 uses the three
   sealed word slots instead (chains in PASSMARKS.md).
4. Wave exceeded 30 min (L4 seed 3 killed by the clock); report was
   rebuilt read-only from daemon logs with the sealed scoring code.

## Questions for Ben

None. Most conservative defaults taken (abstain on doubt, atomic word
file, taught never touched by sleep).

## Reproduce (the breaking point, one L4 seed)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project \
--python 3.12 --with torch --with numpy python -B \
scripts/fable_sleep115_drive.py --root artifacts/fable-sleep115-20260922/runs-repro \
--report artifacts/fable-sleep115-20260922/wave-report-repro.json \
--only l4 --seed 1

Expect: sleeps 1-3 install w0/w1/w2 (5/5 probes each, taught 225/225),
sleeps 4-5 install nothing, boss_of_father + teacher_of_spouse probes
0/5 with 5 abstentions and 0 wrong. Sealed files: PASSMARKS.md + both
scripts (SEAL.sha256.txt verified after the run).

## What it means
The daemon scales to three installs with zero forgetting and zero damage,
then stops exactly where the architecture ends: a 4th new relation has no
slot, so it abstains instead of inventing.

## What it does not mean
Sleep does not schedule itself by need (still a turn counter), install
latency on a shared machine is unpredictable (5-415 s for identical fits),
and nothing here adds a 4th word slot — that needs a new base, not tuning.
