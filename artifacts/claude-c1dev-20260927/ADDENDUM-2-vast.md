# c1-dev addendum 2: the four arms on one vast card (Everyday chat thread, written 2026-09-27 14:43 UTC, before any run)

Additive. PLAN.md, SEAL-2.sha256.txt, the scorer, the readings, the noise report and the prediction are unchanged. No reply
exists yet on any machine.

**Why:** BensPC has not answered ssh since 12:30 UTC 09-27. Ben's standing order (14:05-14:06 UTC, relayed by the Director):
GPU jobs waiting on BensPC go to vast, on the card with the most TFLOPS per $/h, at most $4 per job. The Director asked for
this kit at 14:15 UTC. Nothing in the run needs BensPC: the reader weights are not used (the talker-only arm has no reader) and
the three models are public snapshots at pinned revisions.

1. **What runs:** the same four arms (D, T, Q, L) with chain.cmd's commands, in its order, each retried once if it exits
   non-zero. They run from the same sealed tree: scripts, the practice chats and this folder come from the BensPC kit's commit
   62a5944c8, which checks SEAL-2 24/24. Only box/drive.sh comes from this kit's commit. All four arms run on the one card,
   so every margin compares replies made on the same machine.
2. **What differs from the BensPC plan:** the machine runs Linux, so the winnl2 wrapper prints "winnl2: not Windows, nothing
   changed". torch is 2.11.0+cu128 (BensPC's version) and transformers is 5.17.0, both pinned and fail-closed. 5.17.0 is the
   version every earlier vast chat run used, including bm-390's rival arms. I found no record of BensPC's transformers
   version. Greedy replies can differ by a few tokens between GPUs. Nothing here is compared across machines.
   Main's claude_e2e02d.py has changed since SEAL-2 (ADDENDUM-46/49: comments, and the SLEEP02D refusal moved from the
   talker to the reasoner). With SLEEP02D off the talker path is the same, and the run uses the sealed file anyway.
3. **Models:** the rental downloads bm-390's three pinned snapshots: MiniCPM5-1B 87179e5c1f455ef22e6223592d2d61351b525bfc,
   Qwen3.5-2B 15852e8c16360a2fea060d615a32b45270f8a8fc and LFM2.5-1.2B-Instruct 0f604ada3f766f9f257460c4c9f0b5d6f69d431b.
   These are the ones BensPC holds, so there is no new model. These downloads and torch are the only downloads. No weights
   come back.
4. **Card (the Director's 14:15 rules):**
   - One vast search. Then every offer is checked on the Mac: GPU RAM at least 15,000 MB (the 16 GB class of BensPC's card;
     one model is loaded at a time, the largest about 4 GB in bf16), compute capability at least 8.0 (bf16), a CUDA 12.8
     driver, reliability at least 0.98, at least 8 cores, 40 GB disk and inet_down at least 200.
   - Offers are ranked by TFLOPS per $/h, one per host, best 3.
   - Estimate = 25 min of setup + 60 min of arms x max(1, 5090 TFLOPS / card TFLOPS). Inferred, not measured: ch-403's agent
     ran 336 turns in about 9 minutes on a 5090, at a median of 1.7-1.8 s per turn. One-at-a-time generation is limited
     mostly by memory speed, so the TFLOPS scaling is rough.
   - Fit: estimated hours x $/h + about 13 GB of download at the host's $/GB must be at most 0.8 x the $1.50 money stop.
   - The Mac log and RESULTS-vast.md record the card, its TFLOPS, $/h, TFLOPS per $/h and the estimate.
   - The pick can be a slow, cheap card. A 16 GB card of about 22 TFLOPS would be estimated at about 5 h for about $0.40.
     A 5090 at about $0.45/h would take about 85 min for about $0.65.
5. **Stops (the guard on the Mac, every 5 minutes):**
   - Money: $1.50 for all rentals of this task together. The task cap is $2, inside Ben's $4.
   - Time: 3 h from the first rental on a 5090, scaled up the same way for slower cards. Also a stall (no log growth for
     30 minutes and an idle GPU) and a lost host (no ssh for 20 minutes).
   - Before copying on a money, time or stall end, the guard stops the rental's own run by the PID drive.sh recorded, so no
     file changes during the copy.
   - The instance is destroyed only after W/, outC1/ and drive.log come back and every file matches a sha256 manifest made on
     the rental. Otherwise it is stopped, not destroyed, and the collect job prints FLAG-DIRECTOR.
   - The start re-checks before every create that its job is still released on main. It never touches an instance it did
     not create, and the vast key is never read or printed.
6. **Only one of BensPC and vast runs:**
   - The start refuses if RESULTS-benspc.md exists, if the BensPC run note shows a launched chain, or while a *c1dev-benspc*
     pass is in handoff/queue/ on main or running on the watcher.
   - The BensPC passes (handoff/held/190-c1dev-benspc-bo-p1..p3, sealed kit 62a5944c8) do not look for a vast run. So once
     this is released they stay held, or move to handoff/held/superseded/.
7. **Results:** run-vast/ (the four chat files, logs, the rental's records, the guard's log) and RESULTS-vast.md.
   - COMPLETE means 4 arms x 336 rows over 60 conversations, with V1 OK on all four logs: the winnl2 Linux line, the twinb
     line, and the c1dev settings line in logD.
   - Scoring is then PLAN.md's, with the chats from run-vast/.
8. **Tested against a fake vast and rental** (vastai, ssh, pip, nvidia-smi and the arm runs faked; the four selftests and
   SEAL-2 real). All of these passed:
   - the normal path, then collect: COMPLETE, V1 OK x4, 21 files in the table, 128 KB;
   - an arm that crashes once and is retried;
   - a money stop in the middle of an arm: halted, copied, destroyed;
   - a time stop, with the cap scaled to 94 s from a 20 s base on a 22.1 TFLOPS card;
   - a stall: halted, copied, destroyed;
   - a lost host: stopped, not destroyed;
   - a failed start: copied back, destroyed;
   - three hosts with no ssh: each destroyed, then HOST-FAIL;
   - a job no longer released: nothing rented, NOT-RELEASED;
   - the guard killed, then restarted by the collect job;
   - a second start: refused.
9. **Found while testing:** launching with `cd /root/r && setsid nohup ... & echo launched` backgrounds the whole list, and its
   subshell keeps ssh open until the run ends. This kit launches with `{ setsid nohup ... & }`. The same line in the
   358u/358t/358s vast kits was reported to the Thread manager and the Director at 14:37 UTC.
