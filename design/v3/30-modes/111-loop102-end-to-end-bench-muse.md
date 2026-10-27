# 111 — Loop102 end-to-end bench through the real doorway (Muse, 2026-09-22)

## What was built

`scripts/fable_bench111_run.py` (new, prefix-owned): per item it creates a
FRESH `Loop102Daemon` directory, writes each `taught[].sentence_en`
verbatim as an inbox file, then the English question, drives each turn with
`Loop102Daemon.process_file` (the real mailbox path: bytes in, outbox reply
file out), and scores the question-reply text with exp-66's `classify`
imported read-only (exact normalised match = correct; marker-with-no-gold =
abstain; else wrong). Teach replies are graded ACCEPTED (`Saved:` or the
expected duplicate-ack) vs REJECTED, counted honestly, sentences never
rewritten. Splits: Fable-Edit-200 (150 answer + 50 abstain) and the exp-103
fresh 200 (all 4-hop answers).

## Result

Registered FAIL on E1 (50/200 right behaviour, 150 wrong) and E2 (131/200
wrong); PASS on E3 (50/50 abstain, 0 wrong) and E4 (6.9 s). Full tables in
`artifacts/fable-bench111-20260921/RESULTS.md`.

## Three findings, each with a mechanism

**1. The loop knows; the mouth frames.** Split-A answers are 150/150
present-as-substring in replies, but FakeMouth's OK template (`{owner} is
{answer}.`) never exact-matches gold, so all 150 register wrong. Nothing
about the notebook, reasoner, or ears is implicated: teach rejects 0/800,
abstains 50/50 genuine. Lesson: an end-to-end mark must score the answer
span (or accept contains), not the whole utterance — a scorer/doorway
contract fix, not a model fix. Proposed follow-up (one change): score
contains_gold as correct for answer items, re-seal, re-run; expect E1 PASS.

**2. The N-hop composer never made it into the loop.** Exp-103 proved
`compose_n_hop` (B92) walks 4-hop chains at 193/200 on the fresh split via
direct notebook feed. Loop102's ears chain, however, asks questions through
bench73's 2-hop `compose_question`, which returns the first two hops of any
longer chain. Through the doorway the daemon therefore answers fresh
questions with correct 2-hop prefixes ("Derek Shepherd's spouse's creator
is Frank Herbert.", gold Arabic) — confident wrongs, contains_gold 5/200.
The 69 abstains are the complementary shape: mention/coverage gate fails →
clarify or MISSING. Proposed follow-up (one change): route question turns
through `compose_n_hop` inside the chain, keeping teach patterns identical.

**3. Fresh phrasings expose three unheard templates.** "X works in the field
of Y" (bench73 only knows "worked in the city of"), "X is employed by Y"
(no employer pattern anywhere), "X's child is Y" (no possessive-child
pattern) → clarify rejects; "…citizen of United Kingdom of Great Britain
and Ireland" → the listening doorway's one-fact-at-a-time guard fires on
"and" (bench65 never had an "and"-object, so this was latent). 22 rejects
in 12 items, 0 in split-A. Each is a one-pattern additive fix; none was
applied here (additive-only + no-rewrite rule for the bench).

## Scorer artifact (disclosed, affects reading of E2)

Exp-66's abstain marker "not" is a substring of "notable", so 3 confident
fresh-split wrongs of the form "…'s author's notable work is X." bucket as
abstain. True confident-wrong on fresh is 134, not 131. E3 is unaffected
(all 50 split-A abstains are genuine "I don't know…" replies). Any future
use of this scorer on mouth sentences should use word-boundary markers.

## Fit with the whole

Loop102 remains the verified build: teach/edit/supersede/abstain all work
through the mailbox (split-A proves it). This experiment's value is
precisely what notebook-level arms cannot give: it showed the join (mouth
framing, question composer wiring, template coverage on fresh relations)
is where the next three one-change experiments belong. The FAIL is
diagnostic, stands as recorded, and points at the ears-chain question path
first (it converts wrongs to rights), the scorer contract second, new
patterns third.

## Reproduce

Sealed PASSMARKS sha `e3a3b757…`; predictions P111.1–P111.5 in
`artifacts/fable-predictions-ledger.md` (4/5 TRUE). `export
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python
3.12 --with torch --with numpy python -B scripts/fable_bench111_run.py
--run`. No deviations beyond a 5-item pre-seal smoke probe in temp dirs.
