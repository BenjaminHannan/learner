# Exp 231b: chains in table questions, re-run on 221 + 232c

## Verdict: FAIL (registered)

**Failed marks:** M1a, M1d and M1e.
**Passed marks:** M1b, M1c, M2, M3, M4 and M5.

**What changed.** With 232c's fix, the blind panel can now be taught: 69 of 72 items are answerable, up from 14 in exp 231. On those 69 items:
- 231b gets 35 right, and 221+232c gets 12 (M1c passes).
- On the answer and yes/no items, 231b gets 28 of 62 (45 %), below the 85 % bar.

**The failures:**
- **M1a and M1e fail on one item, c231-071.** It is a conflicting-town trap:
  - Setup: "Magnus Thwaite lives in Pellwick." then "Magnus Thwaite lives in Oskerwell."
  - The agent asks whether to change the city. Nobody answers, so only Pellwick is stored.
  - Asked about the chain, 231b answers "Cyrus Ellery's boss is Magnus Thwaite, and Magnus Thwaite lives in Pellwick."
  - The panel expects an abstain, so the sealed scorer counts this as WRONG. It was RIGHT (an abstain) on 221, 231 and 221+232c.
  - The miss is deterministic (5/5 alone, below). It is not a flake.
- **M1d fails** because of wordings the chain step does not read. 21 of the 34 misses ask about a person by first name only; that is 236's job.

**Build.**
- Base arm "221+232c": `scripts/claude_loop221x232c_agent.py`. It puts TableAsk221Mixin outermost over 232's Loop232Ears, with the 232c subject rule rebound at import, and uses Loop232AgentLoop.
- New arm "231b": `scripts/claude_loop231b_agent.py`. It is the base arm plus 231's sealed Chain231Mixin outermost.
- Both install the 228 guard at import and in the builder, and put SrcGuardMixin228 first in their daemon bases.
- Configs: 221's and 231's sealed configs. Only the descriptive stand_in and daemon strings differ.

**Order of work.**
1. Pilot: dev, suites and sleep smoke, in the scratchpad.
2. Seal at 16:31 (SEAL.sha256.txt, 22 files, including 231's scorer and its byte copy `scorer231-copy.py`, sha a4575fcb...).
3. Panel seal check: panel.jsonl OK (e7aacaec...).
4. One panel run per arm (16:31:16 to 16:31:24).
5. Score, then the registered dev, suites and sleep smoke.
6. After all runs: every sealed file still OK (0 non-OK lines), and the panel seal is still OK.

Each run took under 2 minutes, with the 1-minute load between 12 and 21 at each start (under 60).

## Marks

| mark | bar | result | pass? |
|---|---|---|---|
| M1a 231b WRONG, 71 items + c231-013 if its reply changed | 0 | **1** (c231-071). c231-013 reply changed and is now RIGHT, so it counts, as 0 | **FAIL** |
| M1b question writes, 231b, all 72 | 0 | 0 | pass |
| M1c answerable (69 on 231b): 231b right >= (221+232c) right + 20 | >= 32 | 35 vs 12 (+23) | pass |
| M1d answerable answer + yes/no items: 231b right | >= 85 % | **28 / 62 = 45.2 %** | **FAIL** |
| M1e right on 221+232c but not 231b / right on 231 but not 231b | 0 / 0 | **1 / 1** (c231-071 both) | **FAIL** |
| M2 dev231 on 231b | as 231: 54/54, traps 15/15, 0 WRONG, 0 writes | 231's 54: all answerable and 54/54 RIGHT. d231-055 now answerable and RIGHT (55/55). Traps 15/15, WRONG 0, writes 0. Only reply change vs 231: d231-055 | pass |
| M3 suitediff218 vs 231's rows | GATE clean; moves = predicted (none) | rt136 0, rt143 0, sessions152 0, bench 0 moves; GATE clean on all four | pass |
| M4 sleep smoke | 231 marks, < 300 s | sleeps 1, installed 1 (20 episodes), probes 5/5, wrong 0, broken = abstain, taught 50/50, ow 0, 81.0 s | pass |
| M5 median (231b - 221+232c) ms per panel question | <= +10 ms | -3.46 ms (p90 +0.11) | pass |

**Schema check** (driver side): passed. There were 72 items, the id sets matched 231's saved rows, and all kinds were valid.

**Regrade check:** 231's saved 221 and 231 rows, rescored with the same functions, match 231's scores.json on all 72 items (0 differences).

### Whole panel (72 items, 9 traps)

| arm | RIGHT | WRONG | ABSTAIN | OTHER | answerable on own setup | writes |
|---|---|---|---|---|---|---|
| 221 (231's saved rows) | 13 | 1 | 58 | 0 | 14 | 0 |
| 231 (231's saved rows) | 16 | 1 | 55 | 0 | 14 | 0 |
| 221+232c | 14 | 0 | 58 | 0 | 69 | 0 |
| **231b** | **36** | **1** | **35** | 0 | **69** | 0 |

On the 69 items answerable on 231b:

| arm | right | right, answer + yes/no (of 62) |
|---|---|---|
| 221 | 11 | 4 |
| 231 | 14 | 7 |
| 221+232c | 12 | 5 |
| 231b | 35 | 28 |

Right by family, out of 9 each:

| family | 221 | 231 | 221+232c | 231b |
|---|---|---|---|---|
| verb_2hop | 0 | 0 | 0 | 4 |
| possessive_2hop | 3 | 3 | 4 | 4 |
| of_form | 0 | 1 | 0 | 5 |
| three_hop | 0 | 0 | 0 | 3 |
| user_chain | 1 | 1 | 1 | 6 |
| yes_no_chain | 0 | 2 | 0 | 6 |
| casual | 0 | 0 | 0 | 0 |
| traps | 9 | 9 | 9 | 8 |

## Blocked items (a setup turn did not save), per arm

**221+232c and 231b: 3 each, the same 3.**

1. **Base does not understand "My coach is ..."** (1 item). c231-045, turn "My coach is Gunnar Treece.". The base gives its long not-understood reply. This is the same as in 231.
2. **Conflicting second town, confirmation never given** (2 items):
   - c231-071, turn "Magnus Thwaite lives in Oskerwell.": "I have Magnus Thwaite's city as Pellwick. Do you want me to change it to Oskerwell?"
   - c231-072, turn "Linnea Rourke lives in Ivelford.": same kind of question.
   - These are traps, and not saving here is the intended behaviour.

**221 and 231 (saved rows): 58 each.** Mostly two-word verb teaches, as reported in 231.

232c's fix removed 55 of the 58 blocks.

## Every move

### Panel, 231b vs 221+232c: 38 reply changes
- **23 ABSTAIN -> RIGHT** (the chain answers):
  - 001, 004, 007, 009 (verb_2hop);
  - 019, 022, 024, 025, 027 (of_form);
  - 029, 032, 033 (three_hop);
  - 037, 039, 041, 042, 043 (user_chain);
  - 046, 050, 051, 052, 053, 054 (yes_no_chain).
  - Example, 029: "Jasper Kilby's wife is Ottoline Reyes-Hart, Ottoline Reyes-Hart's brother is Lucan Reyes-Hart, and Lucan Reyes-Hart works for Vannick Robotics."
- **7 ABSTAIN -> ABSTAIN** (003, 006, 028, 047, 048, 057, 058). The long refusal becomes "I don't know anyone called <first name>." All 7 are first-name-only questions.
- **7 RIGHT -> RIGHT** (traps 064, 066, 067, 068, 069, 070, 072). The long refusal becomes a targeted abstain, e.g. "..., but I don't know X's city."
- **1 RIGHT -> WRONG** (c231-071). See the verdict.

### Panel, 231b vs 231's saved rows: 22 reply changes
- **20 ABSTAIN -> RIGHT**: the 23 above minus 025, 051 and 052, which were already right on 231.
- **1 WRONG -> RIGHT**: c231-013 "What is Bram Tolliver's coach's language?". "Sunniva Rask speaks Kettish." now saves. The reply is "Bram Tolliver's coach's language is Kettish.", the same on 221+232c; the base answers it.
- **1 RIGHT -> WRONG**: c231-071.

### Panel, 221+232c vs 221's saved rows
One reply changed: c231-013 went WRONG -> RIGHT. Every other base reply is byte-identical to 221. Many setups now save, but without the chain step the base still cannot answer the chains.

### Suites
There were 0 moves on all four suites vs 231's rows, as predicted.
- 232c's only move vs 138i is rt143 K5, to "I don't know Bram Kite's place of birth.".
- 221 and 231 already gave that exact reply (through the 221 table stage), so K5 is not a move here. Only the internal stage name changed (loop221-table-ask -> fake), and the tool does not compare it.

### Dev
One reply change vs 231: d231-055, blocked by design in 231, now saves both setup turns. It answers "Anselm Rook's boss is Ibbet Crane, and Ibbet Crane lives in Tillmarsh.".

## Every miss on 231b, with cause

**Wrong (1):**
- **c231-071** (trap, blocked): 231b answers with the stored city while a change question is still pending. The scorer expects an abstain.
  - Unregistered check (`diag-unregistered/`): run alone 5 times, it gave the same answer 5/5; 221+232c abstained 5/5.
  - On both arms, the plain one-hop question "Where does Magnus Thwaite live?" also answers "Magnus Thwaite's city is Pellwick.".
  - So the chain step behaves like the base's own one-hop read. Neither one reports the unresolved conflict. The 228 guard was installed.

**Answerable answer and yes/no misses (34 of 62).** "FN" marks a first-name-only question: the setup used a full name, and the question uses only the first name. That is 236's job and is left out here.

**Group A: first-name only, the chain step reached it** and replied "I don't know anyone called X." (17 items):
003 Hollis, 006 Selby, 011 Ysolde, 014 Idris, 017 Leocadia, 020 Ruben, 023 Benedek, 028 Winifred, 031 Taddeo, 034 Oriana, 036 Harriet (also "town"), 047 Tobias (yes/no), 048 Adela (yes/no), 056 Hamish ("Where's"), 057 Liora (leading "so"), 058 desmond (leading "hey," + lower case), 061 alaric ("who's" + lower case).

**Group B: first name plus another gap; the long refusal** (4 items):
- 002 Orla: FN, plus "What language does ... speak?" (no template match).
- 008 Cato: FN, plus the same language wording.
- 059 marisol: FN, plus the language wording, plus no "?".
- 063 evadne: FN, plus no "?" and "ok and" filler.

**Group C: "What language does X speak?" / "Which language ..."** (6 items). Table v1's template is "What language(s) does {X} speak?". It needs "languages" or "language(s)", so the chain reading finds nothing (checked: the "languages" form reads). Items: 005, 021, 026 ("Which language"), 030, 035, 040.

**Group D: "X's boss's town?"** (2 items). The base answers first, with the honest "I don't know Fenna Coyle's town." / "... Oswin Kade's town.", so the chain step never runs. It only acts when the base misses, and the chain reading of "town" would work. Items: 010, 015.

**Group E: no yes/no chain template for "work at / work for"** (1 item): 049 "Does Neville Ashby's husband work at Halvenworth Logistics?".

**Group F: wordings outside the templates** (4 items):
- 044 "Who's the husband of my cousin?": "Who's" contraction.
- 055 "where does isolde brannock's boss live": no "?". The chain step only acts on turns ending in "?", though the reading works with one.
- 060 "wait where does my boss live again?": "wait" is not in the filler list.
- 062 "Do you know where Gemma Tallis's neighbor lives?": indirect question.

**First names in total:** 21 of the 34 misses (groups A and B) are first-name-only questions. If all 21 were fixed and nothing else changed, 231b would be at most 49/62 (79 %), still under the 85 % bar. The other 13 misses (groups C to F) are template and wording gaps.

**Blocked, answer kind (1):** c231-045 (see "Blocked items"). It abstains on every arm.

Every item with all four grades and the 231b reply is in `panel/cases.md`. Full per-item data (replies of every arm, answerable per arm, ms) is in `panel/scores231b.json`.

## Deviations
1. **Driver.** `run231b.py` is a new file in this folder. It imports 231's sealed scorer unchanged (sha checked at start), adds the two arms to its CONFIGS dict at runtime, and uses its own run_arm / load_items / score_one / answerable. The M1 aggregates are computed in the driver, because 231's score() hard-codes arm names "221"/"231" and 221-based answerability.
2. **Driver sha typo, fixed before the seal.** My first pilot call stopped at the sha check because the constant had a typo, so nothing ran. I fixed the constant before any pilot row was produced.
3. **Schema check.** The OPUS-RULES panel-schema contract is implemented in the driver, not the sealed scorer, which may not change. The brief gave no separate schema, so the check uses 231's load_items plus the id sets of 231's saved rows.
4. **M2 bar wording.** The dev set now has 55 answerable items, not 54, because d231-055 saves on 231b. PASSMARKS required 231's 54 to stay answerable and right, and every answerable item to be right. Both held.
5. **M3 base rows.** `base231/` holds byte-identical, renamed copies of 231's sealed suitediff rows, so that the 218 tool finds rt136/rt143. It is the same trick 231 used, and the files are in SEAL.
6. **The base arm was not run on the suites or the sleep smoke.** No mark needs it.
7. **Unregistered diagnosis after the registered runs:**
   - c231-071 alone 5 times per arm, plus the one-hop question (`diag-unregistered/`);
   - a pure-function check of unique_chain231 on missed wordings.
   Neither is part of any mark.

## What it means
- Once the two-word-name teaching gap is closed, the chain step does real work on a blind panel written by someone else. It answered 23 more items than the same base without it (35 vs 12 of 69), and it showed each hop in plain words.
- It never wrote to the notebook on a question, never slowed questions down, and changed nothing on the four frozen suites.
- On the dev set it still gets every item right, including the two-word-name case that used to be blocked.
- 231's one false alarm, c231-013, is gone: the fact now saves and the base answers it correctly.

## What it doesn't mean
- **It does not pass.** On one trap, two different towns were given for the same person and the change was never confirmed. There, 231b answers with the first town instead of flagging the conflict.
  - The base does the same on the one-hop question, so the chain step copies that behaviour into chains. That is still a real wrong-answer mark.
- **It does not handle how people ask.** About half the answerable questions still miss:
  - one-name questions ("Where does Ysolde's boss live?" after teaching "Ysolde Brack"), which is 236's job;
  - "What language does X speak?" without "(s)";
  - "Who's", "wait ...", "Do you know where ...";
  - a missing question mark;
  - "town" after a possessive chain.
- **Fixing first names alone would not reach the 85 % bar.** The template gaps would still leave it at most 79 %.
- **Every rule here is hand-written software** over a notebook. It is not learned understanding.
