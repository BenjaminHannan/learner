# Exp 221b -- PASSMARKS (written and sealed before the fresh panel is opened)

Build: loop221b = loop221 (sealed, read-only) + StoredRel221bMixin outermost on
the ears (scripts/claude_loop221b_agent.py). One change only: when the 221
stack would miss or abstain on a question about one named subject (or the
user), the question's content words are compared with the relation keys that
subject already holds as ACTIVE TAUGHT facts; exactly one match -> ordinary
one-hop ask on that key; otherwise the 221 reply is untouched. Rule text:
module docstring of scripts/claude_loop221b_agent.py (match221b).
Config: loop221b-config.json (= loop221 config; only two description strings
differ). No table rows added; the relation table is untouched.

Verdict = PASS only if every mark M1-M5 passes. One failure = FAIL (named).

## M1 -- fresh blind panel (artifacts/claude-tablepanel221b-20260922/, run ONCE)
Opened only after this seal. Its SEAL.sha256.txt must verify with
`shasum -a 256 -c` first, else M1 is VOID. All three arms (138i, 221, 221b)
run on it by scripts/claude_221b_run.py, graded by its one sealed scorer
(docstring there: gold parts all required; "other values" = the arm's active
taught values not inside gold and not named in the question; RIGHT / WRONG /
MISS; ABSTAIN-type items are those with empty gold or an abstain-like
"expect"; the not-understood clarify counts as an abstain).
- M1a: 221b WRONG = **0** over all items.
- M1b: question-turn writes (fact hash changed on the question) for 221b = **0**.
- M1c: 221b RIGHT on ANSWER-type items >= 221 RIGHT on ANSWER-type items **+ 10**.
- M1d: items RIGHT on 221 but not RIGHT on 221b = **0** (all items).
Field map: the sealed scorer is not edited. If the panel's field values do not
fit it, a separate unsealed field-map file is written after opening, named as
a deviation, and both the sealed-scorer result and the mapped result are
reported; the registered verdict uses the sealed scorer.

## M2 -- dev cases (dev221b.jsonl, 72 items, written by me from scratch)
- M2a: family "hit": 221b RIGHT >= **90 %** (29 of 32 needed).
- M2b: family "ambiguous" (two or more stored keys match): 221b abstains **8/8**
  and the fallback stage never fires on them.
- M2c: the fallback stage fires on **0** items of families guard / keep /
  untaught / ambiguous, and 221b reply == 221 reply on all of them.
- M2d: scripts/claude_221b_unit.py prints UNIT: 11/11 (stem pairs; sleep-derived,
  proposed, web-quarantine and forgotten rows never served by the fallback).

## M3 -- frozen suites vs 221's behaviour
scripts/fable_suitediff218.py --base-dir artifacts/claude-storedrel221b-20260922/base221
(byte-identical renamed copies of 221's sealed suite rows; README there)
--only rt136,rt143,sessions152,bench:
- **0** new WRONG / WRONG-WRITE / junk write / lost OK; GATE clean.
- Predicted moves: **none** (predicted_moves221b.txt). Any move is unpredicted
  and fails M3; a known-flake move (toward abstain / "Was that a question?")
  is still counted, then that item is re-run alone 5 times and reported.

## M4 -- sleep smoke
scripts/fable_sleepsmoke206.py on loop221b: sleeps=1, installed=1 (episodes 20),
probes 5/5, wrong 0, broken=abstain, taught 50/50, overwrote 0, wall < 300 s.

## M5 -- cost
Median (221b ms - 221 ms) on the panel question turns <= **+5 ms**.

## Declared limits (not marks)
- The not-understood clarify counts as an abstain in the scorer.
- USER replies from the fallback render "your ..." in lower case (the same
  rendering 221's own "my" table asks get); not fixed here.
- Base 138i/221 wrong answers that the fallback does not touch (dev G05, G18:
  nhop answers) count against M1a if the panel has such items; not fixed here.
