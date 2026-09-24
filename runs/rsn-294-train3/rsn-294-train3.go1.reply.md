Renting your GPU and launching the reasoner showdown — verifying code first.
Local files are incomplete — pulling the sealed specs and scripts.
The rules file is missing, but the task embeds the key points — I'll proceed on those and note the deviation. Now checking GPU rental preconditions.
Context gathered. Now renting the GPU instance.
Renting offer 43165154 (RTX 5090, 32 cores, rel 0.995, $0.47/h) as rsn-294c.
Contract 52300816 created. Waiting for it to reach running.
Instance running. Setting up access and environment.
Venv ready (torch 2.14.0+cu130, CUDA True, numpy 2.4.6). Waiting on code upload.
Code unpacked. Verifying seals and selftest.
Seals 7/7 OK, selftest ok. Launching pilot runs (timing only).
loop-s1 running. Starting plain-s1 alongside.
plain-s1 is up but loop-s1 vanished — checking what happened.
Both seed-1 runs training. Entering watchdog polling.
plain-s1 finished (~30 min). Waiting on loop-s1, then launching seed-2 pair.
Both seed-1 runs done. Launching seed-2 pair.
Both seed-2 runs training. Resuming watchdog.
All 4 training runs complete. Sealing checkpoint hashes before any eval.
Seal written. Running dev + panel evals once per checkpoint (sequential loop).
All 16 evals done, no failures. Copying results back.
plain-s2/panel-final.json missing after scp timeout — re-copying.
All files present. Now computing scores for RESULTS.md.
Need the exact scoring semantics from the runner code before judging marks.
All scores computed. Gathering train first/last numbers for the report.
Copying checkpoints to the Mac (step 7).
While checkpoints download, checking progress.
Parallel scps got killed by the host. Checking instance health, then single-stream copy.
loop-s1 hashes match the seal. plain-s1 downloading.
All 8 checkpoints verified against the seal. Destroying the instance.
Instance destroyed, none live. Writing RESULTS.md.
**Verdict: FAIL** — the loop reasoner trained cleanly on both seeds, but loses to the equal-size plain transformer on the held-out set on both seeds, scores far below the code arm overall, and practice teaches almost nothing on seed 2. Full detail is in `artifacts/claude-rsn294-20260923/RESULTS.md`; PUSH paths ready (`RESULTS.md`, `SEAL-run.sha256.txt`, `runs/`, ledger appended). Instance destroyed, 0 live.

**Marks table (integer counts, checked = after fact-check, n = 300; code arm = 210/300 overall, 30/30 in each of one_step, backwards, yes_no, newest_correction, missing_fact)**

| mark | bar | loop seed 1 | loop seed 2 |
|---|---|---|---|
| P294.1 invented (checked answered w/o fact) | ≤ 2/300 | 0/300 PASS (raw 22, all fact-checked to IDK) | 0/300 PASS (raw 4, all fact-checked to IDK) |
| P294.2 loop right overall | ≥ 240/300 | 92/300 FAIL | 111/300 FAIL |
| P294.3 missing_fact honest IDK | ≥ 25/30 | 30/30 PASS | 30/30 PASS |
| P294.4 held-out loop − plain | ≥ +10 | 0 − 5 = −5 FAIL | 1 − 8 = −7 FAIL |
| P294.5 no regression (1-step/back/yes-no/newest, each ≥ 27/30) | ≥ 27 each | 3/7/11/12 FAIL all four | 19/8/23/12 FAIL all four |
| P294.6 practice teaches (final − copy-only) | ≥ +10 | 92−45 = +47 PASS | 111−107 = +4 FAIL |

Per-run: loop-s1 40.4 min, copy loss 4.0318→1.0745, practice reward 0.2458→0.3286, panel copy 45/final 92 right; plain-s1 30.3 min, 3.9513→0.0016, 0.7603→1.0070, copy 165/final 184; loop-s2 40.5 min, 4.0276→0.1215, 0.6483→0.9040, copy 107/final 111; plain-s2 29.9 min, 3.9393→0.0003, 0.7560→1.0199, copy 156/final 189. Params 30771221 loop / 30938261 plain. Spend ~$1.32 (2.80 h × $0.4727/h, contract 52300816, credit $9.31 at rental).

**Every move:** 0 live instances at start (no DUPLICATE); credit $9.31 (no LOW-CREDIT; true spend total ≈ $2.93, not the $34.04 that naive `$`-grep gives — most matches are ceilings/rates/balances); rented cheapest ≥16-core offer 43165154 excluding forbidden 43748043/49298963 (1 rental total, running in ~1 min, label rsn-294c); new venv torch 2.14.0+cu130 CUDA True + numpy 2.4.6; nproc 256, RTX 5090 32 GB, disk 60G; tarball-of-main via git archive + scp; seals 7/7 OK; selftest ok; pilots loop (copy 0.22 min, practice net 0.19) + plain (0.14 + 0.13) → est ~120 min < 150 cap → trained; 4 runs defaults --workers 4, 2 at a time (plain-s1 30.3, loop-s1 40.4, plain-s2 29.9, loop-s2 40.5 min); SEAL-run written before any eval; 16/16 dev+eval once per checkpoint, 0 failures; 24 result files copied to runs/; RESULTS.md written; 9 ledger lines appended via cat >>; 8 checkpoints (∼1 GB) copied to ~/premonition-models/rsn294/<run>/ with all sha256 matching SEAL-run; weights never in git; instance destroyed 00:12:37Z, 0 live confirmed.

**Misses:** none functional. One scp retry needed for plain-s2/panel-final.json after a timeout; checkpoint download forced per-run subdirs after a flat-copy filename collision was caught at 4 MB (nothing lost).

**Deviations:** (1) OPUS-RULES.txt path doesn't exist (empty scratchpad dirs) — worked from the task-text rules. (2) Tarball + scp instead of git clone (allowed). (3) pip's torch 2.14.0 instead of image's 2.8.0 (task needs only CUDA torch + numpy). (4) Two remote-cwd backgrounding mistakes (`&&`/`&` parsing), each restarted from repo root; no eval ever ran twice. (5) Wall-clock ~2.8 h slightly over the 3 h half of the $4/3 h ceiling because checkpoint download ran ~100–400 KB/s; dollars (~$1.32) well under $4. Panel items read by me: 0. Sealed files edited: 0. Code patched: never.

**What it means / doesn't mean (plain English):** Think of it like testing whether re-reading a question many times (loop) beats just being a bigger one-pass reader (plain) of the same brain size. The re-reader learned the easy copy skills worse than the plain reader (45–107 vs 156–165 right after copying), practice helped a lot on seed 1 (+47) but barely on seed 2 (+4), and on brand-new kinds of questions (three-step chains, big notebooks) the plain reader actually did better (5 and 8 vs 0 and 1). The safety parts work: the model almost never invents answers that survive the fact-check (0/300 both seeds) and always says "I don't know" when a fact is missing (30/30). This doesn't mean looping can never work — only that this loop, with this training, does not beat an equal-size plain model here.
