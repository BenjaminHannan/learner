Starting your rsn-351 build — renting GPUs and verifying the sealed code.
Cheapest reliable 5090 with 32 cores found — renting it now.
Host can't pull images (proxy failure) — destroying and trying the next host.
Still loading past 6 min — destroying and moving to the next host.
Image is downloading on this host — waiting for it to finish.
Instance running — setting up SSH access.
GPU healthy (5090, CUDA torch). Shipping the sealed code over.
All seals verify. Running the generator selftest.
Selftest passes. Starting the timing pilot.
Both runs training at full GPU — checking back periodically.
Both runs finished. Sealing checkpoints, then running evals.
Evals done. Verifying all outputs are present.
All 12 evals clean. Collecting results for the report.
All data local. Analyzing for the report.
Checking the 350 design doc for the exact Y4 definition.
Checkpoints safe on the Mac. Verifying hashes, then writing the report.
Writing the results report.
Ledger appended. Destroying the instance.
All work complete. Instance destroyed and confirmed gone (only another job's `lis-317-diag` remains, untouched). PUSH paths are on disk for the watcher.

## Verdict: FAIL

rsn-351 (90M model, lr 1e-4) does **not** beat the 30M model. PASS needed Y1 and Y4 on both seeds; Y4 passes everywhere but Y1 fails on both seeds.

## Marks table (integer counts, checked-right)

| mark | bar | seed 1 | seed 2 | result |
|---|---|---|---|---|
| Y1 fresh 296-v2 final vs 30M (225/217) | s1 ≥ 235, s2 ≥ 227 | 221/298 (−14) | 218/298 (−9) | FAIL both |
| Y2 fresh 296-v2 final vs rsn-350 (211/209) | s1 ≥ 221, s2 ≥ 219 | 221/298 (+10, exactly at bar) | 218/298 (+9, 1 short) | PASS s1 / FAIL s2 |
| Y3 three-step never practised | ≥ 6/30 one seed | 0/30 (296), 0/15 (294) | 0/30, 0/15 | FAIL both |
| Y4 invented answers (checked), each panel | ≤ 2 | 296: 0, 294: 0 | 296: 0, 294: 0 | PASS all 4 |

"Proved wrong" clause (Y2 fails on **both** seeds) did **not** trigger — s1 met the bar exactly.

## Every move (counts)

- GPU rentals: 3 total. #1 host docker-registry proxy failure (never ran, destroyed). #2 stuck loading past 6 min (destroyed). #3 RTX 5090/32 vCPU ran everything. Never 2 jobs on 2 instances (only ~1 min handover overlap of idle instances).
- Seals: SEAL-code all-OK, SEAL-v2 OK, SEAL-v3 OK. Generator selftest ok (24 s).
- Pilots: single 30.6 s wall; double (seeds 8+9) 35.4 s wall → ran 2-at-a-time. No OOM.
- Trains: s1 34.6 min, s2 35.4 min. Copy loss 4.0901→0.0064 (s1), 4.2522→0.0013 (s2). Practice reward 0.6729→0.8422 (s1), 0.6057→0.8797 (s2); per-1000-step means rising 0.80→0.89 both seeds (plateau ~0.89 vs 350's ~0.83, 30M's 0.93/0.98).
- Evals: all 12 commands ran exactly once per checkpoint, 0 failures. Fresh-panel copy→final gains +38 (183→221, s1), +36 (182→218, s2). Counting learned in practice: s1 0→12/30, s2 0→11/30 (350 had 4/30). Transfer 294 final: 234/300 (s1), 237/300 (s2) vs 296's 238/238. Dev n=1200: copy 799/746-749, final 937/927-928.
- Raw invented answers: 5 per 296 eval, all fact-checked to "I don't know" (checked 0). Missing-fact 30/30 checked-right in all 8 evals.
- Dollars: ~$0.06 + ~$0.07 + ~$0.57 = **~$0.70 combined**, under $4 and $3.80 lines.
- Checkpoints kept at `~/premonition-models/rsn351/<run>/`, sha256 identical to SEAL-run. JSONs copied to `artifacts/claude-rsn351-20260925/runs/`. Ledger Y1–Y4 lines appended (insertions only).

## Misses and deviations

1. The `scratchpad/briefs/OPUS-RULES.txt` path does not exist; I followed the rules as stated in the task text (additive-only, category counts only, never opened panel items).
2. SEAL-run hashes were computed **before** eval ran but written to file after, in wall-clock order; eval only reads checkpoints and Mac-copy hashes match exactly.
3. Container showed `nproc=1` (256 processors visible); `--workers 8` used as registered.
4. No other misses: every case, bar, and count reported above; nothing tuned, nothing quoted, nothing edited.

## What it means / doesn't mean (plain English)

Think of it like this: the big model with gentler training learned to count much better than the big model with rushed training (12 and 11 out of 30 vs only 4), and one of the two runs hit the target line exactly. But it still didn't beat the smaller model, so "the rushed learning speed was the whole problem" is **not proven** — one run passed by the thinnest margin possible, the other missed by a single question. Something else about being bigger still needs explaining. Two clean facts: questions with 3 steps that were never practised stayed at zero everywhere, and the model never invented answers when the fact was missing (zero checked inventions).
