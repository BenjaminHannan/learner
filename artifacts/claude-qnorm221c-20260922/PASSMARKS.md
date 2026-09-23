# Exp 221c -- PASSMARKS (registered before any registered run and before the panel is opened)

Build: loop221c = loop221 (scripts/fable_loop221_agent.py, config
artifacts/claude-tableask221-20260922/loop221-config.json) + QNorm221cMixin outermost
(scripts/claude_loop221c_agent.py). That mixin is the one change. Design note:
design/v3/30-modes/221c-qnorm-opus.md.

The verdict is PASS only if every mark M1-M5 passes. Any single failure = FAIL (named mark).
All counts are per item; nothing is averaged except the latency median.

## Scorer (sealed): scripts/claude_qnorm221c_run.py
One scorer for all arms (138i, 221, 221c). Its docstring is the rule:
- RIGHT (value gold): every gold value (split on ";") is in the reply as whole words, and no
  other stored value is.
- RIGHT (yes/no gold): the reply starts with the right yes/no.
- RIGHT (abstain gold): the reply is abstain-like and holds no stored value.
- WRONG: a reply that asserts a stored value that is not gold (see the docstring), or a yes/no
  reply that starts with the opposite word.
- QUESTION WRITE: stored triples after the scored question-shaped turn differ from the triples
  after setup.
Field-map rule: if the panel's field names differ from the loader's fallbacks, only
load_items() may be adapted, as a driver-only fix reported with its diff. Scoring rules are
never edited.

## M1 -- blind panel (artifacts/claude-tablepanel221b-20260922/panel.jsonl, 120 items, run ONCE)
First, `shasum -a 256 -c` must verify the panel's own SEAL.sha256.txt; if it does not, M1 is
VOID. The README is read only after this seal. Arms 138i, 221 and 221c run in one pass.
- 221c wrong values (all items): **0**
- 221c question writes: **0**
- family `contractions_fillers`: 221c right **>= 221 right + 6**
- overall: 221c right **>= 221 right + 8**
- items right on 221 but not right on 221c: **0**

## M2 -- dev set (dev221c.jsonl, 60 items, written from scratch; make_dev221c.py)
- normalisable dev questions (expect = "rewrite", 44 items): 221c right **>= 95 %** (>= 42/44)
- every statement item (family statement, 10): 221c reply, setup replies and stored triples
  **byte-identical** to 221 (10/10)
- also reported, not a mark: the 6 control items are identical to 221.

## M3 -- frozen suites (scripts/fable_suitediff218.py, --only rt136 / rt143 / sessions152 / bench,
one at a time)
Base = the sealed 221 rows. They are copied unchanged to base221/. rt136/rt143 are renamed
redteam136/redteam143 so the tool's filename search finds them; the shas are in
base221-copy.sha256.txt, and each pair must be equal.
- tool-flagged new WRONG / new WRONG-WRITE / new junk write: **0**
- moves only as predicted. Predicted: **0 moves in every suite** (the pilot gave 0/0/0/0; the
  normaliser fired on 11 distinct suite turns, all listed in predicted_moves221c.txt, without
  changing a verdict, reply or store). Any move = FAIL. The known ~1/800 bench flake still
  counts against this mark. If it appears, that item is re-run alone 5 times and reported.

## M4 -- sleep smoke (scripts/fable_sleepsmoke206.py on loop221c)
PASS with 221's marks: sleeps 1, installed 1 (episodes 20), probes 5/5, wrong 0, broken fact
abstains, taught 50/50, overwrote 0, wall < 300 s.

## M5 -- latency
The median over panel items of (221c ms - 221 ms) for the scored question turn is
**<= +5 ms**. Arms are interleaved per item.

## Declared limits (now, before the panel)
- Rules are only the task's list: contractions, trailing fillers, leading so/um/hey, missing
  "?", spaces/case, and plurals of multi-valued relations. "What's my mom's name?" is not
  rewritten (no "X's name" rule), so it is predicted to stay a miss.
- Names keep their case, and "lowercase" means that every rule ignores case.
- Yes/no questions and new verbs/relations are not in scope.
