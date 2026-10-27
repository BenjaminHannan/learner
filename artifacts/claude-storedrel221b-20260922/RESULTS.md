# Exp 221b -- stored-relation fallback for questions (on loop221)

## Verdict: FAIL (registered), on M3 only.
- M3 fails because of one unpredicted bench move. It is the known flake type: a correct
  answer turned into an abstain. When the same item was run again 5 times, all 5 were
  correct.
- Every other mark passes: M1 (fresh blind panel), M2 (dev cases), M4 (sleep smoke) and
  M5 (cost).
- On the fresh panel, 221b answered 23 more items right than 221, with 0 wrong values and
  0 writes.

Build: loop221b = loop221 + StoredRel221bMixin outermost (scripts/claude_loop221b_agent.py).
Nothing else changed. The relation table is untouched, and no rows were added. I never
opened the old 221 panel.

The seal (SEAL.sha256.txt, 20 files, 15:27:08) was made before the fresh panel was opened.
It verified 20/20 after all runs. The panel's own seal verified OK before its run.

## Marks

| mark | bar | result | pass? |
|---|---|---|---|
| M1a 221b wrong values, fresh panel (120 items) | 0 | 0 | pass |
| M1b 221b question-turn writes | 0 | 0 (138i 0, 221 0) | pass |
| M1c 221b right (answer-type) >= 221 + 10 | >= 49 | 221b 62 vs 221 39 (+23); 138i 29 | pass |
| M1d items right on 221, not right on 221b | 0 | 0 | pass |
| M2a dev "hit" right | >= 90 % | 32/32 | pass |
| M2b dev "ambiguous" abstain, fallback silent | 8/8 | 8/8 | pass |
| M2c fallback fires outside "hit" / reply differs from 221 | 0 / 0 | 0 / 0 (40 items) | pass |
| M2d unit checks | 11/11 | 11/11 | pass |
| M3 suitediff218 vs 221 rows: new WRONG / WRONG-WRITE / junk / lost OK | 0 | 0 (GATE: clean) | pass |
| M3 unpredicted moves (predicted: none) | 0 | **1** (bench132-4hop-160, correct -> abstain) | **FAIL** |
| M4 sleep smoke | 221 marks, < 300 s | sleeps 1, installed 1 (20 ep), probes 5/5, wrong 0, broken=abstain, taught 50/50, ow 0, 84 s | pass |
| M5 median (221b - 221) ms per panel question | <= +5 | -0.02 ms (dev -2.24) | pass |

## Fresh panel detail (sealed scorer, answer-type rights by family)

| family (items) | 138i | 221 | 221b |
|---|---|---|---|
| named (15) | 14 | 14 | 15 |
| word_form (15) | 1 | 6 | 12 |
| contractions_fillers (15) | 2 | 2 | 6 |
| of_form (15) | 1 | 4 | 13 |
| synonyms (15) | 1 | 3 | 3 |
| user_facts (14 answer + 1 abstain) | 5 | 5 | 8 |
| yes_no (15) | 6* | 6* | 6* |
| traps (15 abstain; count = correct abstains) | 15 | 15 | 15 |

*Scorer flaw, found after the run. For the 6 yes/no items with gold "no", the scorer counts
the abstain reply as right, because "I have **no** record ..." contains the word "no". The
yes/no replies are byte-identical in all three arms, so M1c and M1d are not affected.
Hand-corrected answer-type rights: 138i 23, 221 33, 221b 56. That is still +23.

### Every move 221 -> 221b on the panel (23; all MISS-abstain -> RIGHT; the fallback fired on exactly these 23)
- named: 003 wedding anniversary.
- word_form:
  - 016 "Who coaches" -> coach
  - 017 "founded" -> founding_date
  - 018 "graduate" -> graduation_date
  - 019 "owns" -> owner
  - 021 "tutors" -> tutor
  - 024 "mentors" -> mentor
- contractions_fillers: 033 pet, 037 hometown ("again"), 040 anniversary ("When's"), 044 gym.
- of_form:
  - 046 landlord, 049 principal, 050 address, 051 mayor
  - 052 manager ("Who's the ... of")
  - 056 opening date, 057 architect, 058 population, 059 dentist
- user_facts: 092 landlord, 097 gym, 100 hometown.

By hand, every one of these is the taught value, served from its own taught key. The reply
names that key.

### Remaining 221b misses (diagnosis only; nothing changed after the run)
- **Synonyms (12):** physician/doctor, supervisor/boss, city/residence, native
  language/mother_tongue, birthday/date_of_birth, attorney/lawyer, yoga instructor/teacher,
  veterinarian/vet, cell/mobile, employer/company, family doctor/gp, best friend/best_mate.
  These are out of scope by design (no synonym lists).
- **Filler words (9):** a leading "so" / "Um," / "Hey," / "Quick q,", or a trailing
  ", btw" / ", do you know" / ", remind me". Also:
  - one question with no "?" (042);
  - one first-name-only question (032, "Ivo").
  The rule needs a question word first, and it needs every content word to match.
- **Verb forms that are not a relation word (3):** "directs" (director), "live" (residence),
  "rent from" (landlord).
- **Setups the base never stored (8):** 7 "My R is V." user facts (for example wifi password,
  locker number) and 048 "Harrow & Finch". The notebook held nothing to read.
- **One "of the" name (053):** "the Cinder Owls" is refused by the "of" guard.
- **yes/no (9 gold "yes"):** not handled by 221 or 221b.

## M3: every suite move
- rt136: 0 moves. rt143: 0. sessions152: 0.
- bench: 1 move, **bench132-4hop-160**, correct -> abstain (not-understood reply). The
  stored facts were identical, and the tool classed it as a reply-only move.
  - This cannot come from the fallback. The fallback only ever replaces a miss with an
    ask; it never turns an answer into a clarify.
  - It matches the known ~1/800 flake. The pilot (pre-seal) had 0 bench moves.
- Follow-up: the bench132_4hop split was re-run 5 times (flake160/run1-5). Item 160 was
  "correct" 5/5, and each run had 0 moves (191 correct / 9 abstain, the same as 221's rows).
- The registered mark still counts the move, so M3 = FAIL.

## Deviations
1. My first launch of the registered dev / unit / suitediff commands did not run anything.
   zsh did not split a command held in a variable ("command not found"). I then ran the same
   commands spelled out, and no sealed file changed in between. The failed attempt's log
   lines were overwritten.
2. Flake follow-up runs 2-5 started while the 1-minute load was 92, above the rule's 60.
   Run 1 first failed because its log directory did not exist yet. I redid it after the load
   fell to 57. These are diagnostics, not marks.
3. Base rows for M3 are byte-identical copies of 221's sealed suite rows (base221/, sha256
   equal to the originals, listed in the seal). I renamed them only so the suite tool finds
   the rt136/rt143 files. Pointing it straight at the 221 folder skipped rt136 and rt143.
4. Scorer flaw on yes/no "no" gold (above). It is reported, not fixed. The sealed scorer is
   unchanged.
5. Two dev cases (H11, H31) were rewritten before the seal. Their first setups ("My
   graduation date is ...", "My coach is ...") were never stored by the base. The notes field
   records this.

## What it means
- The fallback does what it was built to do. When someone asks about a fact the agent was
  taught, in words that match the stored relation name (like "Who owns X?" for "owner", or
  "When was X founded?" for "founding date"), the agent now answers instead of saying "I
  don't know."
- On a fresh blind panel it answered 23 more questions than 221. It gave 0 wrong answers,
  wrote nothing from a question, and lost nothing 221 already got right. All 15 trap
  questions still got an honest "I don't know."
- It costs no measurable time, and the sleep smoke is unchanged.

## What it doesn't mean
- It does not understand synonyms. "Doctor" still does not find "physician", on purpose.
  Those 12 panel items are still misses.
- It does not cope with chatty wording ("Um, who's ...", "..., btw?"), or with a question
  that has no question mark.
- It is not a PASS. The registered rule counts the one flaky bench move, and I am not
  overriding my own mark.
- It says nothing about two-hop questions, yes/no questions, or writes. The panel came from
  one writer, with 15 items per family.

## Files
- PASSMARKS.md, SEAL.sha256.txt, SEAL.time.txt, loop221b-config.json, dev221b.jsonl,
  predicted_moves221b.txt, base221/ (+ README.txt)
- dev/ (+ dev.log), unit.log, panel/ (rows.jsonl, summary.json) + panel.log,
  suitediff/ (+ suitediff.log), flake160/run1-5, sleepsmoke/ (+ sleepsmoke.log)
- Code: scripts/claude_loop221b_agent.py, scripts/claude_221b_run.py,
  scripts/claude_221b_unit.py. Design note: design/v3/30-modes/221b-storedrel-opus.md
