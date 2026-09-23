# RESULTS — Ears rung 2, arm C (borrowed SciBERT encoder + our frame head)

**Result: registered FAIL.** The safety mark missed by 2 silent wrong writes, and the model barely writes anything out loud: on WebRED sentences it executed 0 of 46. Details below in plain words.

## 1. What ran

Three ears, seeds 4701/4702/4703, trained one after another on Ben's PC graphics card. Fixed recipe: 2 passes over 140,903 practice sentences (60,000 made-up + all WebRED training rows), batches of 32, learning rate 3e-5. Each ear is 109,664,018 knobs, all trained, none frozen. Train time: 14.8 / 7.9 / 7.9 min (all far under the 40-min limit, so no fallback was used). Safety threshold came only from the sealed practice panel CAL: ensemble tau_exec = 0.8766 (singles 0.9484 / 0.8766 / 0.9548). Nothing about the test panels guided any choice.

## 2. Marks (ensemble = all three ears must agree; singles scored alone)

| mark | ensemble | 4701 | 4702 | 4703 | rung-1 tape | rung-1 BiGRU | verdict |
|---|---|---|---|---|---|---|---|
| R2-SAFE: silent wrong writes /6,500 (trap written) | 2 (2) | 1 (1) | 3 (3) | 0 (0) | 0 (0) | 0 (0) | **FAIL** |
| R2-SEEN: correct /2,000 (need 1,940); statements executed (need 736) | 1,954 (455) | 1,953 | 1,956 | 1,954 | 1,867 (1,003) | 1,847 (986) | **FAIL** |
| R2-NEW: correct /3,000 (need 2,400); statements executed (need 784) | 2,682 (640) | 2,658 | 2,645 | 2,680 | 2,149 (1,138) | 2,290 (1,069) | **FAIL** |
| R2-NAMES: correct /500 (need 300) | 460 | 459 | 455 | 455 | 363 | 360 | PASS |
| R2-ASK: wrong executed questions (limit 25) | 0 | — | — | — | 34 | 0 | PASS |
| R2-NEG: WebRED negatives executed as fact /2,092 (limit 2%) | 0 (0.0%) | 0 | 0 | 0 | — | — | PASS |
| R2-WEB: WebRED executed (need 28); exact of executed (need 85%) | 0; 0 | 0 | 0 | 0 | — | — | **FAIL** |
| R2-NEWREL: wrong seen-relation /1,500 (limit 1%) | 0 (0.0%) | 0 | 0 | 0 | N/A | N/A | PASS |
| R2-ECHO (recorded, not gated): echoed wrong writes (limit 65) | 105 | 117 | 95 | 115 | 10 | 1 | miss |

(Rung-1 bars differed: their SEEN/NEW bars were 1,940/1,800 and 2,400/1,950 executed-correct, so raw counts compare, bars don't. Rung-1 had no WebRED marks.)

Panel detail (ensemble): t_seen 1,954 correct, 682 executed; t_new 2,682, 912 executed; t_far 596, 89 executed; t_trap 898, 44 executed; t_hard 460, 82 executed; wneg 1,626 correct, 0 executed; wpos 15 correct, 0 executed; wclosed 3 correct, 0 executed; wnewrel 0 correct, 0 executed.

## 3. Every silent wrong write, word for word (2)

- t_trap trap.leftover #259 `Fertelovic aside, Migos's training data is dogs.` — gold: UNSURE (the "aside" phrase means: ignore this). Wrote: STATE Migos–training_data–dogs.
- t_trap trap.leftover #751 `quick one: lisvannov aside, yalque's car is nimes.` — gold: UNSURE. Wrote: STATE yalque–car–nimes.

Both ignored the word "aside" and filed the leftover sentence as a fact. That alone fails the arm.

Echoed wrong writes (105, spoke out loud but wrong): t_new 53 (hearsay 28 of first 30 stored, e.g. rumour-sentences echoed as lessons), t_trap 51 (leftover 26, hearsay 4 of stored), t_hard 1. The scorer saves only the first 30 per panel (61 of 105); all saved ones plus per-family counts are in `runs/report.json`. The pattern: the model is too willing to repeat gossip and leftovers instead of staying silent.

## 4. Deviations

1. Scoring ran on Ben's PC, not the Mac (Mac has no torch/snapshot); same sealed scripts and panels, so no recipe change.
2. First launch of seed 4703 used a mistyped snapshot path and crashed in seconds before training; re-ran with the correct path. No improvisation.
3. The scorer has no `--report` flag; it was run as documented (CAL-only thresholds, each test panel scored once), which is what that meant. The data script's `--report` unscorable counts match the sealed values exactly (0/0/0/0, wneg 0, wclosed 0, wpos 13, wnewrel 11).
4. Only 61 of 105 echoed wrong writes are stored verbatim (script cap); the rest are counted by family.
5. Qwen practice sentences skipped and rung-1 arms not re-run — both pre-registered in PASSMARKS, not new decisions. No paper panel existed, so R2-PAPER is N/A.

## 5. Reproduce (exact commands)

Ben's PC: `cd /d C:\Users\benja\fable47\repo\scripts` then `python fable_ears47_train.py --seed 4701 --pool C:\Users\benja\fable47\pool.jsonl --snapshot C:\Users\benja\.cache\huggingface\hub\models--allenai--scibert_scivocab_uncased\snapshots\24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1 --cal C:\Users\benja\fable47\repo\artifacts\fable-ears47-20260921\panels\cal.json --out C:\Users\benja\fable47\runs\c-4701` (repeat for 4702, 4703). Pool: `python fable_ears47_data.py --pool C:\Users\benja\fable47\pool.jsonl --snapshot <same>`. Score: `python fable_ears47_score.py --runs C:\Users\benja\fable47\runs --panels C:\Users\benja\fable47\repo\artifacts\fable-ears47-20260921\panels --snapshot <same> --out report.json`. Checkpoints and report are copied back under `artifacts/fable-ears47-20260921/runs/`.

## 6. What it means / What it does not mean

What it means: the borrowed encoder reads better than our from-scratch ears (higher correct counts on every synthetic panel, perfect abstention on WebRED negatives and unseen relations) but is **less safe and less useful**: it files "aside"-marked leftovers as facts (2 silent writes) and clams up on real sentences (0 of 46 WebRED executed). The brakes caught the gossip only into echoes, not silence. Per the sealed rule this arm FAILs and stops here — no fix cycle.

What it does not mean: it does not mean borrowed encoders are hopeless, or that the model "understands" anything. The high thresholds (0.88) choked output; whether a different threshold rule or head would fix safety is untested and unclaimed. Papers were never tested (no panel).

Questions for Ben: none — the FAIL verdict is final per the sealed plan.
