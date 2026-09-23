# RESULTS — Experiment 53: mouth (borrowed decoder), 2026-09-22

The mouth turns a RESULT RECORD into one plain English sentence. Borrowed part:
HuggingFaceTB/SmolLM2-360M-Instruct (Apache-2.0), body frozen. Ours: the record
prompt format, a record adapter (10 new embedding rows + last block
+ untied lm_head = 57,037,440 trainable params), and a plain-software
FAITHFULNESS BRAKE (any output word outside the record or a fixed function-word
list falls back to TemplateMouth). Score: O1 PASS, O2 FAIL, O3 PASS, O4 PASS,
O5 FAIL. A registered FAIL stays a FAIL.

## Marks (integers)

| mark | bar | got | verdict |
|---|---|---|---|
| O1 after-brake violations / 500 | 0 | 0 (raw decoder: 296) | PASS |
| O2 status recoverable / 500 | >= 480 | 426 | FAIL |
| O3 OK answer verbatim / 250 | >= 240 | 250 | PASS |
| O4 train + score wall-clock | < 25 min | 762.6 s + 423.4 s = 19.8 min | PASS |
| O5 replay: wrong writes / correct / abstentions | 0 / 12 / 3 per run | 1 / 11 / 2 per run, 3/3 runs | FAIL |

Held-out mix: 250 OK, 80 MISSING_FACT, 60 BROKEN_CHAIN, 40 AMBIGUOUS, 40
UNKNOWN_ENTITY, 30 BAD_REQUEST. The decoder raw-passed on 204/500; all
296 fallbacks (= TemplateMouth) classify correctly. Of the 204 raw passes, 74
carried a wrong or missing status anchor (e.g. an OK sentence containing "more
than one"), which is the whole O2 gap (500 − 74 = 426).

## O5 replay detail (per run, 3/3 identical)

Baseline replay-report.json (bridge up): wrong 0, missing 0, correct 12,
abstentions 3. Ours: wrong 1, missing 0, correct 11, abstentions 2, taught 13,
sleeps 2. Attribution: the wrong-write ("Kai's sister" stored as sister, not
sibling) and the missing correct (Kai's sibling two-hop) are ears-caused — the
Qwen bridge was down/flaky (38 fake-fallback + 1 english + 1 deterministic turn
per run) and the TemplateMouth-fake control shows the same two gaps. The mouth
cannot write (it returns strings; writes go through LISTENING). One
gap is mouth-caused: turn 29's raw BROKEN sentence passed the brake lexically
but lacked its anchor, so one abstention was missed.
Replay mouth stats: 45 says, 15 raw passes, 30 fallbacks.

## 10 verbatim held-out examples (raw -> final)

1. MISSING good: "I don't know who Paula's grandfather is." -> same. PASS.
2. AMBIGUOUS good: "I know more than one Priya -- Liam (E0049), Kira (E0047)
   -- which one do you mean" -> same. PASS.
3. OK, brake catches wrong answer: "I read that Tom's dentist's dentist's
   Tom's dentist's ..." -> "Tom's dentist's best friend is Zed." PASS.
4. OK web source kept: looping raw -> "Wren's employer's uncle is Oscar. (I
   read that online; you didn't tell me.)" PASS.
5. OK hallucinated relation, caught: raw "I read that you didn't tell me more
   than one's spouse -- that is Iris's spouse is Iris. ..." ->
   "Iris's spouse is Mira. ..." PASS (fallback; raw misclassifies AMBIGUOUS).
6. AMBIGUOUS truncated ids, caught: ": Ana (E: I know more than one: Ana's
   best friend -- ..." -> "I know more than one Ana: Greta (E0041), Victor
   (E0046). Which one do you mean?" PASS.
7. BAD_REQUEST loops but keeps anchor: "I could not use that: I could not use
   that question: ..." -> same. PASS.
8. BROKEN loops with anchor: "I stopped: Tom's hometown is Bristol, Bristol,
   I stopped: ..." -> same. PASS.
9. BROKEN raw passes brake but anchorless (replay turn 29 pattern): "I found
   it: Ana's mother's mother's mother..." -> missed abstention. FAIL case.
10. OK answer missing, caught: "I don't know: that's not: that's: that's:
    ..." -> fallback with exact answer. PASS (9 such fallbacks in replay).

## Deviations (all before the registered run)

- lr 1e-4, 1200 steps (pilots: 2e-5 stalls at loss 2.8/300 steps; 1e-4 reaches
  0.03 on seen pairs).
- Untied lm_head (cloned off SmolLM2's tied embeddings) at train and inference,
  so the head trains without moving old input rows.
- Brake rejects empty decodes; 9 fixed template words
  added to the function list; machine-check: 3500/3500 template sentences pass.
- Score uses one batched decode pass (batch 8); replay ran with the bridge
  down/flaky (see O5 table).

## Reproduce (from repo root)

```
python3 -B scripts/fable_mouth53_data.py --out artifacts/fable-mouth53-20260921/data --train 3000 --seed 5301
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy --with transformers python -B scripts/fable_mouth53_train.py --data artifacts/fable-mouth53-20260921/data --out artifacts/fable-mouth53-20260921/adapter --steps 1200 --lr 1e-4 --seed 5301
uv run --offline --no-project --python 3.12 --with torch --with numpy --with transformers python -B scripts/fable_mouth53_score.py --data artifacts/fable-mouth53-20260921/data --adapter artifacts/fable-mouth53-20260921/adapter --out artifacts/fable-mouth53-20260921/score.json
uv run --offline --no-project --python 3.12 --with torch --with numpy --with transformers python -B scripts/fable_mouth53_replay.py --adapter artifacts/fable-mouth53-20260921/adapter --replay 3 --out artifacts/fable-mouth53-20260921/replay-report.json
```

## What it means / What it does not mean

What it means: the brake works — zero faithfulness violations reach Ben (O1),
every OK answer is stated exactly (O3), and the adapter (57M params, 12.7 min
CPU train) learned the sentence shapes well enough to speak unaided on 204/500
records. What it does not mean: the mouth does not reason or check facts — 74
of its unassisted sentences carry the wrong status signal (O2 FAIL), and one
anchorless sentence cost a real abstention in the live loop (O5 FAIL). The mouth
is safe only with the brake on; without it, it loops, truncates ids, and
invents relations.
