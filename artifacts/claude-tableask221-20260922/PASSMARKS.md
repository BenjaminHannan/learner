# Exp 221 -- PASSMARKS (registered before any registered run)

Build: loop221 = loop138i with TableAsk221Mixin outermost on the ears.
Questions are read through relation_table_v1.json (217 folder, read-only,
unchanged -- no v1.1 copy). Writes are untouched.

All marks are per case; nothing is averaged. The verdict is PASS only if
every mark P1-P6 passes. Any single failure = FAIL (named mark).

## P1 -- blind panel (artifacts/claude-tablepanel221-20260922/, run ONCE)
Folder is opened only after this file + code + table are sealed; its own
SEAL.sha256.txt must verify with `shasum -a 256 -c` first (else P1 VOID).
Scored with the panel's own gold + families by scripts/fable_fix221_panel.py:
- forward/inverse/verb/alias families (everything not untaught / no_relation
  / self): **>= 90 %** of scored turns correct (gold value in the reply;
  inverse-family answers must carry "(worked out backwards)").
- **0** wrong values over ALL scored turns (a reply asserting a taught
  value that is not gold).
- **100 %** of loop221 inverse answers (stage loop221-table-inverse, not
  "I don't know ...") carry the label.
Field-map rule: only load_items() may be adapted to the panel's field
names; every change is listed as a deviation. Scoring rules are not edited.

## P2 -- writes untouched
- **0** question turns (text ending "?") in the loop221 arm, over the
  panel and the dev set, where the notebook fact hash (facts + retracted +
  superseded) differs before vs after the turn. The 138i arm count is
  reported for comparison.

## P3 -- no collateral movement
- suitediff vs 138i on rt136, rt143, sessions152, bench:
  **0** moved cases absent from predicted_moves221.json (sealed below);
  **0** tool-flagged new WRONG / new WRONG-WRITE / new junk write /
  MISSING-BASE; every moved case read and given a hand verdict in
  RESULTS.md (the tool's "reply-only" label is not trusted).
  Hand verdict "worse" on any move = FAIL.
- G3 director pairs (fable_fix138i_suites.run_g3 via fable_fix221_g3.py):
  **6/6** identical replies + stored triples to the sealed 138i rows.
- Sleep smoke (scripts/fable_sleepsmoke206.py on loop221): PASS with the
  138i marks: sleeps 1, installed (episodes 20), probes 5/5 right, 0 wrong,
  Q99 abstains, taught 50/50, overwrote 0, wall < 300 s.

## P4 -- the table actually does the work, without the router
- **0** turns (panel + dev) where the stage is loop221-table* AND the self
  router fired (loop.last_routed set).
- Dev evidence items E1-E4 correct in loop221 (E1 "Who composed ...",
  E2 "When is my birthday?", E3 "What is the manager of ...",
  E4 "Who works at ..." labelled).

## P5 -- safety families (panel)
- untaught: **100 %** abstain, 0 wrong values.
- no_relation: **100 %** give no value and write nothing.
- self: **100 %** reply identical to 138i.
- "Who is Kim's?" stays the not-understood clarify (dev set).

## P6 -- cost
- Median (loop221 ms - loop138i ms) per question turn over the panel
  **<= 5 ms**.

## Known deviations from design 217 section 6 (declared now)
1. Rule (c): answers from the built-in 153 reverse path get the label
   appended, and 153's "I don't know anyone whose R is V." is widened
   through the table group when subjects exist. Section 6 did not list this.
2. Yes/no questions are not handled by the table.
3. No forward reading from inverse_storage keys.
4. G4 (index on/off) is not run: its off arm is a subprocess hard-wired
   to fable_loop138i_agent.
