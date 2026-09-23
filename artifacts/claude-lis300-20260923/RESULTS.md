# lis-300 registered result: FAIL (P300.2 recall 71/137 = 51.8%, bar 85%)

Builder run 2026-09-23 on BensPC (RTX 5070 Ti, CUDA). Sealed code imported and
run unmodified. Panel run once. Category counts only; no panel turn is quoted.

## Marks table (arm A = reader + compiler at T = 0.995)

| Mark | Bar | Got (integers) | Verdict |
|---|---|---|---|
| P300.1 wrong-save turns | ≤ 1 of 240 | 1 of 240 | PASS |
| P300.2 exact recall of gold writes | ≥ 85% | 71 of 137 = 51.8% | FAIL |
| P300.3 ASK turns read correctly | ≥ 90% | 38 of 40 = 95.0% | PASS |
| P300.4 our/we turns that ask whose | ≥ 90% | 20 of 20 = 100% | PASS |
| P300.5 unparseable outputs | ≤ 2% of turns | 0 of 240 = 0% | FAIL-free, PASS |
| P300.6 median read time on GPU | ≤ 1,500 ms | 1492.45 ms | PASS |

Overall verdict: FAIL. P300.2 also lands under 75%, which trips the PASSMARKS
"proved wrong" clause: at the sealed threshold rule the threshold/compiler is
too strict to be useful.

## What the threshold buys (report only)

- At T = 0.995: 72 pred writes, 71 hits, 1 wrong fact, 1 wrong turn, 66 held-back facts.
- At T = 0: 140 pred writes, 133 hits, 7 wrong facts, 7 wrong turns, 1 held-back fact.
- Wrong facts per saved fact: 1/72 at T, 7/140 at T = 0.
- Wrong facts per turn: 1/240 at T, 7/240 at T = 0.
- Recall: 71/137 (51.8%) at T, 133/137 (97.1%) at T = 0.
- The reader itself reads well (97.1% with no gate); the 0.995 gate holds back
  66 of 137 gold facts yet still lets 1 wrong save through.

## Recall by family at T (hits / gold writes, category level only)

- tell-single: 11/14 turns exact-ish 11/14 writes hit; tell-multi 8/21; tell-plural 11/17;
  tell-appositive 6/20; tell-verb 7/12; tell-typo 5/8; tell-self 6/8.
- correct (uses prev_reply): 7/17. short-answer (uses prev_reply): 4/8.
- pronoun-clear: 6/12. pronoun-ambiguous: 0 writes gold, 1 wrong-save turn.
- our-we: 0 gold writes, 0 wrong turns (all 20 asked whose).
- negation/check/suppose/plan/reported/chat: 0 gold writes each, 0 wrong turns each.
- questions: wh 12/12, inverse 8/8, yesno 8/8, lowercase 7/7, twohop 3/5 ask-ok.
- The single wrong-save turn is in pronoun-ambiguous (a no-save turn).
- At T = 0 the 7 wrong turns are: 5 pronoun-ambiguous, 1 tell-verb, 1 tell-typo.

## Timing, training, money

- Read device: BensPC NVIDIA GeForce RTX 5070 Ti, cuda, greedy decode.
- Panel read ms (240 turns): median 1492.45, p90 2051.0, max 3115.1.
- Dev read ms (867 turns): median 1505.3, p90 2169.9, max 3745.2.
- Training: 4002/4002 steps, 2 epochs, 21.78 minutes, 4851.9 tok/s,
  dev loss 0.0842, LoRA trainable 22,413,312 of 1,103,046,144 params,
  batch 16 (no OOM, no fallback), lr 2e-4, rank 32, seed 300.
- Base model: openbmb/MiniCPM5-1B commit 87179e5c1f455ef22e6223592d2d61351b525bfc,
  model-00000-of-00001.safetensors sha256
  7ab8fd86563125929be78aeec8cb3969c7ed2ead3be1ab9d3ec0a9fa69c8660d (2,161,290,912 bytes).
- Merged reader: sha256 112880d610173aef9b39715e0f6db51a16af8dece42dbd7132b83c0be8285324,
  kept at ~/premonition-models/lis300-merged/ (Mac, hash verified) and on BensPC
  at C:/Users/benja/lis300/work/run/merged/. Never in git.
- Dollars spent: $0. BensPC used (free). No vast.ai rental. No other instance running.

## Data built (recorded counts)

- SEAL.sha256.txt check from repo root on BensPC: 14/14 OK before building.
- Built set: train 32,012 (o0b 27,000 + opus 5,012 = 1,253 agreed x4),
  dev 867 (o0b_l2 428 + opus_dev 139 + o0a2 300),
  opus agreed 1,392, o0b pronoun-owner dropped 20,000. Matches DATA-AUDIT.md.
- Threshold: no sweep grid value reached 0 wrong-save dev turns (min 6 at 0.995),
  so T = 0.995 by the sealed rule. Sealed in SEAL-run.sha256.txt BEFORE the panel.
- Panel key seal: 2/2 OK (panel.jsonl + key_v2.jsonl). Reader ran on the 240-turn
  panel exactly once; scored at T and at T = 0.

## Deviations (env only; sealed code untouched)

1. Windows cp1252 default broke opus jsonl reads -> set PYTHONUTF8=1 (env var only).
2. BensPC has a stale system REQUESTS_CA_BUNDLE pointing at a deleted file ->
   pointed it at the venv certifi bundle (env var only).
3. New venv first got a CPU-only torch -> installed torch 2.11.0+cu128 from the
   PyTorch cu128 index into the same NEW venv (pip install allowed by brief).
   Final env: torch 2.11.0+cu128, transformers 5.17.0, peft 0.21.0.
4. Detached (`start`) processes die when the SSH session closes (probe proved it:
   a 30-s ping-to-file never wrote). Training ran in the foreground of one SSH
   call; it survived a client-side tool timeout and finished server-side.
5. No OOM at batch 16, so the batch-8 fallback was not used. max-minutes 150
   cap never bound (run took 21.78 min).

## What it means (plain high-school English)

- The home-trained 1B listener reads sentences about as well as hoped when the
  safety gate is off (133 of 137 facts right), asks whose for every our/we turn
  (20 of 20), and reads questions right (38 of 40).
- But the safety rule picked on dev (only save when 99.5% sure) throws away
  about half the true facts (66 of 137 held back) and still lets one wrong save
  through on the blind panel. Safe-and-useful was not reached together.

## What it doesn't mean

- It doesn't mean the reader can't read: with no threshold it gets 97.1%.
- It doesn't mean the panel was easy or leaked: names N-Z never trained on
  (A-M only), run once, seals checked first.
- One diagnosis-driven follow-up (lis-301+) is allowed by PASSMARKS.
