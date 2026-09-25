# rsn-355 RESULTS (builder, 2026-09-25, BensPC GPU)

## Verdict: FAIL

H1 fails on both seeds (three-step still 0/30 after the shared-step fix), H2 passes on
seed 1 but fails on seed 2, H3 passes everywhere. PASS needed H1+H2+H3 on both seeds.

## Marks (final checkpoints, checked right, integer counts)

| mark | seed 1 | seed 2 | bar | result |
|---|---|---|---|---|
| H1 panel296 v2 heldout_three_step (/30) | 0 | 0 | >= 6/30 both seeds | FAIL both |
| H2 panel296 v2 total WITHOUT three-step | 223 | 197 | s1 >= 220, s2 >= 212 | PASS s1, FAIL s2 |
| H3 invented answers checked, panel296 | 0 | 0 | <= 2 each panel | PASS both |
| H3 invented answers checked, panel294 | 0 | 0 | <= 2 each panel | PASS both |
| H4 panel294 v3 heldout_three_step (/15) final | 0 | 0 | report | n/a |
| H4 panel294 v3 heldout_three_step (/15) copy | 0 | 0 | report | n/a |
| H4 dev value3 (/100) final | 0 | 0 | report | n/a |
| H4 dev value3 (/100) copy | 0 | 0 | report | n/a |

Proved-wrong clause ("H1 <= 1/30 on both seeds while H2 passes", i.e. the untrained slot
was the blocker and the net still cannot chain past practice): H1 is 0/30 on both seeds,
but H2 passes only on seed 1 (seed 2: 197 < 212). So the clause triggers for seed 1 and
does NOT trigger cleanly overall / for seed 2. The shared input did not unlock three-step
on either seed; seed 2 additionally lost ground elsewhere (comparing 0/30 checked, counting
8/30 checked after practice).

## Training (defaults: copy 6000 + RL 6000, batch 256/128, lr 3e-4, plain arm 30m, 31349141 params)

| run | minutes | copy action_ce first -> last | practice reward mean per 1000 steps |
|---|---|---|---|
| plain355-s1 (seed 1) | 43.9 | 3.8230 -> 0.0136 | 0-999: 0.7729, 1000-1999: 0.8334, 2000-2999: 0.8611, 3000-3999: 0.8490, 4000-4999: 0.8440, 5000-5999: 0.8919 |
| plain355-s2 (seed 2) | 43.8 | 3.8834 -> 0.0007 | 0-999: 0.7978, 1000-1999: 0.8061, 2000-2999: 0.8277, 3000-3999: 0.8509, 4000-4999: 0.8581, 5000-5999: 0.8438 |

Device cuda, torch 2.11.0+cu128 (lis300 venv). Copy phase ~15.7 min, practice ~28 min.

## Panel296 v2 (fresh, n=298) per-category checked right

order: backwards / before_after / comparing / counting / heldout_three_step / missing_fact /
newest_correction(n=28) / one_step / two_step / yes_no; raw and checked totals at end.

| ckpt | by-category checked | raw right / checked right |
|---|---|---|
| s1 copy_only | 30 / 3 / 0 / 0 / 0 / 30 / 19 / 30 / 18 / 30 | 168 / 160 |
| s1 final | 30 / 18 / 16 / 17 / 0 / 30 / 22 / 30 / 30 / 30 | 217 / 223 |
| s2 copy_only | 30 / 12 / 0 / 0 / 0 / 30 / 20 / 30 / 29 / 30 | 177 / 181 |
| s2 final | 30 / 19 / 0 / 8 / 0 / 30 / 20 / 30 / 30 / 30 | 205 / 197 |

Raw invented-without-fact on 296 panels: 6 (s1 final), 5 (s2 final), 5/5 copy; every one
fact-checked to IDK, so checked invented = 0. H2 check: s1 223-0=223 >= 220 PASS;
s2 197-0=197 < 212 FAIL.

## Panel294 v3 (transfer, n=300) per-category checked right

order: backwards / before_after / comparing / counting / heldout_big_notebook(n=15) /
heldout_three_step(n=15) / missing_fact / newest_correction / one_step / two_step / yes_no.

| ckpt | by-category checked | raw right / checked right |
|---|---|---|
| s1 copy_only | 30 / 1 / 0 / 0 / 15 / 0 / 30 / 30 / 30 / 19 / 30 | 196 / 185 |
| s1 final | 30 / 17 / 12 / 21 / 15 / 0 / 30 / 30 / 30 / 30 / 30 | 245 / 245 |
| s2 copy_only | 30 / 11 / 0 / 0 / 15 / 0 / 30 / 30 / 30 / 30 / 30 | 206 / 206 |
| s2 final | 30 / 19 / 0 / 12 / 15 / 0 / 30 / 30 / 30 / 30 / 30 | 238 / 226 |

Checked invented on 294 panels: 0 everywhere (no raw inventions either).

## Dev (fresh generator, seed 777, n=100 per kind + big_notebook)

dev value3 checked right: s1 copy 0/100, s1 final 0/100, s2 copy 0/100, s2 final 0/100
(all checked IDK; raw wrong 95/95/96/92, rest raw IDK).
dev totals checked: s1 copy 738/1200, s1 final 947/1200, s2 copy 777/1200, s2 final 851/1200.

## Moves (every step)

1. SEAL: `git archive origin/main` to temp dir, `shasum -a 256 -c` on SEAL-code.sha256.txt
   (6/6 OK), reasonpanel296 SEAL-v2 (2/2 OK), reasonpanel294 SEAL-v3 (2/2 OK).
2. CODE: tar of scripts + the three artifact dirs copied to BensPC, extracted to
   C:/Users/benja/premonition-models/rsn355/code keeping paths. nvidia-smi: RTX 5070 Ti
   16 GB, driver 591.86, CUDA 13.1. C: ~53 GB free. CPU AMD Ryzen 5 7600X 6C/12T.
   Venv C:/Users/benja/lis300/venv, torch 2.11.0+cu128, cuda True.
   `claude_rsn296_gen.py` selftest ok (row buckets + 0 gold-action mismatches).
3. PILOT: seed 9, copy 100 + RL 50, --workers 0: exit 0, 30.7 s wall (train minutes 0.5;
   copy min 0.02->0.25, RL min 0.26->0.46). Full estimate 60x0.25+120x0.21 ~= 40 min.
   Two-at-once (seeds 8+9): 32.9 s wall, both exit 0. Chose 2-at-a-time (~44 min wall for
   both full runs vs ~88 min sequential). Under 8 h, proceeded.
4. TRAIN: both seeds, full defaults + --workers 0, launched together, exit 0, 43.9/43.8 min.
5. SEAL-run.sha256.txt written BEFORE any eval (hashes below).
6. EVAL once per checkpoint (12 commands, category counts only, items never opened):
   dev + panel296 + panel294 for copy_only.pt and final.pt of both runs. ALL-EVALS-DONE.
7. Copied back 16 files (train_log.jsonl, train_summary.json, dev-copy/final.json,
   panel296/294-copy/final.json per run) into runs/plain355-s1, runs/plain355-s2.
8. Checkpoints KEPT on BensPC only (never pushed, never copied to Mac):
   C:/Users/benja/premonition-models/rsn355/plain355-s1/{copy_only.pt,final.pt}
   C:/Users/benja/premonition-models/rsn355/plain355-s2/{copy_only.pt,final.pt}
   sha256 (lowercase, SEAL-run.sha256.txt):
   s1/copy_only cd2f811dbbe6fc08ad05da301ff904ff2d5f30f2f886e6a8b4e3df1daa0a617a
   s1/final     fc6090b1592107e3bf4f47c3546aa748b4eea5bb46a117051b4e709f4d8e4291
   s2/copy_only a7f731c4729e629825048dde5678d824d45d314e95b5afe75d531c483c310ba7
   s2/final     9baca68d207cb404c7d587bf53be94eacc68acc51987991c5dc923d7aa8284e4
   (kept copies hash-match the trained files; ~125 MB each).

## Deviations and misses

- D1 (registered in plan): --workers 0 on Windows; same generator and seeds, different
  practice-puzzle stream than rental runs.
- D2: OPUS-RULES.txt path from the brief did not exist (empty scratchpad dir); worked from
  the brief's summary of the rules (additive-only, append-only ledger, sealed code unedited,
  panels once/category-only, no weights pushed). Nothing existing was edited or deleted;
  ledger touched only by append.
- D3: first detached launch (Start-Process) died silently on ssh disconnect (empty logs,
  PIDs gone, GPU idle); relaunched via WMI Win32_Process.Create, which survived disconnect
  (GPU 67-86%, both PIDs alive to completion). No code changed; no extra training.
- Misses: none in procedure (seals all OK, both trains exit 0, all 12 evals exit 0, all 16
  files copied back). Result misses are the H1/H2 fails above.

## What this means (plain English)

The shared "chain step" input did not teach the net to answer three-step questions: it got
0 out of 30 on both tries, same as before the fix, and it always said "I don't know" there
(which is honest, not a lie: invented-answer count is 0). On seed 1 everything else held up,
so the old "untrained slot" story looks wrong for that seed -- the net just does not chain
a third lookup even when the input is trained. On seed 2 the net additionally got worse at
comparing/counting questions, so that seed fails the do-no-harm bar too. Bottom line for the
director: input fix tested and not the blocker; the next step per the plan is practising
three-step itself, not more input fixes. This does not show anything about other skills, and
"0/30" does not mean the net is broken -- it means this one new trick did not transfer.
