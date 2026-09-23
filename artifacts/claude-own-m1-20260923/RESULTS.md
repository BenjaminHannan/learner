# own-M1 (mouth) RESULTS — builder own-m1b, 2026-09-23 (rerun after first host went offline)

## Verdict: registered FAIL (4/5 marks PASS; Pm1.4 variety FAILS)

The fine-tuned MiniCPM5-1B mouth learned the slot format perfectly (1000/1000 first-try
passes, 0 gate failures on recount, 0 fallbacks, 0 crashes) but collapsed onto a handful of
head templates: 45 distinct slotted replies on 1000 dev rows (bar >= 300) and the single most
common reply on 175 rows (bar <= 30). The "proved wrong" clause is NOT triggered (first-try
100% >> 80% floor): fine-tuning did teach the slot format; the 1B speaker is viable as
trained for format, but not for variety. One diagnosis-driven follow-up is the director's call.

## Marks (measured once on own-M0 dev split, 1000 rows, disjoint names; dev material, fictional names)

| Mark | Bar | Measured (integers) | Result |
|---|---|---|---|
| Pm1.1 spoke within 5 tries | >= 990/1000 (99%) | 1000/1000 spoke, 0 fell back | PASS |
| Pm1.2 first-try (greedy) pass | >= 950/1000 (95%) | 1000/1000, tries histogram {1: 1000} | PASS |
| Pm1.3 fresh slot_check recount failures on winning raws | 0 | 0/1000 (independent recount, sealed slot_check) | PASS |
| Pm1.4 variety: distinct slotted replies >= 300/1000 (30%); top reply <= 30 rows (3%) | both | 45 distinct; top reply 175 rows (17.5%) | FAIL |
| Pm1.5 crashes | 0 | 0 | PASS |

Fallbacks per status (rows, spoke): OK [350, 350], SAVED [150, 150], UNKNOWN [150, 150],
ABSTAIN [100, 100], CLARIFY [150, 150], FORGOT [100, 100]. Fell back: 0 in every status.
First-try passes per status equal spoke in every status (all 1000 passed on try 1).

Speak speed on the GPU (RTX 5090, cuda, bf16): median 2137.2 ms, p90 2469.3 ms, max 4669.9 ms.
Training: 19.93 min, 2501.7 tok/s, 2500/2500 steps, 2 epochs, no time-cap stop, dev_loss 0.1571.
Dollars: ~$0.88 this rental (contract 52279343, $0.5156/h, alive ~102 min; ceiling $4.00/3 h respected).

## What was run (no sealed file touched; never opened any TEST-ONLY panel or convbench file)

0. GPU: vast.ai contract 52279343, 1x RTX 5090 (32 GB), reliability 0.9886, $0.5156/h, label
   own-m1b, IP 154.9.228.248 (not the dead 180.189.55.38 host). DUPLICATE check at rent time:
   0 instances live. Destroyed at 2026-09-23T20:27Z; confirmed gone (only another agent's
   rsn-294 box remains; never touched). New venv: torch 2.14.0+cu130, transformers 5.17.0,
   peft 0.21.0, safetensors, huggingface_hub. Ledger total stays far under the $30 cap.
1. CODE+DATA: seal check 5/5 OK from /root/m1. M0 rebuilt deterministically
   (scripts/claude_own_m0_build.py from origin/builder-outbox): 20000 train + 1000 dev rows;
   rebuilt dev.jsonl byte-identical (cmp) to origin/builder-outbox dev.jsonl; stats.json
   identical. M1 data build: train kept 20000 dropped 0; dev kept 1000 dropped 0 (as expected).
2. MODEL: huggingface_hub.snapshot_download("openbmb/MiniCPM5-1B"), commit
   87179e5c1f455ef22e6223592d2d61351b525bfc; base model-00000-of-00001.safetensors sha256
   7ab8fd86563125929be78aeec8cb3969c7ed2ead3be1ab9d3ec0a9fa69c8660d (2.1 GB).
3. TRAIN: scripts/claude_lis300_train.py --epochs 2 --lr 2e-4 --rank 32 --batch 16 --max-len 256
   --max-minutes 120 --merge. Batch 16 fit (no OOM, no --batch 8 fallback). 22,413,312 trainable
   params of 1,103,046,144. Merged: /root/work/run/merged/model.safetensors sha256
   b40cc2d694e4c28560a8e8c57038ed88610fa38bcc97789012e37ab38aaff2d7.
4. SEAL: SEAL-run.sha256.txt written BEFORE measuring (merged safetensors + data counts.json
   01ebea10d985a125753884919ae0ad2c281ec1b8c21f0d54b486bb5baf9dedaf).
5. MEASURE ONCE: speak.py over the 1000 dev rows, one run only. Pm1.3 recounted independently
   with the sealed slot_check on every non-null reply's winning raw (last non-empty raw):
   0 failures / 1000.
6. Model kept at ~/premonition-models/own-m1-mouth/ (model.safetensors + config + tokenizer
   files); sha256 matches the seal: b40cc2d6... Weights never in git.

## Diagnosis note for Pm1.4 (one note, per PASSMARKS)

M0 dev itself carries 339 distinct slotted replies (most common template: 7 rows, 0.7%), so the
data does not cap variety at 45. The trained mouth keeps only the head template(s) per status
(e.g. OK answers collapse to "Yeah, <S1>'s <R1> is <V1>." ± a follow-up question: 175 + 162 of
350 OK rows). Greedy decoding is over-confident after 2 epochs at lr 2e-4; every row passed on
try 1, so the 4 sampled retries never got used on dev. A follow-up could try: fewer epochs /
lower lr, temperature on the first try, or a variety term — director's call, exactly one change.

## Deviations (3, all disclosed; sealed code and sealed data untouched)

- D1: vast.ai `attach ssh` with the numeric key id did not grant SSH (Permission denied after
  reboot); re-attaching with the full public-key string worked (SSH_OK). No key printed anywhere.
- D2: first training launch crashed before step 1 (torch 2.14/triton JIT needs a host C
  compiler; image has none). Installed gcc 11.4 via apt (environment fix, not a code patch) and
  re-ran the full 2-epoch training from scratch; the crashed attempt wrote no weights and is
  discarded. Sealed scripts untouched.
- D3: watchdog polls stretched from ~60 s to ~115 s during the ~40 min speak run; instance
  actual_status=running and dev_out.jsonl grew on every poll (no 10-min stall rule triggered;
  no re-rent needed — exactly one instance ever live for this task).

## 20 random dev rows (seed 7; dev material, fictional names): status | user turn | filled reply (all try 1)

1. OK | "what is Hrallo's friend" | "Yeah, Hrallo's friend is Yvallo."
2. FORGOT | "unremember Trallo's sport" | "Okay, forgotten. I no longer hold what Trallo's sport is."
3. OK | "Frella's hometown?" | "Yeah, Frella's hometown is Ploverst."
4. SAVED | "Frella's doctor is Ivallo btw" | "Got it, and saved. Frella's doctor is Ivallo."
5. ABSTAIN | "Lrella's sister?" | "I have no idea who Lrella's sister is, sorry."
6. OK | "whats Frella's favorite food" | "Yeah, Frella's favorite_food is cheese. Want me to remember anything else about Frella?"
7. OK | "what sport does Vrallo like" | "Yeah, Vrallo's sport is skating."
8. CLARIFY | "Lrella?" | "Which Lrella are you after? I know two, I mean."
9. UNKNOWN | "Where is Jrallo's workplace?" | "I don't know that one. Where Jrallo's work_location is hasn't come up."
10. OK | "Xrallo's father's brother?" | "Yeah, Xrallo's father's brother is Lvallo."
11. SAVED | "Frella's mentor is Kvella" | "Got it, and saved. Frella's mentor is Kvella."
12. UNKNOWN | "whos Zrallo's father" | "I don't know that one. Who Zrallo's father is hasn't come up."
13. OK | "what is Brella's mentor" | "Yeah, Brella's mentor is Kvella. Want me to remember anything else about Brella?"
14. FORGOT | "forget crella's mother pls" | "Okay, forgotten. I no longer hold who Crella's mother is."
15. UNKNOWN | "hey who is Rrallo's cousin btw" | "I don't know that one. Who Rrallo's cousin is hasn't come up."
16. OK | "where is jrallo's city" | "Yeah, Jrallo's city is Glenhaven. Want me to remember anything else about Jrallo?"
17. OK | "Hrallo's brother's cousin?" | "Yeah, Hrallo's brother's cousin is Gvella. Want me to remember anything else about Hrallo?"
18. OK | "do u know Lrallo's sport" | "Yeah, Lrallo's sport is darts. Want me to remember anything else about Lrallo?"
19. SAVED | "oh btw Hrallo's workplace is Foxglove" | "Got it, and saved. Hrallo's work_location is Foxglove."
20. SAVED | "so Hrallo's teacher is Kvella" | "Got it, and saved. Hrallo's teacher is Kvella."

## What this means / doesn't mean (plain English)

The mouth learned the grammar of safe replies perfectly: every one of 1000 test replies used the
name slots correctly, stated values exactly when required, and never leaked or invented a name —
checked twice, by the speaker itself and by an independent recount (0 failures both times). What
it did not learn is variety: it answers almost everything with the same few sentence shapes
("Yeah, ... is ...."). For a mouth that must never garble a name, format-perfect but repetitive
is the safer half to have; but the registered variety bar (30% distinct, top shape <= 3%) is
missed by a mile (4.5%, 17.5%), so the run is a registered FAIL and needs the director's one
follow-up change before this mouth ships. Nothing here says anything about conversation quality
(M3/convbench-f0 was never opened) or about the ear.
