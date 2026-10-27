# Experiment 52 — registered pass marks (written and sealed BEFORE any registered run)

Date written: 2026-09-21. Registered seeds: **5201, 5202, 5203** (fresh; never run before).
Every mark is scored per seed and reported as integers, never averaged across seeds.
Development used throwaway seed 9999 only (`--selftest`: 34/34 checks, smoke base).
Predictions P214–P218 were appended to `artifacts/fable-predictions-ledger.md` before this seal.

## What is being tested

Experiment 46's install recipe (robust loss ε=0.10, router hardened to argmax chain ±30
logits after every fold fit and the refit, unchanged 4-fold gate OOF ≥ 0.80 / refit
agreement ≥ 0.90 / base unchanged / reload identical, 60-start audit) was proven only on
clean toy episodes handed in by the experiment. This run feeds it episodes **mined
automatically from a real 200-turn conversation log** by pure rules, with candidate words
chosen by a **frequency rule over repeated relation chains** (never by the model), and
proves after every sleep that old skills and taught facts are unchanged.

## The registered cell structure

- 3 seeds × 3 nights per seed = **9 logs**, each exactly **200 turns**.
- Night = corruption level `wrong` ∈ {0, 2, 4}: of the 20 standing confirmed teachings per
  chain, exactly `wrong` are corrupted (the teacher confirmed a wrong answer and never
  corrected it). Corrections that heal an initially-wrong confirmation are supersessions,
  not standing corruption.
- Each log carries realistic noise: 28 small-talk turns, 6 teach turns (3 duplicate-save,
  3 CONFLICT), 8 ambiguous asks, 8 unanswered asks (MISSING_FACT/BROKEN_CHAIN), 4 unconfirmed
  asks, 4 stray confirms, 6 corrections (2 per chain, superseding an earlier episode), and a
  decoy chain (mother→father) confirmed only 8 times.
- Per log the miner must find **exactly 3 candidate chains × 20 standing episodes** →
  3 install attempts per log → **27 install cells** total.

## Definitions

- **Standing episode**: after replaying the whole log through the miner (status rule, pair
  rule, supersede rule, fall-through rule, answer-in-vocab rule — all in the script
  docstring), the latest confirmed (start, chain, answer) per key.
- **Candidate chain**: length ≥ 2 and standing count ≥ 20 (the frequency rule). Visited in
  sorted order; a chain with no matching word slot would be REFUSED, never forced.
- **Installed**: the unchanged Exp 46 gate passed (OOF ≥ 0.80, agreement ≥ 0.90, base
  answers unchanged, weights-only reload identical).
- **Wrong install** (Exp 46's definition, unchanged): installed AND (60-start audit
  disagreements > 0 OR fresh accuracy < 0.99).
- **Taught facts**: every notebook FACT with source `taught`, compared fact-id by fact-id
  (subject, relation, value JSON, active flag) before vs after each sleep.
- **Notebook hash chain unchanged**: the pre-sleep `events.jsonl` bytes remain an exact
  prefix after sleep appends its report row, and a fresh reload verifies the chain
  (no LogCorrupt, event count +1, last-hash matches). Sleep appends one `sleep-derived`
  report row; it never rewrites history.
- **Old skills bit-identical**: in every saved install, every parameter except the target
  word slot is byte-equal to the frozen wake snapshot; in the live state the token-routing
  table is byte-equal to the original base; the 900-question base probe answers
  answer-for-answer unchanged. A word re-trained as tonight's target is the new sleep
  result, not an old skill.

## Registered marks (all must pass)

- **M1 safety — 0 wrong installs** across all 27 cells. One wrong install = FAIL.
- **M2 noisy — installs ≥ 15/18 at ≤ 2 standing-wrong.** The brief's mark “≥ 12/15 at ≤ 2
  wrong” assumes 15 cells; this design has 3 seeds × 3 chains × 2 levels = 18 cells at
  ≤ 2 wrong, so the same 80 % rate registers as ≥ 15/18 (14/18 = 77.8 % would FAIL).
  Reported per level too (9 cells at 0 wrong, 9 at 2 wrong).
- **M3 notebook integrity — 100 %** in all 9 sleeps: taught facts unchanged, pre-sleep
  prefix byte-identical after the report row, chain valid on fresh reload, exactly one
  `sleep-derived` report row written per sleep.
- **M4 sleep wall-clock — every `sleep()` call < 600 s.** (Total wave also reported.)
- **M5 miner exact — 9/9 logs**: exactly 200 turns; exactly 3 candidates; each candidate
  exactly 20 standing; decoy chain counted at 8 and not a candidate; 6 supersessions;
  standing total 68; standing-wrong per candidate == the night's corruption level
  (manipulation check); no episode whose originating ask status ≠ OK.
- **M6 old skills — 9/9 sleeps**: old skills bit-identical AND base probe unchanged.

Base validity: each seed's base stage must reach fresh 1–3-hop accuracy ≥ 0.99 (Exp 44's
R1 level). A failing base seed is reported **VOID**; no replacement seed is chosen after
seeing outcomes.

## Failure protocol

A missed mark is recorded as FAIL in RESULTS.md first. Only then may ONE clearly described
change be made as “v2”, with its own sealed marks, run on the same three seeds plus fresh
seeds. No further tuning.

## Given by hand (not learned) — must appear in RESULTS.md

1. The miner's five rules and the ≥ 20 frequency threshold (fixed constants, not learned).
2. The Exp 46 recipe itself: loss form, ε = 0.10, hardening ±30, gate constants, 60-start
   audit, wrong-install definition.
3. The three word slots and their chains (a candidate with no slot is refused).
4. The 0.9 answer threshold, the hop loop, the lookup matrices (Exp 44, unchanged).
5. The log generator: how many noise turns of each kind, and which slots are corrupted.
