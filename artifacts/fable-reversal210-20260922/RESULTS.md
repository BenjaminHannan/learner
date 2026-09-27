# RESULTS — Exp 210: TRUE REVERSAL SPLIT (Muse) — VALID

Registered verdict: **VALID** (R1–R3 hold; one reported driver-only fix, re-run open).

## Marks table (integer counts, scorer v2, every seed/item reported)

| arm | split | n | right | wrong | abstain | contains_gold |
|---|---|---|---|---|---|---|
| loop138i | reversal (50) | 50 | 0 | 3 | 47 | 0 |
| loop138i | control (20) | 20 | 5 | 1 | 14 | 5 |
| smollm-incontext | reversal (50) | 50 | 25 | 25 | 0 | 45 |
| smollm-incontext | control (20) | 20 | 10 | 10 | 0 | 20 |

Plus: checker VIOLATIONS 0 (R1); coverage 70/70 ids both arms (R2);
loop `items_with_inverse_stored` 0/70, `teach_rejects` 9 (all 9 are the
`painter` items: `X is the painter of Y.` is rejected by the loop's ears);
run 243.7 s < 1500 s; seal 6/7 OK post-run (below).

## What happened, per arm

- **Loop138i does not answer reverse questions from the stored forward
  fact.** It stores the taught fact only (0 inverse triples in
  events.jsonl across 70 items) but cannot use it in reverse: 47/50
  reversal abstains (verb questions `Who composed Y?` / `What did X
  compose?` are outside its closed verb tables: only
  lives-in/works-for/works-at/speaks/born-in). 3 reversal wrongs are
  smalltalk misfires (`I do not have favourites.` ×2 on `Who designed…?`,
  `You never told me why.` ×1), 0 contain gold. Controls: 5/20 right
  (all O_FIRST `Who PAST Y?` where the relation read succeeded), 14
  abstain, 1 wrong. So: taught facts only, no reverse lookup at question
  time (190-style lookup does not fire for these verbs).
- **SmolLM in-context gets half the reversals exactly (25/50) and
  contains gold in 45/50.** Its 25 wrongs mostly echo the taught sentence
  (`Marisol Underbough wrote Oaken Melodies.`) so scorer-v2 exact-match
  marks them wrong — retrieval works, answer shaping does not. Controls
  10/20 right, same pattern. This is the signal the broken bench65 split
  could never give: one direction taught, gold never in the question.

## Deviations (all open, none silent)

1. **Driver-only fix after the seal** (reported per rules): the coverage
   check keyed arm `smollm` instead of `smollm-incontext` (KeyError, first
   run crashed before writing the summary; no verdicts were affected).
   Diff (one line in `scripts/fable_reversal210_run.py`):
   `(sm_rows, "smollm")` → `(sm_rows, "smollm-incontext")`. Affected marks
   re-run in the open (the 243.7 s run above). Post-run seal: 6/7 OK;
   `fable_reversal210_run.py` mismatch is this fix. No rule changes.
2. S_FIRST teaches use copula form (`X is the ROLE of Y.`) rather than
   verb form (`X composed Y.`): piloted pre-seal that the loop's ears
   reject verb-form teaches outside its 5-verb table, which would have
   left nothing stored to reverse from. One direction taught either way;
   checker proves it.
3. Plain transformer baseline not run: it is a synthetic token-story
   model with a closed vocab, not an English QA model; porting it is a
   new project, not a 90-minute arm (see design doc).

## Reproduce

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1
uv run --offline --no-project --python 3.12 --with torch --with numpy --with transformers python -B scripts/fable_reversal210_check.py
uv run --offline --no-project --python 3.12 --with torch --with numpy --with transformers python -B scripts/fable_reversal210_run.py --run
```

## Questions for Ben

None. (Suggested follow-up, not asked: teach the loop the 8 verb→role
rows so this split can re-test it as a real reversal benchmark.)

What it means: we now own a checker-proven true reversal split, and on
it the loop stores forward facts but cannot answer backwards, while
SmolLM retrieves backwards half the time exactly.
What it does not mean: the loop is incapable of reversal in general —
its question parser simply has no verb→relation rows for these 8 verbs.
