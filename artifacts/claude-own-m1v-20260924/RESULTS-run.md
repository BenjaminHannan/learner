# own-M1v run results (builder, 2026-09-24)

Sealed code, one run on BensPC GPU. Weights: own-M1n merged
(model.safetensors sha256 de12daf488e462814caa6c9de23603aae22326b26060525b2b534f08c4b1564a,
verified on BensPC). Command: `python scripts/claude_own_m1v_speak.py --model
C:/Users/benja/own-m1n/merged --data artifacts/claude-own-m0b-20260923/dev.jsonl
--out dev_out.jsonl --samples 4 --seed 1`. One run only, seed 1. No training.

## Pass marks (counts only)

| Mark | Bar | Got |
|---|---|---|
| Pm1v.1 spoke (reply passed the gate within 5 tries) | >= 990/1000 | 1000/1000 |
| Pm1v.2 fresh slot_check recount failures on winning raws | 0 | 0 |
| Pm1v.3 variety: distinct slotted replies | >= 300/1000 | 461/1000 |
| Pm1v.3 variety: single most common reply | <= 50/1000 | 42/1000 |
| Pm1v.4 grammar | blind graders (mouth thread, not graded here) | n/a |
| Pm1v.5 crashes | 0 | 0 |

## Detail

- Fell back (no reply passed the gate): 0/1000.
- Per-status rows / spoke: OK 350/350, SAVED 150/150, UNKNOWN 150/150,
  ABSTAIN 100/100, CLARIFY 150/150, FORGOT 100/100.
- Try histogram (tries needed to pass the gate): {"1": 1000}. Every row passed
  on the first sampled try; greedy fallback was never needed.
- Timing on GPU: median 866.1 ms/row, p90 1032.8 ms/row.
- Device: cuda (BensPC NVIDIA GeForce RTX 5070 Ti, 16303 MiB, driver 591.86).
- Pm1v.2 recount: for all 1000/1000 rows with a non-null reply, the sealed
  slot_check (scripts/claude_own_m1_common.py, origin/main copy) was re-run on
  raw[tries-1]; 0 failures.

## Pm1v.3 top 5 slotted replies (quoted verbatim, slots unfilled)

1. 42: `<S1>'s <R1> is <V1>.`
2. 29: `You told me <S1>'s <R1> is <V1>.`
3. 18: `Got it, <S1>'s <R1> is <V1>.`
4. 15: `I don't know who <S1>'s <R1> is.`
5. 14: `From what you told me, I worked out that <S1>'s <R1> is <V1>.`

## 10 random filled replies (seed 7, dev material, fictional names)

1. [ANSWER/OK] "It's Yvallo. That's Hrallo's friend."
2. [FORGOT_ACK/FORGOT] "Okay, Trallo's sport is cleared."
3. [ANSWER/OK] "I figured out Frella's hometown is Ploverst, going by what you've said."
4. [ACK_SAVE/SAVED] "Alright, Frella's doctor is Ivallo. Got it."
5. [ABSTAIN/ABSTAIN] "You haven't told me Lrella's sister yet."
6. [ANSWER/OK] "Frella's favorite_food is cheese."
7. [ANSWER/OK] "I figured out Vrallo's sport is skating, going by what you told me."
8. [CLARIFY/CLARIFY] "I've got more than one Lrella. Which one?"
9. [ABSTAIN/UNKNOWN] "Sorry, Jrallo's work_location isn't in my notes."
10. [ANSWER/OK] "Oh, Xrallo's father's brother? That's Lvallo."

## Note (counted, not graded here)

- 165/1000 filled replies contain a raw underscore relation name
  (e.g. "work_location", "favorite_food"). The sealed run code fills slots with
  raw names; the say-forms printer fix is the mouth thread's follow-up.
  Grammar (Pm1v.4) is graded by the mouth thread's blind graders on dev_out.jsonl.

## Deviations

- OPUS-RULES.txt path in the task did not exist (that scratchpad dir is empty);
  worked from the task text's key points (additive-only, fictional names, one run).
- No `lis-301` venv exists on BensPC; used `C:/Users/benja/lis300/venv`
  (torch 2.11.0+cu128, transformers 5.17.0, cuda available).
- First remote-launch attempt failed instantly (shell arg-splitting, argparse
  usage error, no output written); the second launch is the single real run.
- dev_summary.json re-encoded UTF-16 -> UTF-8 (PowerShell `>` writes UTF-16);
  content identical to the printed summary.
- Worktree is behind origin/main, so the SEAL check ran in /tmp/own-m1v-seal
  (git archive origin/main): all 8 lines OK.
