# own-M1n: mouth v2 (natural replies) — builder RESULTS (2026-09-23)

## Verdict: FAIL (1 of 5 marks fails)

- Pm1n.1 spoke: PASS (1000/1000).
- Pm1n.2 first-try pass: PASS (1000/1000).
- Pm1n.3 slot_check recount fails: PASS (0).
- Pm1n.4 variety: FAIL — 59 distinct slotted replies / 1000 rows (5.9%, bar >= 30%);
  top reply "<S1>'s <R1> is <V1>." on 129/1000 rows (12.9%, bar <= 3%).
- Pm1n.5 crashes: PASS (0).

The 5.6k natural rows taught the slot format perfectly (100% first-try gate pass, 0 recount
fails) but the mouth collapsed to a handful of stock phrasings: the top 5 slotted replies cover
457/1000 dev rows. The "proved wrong" clause (first-try < 80%) is NOT triggered — the format
learned fine; variety did not.

## What ran

- Code + data: SEAL-code 5/5 OK, SEAL-data 3/3 OK (hashes match origin/main; no sealed file changed).
  `claude_own_m1_data.py --m0 <m0b>`: train kept 5602, dropped 0; dev kept 1000, dropped 0 (as expected).
- Base model: openbmb/MiniCPM5-1B, snapshot commit 87179e5c1f455ef22e6223592d2d61351b525bfc.
- Train (sealed `claude_lis300_train.py`, unedited): LoRA r32, 2 epochs, lr 2e-4, batch 16
  (no OOM, no batch-8 fallback), max-len 256, seed 300, --merge. 702/702 steps, no early stop.
  - train_log.jsonl: 36 lines; step 1 loss 2.9962; step 700 (last) loss 0.262.
  - dev_loss 0.9034; trainable params 22,413,312 / 1,103,046,144.
  - Training minutes 3.72; tok/s 3658.9; device cuda (1x RTX 5090).
- Merged safetensors sha256: de12daf488e462814caa6c9de23603aae22326b26060525b2b534f08c4b1564a
  (2161290944 bytes). data/counts.json sha256: 986dd779ab9fac239cab2c478552f45ebb84a53172aba420af150fe80e07bec2.
  Both sealed in SEAL-run.sha256.txt BEFORE the dev measurement.
- Measure ONCE (sealed `claude_own_m1_speak.py`, unedited, default 4 samples): 1000/1000 dev rows,
  spoke 1000, fell back 0, first-try 1000. No re-run, no tuning.

## Marks table (integer counts)

| Mark | Bar | Count | Result |
|---|---|---|---|
| Pm1n.1 spoke within 5 tries | >= 990/1000 (99%) | 1000/1000 (100.0%) | PASS |
| Pm1n.2 greedy first-try pass | >= 950/1000 (95%) | 1000/1000 (100.0%) | PASS |
| Pm1n.3 recount fails (fresh slot_check on winning raw) | 0 | 0/1000 non-null | PASS |
| Pm1n.4a distinct slotted replies | >= 300/1000 (30%) | 59/1000 (5.9%) | FAIL |
| Pm1n.4b single most common reply | <= 30/1000 (3%) | 129/1000 (12.9%) | FAIL |
| Pm1n.5 crashes | 0 | 0 | PASS |

Fallbacks per status (rows, spoke): OK 350/350, SAVED 150/150, UNKNOWN 150/150, ABSTAIN 100/100,
CLARIFY 150/150, FORGOT 100/100. Fallbacks: 0 in every status.

Top 5 slotted replies: "<S1>'s <R1> is <V1>." 129; "Which <S1>? I know more than one." 86;
"I worked out from what you told me that <S1>'s <R1> is <V1>." 83;
"I don't know <S1>'s <R1>." 82; "I don't know who <S1>'s <R1> is." 77.

Speak timing (cuda): median 1221.5 ms/row, p90 1381.7 ms/row.

## Cost

- Rental: 1x RTX 5090, vast.ai instance 52279213 (label own-m1n), $0.5159/hr,
  2026-09-23 18:43:40Z → 20:02:52Z (79.2 min = 1.32 h) ≈ $0.68.
  Task ceiling $4.00/3h respected. Instance destroyed after the run; `show instances` confirms
  only the parallel v1 rerun own-m1b remains (not mine, untouched).
- Ledger rental total after this run stays far under the $30 cap.

## Model kept (weights never in git)

- Mac copy: ~/premonition-models/own-m1n-mouth/merged/ (from <work>/run/merged).
- Local shasum of the copied model.safetensors:
  de12daf488e462814caa6c9de23603aae22326b26060525b2b534f08c4b1564a (equals the sealed hash).

## Deviations / notes

1. OPUS-RULES.txt path from the task (/private/tmp/claude-502/…/OPUS-RULES.txt) does not exist on this
   Mac; worked from the key points restated in the task instead. Additive-only obeyed: only new files
   under artifacts/claude-own-m1n-20260923/ were created; ledger appended with cat >>.
2. No TEST-ONLY panel, convbench file, or panel artifact was opened at any point.
3. Sealed code was imported and run unedited (sha-verified before running). No patch, no re-run of dev.
4. 20 quoted dev rows are in dev_out_sample.jsonl (seed-7 sample; dev material, fictional names).
5. Added the Mac's ssh pubkey to the vast.ai account (key id 1420036) to attach to the rental;
   no secret printed or stored in the repo.
