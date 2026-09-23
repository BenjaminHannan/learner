# Exp 221 -- questions read through the relation table (writes untouched)

## Verdict: FAIL (registered). P1 fails, and P3 fails on one mark. P2, P4, P5 and P6 pass.

Build: loop221 = loop138i with TableAsk221Mixin outermost on the ears.
Code: scripts/fable_fix221_tableask.py, scripts/fable_loop221_agent.py.
The table is relation_table_v1.json (217 folder), read-only and unchanged.
No v1.1 copy was made.
Order kept: PASSMARKS + code + table were sealed (SEAL.sha256.txt, 14:48:21) before any
registered run. Then the panel seal was checked (both files OK) and the panel was run once.
All runs used Mac CPU with OMP/MKL=1, one at a time.

## Marks

| mark | registered bar | result | pass? |
|---|---|---|---|
| P1 answer families (verb/when/alias/of_form/inverse) | >= 90 % | **46/71 = 64.8 %** (verb 9/14, when 6/14, alias 8/16, of_form 11/14, inverse 12/13) | **FAIL** |
| P1 wrong values, all 91 items | 0 | 0 | pass |
| P1 labelled inverse answers | 100 % | 9/9 | pass |
| P2 question turns that changed the notebook (loop221) | 0 | 0/90 panel turns, 0/31 dev turns (138i arm: 0 and 0). All 91 scored turns (incl. the one without "?") wrote nothing | pass |
| P3 moves not predicted in advance | 0 | 0 (rt136 0 moves, rt143 20, sessions152 1, bench 0 -- all 21 were predicted) | pass |
| P3 tool-flagged new WRONG / WRONG-WRITE / junk | 0 | **1 new WRONG** (rt143 S5, see below) | **FAIL** |
| P3 hand verdict "worse" | 0 | 0 by hand (S5 is a true taught fact; see below) | pass |
| P3 G3 director pairs | 6/6 identical to sealed 138i | 6/6 | pass |
| P3 sleep smoke | same marks as 138i | sleeps 1, installed (episodes 20), probes 5/5, wrong 0, Q99 abstains, taught 50/50, overwrote 0, 278 s (< 300; 138i took 99 s on a quieter Mac; load average 88 now) | pass |
| P4 turns where the table answered AND the router fired | 0 | 0 (panel and dev) | pass |
| P4 dev evidence E1-E4 | all correct | 4/4 (and E5 too) | pass |
| P5 untaught | 100 % abstain, 0 wrong | 10/10 | pass |
| P5 no_relation | 100 % no value, no write | 5/5 | pass |
| P5 self | 100 % = 138i | 5/5 (also = panel expected_reply 5/5) | pass |
| P5 "Who is Kim's?" | stays a clarify | unchanged not-understood reply | pass |
| P6 median added ms per question turn | <= 5 | -1.1 ms on the panel (dev -4.5); loop221 is faster because routing is skipped | pass |

For comparison, 138i on the same panel scored 12/71 by the panel's own base grades (verb 3,
when 0, alias 4, of_form 2, inverse 3). All 3 of those inverse answers were unlabelled, so
138i scores 9/71 under the P1 label rule. Loop221 therefore moved 37 items from unhelpful to
correct, and moved none to wrong.

## Every P1 case
See p1-cases.md (91 rows: id, family, question, loop221 reply, grade). Full replies from
both arms are in p1panel/rows.jsonl and turns.jsonl. The 25 misses, grouped by cause
(this is diagnosis only; nothing was changed after the run):

- **12: no table template matches the wording.**
  - Speak: p221-009 "What language does X speak?", 013 "What language do I speak?"
  - Own, coach: 011 "Who owns ...", 012 "Who coaches ..."
  - Work: 010 "Where do I work?"
  - Birthday wording: 026 "When's X's birthday?", 027 "When is my birthday again?", 028 "When was X's birthday?"
  - Other: 037 "Who's my manager?", 042 "What's my mom's name?", 044 "What is the name of X's pet?", 066 "Which books did X write?"
- **9: the stored relation word is in no table group.**
  - Dates: 018/025 founding_date/founding_year, 021 wedding_anniversary, 022 opening_date, 023 graduation_date
  - Aliases: 035 physician (asked as doctor), 039 supervisor (asked as boss), 040 residence (asked as city), 041 native_language (asked as mother tongue)
- **3: "Who is the R of X?" where R is in no table group.** 048 landlord, 052 dentist, 053 mayor. The "the R of X" form is generic, but section 6 only reads relations that are listed in the table.
- **1: a deliberate table decision.** 033: hometown is not an alias of birthplace (217 rule: aliases only for true synonyms). The panel counts them as the same.

Every miss is an abstain ("I do not know ..." / "I don't know X's R."). None asserts a value.

## Every P3 move (hand verdicts)
- **rt136:** no moves.
- **rt143** (20 moves; all predicted by rule A):
  - **Plain abstain replaced by a targeted abstain; suite verdict OK -> OK (11 cases):**
    - "I don't know Bram Kite's country of citizenship.": K1
    - "I don't know Norland's official language.": K2
    - "I don't know Bram Kite's notable work.": K3
    - "I don't know Cora Lind's spouse.": K4
    - "I don't know Bram Kite's place of birth.": K5
    - "I don't know anyone whose founder is Ada Wren." (unlabelled because it is not an answer): K7
    - "I don't know Cora Lind's employer.": L2
    - "I don't know Bram Kite's religion or worldview.": L5
    - "I don't know Bram Kite's date of birth.": L6
    - "I don't know Hana Okafor's spouse.": Q7 (after the correction, the old spouse has no fact)
    - "I don't know anyone called Norlandia.": O3 (the substring trap was avoided)
  - **Unknown-entity abstains, OK -> OK:** O2 "I don't know anyone called Jonas Pike.", O4 "... Vera Quinn." Hand verdict: fine.
  - **The 138i reply "I have no opinions." was wrong:**
    - K9: the new reply is "I don't know anyone called Ostmark." (WRONG-ANSWER -> OK). Better.
    - J8: the question has a one-letter typo in the name. The new reply is "I don't know anyone called Norlanb." (WRONG-ANSWER -> MISSED). Better: an honest miss instead of a wrong reply.
  - **Real answers, MISSED -> OK:**
    - P1 "Dara Fenn's country of citizenship is Litora."
    - P2 "Dara Fenner's country of citizenship is Cardova."
    - Q1 "Joren Hale's spouse is Petra Voss."
    - Q2 "Sella Marne's country of citizenship is Tormeil."
    - Hand verdict: better. P1 and P2 are the near-name pair and each got its own value.
  - **S5, flagged "new WRONG" (OK -> WRONG-ANSWER).**
    - Teaches: "Bram Kite is married to Cora Lind" and "Cora Lind is married to Bram Kite".
    - Question: "Who is Bram Kite married to?"
    - New reply: "Bram Kite's spouse is Cora Lind."
    - The suite's gold is "abstain" (a loop-guard test on a 2-cycle). By hand, the reply is a
      true one-hop fact, taught word for word, so this is not a worse answer. The registered
      mark counts tool flags, though, so P3 fails on this line. I am not overriding my own mark.
- **sessions152** (1 move, predicted A): S1-family10#19 "Who is Kip married to?" after
  "Kip's wife is Jo." gives "Kip's wife is Jo." (UNHELPFUL -> OK). Better. fact_writes unchanged.
- **bench:** no moves. 58 cases were predicted as candidates and did not move; the prediction
  is a superset by design.

## What this means
- The narrow claim holds. Reading questions through the table adds answers without touching
  writes: 0 question-turn writes and 0 wrong values on 91 blind items. It lifts 138i from
  9-12/71 to 46/71 on these families, keeps G3 and the sleep smoke identical, and costs no time.
- Inverse answers are always labelled "(worked out backwards)", and none of them is stored.

## What this does not mean
- It does not reach the registered 90 % bar. Coverage is the bottleneck, not safety: 21 of
  the 25 misses are wording or relations that table v1 does not list.
- It says nothing about two-hop questions, writes, sleep beyond the smoke, or the other
  parallel pieces (215/216/219/220).
- The panel is 91 items from one writer. Per-family counts are small (13-16).

## Deviations
1. Panel field map, written after opening the panel. This is scripts/fable_fix221_panelmap.py
   (sha in panelmap.sha256.txt); the sealed runner was not edited.
   - Fields are read directly: setup / question / family / gold.
   - A gold of "A; B" is split, and ALL parts must appear (the README's rule).
   - For the wrong-value test, "other taught values" come from stored_after_setup instead of
     a regex over the setup sentences.
   - P2 also counts the one scored turn that has no "?" (p221-085).
2. Design section 6 rule (c), declared in PASSMARKS: 153 reverse answers get the label, and
   153's "I don't know anyone whose ..." is widened through the table group.
3. Also declared in PASSMARKS:
   - Yes/no questions are not handled.
   - There is no forward reading from inverse_storage keys.
   - G4 was not run (its subprocess is hard-wired to 138i).
4. The sleep smoke took 278 s against 99 s for 138i. The Mac was under heavy load (load
   average about 88). It is under the 300 s bar.
5. I ran the dev set again on the sealed code (dev-sealed/) to score P4 and the "Kim's"
   check. This matches the pre-seal dev run: 30/31.

## Files
- PASSMARKS.md, SEAL.sha256.txt, predicted_moves221.json/.txt, loop221-config.json, dev221.jsonl
- p1panel/ (+ p1panel.log, p1-cases.md), dev-sealed/
- suitediff/ (+ suitediff-*.log, p3check.log), g3/ (+ g3.log), sleepsmoke/ (+ sleepsmoke.log)
