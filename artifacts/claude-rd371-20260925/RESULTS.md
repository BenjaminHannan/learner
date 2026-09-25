# rd-371: learned verifier replaces the min-token cutoff — GPU run report (2026-09-25)

Verdict: FAIL (V1 and G1 fail; the PASSMARKS "proved wrong" clause is TRUE).
Plain English: we trained a second small model whose only job was to double-check
each fact the reader wrote down, hoping it would rescue good facts the strict
0.995 cutoff throws away. It did the opposite: on the sealed 240-turn panel it
saved only 15 right facts while the plain cutoff saved 106. It was safe
(0 wrong turns) and fast (+19 ms), but it held back nearly everything, including
on dev (400 hits vs 462). The strict cutoff remains the better gate.

## Marks (PASSMARKS.md table, integer counts)

| Mark | Bar | Measured | Result |
|---|---|---|---|
| V1 more right facts saved | B saved_right >= A + 30 (106 + 30 = 136) | B 15 vs A 106 | FAIL |
| proved-wrong clause | B saved_right <= A + 10 (116) | 15 <= 116 | TRUE (hypothesis proved wrong) |
| V2 safe | B wrong_turns <= 2 and <= A + 1 (3) | B 0 vs A 2 | PASS |
| V3 no invention | B nofact_rows_with_save <= 1 | B 0 (key absent = 0; scorer only writes the key when > 0) | PASS |
| G1 dev all-or-nothing hits | B at T_B >= A at 0.995 | B 400 vs A 462 | FAIL |
| G2 time | B median ms <= A + 400 (1357.9) | B 976.6 vs A 957.9 (+18.7) | PASS |

PASS required all five. Overall: FAIL.

## Panel scores verbatim (scorer counts only, 240 rows, 426 gold facts, reader R0 342)

score_A.json (reader + min-token 0.995):

```json
{
 "rows": 240,
 "gold": 426,
 "R0": 342,
 "saved_right": 106,
 "held_right": 236,
 "saved_wrong": 2,
 "wrong_turns": 2,
 "threshold": 0.995,
 "ms_median": 957.9,
 "per_kind": {
  "correct:R0": 21,
  "correct:gold": 22,
  "correct:saved_right": 1,
  "long_multi:R0": 153,
  "long_multi:gold": 202,
  "long_multi:saved_right": 38,
  "short_answer:R0": 14,
  "short_answer:gold": 17,
  "short_answer:saved_right": 1,
  "short_answer:wrong_turns": 1,
  "teach_single:R0": 28,
  "teach_single:gold": 30,
  "teach_single:saved_right": 13,
  "trap:R0": 126,
  "trap:gold": 155,
  "trap:saved_right": 53,
  "trap:wrong_turns": 1
 }
}
```

score_B.json (same reads + verifier at T_B 0.9999):

```json
{
 "rows": 240,
 "gold": 426,
 "R0": 342,
 "held_right": 327,
 "saved_wrong": 0,
 "wrong_turns": 0,
 "saved_right": 15,
 "threshold": 0.9999,
 "ms_median": 976.6,
 "per_kind": {
  "correct:R0": 21,
  "correct:gold": 22,
  "correct:saved_right": 1,
  "long_multi:R0": 153,
  "long_multi:gold": 202,
  "long_multi:saved_right": 1,
  "short_answer:R0": 14,
  "short_answer:gold": 17,
  "teach_single:R0": 28,
  "teach_single:gold": 30,
  "teach_single:saved_right": 5,
  "trap:R0": 126,
  "trap:gold": 155,
  "trap:saved_right": 8
 }
}
```

Per-kind saved_right / wrong (report-only): correct 1/0 vs 1/0, long_multi 1/0 vs
38/0, short_answer 1/0 vs 1/1 wrong turn, teach_single 5/0 vs 13/0,
trap 8/0 vs 53/1 wrong turn. No panel text is quoted anywhere in this report.

## Cutoff sweep (lis-301 dev, 959 turns, 761 gold writes; full curve in SWEEP.json)

Printed grid (wrong_save_turns, recall of 761):

- t=0.5: 6, 725 | t=0.7: 6, 725 | t=0.8: 6, 724 | t=0.9: 5, 722
- t=0.95: 3, 718 | t=0.97: 3, 718 | t=0.98: 3, 713 | t=0.99: 3, 705
- t=0.995: 3, 682 | t=0.998: 3, 632 | t=0.999: 2, 590
- t=0.9995: 1, 529 | t=0.9999: 1, 400

T_B = 0.9999 (no grid value reached 0 wrong-save turns, so the largest grid
value per the registered rule). At T_B: 400 hits, 1 wrong turn (o0a2 family),
1 wrong turn on a no-save turn.

G1 detail: B at 0.9999: hits 400, pred_writes 401, wrong_facts 1, turn_exact 261,
held_back 356. A at 0.995: hits 462, pred_writes 464, wrong_facts 2,
turn_exact 347, held_back 294, wrong_turns 2.

## Data (DATA.json; printed counts)

- rdata (claude_lis318_data.py): train 45124, dev 1181
  (chat318_agreed 2260, chat318_dev 222).
- vdata (claude_rd371_data.py): train 22498 (expected 22498 OK), dev 1200
  (expected 1200 OK). yes/no: o0b 8000/8000, opus 797/797, opus301 905/905,
  chat318 2147/2147. no kinds: swap 2407, owner 2406, value 2406, rel 2406,
  mode 2207, we_me 17.

## Training

- 2814 steps (planned 2814, stopped null), 2 epochs, lr 2e-4, rank 32,
  batch 16, max-len 256, seed 300, --merge. No OOM, no --batch 8 fallback.
- 5.75 minutes, 7998.6 tok/s, device cuda, dev loss 0.014528447382472222,
  trainable params 22413312 / 1103046144.
- BASE openbmb/MiniCPM5-1B commit 87179e5c1f455ef22e6223592d2d61351b525bfc
  (matches expected). MiniLM and self122_head.pt not needed; route122 check
  skipped per task.
- Merged model sha256:
  41a84ce67c0dddecff36985725aee61149ce3c205a908936ee183d0add257d86
  (sealed in SEAL-run.sha256.txt BEFORE the panel read; Mac copy at
  ~/premonition-models/rd371-verifier-merged/ sha matches). Weights never in git.

## Setup and wall time (UTC 2026-09-25)

- GPU: 1x RTX 5090, 16 CPU, vast.ai instance 52641003 (offer 52190811,
  reliability >= 0.98 filter, dph billed $0.5037). Created 19:47:46, running
  at once (inside the 6-min rule), destroyed ~20:32. ~0.74 h x $0.5037 = ~$0.37
  of the $1.50 budget. Credit $7.42 at start (no CREDIT-STOP). No duplicate
  label; 1 rental total (no HOST-FAIL). `vastai show instances` after destroy:
  0 rent-rd-371 live. Torch 2.8.0+cu128 (image torch, CUDA True).
- Tree: `git archive origin/builder-outbox` + `git archive origin/main`
  (main on top), 169 MB tgz. Seals from tree root all OK: lis300, lis301,
  lis318-data, readpanel371 (in its dir). READER (~/premonition-models/
  lis301-merged, rsync --partial, one resume after a broken first pass) sha256
  b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890 on Mac
  and box.
- DATA steps 20:02-20:03 (both EXIT 0). TRAIN first attempt 20:04 EXIT nonzero
  (ModuleNotFoundError peft); restarted ~20:05 after `pip install peft`
  (0.21.0, environment only, code untouched), done 20:12. Dev verify 20:16-20:18
  (1072 facts, EXIT 0). Sweep + G1 ~20:18-20:19. SEAL-run written 20:19:19.
  Panel: read 20:20-20:23 (READER read panel.jsonl exactly once), verify +
  both scores done 20:24 (all four EXIT 0). Copy-back + model rsync 20:25-20:30,
  sha verified before destroy. No 10-min watchdog trip (all steps logged).
- The BensPC copy of this task (handoff/held) was never run.

## Deviations and misses

1. Kit pip line did not include `peft`, which claude_lis300_train.py imports:
   exact error `ModuleNotFoundError: No module named 'peft'`. Installed peft
   0.21.0 on the box (environment fix, script unedited) and restarted. Batch 16
   held, so the --batch 8 fallback was not used. Reported, not hidden.
2. Offer 52190811 listed $0.469 but billed $0.5037; cost uses billed dph.
3. score files omit `nofact_rows_with_save` when it is 0 (Counter only writes
   the key when the branch fires); V3 = 0 read from the absent key.
4. V1 miss by 121 facts (15 vs needed 136); G1 miss by 62 dev hits (400 vs 462).

## What this means / doesn't mean

- Means: at its dev-chosen cutoff, the learned verifier is far more
  conservative than the 0.995 min-token rule and saves fewer right facts on
  both dev and the sealed panel, while staying safe (0 wrong). The registered
  "proved wrong" clause fired: the verifier does not recover right facts the
  cutoff throws away.
- Doesn't mean: verifiers can never work, or the reader is good enough as is
  (the cutoff still held back 236 right panel facts). It means this verifier,
  this data mix, and this cutoff rule did not beat the cutoff.
