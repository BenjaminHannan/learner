# 136 — Teach-frame red team on loop129b (Muse, 2026-09-22)

## Problem

Loop129b fixed sentence-final periods leaking into stored values (exp 129).
The teach frame still had open red-team questions: which ordinary phrasings
fail, and which non-facts get silently stored. Other agents own fixes 135
(officeholder junk) and 137 (two-word possessives); this experiment finds
bugs without fixing them, excluding those two plus the closing-quote leak
from the novelty count while keeping one confirming case each.

## Method

145 fresh cases, expectations frozen BEFORE running (`cases136.json`, sealed
`SEAL.sha256.txt`, PASSMARKS M1–M4 sealed the same way). Coverage: all 46
bench73 `STATEMENT_PATTERNS` families, all 7 bench92 `EXTRA` families, the
FakeEars possessive frame, plus phrasing variants (no period, extra spaces,
curly/unicode, `!`, year qualifiers). Adversarial: chit-chat, negations,
statement-shaped questions, hedges, hypotheticals, plurals/compounds,
reported speech, corrections, numbers/dates, lowercase, emoji, multi-sentence
messages. Each case runs alone through a fresh loop129b daemon dir
(`fable_fix129_common.new_daemon129b` + mailbox `process_file`); stored
facts read via `fable_loop90_agent.notebook_triples`. Verdicts:
OK / WRONG-WRITE (any stored triple outside expectation) / MISSED
(expected write, got none) / HARNESS-ERROR. New files only:
`scripts/fable_redteam136_cases.py`, `scripts/fable_redteam136_run.py`,
`artifacts/fable-redteam136-20260922/`.

## Findings (21 WRONG-WRITE in 8 classes, 5 MISSED in 4 classes)

The guards are strong on refusal: every hearsay, compound-sentence, and
question-shaped probe correctly wrote nothing. All 8 wrong-write classes
are values or subjects the parsers accept too eagerly: the officeholder
catch-all (`fable_bench73_english_arm.py:127`) stores chit-chat and kinship
("The weather is nice", "The mother of Ann is Sue"); it also shadows the
three "The-NP" extra patterns (`fable_bench92_english_arm.py:176`) so head
coach / broadcaster / director store as officeholder. Values keep negation
and hedge adverbs ("not Lisbon", "probably Ann"), emoji, second-sentence
tails ("Rome. Thanks"), and bare "A and B" compounds — none of the value
screens (`fable_earsguard91.py:48`, `fable_fix129_punct.py:119`) look for
them. Two punctuation asymmetries: a trailing closing quote leaks into the
value while a leading quote refuses the whole teach; FakeEars'
`value.rstrip(".")` (`fable_agent_loop.py:136`) eats abbreviation dots
before the abbrev-aware sanitizer runs. Coverage misses: multi-word
possessive subjects, lowercase "The"-frames, and "Sorry, I meant …" on
possessive shapes (the correction prefix path only serves bench73 shapes).

## Proposed fixes (one single change per class, not applied)

W1: allowlist office nouns on the catch-all. W2: try EXTRA patterns before
officeholder. W3: clarify on leading not/never/probably/maybe in values.
W4: strip trailing symbol runs in `strip_sentence_punct`. W5: cut values at
". " + capital. W6: clarify on bare "and" between name-spans. W7: drop
unmatched trailing quotes. W8: route FakeEars values through
`strip_sentence_punct`. Rank by user likelihood: W3 > W1 > W4 > W6 > W5 >
W8 > W7 > W2; the top coverage miss (multi-word possessive subjects) is
fix 137's territory.

## Result

M1–M4 PASS (145/145 verdicts, 0 harness errors; 3/3 knowns reproduce;
21/21 wrong-writes classified; 1.2 s). P136.1 TRUE (8 classes vs bar 4–8).
Full per-case evidence: `results136.json`, `cases136-verdicts.tsv`.

## What it means

The teach frame's refusal side is trustworthy, but normal chat — negations,
opinions about "The …", emoji, politeness tails — still lands in the
notebook as facts.

## What it does not mean

Frequencies here are per-probe, not per-user-traffic, and no fix here was
implemented or tested; each class needs its own one-change experiment.
