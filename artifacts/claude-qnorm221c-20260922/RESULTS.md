# Exp 221c -- question normalisation before table matching

## Verdict: FAIL (registered). M1 fails on two bars: contractions_fillers is +3 against a bar of +6, and overall is +5 against a bar of +8. M2, M3, M4 and M5 pass.

The safety marks all held on the blind panel: 0 wrong values, 0 question writes, and no item
went from right to not right.

Build: loop221c = loop221 + QNorm221cMixin outermost (scripts/claude_loop221c_agent.py).
Design note: design/v3/30-modes/221c-qnorm-opus.md.

Order kept:
1. Code, config, dev cases, scorer, PASSMARKS, the predicted moves and the 221 base-row
   copies were sealed first (SEAL.sha256.txt, 16 files, re-verified 16/16 OK after all runs).
2. Predictions P221c.1-8 were appended to the ledger.
3. The panel's own seal was verified (panel.jsonl: OK).
4. Then the panel was opened and run once, all three arms in one pass.

The README was read after the run. The sealed loader read every field correctly (a null gold
means abstain), so no field-map change was needed. All runs were on Mac CPU with OMP/MKL=1,
one at a time, at 1-minute load 11-26.

## Marks

| mark | bar | result | pass? |
|---|---|---|---|
| M1 221c wrong values (120 items) | 0 | 0 (221: 0, 138i: 0) | pass |
| M1 221c question writes | 0 | 0 (221: 0, 138i: 0) | pass |
| M1 contractions_fillers right | >= 221 + 6 = 8 | **5/15** (221: 2, 138i: 2) | **FAIL** |
| M1 overall right | >= 221 + 8 = 57 | **54/120** (221: 49, 138i: 39) | **FAIL** |
| M1 right on 221 but not on 221c | 0 | 0 | pass |
| M2 normalisable dev questions right | >= 42/44 | 44/44 (221: 13/44) | pass |
| M2 statements byte-identical to 221 | 10/10 | 10/10 (controls 6/6 identical too) | pass |
| M3 new WRONG / WRONG-WRITE / junk (rt136, rt143, sessions152, bench vs sealed 221 rows) | 0 | 0 / 0 / 0; GATE clean | pass |
| M3 moves only as predicted (0 predicted) | 0 unpredicted | 0 moves in all four suites | pass |
| M4 sleep smoke | 221's marks | sleeps 1, installed 1, episodes 20, probes 5/5, wrong 0, broken fact abstains, taught 50/50, overwrote 0, 95.5 s | pass |
| M5 median added ms, 221c - 221, per panel question | <= +5 | +0.04 ms (dev +0.02) | pass |

Per family, right out of 15 (138i / 221 / 221c):

| family | 138i | 221 | 221c |
|---|---|---|---|
| contractions_fillers | 2 | 2 | 5 |
| named | 14 | 14 | 14 |
| of_form | 1 | 4 | 5 |
| synonyms | 1 | 3 | 3 |
| traps | 15 | 15 | 15 |
| user_facts | 5 | 5 | 6 |
| word_form | 1 | 6 | 6 |
| yes_no | 0 | 0 | 0 |

## Every panel move (221 -> 221c)
The normaliser fired on 7 of 120 items. Only those 7 replies changed.
- **q221b-037** "What's Rowan Aske's hometown again?": abstain -> "Rowan Aske's hometown is Kilbrae." Fixed.
- **q221b-038** "Hey, who's Petra Lindell's neighbor?": not understood -> "Petra Lindell's neighbor is Gus Arnott." Fixed.
- **q221b-040** "When's Callum Brisk's anniversary?": not understood -> "Callum Brisk's anniversary is August 20." Fixed.
- **q221b-052** (of_form) "Who's the manager of Seren Abbot?": not understood -> "Seren Abbot's manager is Hugo Lark." Fixed.
- **q221b-100** (user_facts) "What's my hometown again?": not understood -> "your hometown is Pellory." Fixed.
- **q221b-032** "When's Ivo's birthday again?": not understood -> "I don't know anyone called Ivo." Still a miss.
  - It is rewritten to "When is Ivo's birthday?", but the fact is stored under "Ivo Castellan".
  - The first-name-only lookup is not a normalisation problem.
- **q221b-088** (traps) "Where does Hanne Solberg live now?": not understood -> "I don't know Hanne Solberg's city." Still right (abstain), and the reply is clearer.

## Why the two M1 bars failed (diagnosis only; nothing changed after the run)
10 of 15 contractions_fillers items are still missed. In 2 of them (031 dentist, 039 email)
221 was already right, and they stayed right. The misses fall into four groups:
- **Fillers or lead-ins outside the task's list (5).** 034 "so who's" (no comma), 035
  ", remind me", 041 ", do you know", 043 "Quick q,", 045 ", btw".
- **The "matches a template" gate blocked open-vocabulary relations (2).**
  - 036 "Um, who's Jonah Pike's vet?" was rewritten to "Who is Jonah Pike's vet?".
  - 042 "what's Bertrand Oake's favorite movie" (no "?") was rewritten to "What is Bertrand
    Oake's favorite movie?".
  - vet and favorite_movie are not table relations, so neither rewrite has a table reading, and
    the original text was used.
  - 221's base already answers open-vocabulary "Who is X's R?" (031 dentist, 039 email).
    Letting a rewrite through when the *base* parses it as an ask, not only when a table
    template matches, would probably have fixed these two. That is untested.
- **"X's R called?" (2).** 033 "pet called", 044 "gym called". This is not a rule on the list.
- **First name only (1).** 032 "Ivo" for Ivo Castellan.

## Deviations
1. **Sleep smoke, first attempt.** The first call passed a directory as `--report` (a driver
   command error). It crashed while writing the report, after the run, and printed no summary
   line (sleepsmoke-attempt1-reportpath-error.log). I deleted its work dir and ran once more
   with a file path. That second run is the one reported. No sealed file changed.
2. **221 base rows.** 221's rt136/rt143 rows are named rt136-rows.json / rt143-rows.json, which
   the suitediff filename search does not find: `--base-dir` on 221's folder gave "SKIPPED" in
   a pilot. I copied them unchanged, before the seal, to base221/redteam136-rows.json and
   redteam143-rows.json, together with the sessions152 and bench rows. Source and copy shas
   match (base221-copy.sha256.txt). The diff files show that these copies were the base.
3. **Dev cases fixed during the pilot, before the seal.**
   - 5 dev setups used "works for" / "lives in", or "My best friend is ...". 221 does not
     store those, so I changed them to possessive setups.
   - 2 plural cases used hobby and neighbour, which the notebook treats as single-valued. I
     changed their gold to the one stored value.
   - No normaliser rule was changed because of the dev set.

## What it means
- Rewriting contractions, simple fillers, a missing "?" and plural nouns before table
  matching is safe on everything we measured:
  - 0 wrong answers and 0 writes on 120 blind questions;
  - no answer lost;
  - 0 moves on four frozen suites;
  - sleep smoke unchanged;
  - no added time.
- It fixed 5 blind questions and all 31 dev questions that 221 missed.
- On the blind panel, most question wording problems are *not* the specific ones this rule
  list covers, so the gain is smaller than the bars asked for.

## What it doesn't mean
- It does not mean normalisation is "done". Real users say "btw", "remind me", "quick q" and
  "X's pet called", which this list does not cover.
- The template-only gate also blocks relations outside the table, even when the plain base
  could answer them.
- The +5 comes from one panel by one writer, with 15 items per family. That is too small to
  estimate a precise rate.
- The dev result (44/44) is on my own cases. It shows that the rules do what they say, not
  how often they help.

## Files
- PASSMARKS.md, SEAL.sha256.txt, predicted_moves221c.txt, loop221c-config.json
- make_dev221c.py, dev221c.jsonl, base221/ (+ base221-copy.sha256.txt)
- panel/ (rows.jsonl, cases.md, summary.json) + panel.log
- dev/ + dev.log
- suites/ (suitediff/, suitediff-*.log, wait.log, qnorm-trace.jsonl)
- sleepsmoke/ + sleepsmoke.log (+ sleepsmoke-attempt1-reportpath-error.log)
- Code: scripts/claude_loop221c_agent.py, scripts/claude_qnorm221c_run.py
