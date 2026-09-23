# lis-301 registered result: FAIL (P301.2 recall 51/145 = 35.2%, bar 85%)

Builder run 2026-09-23 on BensPC (RTX 5070 Ti, CUDA). Sealed code imported and
run unmodified. Panel 301 run once. Category counts only; no panel turn is quoted.

## Marks table (arm A = reader + compiler at T = 0.995)

| Mark | Bar | Got (integers) | Verdict |
|---|---|---|---|
| P301.1 wrong-save turns | ≤ 1 of 240 | 0 of 240 | PASS |
| P301.2 exact recall of gold writes | ≥ 85% | 51 of 145 = 35.2% | FAIL |
| P301.3 ASK turns read correctly | ≥ 90% | 34 of 40 = 85.0% | FAIL |
| P301.4 our/we turns that ask whose | ≥ 90% | 17 of 18 = 94.4% | PASS |
| P301.5 unparseable outputs | ≤ 2% of turns | 0 of 240 = 0% | PASS |
| P301.6 median read time on GPU | ≤ 1,500 ms | 1522.7 ms | FAIL |

Overall verdict: FAIL. P301.2 also lands under 75%, and dev still has no
zero-wrong T below 0.995 (minimum 2 wrong turns at t=0.980/0.990/0.995), so two
of the three PASSMARKS "proved wrong" clauses trip: more hard-case data alone
does not make the reader safe and useful at once, and the next step is a
different mechanism, not more rows.

## What the threshold buys (report only)

- At T = 0.995: 51 pred writes, 51 hits, 0 wrong facts, 0 wrong turns, 93 held-back facts.
- At T = 0: 147 pred writes, 142 hits, 5 wrong facts, 4 wrong turns, 0 held-back facts.
- Wrong facts per saved fact: 0/51 at T, 5/147 at T = 0.
- Wrong facts per turn: 0/240 at T, 4/240 at T = 0.
- Recall: 51/145 (35.2%) at T, 142/145 (97.9%) at T = 0.
- The reader itself still reads well (97.9% with no gate); the 0.995 gate holds
  back 93 of 145 gold facts to reach 0 wrong saves.

## Recall by family at T (hits / gold writes, category level only)

- tell-single 6/14; tell-multi 2/24; tell-plural 9/18; tell-appositive 0/21;
  tell-verb 6/12; tell-typo 5/8; tell-self 5/7.
- correct (uses prev_reply) 9/19. short-answer (uses prev_reply) 3/7.
- pronoun-clear 5/13. pronoun-ambiguous 0 gold writes, 0 wrong turns.
- our-we: 0 gold writes, 0 wrong turns (17 of 18 asked whose).
- negation/check/suppose/plan/reported/chat: 0 gold writes each, 0 wrong turns each
  (12/12/10/10/8/8 turns).
- questions: wh ask 11/11 (1 gold write held back); inverse 6/8; yesno 7/7
  (+1 write hit); lowercase 5/7; twohop 3/5. ASK misses: 6 total
  (2 inverse, 2 lowercase, 2 twohop).
- The 0 wrong-save turns at T: no family wrote a wrong fact.
- At T = 0 the 4 wrong turns are: 1 pronoun-ambiguous, 1 tell-typo, 1 our-we,
  1 tell-appositive (2 of the 4 on no-save turns).

## Timing, training, money

- Read device: BensPC NVIDIA GeForce RTX 5070 Ti, cuda, greedy decode.
- Panel read ms (240 turns): median 1522.7, p90 2158.8, max 2942.8.
- Dev read ms (959 turns): median 1482.1, p90 2213.7, max 3684.1.
- Training: 4622/4622 steps, 2 epochs, 26.05 minutes, 4727.7 tok/s,
  dev loss 0.0545, LoRA trainable 22,413,312 of 1,103,046,144 params,
  batch 16 (no OOM, no fallback), lr 2e-4, rank 32, seed 300.
- Base model: same openbmb/MiniCPM5-1B snapshot as lis-300 (reused download),
  model-00000-of-00001.safetensors sha256
  7ab8fd86563125929be78aeec8cb3969c7ed2ead3be1ab9d3ec0a9fa69c8660d (verified
  on BensPC before training; commit 87179e5c as in lis-300 RESULTS.md).
- Merged reader: sha256 b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890,
  kept at ~/premonition-models/lis301-merged/ (Mac, hash verified) and on BensPC
  at C:/Users/benja/lis301/work/run/merged/. Never in git.
- Dollars spent: $0. BensPC used (free). No vast.ai rental. No other instance running.

## Data built (recorded counts)

- SEAL.sha256.txt checks from the BensPC repo copy before building:
  lis-300 seal 14/14 OK, lis-301 seal 13/13 OK.
- Built set: train 36,972 (o0b 27,000 + opus 5,012 + opus301 4,960 = 1,240
  agreed non-dev rows x4), dev 959 (o0b_l2 428 + opus_dev 131 + o0a2 263 +
  opus301_dev 137), opus301 agreed 1,377, dev dropped by relabel 45
  (opus_dev 8 + o0a2 37). Matches DATA-AUDIT.md exactly.
- Threshold: no sweep grid value reached 0 wrong-save dev turns (minimum 2 at
  t=0.980, t=0.990 and t=0.995), so T = 0.995 by the sealed rule. At T, dev:
  462/761 hits (60.7%), 2 wrong turns (both o0a2 family rows), ask 77/81,
  we 13/13. Sealed in SEAL-run.sha256.txt BEFORE the panel.
- Panel key seal: 2/2 OK (panel.jsonl + key_v2.jsonl). Reader ran on the 240-turn
  panel exactly once; scored at T and at T = 0.

## Deviations (env only; sealed code untouched)

1. Reused the lis-300 venv (torch 2.11.0+cu128, transformers 5.17.0, peft 0.21.0)
   and the downloaded base-model snapshot (safetensors sha256 re-verified) instead
   of a new venv and re-download; new work dir C:/Users/benja/lis301 used throughout.
2. Windows cp1252 default: set PYTHONUTF8=1 (env var only), as in lis-300.
3. Train launched with the venv certifi bundle in REQUESTS_CA_BUNDLE/SSL_CERT_FILE
   (env vars only; training itself is offline after the snapshot reuse).
4. No OOM at batch 16, so the batch-8 fallback was not used. max-minutes 150
   cap never bound (run took 26.05 min).

## What it means (plain high-school English)

- The extra hard-case rows did buy safety: the blind panel now has 0 wrong saves
  (lis-300 had 1), and dev wrong turns fell from 6 to 2 at the top threshold.
- But the safety gate still throws away almost two thirds of the true facts
  (93 of 145 held back), so recall collapsed to 35.2% (lis-300 had 51.8%).
  Safe and useful were not reached together, and dev still has no threshold with
  zero wrong turns, so adding rows alone is not fixing it.

## What it doesn't mean

- It doesn't mean the reader can't read: with no threshold it gets 142 of 145
  facts (97.9%), same as lis-300.
- It doesn't mean the test leaked: panel names N-Z never trained on (A-M only),
  run once, seals checked first (data 14/14 + 13/13, key 2/2, run sealed pre-panel).
- Per PASSMARKS, the next step is a different mechanism, not more rows.
