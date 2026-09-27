# Exp 236: questions that use only a first name. Result: PASS (registered, all marks)

loop236 is loop221 with one change: FirstName236Mixin is outermost on the Loop221Ears stack.
It acts only on question turns (the turn ends in "?").
- Code: scripts/claude_loop236_agent.py. The 228 guard is installed at import, and
  SrcGuardMixin228 is first in the Loop236Daemon bases.
- Order: pilots first. At 15:53:13, PASSMARKS, code, config, scorer, dev cases, the copied
  221 base rows and the design note were sealed (SEAL.sha256.txt, 13 files, all still OK at
  the end). Ledger lines P236.1-4 were appended.
- Then the registered runs, one at a time, each run once: suites, dev, sleep smoke, then the
  panel.
- I checked the panel writer's seal from the repo root (panel.jsonl OK, base221.jsonl OK)
  before I opened the panel.
- Machine: Mac CPU, OMP/MKL=1. The 1-minute load was 6-10 throughout.

## Marks

| mark | bar | result | pass? |
|---|---|---|---|
| M1a panel unique_first + of_form right | >= 90 % | 30/30 (unique_first 20/20, of_form 10/10) | pass |
| M1b panel ambiguous: clarify naming every candidate, 0 values | 100 % | 10/10 | pass |
| M1c panel exact_wins: single-name entity's value | 100 % | 6/6 | pass |
| M1d panel no_match + last_name_only byte-identical to 221 | 100 % | 10/10 (6 + 4) | pass |
| M1e panel statements: same reply + same active and all-taught triples as 221 | 100 % | 4/4 | pass |
| M1f panel wrong values (60 items) | 0 | 0 | pass |
| M1g panel question turns that changed taught facts | 0 | 0/56 | pass |
| M2 dev cases (28) | 28/28, 0 wrong, 0 question writes | 28/28, 0, 0 | pass |
| M3 suites vs 221 rows: new WRONG / WRONG-WRITE / junk / lost OK | 0 | 0 / 0 / 0 / 0; GATE clean | pass |
| M3 moves, all predicted by id | predicted 0 in every suite | rt136 0, rt143 0, sessions152 0, bench 0 | pass |
| M4 sleep smoke = 221's marks | sleeps 1, installed, episodes 20, probes 5/5, wrong 0, broken chain abstain, taught 50/50, overwrote 0, < 300 s | all the same; 83.2 s | pass |
| M5 median added ms per question (panel, paired vs fresh 221) | <= +5 | +0.19 ms (dev: +0.38 ms) | pass |

Every setup turn on the panel and dev sets got the same reply on both arms (60/60, 28/28).
My fresh 221 run agrees with the writer's base221.jsonl on all 60 items: final reply,
setup replies and stored facts (base221-agreement.txt).

## Every move
- **Panel (40 moves, all abstain -> answer or clarify, as predicted by family):**
  - **unique_first f236-001..020 and of_form f236-021..030 (30 items).** Each went from
    "I don't know anyone called T." to "<Full Name>'s <relation> is <gold>.".
  - **ambiguous f236-031..040 (10 items).** Each went to "Which T do you mean: A or B?",
    naming both stored people, with no value.
  - Unmoved: exact_wins 041-046, no_match 047-052, last_name_only 053-056 and statements
    057-060. These 20 are byte-identical to 221.
  - Every reply is listed in panel-score.log.
- **Dev (15 moves, as predicted in P236.2):**
  - unique_first d236-01, 03, 05, 07, 08, 23, 25, 26
  - of_form 02, 06
  - ambiguous 09, 10, 11, 27, 28
  - Replies are in dev236-score.log.
- **Suites:** none. rt143 P1-P8 (Dara Fenn / Dara Fenner) always use the full name and are
  unchanged. A question that says only "Dara" is tested on dev: d236-09 and d236-27 give
  "Which Dara do you mean: Dara Fenn or Dara Fenner?".
- **Flip check (228 rule):** no unpredicted flip toward an abstain or "Was that a question?"
  happened anywhere, so no 5x reruns were needed. The guard was installed.

## Deviations
1. **Copied base rows for M3.** The brief pointed at
   artifacts/claude-tableask221-20260922/suitediff/. With that folder, fable_suitediff218.py
   reports rt136 and rt143 as SKIPPED, because it looks for files named "redteam136" and
   "redteam143".
   - I copied 221's suitediff rows byte-for-byte into base221rows/, with those two files
     renamed (redteam136-rows.json, redteam143-rows.json).
   - This was declared in PASSMARKS and sealed. No code was changed.
2. **Suites ran much faster than 221's.** 26.8 s total here against about 190 s for 221. The
   likely reason is load: about 8 here, 88 during 221's run. As a check, the pilot rt143 rows
   file came out byte-identical to 221's saved rt143 rows.
3. **No field map was needed.** The panel's fields (id, family, setup, question, gold) matched
   the sealed scorer. "statements" is mapped to "statement" inside the sealed scorer.
4. **One dev case was changed during the pilot, before the seal.** In d236-04, the setup
   "Orrin Vask lives in Brindle." saves nothing on 221 (the exp-232 multi-word verb gap). Its
   family was changed to no_match, with a note in the file. d236-25 adds the possessive setup
   version, and that one answers.

## What it means
- On this blind panel, a question that uses only someone's first name now gets the right answer
  whenever exactly one stored person has that first name: 30 of 30 were right.
- When two stored people share the first name, it asks which one you mean and gives no value.
- If the first name alone is itself a stored person, that person wins.
- A first name nobody has, a surname on its own, and every statement behave exactly as before.
- It wrote nothing on questions, never gave a wrong value, left the frozen suites and the sleep
  smoke unchanged, and costs well under 1 ms.

## What it doesn't mean
- **One writer, clean template.** The panel is 60 items from one writer, all built from the
  clean template "<First> <Last>'s <relation> is <Value>." with questions the base already
  reads when given the full name.
  - It does not show that first names work inside questions the base cannot read at all.
  - It does not show they work in two-hop questions, yes/no questions, or teaches.
- **It never guesses a surname.** "Who is Marr's employer?" still abstains, by design.
- **Some cases are only covered by dev.** No panel item has more than 2 people sharing a first
  name. The 3-name and 4-name clarify are covered only by dev (d236-11, d236-28). With more
  than 3 people, only 3 names are listed.
- **Only full names already stored as subjects.** A first name matches only people stored as
  the subject of a taught fact. Someone who appears only as a value (for example "Yimow
  Lylkow" as a spouse) is not found by their first name.
- **Only a lone first name.** A capitalised word followed by another capitalised word (for
  example "Ysolde Kane") is treated as a different full name and left alone.
