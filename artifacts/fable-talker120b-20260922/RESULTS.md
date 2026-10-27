# RESULTS — Experiment 120b: talker mouth raw-decode bugs (Muse), 2026-09-22

## Result

O6 stays FAIL (313/500 raw unfaithful, bar <= 50) with a pinned diagnosis:
164 boundary-only, 10 truncation-only, 139 both, 0 other. The largest bucket
traces to a one-character training-mask bug (first target token never in the
loss); the fix needs retraining, so no decode-side re-score can pass O6. The
retrain is prepared frozen + CPU-smoked; the director runs the GPU job.

## Marks table (integers; every seed/case reported, never averaged)

| Mark | Bar | Got | Verdict |
|---|---|---|---|
| O1 after-brake violations | 0/500 | 0/500 (director) | PASS (carried) |
| O2 status correct | >= 480/500 | 486/500 (director) | PASS (carried) |
| O3 OK answers | >= 240/250 | 250/250 (director) | PASS (carried) |
| O5 wire51 replay | 0 wrong writes | 0 (director) | PASS (carried) |
| O6 raw unfaithful | <= 50/500 | 313/500 (reproduced 313/313 exactly) | FAIL |
| Smoke (fixed trainer, 100 CPU steps, bs2, seed 12001) | loss falls | 5.5061 -> 3.7325 | PASS |

## Diagnosis evidence (all from the director's seed-12002 checkpoint, Mac CPU)

1. Prompt check 500/500: decode prompt ids == training serialisation ids —
   decoding is faithful; the defect is trained in.
2. Mask audit (train.py:150-151): `tgt_mask = (pos > pre)` drops position
   `pre`, the first target token: first_target_covered = false (23 of 24
   target tokens masked). Step-0 probe: p_gen = 1.0, diffuse attention, greedy
   emits "ing"/":"/"s". Junk opens 303/313 misses.
3. Truncation is largely independent: forcing the reference's first token
   repairs the tail in only 4/12 cases. Held-out names are 3–4 BPE pieces
   (Farah = F+ar+a+h; Ashford = As+h+for+d; Gideon = G+ide+on;
   Mabel = M+a+b+el); the copy head emits 1–2 pieces then drifts ("Fara",
   "Gide", "Ma", "Ash", "Umarar", "Ximenaenaenain") and leaks serialize words
   ("Sten source", "Vita source"). All 10 pure-truncation cases are SAVED.
4. Status pattern: UNKNOWN/FORGOT/CLARIFY have 0/150 faithful raws (their
   openers "I/Sorry/Which" were never supervised at step 0); OK keeps 162/250.

## The ONE change (targets the 303 junk-bearing misses)

scripts/fable_talker120b_train.py = frozen copy of fable_talker120_train.py
with `pos > pre` -> `pos >= pre` only (diff checked; sha256 below). Mask
verified on 50 train pairs (new covers first target 50/50). Retrain recipe
otherwise identical to exp 120. Expectation stated honestly: boundary-only ->
~0, "both" shrinks to its truncation remainder, truncation-only persists
(separate copy-head experiment needed). O6 may still FAIL after retraining.

Frozen sha256: train bd7515d7…7a2a9, diagnose 239c94cd…7022,
tokenizer bb251982…6024, train.jsonl f4e1cc36…f98cb, heldout.jsonl
f14bd0dd…a04795 (full hashes in design doc / `shasum -a 256`).

## Exact reproduce (Mac)

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_talker120b_diagnose.py --data artifacts/fable-talker120-20260922/data --ckpt artifacts/claude-talker120-run-20260922/fable_talker120_ckpt_last.pt --tok artifacts/fable-talker101-20260921/fable_talker101_tokenizer.json --out artifacts/fable-talker120b-20260922/diag-full.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_talker120b_train.py --ckpt artifacts/fable-talker101-20260921/fable_talker101_smoke_cpu/fable_talker101_ckpt_last.pt --tok artifacts/fable-talker101-20260921/fable_talker101_tokenizer.json --data artifacts/fable-talker120-20260922/data --out artifacts/fable-talker120b-20260922/smoke --steps 100 --bs 2 --ctx 256 --lr 1e-4 --seed 12001 --device cpu
```

GPU one-liner for the director: see design doc 120b (sync + detached launch,
seed 12002, out fable-talker120b-ft). No GPU job launched by this agent; no
BensPC contact; no commits; no other agent's files touched. Decode run
346 s + smoke 13 s, each < 25 min. Deviations: none.

## Questions for Ben

None. Default taken: retrain (not a decode hack), since the unsupervised
position cannot be fixed at decode time without labels.

## What it means

The 313 misses are two trained-in defects with file:line causes, the big one
a single-character mask fix ready for the GPU.

## What it does not mean

The mask fix does not promise O6 — multi-piece name copying is a separate,
unfixed weakness, and this checkpoint cannot be re-scored into a pass.
