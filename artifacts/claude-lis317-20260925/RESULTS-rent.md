# lis-317-diag: what the reader reads in chatty DEV turns (rented GPU, REPORT ONLY, 2026-09-25)

Verdict: DONE, report only. DEV data, no marks, no training, no TEST-ONLY panel touched.
Decision (PLAN.md rule, fixed before the run): R0 = 89/131 = 67.9% -> 60-80% band: both; the gate first (no training).

## Where and what

- Rental: vast.ai contract 52507626, 1x NVIDIA GeForce RTX 5090, 32607 MiB, offer 44173708
  (16 vCPU, 537 GB disk, down/up 461/425 Mbps, reliability 0.9984).
- Image: pytorch/pytorch:2.8.0-cuda12.9-cudnn9-runtime. Image torch 2.8.0+cu129, CUDA True,
  transformers 5.17.0 installed clean (no torch/torchvision upgrade needed, unlike rent-330-dev).
- Window: rented 2026-09-25 00:41:59Z, running ~00:45Z, destroyed ~02:02:50Z, confirmed 0
  lis-317-diag live after (siblings rent-360-gram, rent-336b untouched).
- Hours alive: ~4851 s = ~1.35 h. dph $0.5037. Dollars ~$0.68. Budget $1.50: respected.
- Credit at start: $2.79.
- Tree: git archive origin/builder-outbox + git archive origin/main on top (main wins).
  Skipped per task: BASE, MiniLM, self122_head.pt downloads and the route122 check
  (this task never builds the agent). READER = ~/premonition-models/lis301-merged,
  model.safetensors sha256 b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890 (match).
- Month-end code never edited. Every step under nohup/setsid with a log; sampler resumes
  from its output file (not needed: no restarts).
- Env on box: HF_HUB_OFFLINE=1 PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1.

## Wall time per step (UTC, from the rental)

- Upload tree.tgz (158 MB): 00:45:38Z -> 00:47:37Z = 119 s.
- Upload reader.tar (2.0 GB): first scp broke at 1.1 GB after ~17 min (connection reset by
  peer); resumed with rsync --partial, complete 01:11:59Z, sha256 match on both files.
- Extract + READER sha check + pip install: 01:12:21Z -> 01:12:50Z.
- Seal (from inside artifacts/claude-e2e331-dev-20260924): 3/3 OK at 01:13:15Z.
- s1 sampler e2e (194 rows, K=8, temp 1.0): start 01:13:25Z, last write 01:21:12Z = 467 s
  (~2.4 s/row), exit clean, "done 194 rows on cuda".
- s2 sampler lis301dev (959 rows, K=8, temp 1.0, --no-tokens): start 01:21:31Z, last write
  02:00:45Z = 2354 s (~2.45 s/row), exit clean, "done 959 rows on cuda".
- s3 scorer: start 02:01:21Z, done same second (<1 s), exit 0.
- Copy back (rsync): 427668 + 1436426 + 647 bytes, byte-exact vs the box (wc -c match).

## Row counts and file sizes (local, verified)

- artifacts/claude-lis317-20260925/reads_e2edev.jsonl: 194 lines, 427668 bytes.
- artifacts/claude-lis317-20260925/reads_lis301dev.jsonl: 959 lines, 1436426 bytes.
- artifacts/claude-lis317-20260925/score_e2edev.txt: 647 bytes.
- Inputs: rows_e2edev.jsonl 194 lines; dev_rows.jsonl 959 lines (match).

## score_e2edev.txt (verbatim)

R0: 89
R0rel: 44
RT: 20
W0: 52
W0_kind:ask: 11
W0_kind:correct: 6
W0_kind:creative: 3
W0_kind:smalltalk: 5
W0_kind:teach: 27
W_total: 141
ask_act_ASK: 55
ask_turns: 71
gold: 131
not_found: 42
agreement (K=8): level -> right writable facts kept / wrong writable facts kept
  >= 0/8: right 89, wrong 52
  >= 1/8: right 89, wrong 47
  >= 2/8: right 89, wrong 45
  >= 3/8: right 88, wrong 43
  >= 4/8: right 88, wrong 36
  >= 5/8: right 85, wrong 33
  >= 6/8: right 81, wrong 23
  >= 7/8: right 77, wrong 16
  >= 8/8: right 68, wrong 9
R0 = 89/131 = 67.9%   RT = 20/131   W0 = 52
DECISION (PLAN.md rule): 60-80% -> both; the gate first (no training).

## Reading of the numbers (counts only, DEV data)

- 131 gold teach/correct facts: 89 read with a writable mode and matching owner+value (R0 67.9%);
  44 of those also match the bank's relation word (R0rel, a lower bound since relations are free text);
  only 20 of the 89 clear the live T=0.995 gate (RT 20/131 = 15.3%).
- 42 gold facts not found in the greedy read at all; 141 writable facts total in greedy reads,
  52 matching no gold fact of their turn (W0), spread across teach (27), ask (11), correct (6),
  smalltalk (5), creative (3) turns.
- Ask turns: 71 ask turns, greedy act ASK on 55.
- Agreement (K=8 resamples): requiring full 8/8 agreement keeps 68 right / 9 wrong
  (from 89 right / 52 wrong with no agreement requirement).

## Deviations (3, all environment/transport, 0 code edits)

1. Cheapest 5090 offer 45669197 was gone at rent time; re-searched, took 44173708 ($0.5037/h
   billed). First-choice churn, same as rent-330-dev saw.
2. Reader upload broke once (scp connection reset at ~1.1/2.0 GB); resumed with rsync
   --partial to a byte-exact match. No data loss (checksums match both files).
3. Two ssh launch commands printed their echo but the client hit the 60 s tool timeout with
   the session held open; both jobs had actually launched (verified running via probe, logs
   and row counts grew normally). Seal 3/3, both samplers and the scorer exited clean.

## What it means (plain high-school English)

- The reader reads about two-thirds of chatty DEV facts correctly before any gate (89 of 131),
  which lands in the middle band the plan fixed in advance: neither "the reader is fine, only
  fix the gate" (needed 105+) nor "the reader is broken, retrain it" (below 79). So the plan
  says: do both, gate first since it needs no training.
- The live gate looks harsh here: only 20 of the 89 correctly read facts clear T=0.995.
  Agreement across resamples separates right from wrong reads (at 8/8: 68 right kept, 9 wrong kept).

## What it doesn't mean

- It doesn't mean anything registered: DEV turns only, mechanical counts, no blind judges ran.
- It doesn't mean the gate fix will work: this run only measured reads, it built no new gate.
