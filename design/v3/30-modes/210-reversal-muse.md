# 210 — True reversal split (benchmark repair; no agent change) — Muse

## 1. The problem (director-verified, reproduced here)

`data/open/bench65/fable_edit_200.jsonl` has 50 `reversal` rows in
fwd/rev pairs sharing both taught sentences. Checking the pair for
`Gilded Mirrors`: the fwd question `Who is the composer of Gilded
Mirrors?` has gold `Gilded Mirrors` (the answer sits inside the
question — pure lookup), the rev question `Who composed by Gilded
Mirrors?` is ungrammatical, and both directions are taught
(`composer_of` and `composed_by` sentences). **Exp 66/125 reversal
numbers therefore come from this broken split: they measure lookup and
tolerance of broken grammar, not reversal.** Nothing in bench65 or any
sealed file was edited; the repair is a new split.

## 2. Design of the new split (`data/open/reversal210/`)

70 items, fictional names only, every person and work unique (lookup is
unambiguous). Builder: `scripts/fable_reversal210_build.py`.
Checker: `scripts/fable_reversal210_check.py` (8 checks C1–C8).

- 50 reversal facts across 8 verbs (compose/write/discover/found/paint/
  direct/invent/design). Each taught with exactly ONE sentence:
  S_FIRST `PERSON is the ROLE of WORK.` or O_FIRST `WORK's ROLE is
  PERSON.`
- Asked the other way with grammatical verb questions: S_FIRST →
  `Who PAST WORK?` (gold: person); O_FIRST → `What did PERSON BASE?`
  (gold: work).
- 20 controls taught one way, asked the SAME way (`What did X BASE?`
  for S_FIRST, `Who PAST Y?` for O_FIRST).
- Checker proves: gold never inside its question; one taught sentence;
  taught shape matches direction tag; asked direction never taught;
  questions grammatical Who/What verb forms.

Teach syntax choice: pre-seal pilots showed the loop's ears reject
verb-form teaches (`X composed Y.`) and passive copulas (`The composer
of Y is X.`), but store `X is the composer of Y.` and `Y's composer is
X.` — so the copula carries the one taught direction (a fact the loop
can actually store is prerequisite to testing reversal).

## 3. Arms and protocol (`scripts/fable_reversal210_run.py`)

- **loop138i**: one fresh `Loop138iDaemon` per item (bench132 driver
  shape), teach verbatim, then question; scorer v2
  (right/wrong/abstain). Rows also store teach replies, FACT triples
  read from `events.jsonl`, and an inverse-stored count.
- **SmolLM in-context**: the bench125 arm verbatim (`build_prompt` +
  `greedy_answer` from `fable_bench66_baselines.py`), scorer v2.
- **Plain transformer baseline** (`artifacts/fable-baseline-
  transformer-v2-20260920`): not run. It is a synthetic token-story
  lookup model with its own closed vocabulary and story renderer — it
  has no English sentence reader and cannot take these items without a
  full re-tokenization and retraining project. Stating this instead of
  faking an equivalent.

## 4. Outcome (registered run, 243.7 s)

Loop: reversal 0/47/3 (right/wrong/abstain), controls 5/1/14, 0 inverse
facts stored in 70 items, 9 teach rejects (all `painter` items — the
ears reject `X is the painter of Y.`; every other verb stores). The 3
reversal wrongs are smalltalk misfires, 0 contain gold. Reading: the
loop keeps taught facts only and never works them out backwards for
these verbs — its question parser only maps 5 verbs
(lives-in/works-for/works-at/speaks/born-in) to relations, and no
190-style reverse lookup fires here. Controls show the ceiling is
partial even forward for the same reason.
SmolLM: reversal 25/0/25 with contains-gold 45/50 — it retrieves the
fact backwards but often echoes the whole taught sentence, failing
exact match. That gap (retrieve vs. answer) is exactly what the broken
split hid.

## 5. Marks

R1 checker VIOLATIONS 0 — hold. R2 70/70 ids in both row files, verdicts
only right/wrong/abstain — hold. R3 this note (§1) — hold. Verdict
VALID. Open deviations: one-line driver fix post-seal (coverage key
`smollm` → `smollm-incontext`; first attempt crashed pre-summary;
re-ran open; seal 6/7, data/checker/PASSMARKS/config OK); no agent, rule,
or sealed-data change.

What it means: a true reversal benchmark now exists, and on it our
agent remembers forwards but cannot answer backwards, while the
borrowed LM can.
What it does not mean: reversal is impossible for our architecture —
adding the 8 verb→role question rows would let this same split re-test
that claim directly.
