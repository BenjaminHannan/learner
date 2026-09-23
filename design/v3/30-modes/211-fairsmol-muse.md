# 211 — Fair-prompt SmolLM arm (benchmark fairness; no agent change)

## Problem

Bench125 compared our loop against a SmolLM2-360M baseline whose prompt
(`scripts/fable_bench66_baselines.py:52,134-136`) lists old and new facts
with no order and no "newer facts replace older ones" cue, and whose
abstain detector (`_ABSTAIN_MARKERS`, line 54, matched by substring at
line 95) contains the bare word "not" — so any answer containing "not"
could count as an abstain. Both directions flatter or punish the baseline
for prompt/scorer reasons rather than capability reasons, which makes the
loop-vs-baseline gap hard to read.

## Design

New file `scripts/fable_fairsmol211.py` only (imports bench66/bench125,
edits nothing). Same model, splits, greedy decoding (<= 16 tokens) and
scorer (classify_v2 + contains-gold) as bench125's in-context arm; the
only change under test is the prompt. `build_fair_prompt` numbers facts
in teaching order, annotates each `taught[].edit == true` entry with
"(this replaces fact N)" (N = the earlier same-subject-same-relation
fact, else "(this is a new fact)"), and the system line states newer
facts win, says to answer "I don't know" when the facts don't say, and
gives one abstain example. `classify_phrase` keeps bench66's classify
shape (exact → correct; marker + no gold → abstain; else wrong) but
matches only whole phrases ("unknown", "i don't know", "i dont know")
by word-boundary regex — no bare "not".

## Marks

F1 reports the fair arm per-item (right/wrong/abstain) beside bench125's
old in-context arm on both splits. F2 re-scores bench66's 200 saved
in-context answers with the phrase detector and counts how many old
abstains were merely "not"-containing. F3 places the loop wrong rates
(read from bench125's JSON) beside fair SmolLM's. Verdict VALID iff
F1–F3 are all reported.

## Result and reading

Fair prompting converts wrong answers into abstains (edit200 wrong
148→99, abstain 0→84) but also loses answerable items (correct 52→17);
the loop still wins on wrong rate (0.0/0.025 vs 0.495/0.565). The
"not" hazard proved empty here: zero of 200 saved answers contain
"not", and old-vs-phrase verdicts agree 200/200 — bench66's abstain
counts stand. The comparison is now cleaner, and the remaining gap is
capability, not prompt formatting. Full detail:
`artifacts/fable-fairsmol211-20260922/RESULTS.md`.
