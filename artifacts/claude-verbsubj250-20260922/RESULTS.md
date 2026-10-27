# Exp 250 RESULTS: verb questions with lowercase / multi-word names (243 cause B)

**Result: registered FAIL, on mark M1b only.** The sealed scorer counts 6 panel items with a
wrong value. All 6 are direction items (q243-085..090) where loop250's reply is byte-identical
to base228's own reply in base228.jsonl ("Who does Brylto employ?" -> "Brylto's employer is
Gedund."). This change did not cause them; they are base228 leaks, and exp 251 owns them. M1e
lists them and does not count them, but M1b as written ("0 on all 124") does. I sealed M1b
literally, so the verdict stays FAIL. Whether inherited leaks should be left out of M1b is the
director's call. I have not re-scored anything.
Every other mark passed: verb_subject 11/12, 0 question writes, controls 12/12 byte-identical,
0 regressions, untaught 10/10, 0 new direction leaks, dev 57/57, suites clean with only the
predicted move, sleep smoke equal to 138i, M5 -0.07 ms.

## Marks
| mark | bar | result | pass |
|---|---|---|---|
| Schema | no mismatch | SCHEMA OK (hashes = director's) | yes |
| M1a verb_subject right | >= 11/12 | 11/12 | yes |
| M1b wrong-value items (124) | 0 | 6 (all base228 direction leaks, byte-identical, 0 new) | **no** |
| M1c question writes (124) | 0 | 0 | yes |
| M1d control byte-identical | 12/12 | 12/12 | yes |
| M1e regressions other families | 0 | 0 | yes |
| M1e untaught value-free | 10/10 | 10/10 | yes |
| M1e new direction leaks | 0 | 0 (base leaks listed: 085, 086, 087, 088, 089, 090) | yes |
| M1f combo | no bar | 0/8 right, 0 wrong values | - |
| M2 dev fix / keep / trap | 35/35, 12/12, 10/10 | 35/35, 12/12, 10/10; 0 writes; setup replies identical | yes |
| M3 suites vs 138i | only rt143 K5, GATE clean | rt143 K5 reply-only only; rt136/sessions152/bench 0; GATE clean | yes |
| M4 sleep smoke | 138i marks | sleeps 1, installed 1, probes 5/5, wrong 0, taught 50/50, ow 0, 92.4 s | yes |
| M5 median added ms | <= +5 | -0.066 | yes |
| live base228 = base228.jsonl | (sanity) | 124/124 | - |

## Every move
- Panel verb_subject (decline -> right, 11): q243-057 "Where does kekyn live?" -> "Kekyn's city is
  Taerow."; 058 Puxund Tryska; 059 julvel stalar; 060 Bragel Kruskek (work for); 061 thaltel (work
  for); 062 naman (where work); 063 Kydow Zorkund (where work); 065 jaene yyrvett (work for); 066
  "WHERE DOES VYTITH JERVUND LIVE?"; 067 vraemin thanund; 068 braeltel (where work). Answers use
  the stored spelling ("Julvel Stalar").
- Panel miss (1): q243-064 "Where do rorkix live?" stays the glued decline. Diagnosis: the
  verb-question regex I copied from fable_fix167_verb.py uses `does?`, which matches "doe"/"does"
  but never "do". Even "Where do Rorkix live?" misses on the base for the same reason.
- Panel, all other families: 0 moves against base228 (controls byte-identical; untaught 122/123
  now give "I don't know Gruvund's city." / "I don't know Vraekett Gezek's city." instead of the
  glued decline; no value; they count as right for untaught).
- Dev: 35 fix items decline -> right; 0 keep moves; traps value-free.
- Suites: rt143 K5 reply-only move (verdict OK -> OK, stored identical): glued decline ->
  "I don't know Bram Kite's place of birth." This was the predicted move.

## Deviations
- Scope: the widened subject check covers 167d's two question shapes ("Where does X work?",
  "What language does X speak?") as well as Verb167's three. It is the same check in the same
  slot, recorded in the design note before sealing. It accounts for 3 of the 11 panel wins
  (062, 063, 068).
- Before sealing, one command in my seal step ran `ls` on the panel's SEAL.sha256.txt path with
  its output thrown away. No panel content was read or printed before my seal.
- Before sealing, I changed dev case d250-042 from keep to fix (the base declines it because
  Pell has 2 facts) and added keeps 056 and 057. Also before sealing, the scorer was changed to
  alternate arm order item by item, for fair timing.
- After sealing, no file was changed and nothing was re-run. Seals re-verified OK before the panel run.

## What it means
When you ask "Where does brannick live?" or "Who does joren hale work for?" about someone
Premonition knows, it now answers with the stored fact, spelled the way it was taught.
Before, it said "I don't know." It only does this when the name matches exactly one person in
its notebook, so a word like "it" or "everyone" is never treated as a name. It never saves
anything from a question. Questions it already answered give exactly the same replies as before.

## What it doesn't mean
It does not fix "Where do X live?" (with "do" instead of "does"). That wording still fails
because of an old pattern bug. It does not help any other kind of question: combo, whats,
no-apostrophe, first-person and my-relation items all still decline. It does not fix the
direction leaks ("Who does X employ?" answered with X's employer). Those come from the base,
and exp 251 owns them. They are also why the registered verdict is FAIL. The panel has only 12
items for this family, so 11/12 shows the wall is gone for these shapes. It is not a measure
of how often real users hit it.
