# Exp 136 RESULTS — teach-frame red team on loop129b (Muse)

Target: loop129b (`scripts/fable_loop129b_agent.py`, config
`artifacts/fable-fix129-20260922/loop129b-config.json`). 145 fresh cases with
frozen expectations (`cases136.json`, sha `ff141707…0380`), one message each
through a fresh daemon dir (`new_daemon129b` + mailbox `process_file`;
triples via `notebook_triples`). Verdicts: every case reported in
`results136.json` + `cases136-verdicts.tsv`, never averaged.

## Marks table (integer counts, n = 145)

| mark | bar | got | verdict |
|---|---|---|---|
| M1 completeness, 0 HARNESS-ERROR | 145/145, 0 | 145/145, 0 | PASS |
| M2 knowns reproduce (C124 WW, C125 MISSED, C126 WW) | 3/3 | 3/3 | PASS |
| M3 every WRONG-WRITE in a file:line class + 1-line fix | 21/21 | 21/21 | PASS |
| M4 wave < 1500 s Mac CPU | < 1500 s | 1.2 s | PASS |

Totals: OK 119, WRONG-WRITE 21, MISSED 5, HARNESS-ERROR 0.
Coverage teaches: 59/62 OK (the 3 misses are the shadowed-extra class W2).
All chit-chat/opinion/negation/hedge/hypothetical/plural/reported/question
probes that the guards catch: OK (no write). Corrections C104/C105/C107
write exact; C106 MISSED (below).

## WRONG-WRITE classes (novel = excludes the 3 knowns; rank = user likelihood)

- W1 officeholder junk drawer, 6 cases (C063 C070 C124 C127 C128 C129):
  any "The NP is X" (weather, meeting, mother of Ann, CEO…) stores
  `(NP, officeholder, X)`. Pattern `scripts/fable_bench73_english_arm.py:127`.
  Fix: fire the catch-all only for an allowlist of office nouns.
- W2 shadowed The-frames, 3 cases (C051 C052 C053): head_coach /
  original_broadcaster / director_manager never match because bench73 runs
  first and officeholder eats them. Order
  `scripts/fable_bench92_english_arm.py:176` + `scripts/fable_loop121_agent.py:221`.
  Fix: try EXTRA patterns before the generic officeholder.
- W3 negation/hedge adverbs in values, 4 cases (C072 C075 C082 C086):
  "not Lisbon", "not Lima", "probably Ann", "maybe Rome" stored raw. No
  check on values, `scripts/fable_agent_loop.py:134`.
  Fix: clarify on leading not/never/probably/maybe/perhaps in the value.
- W4 emoji tails, 3 cases (C117 C118 C119): sanitizer only strips `.!?;:`,
  `scripts/fable_fix129_punct.py:119`. Fix: also drop trailing
  non-alphanumeric symbol runs.
- W5 second-sentence tail, 1 case (C123 "Rome. Thanks!"): FakeEars takes
  rest-of-line, `scripts/fable_agent_loop.py:136`; guards miss it,
  `scripts/fable_earsguard91.py:48`. Fix: cut value at ". " + capital.
- W6 compound "A and B" values, 2 cases (C135 C136): `_AND_POSSESSIVE`
  only catches "and X's", `scripts/fable_earsguard91.py:41`.
  Fix: clarify on bare "and" joining two name-spans in the value.
- W7 trailing closing quote, 1 case (C126, known c): only paired quotes
  stripped, `scripts/fable_fix129_punct.py:104`. Fix: drop unmatched
  trailing quote chars too.
- W8 abbreviation dots eaten, 1 case (C140 "D.C." → "D.C"): FakeEars
  `value.rstrip(".")`, `scripts/fable_agent_loop.py:136`, runs before the
  abbrev-aware sanitizer. Fix: route the value through
  `strip_sentence_punct` instead of `rstrip`.

Rank by likelihood: W3 > W1 > W4 > W6 > W5 > W8 > W7 > W2.

## MISSED (coverage, expected write got none)

- M-A multi-word possessive subjects (C125 Dara Fenn, C130 Mary Kay;
  known b): FakeEars one-word rule. Most user-visible miss.
- M-B leading-quote teach (C131) refuses while trailing-quote (C126)
  writes junk — asymmetric quote handling.
- M-C lowercase "The"-frames (C115): case-sensitive bench patterns.
- M-D "Sorry, I meant …" + possessive (C106): correction-prefix path only
  handles bench73 shapes; possessive falls through to FakeEars, which does
  not know that prefix.

## What it means

Loop129b is safe on refusals (0 silent mis-routes among 80+ no-write
probes) but still stores 8 classes of junk a normal user will hit, topped
by negations/hedges and officeholder chit-chat.

## What it does not mean

No fix was applied or re-tested here; classes are diagnoses with proposed
single-change fixes, and frequencies are per-probe, not per-user-traffic.

## Deviations / questions for Ben

None. One judgment call: lowercase possessives (C114) counted as OK
(stored as-is); no deduplication against fix-135/137 work beyond the
brief's 3 knowns.

Reproduce: PASSMARKS.md command block (sealed `SEAL.sha256.txt`).
Ledger: P136.1 TRUE (8 classes, bar was 4–8).
