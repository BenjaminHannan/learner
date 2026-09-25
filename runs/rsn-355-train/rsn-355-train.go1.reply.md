Building your shared-step arm — verifying the sealed code and firing up the GPU runs.
Sealed code confirmed on paper — now verifying the untouched archives match.
All seals check out — now connecting to the GPU machine.
GPU is ready — now setting up the code on the Windows side.
Python with CUDA is good — now shipping the sealed code over.
Selftest passed — now running the timing pilot.
Both full training runs are off — I'll check progress periodically.
Both trainers exited silently — investigating what happened.
Quoting got tangled — I'll ship a launcher script file instead.
Both trainers are running detached at 67% GPU — now waiting.
Both runs finished — verifying outputs before sealing.
Hashes match — writing the run seal before any eval.
Seal written — now the one-time evals per checkpoint.
All 12 evals done — pulling the result files back.
Panels show zero three-step everywhere — now pinning down the H3 "invented answers" definition.
Dev value3 is zero across the board — now extracting training curves.
All numbers in hand — checking ledger format before writing results.
Writing the results file.
Work complete. Final report for the director:

## VERDICT: FAIL

rsn-355 (shared chain-step input, plain arm, seeds 1+2, BensPC GPU, $0) does not pass. Three-step is still 0/30 on both seeds, and seed 2 additionally fails the do-no-harm bar.

## Marks table (final checkpoints, checked right, integer counts)

| mark | seed 1 | seed 2 | bar | result |
|---|---|---|---|---|
| H1 panel296 v2 heldout_three_step (/30) | 0 | 0 | ≥ 6/30 BOTH seeds | FAIL both |
| H2 panel296 v2 total WITHOUT three-step | 223 | 197 | s1 ≥ 220, s2 ≥ 212 | PASS s1, FAIL s2 |
| H3 invented answers checked, panel296 | 0 | 0 | ≤ 2 each panel | PASS both |
| H3 invented answers checked, panel294 | 0 | 0 | ≤ 2 each panel | PASS both |
| H4 panel294 v3 heldout_three_step (/15) final (copy) | 0 (0) | 0 (0) | report | n/a |
| H4 dev value3 (/100) final (copy) | 0 (0) | 0 (0) | report | n/a |

Proved-wrong clause ("H1 ≤ 1/30 on both seeds while H2 passes"): triggers for seed 1 only (H1 0/30 + H2 223 ≥ 220), NOT overall — seed 2 fails H2 (197 < 212), so the clause does not trigger cleanly.

## Every move

1. SEAL: `git archive origin/main` to temp dir; `shasum -c` → code seal 6/6 OK, panel296 seal 2/2 OK, panel294 seal 2/2 OK.
2. CODE: tar of scripts + 3 artifact dirs → BensPC `premonition-models/rsn355/code`. RTX 5070 Ti 16 GB / driver 591.86 / CUDA 13.1; C: ~53 GB free; 6C/12T; lis300 venv torch 2.11.0+cu128 CUDA True. `claude_rsn296_gen.py` → selftest ok, 0 gold-action mismatches.
3. PILOT: seed 9, copy 100 + RL 50, --workers 0 → exit 0, 30.7 s. Estimate 60×0.25+120×0.21 ≈ 40 min. Two-at-once (seeds 8+9) → 32.9 s, both exit 0. Chose 2-at-a-time; well under 8 h.
4. TRAIN: seeds 1+2, full defaults + --workers 0, together → exit 0. s1 43.9 min, copy action_ce 3.8230→0.0136; s2 43.8 min, 3.8834→0.0007. RL means/1000 steps: s1 0.7729/0.8334/0.8611/0.8490/0.8440/0.8919; s2 0.7978/0.8061/0.8277/0.8509/0.8581/0.8438.
5. SEAL-run.sha256.txt written BEFORE any eval (4 checkpoint hashes, kept-location paths).
6. EVAL once per checkpoint (12 cmds, category counts only, items never opened): ALL-EVALS-DONE. Panel296 final checked/raw: s1 223/217, s2 197/205 (n=298). Panel294 final: s1 245/245, s2 226/238 (n=300). Per-category tables are in RESULTS.md. Dev value3 0/100 copy and final, both seeds.
7. Copied 16 files back to `artifacts/claude-rsn355-20260925/runs/<R>/`. RESULTS.md written, ledger appended with 4 H-lines.
8. Checkpoints (~125 MB each) kept ONLY on BensPC at `premonition-models/rsn355/plain355-s1|2/{copy_only.pt,final.pt}`, hash-verified against trained files (s1copy cd2f811d…, s1final fc6090b1…, s2copy a7f731c4…, s2final 9baca68d…). Never pushed, never copied to Mac.

## Misses and deviations

- Misses in procedure: none (all seals OK, trains exit 0, evals exit 0, all files back). Result misses: H1 both seeds, H2 seed 2 (comparing 0/30 and counting 8/30 checked after practice).
- D1 (registered): --workers 0 on Windows — same generator/seeds, different puzzle stream than rentals.
- D2: OPUS-RULES.txt path from the brief did not exist (empty scratchpad dir); I worked from the brief's rule summary. Nothing existing edited/deleted; ledger append-only.
- D3: first detached launch died silently when ssh closed (PIDs gone, GPU idle, empty logs); relaunched via WMI process-create, which survived (GPU 67–86% to completion). No code changed, no retraining.

## What it means / doesn't mean (plain English)

The shared chain-step input did not unlock three-step questions: 0/30 on both tries, always answered "I don't know" (honest — invented answers are 0, so nothing was made up). On seed 1 everything else held up, which points away from the "untrained slot" story and toward the net simply not chaining a third lookup it never practised. Seed 2 additionally slipped on comparing/counting, so it fails do-no-harm too. Per the plan, the next step is practising three-step itself, not more input fixes. This says nothing bad about the other skills — the net learned what it practised; this one new trick just didn't transfer.

PUSH: `artifacts/claude-rsn355-20260925/RESULTS.md` `artifacts/claude-rsn355-20260925/SEAL-run.sha256.txt` `artifacts/claude-rsn355-20260925/runs` `artifacts/fable-predictions-ledger.md`
