# Exp 135 — officeholder catch-all guard (design, Muse)

## Problem
`fable_bench73_english_arm.py` STATEMENT_PATTERNS ends with a catch-all
`The (.+?) is (.+?)` → `officeholder`. The director showed any such sentence
is written: "The mother of Dara Fenn is Ora Fenn." →
`('mother of Dara Fenn','officeholder','Ora Fenn')`, same for father/boss
(reproduced on loop129a/129b). A confident wrong write from a held-out probe.

## Change (one)
`scripts/fable_fix135_office.py` (mixin) + `scripts/fable_loop135_agent.py`
(loop129b + mixin). The catch-all fires only when the head phrase (text
before `" of "`, else the whole subject) is an office title derived
mechanically from existing code tables; otherwise the parse returns None and
the sentence takes the loop's unparsed path (clarify, no write). No
mother-relation routing is added (separate later change, as briefed).

## Mechanical title list
Sources (all read-only imports): `REL_MENTION_CUES` (bench73) and
`REL_CUES92`/`EXTRA_REL_CUES` (bench92) for officeholder, head_of_state,
head_of_government, chairperson, chief_executive_officer, plus
director_manager, head_coach, original_broadcaster. The last three are
required by measurement, not taste: the loop's catch-all fires bench73-first,
so it swallows bench92's director/head-coach/broadcaster sentences — 110
teaches in bench103-s2fresh, 132 in bench121. Excluding them would regress
K2. Plus literal `The <head> of` heads of office-like statement patterns
(this covers the data's misspelt `origianl broadcaster` pattern verbatim).
Rule: cue phrases lowercased, trailing `of`/`of the` stripped; singles match
a whole head or a whole head-token (`vice president` works); phrases match
whole heads. Full list printed to
`artifacts/fable-fix135-20260922/office-titles-135.json`. Junk admitted by
the mechanical rule (`head`, `leads`, `name`, `government`, `aired`) can only
*allow* writes the base also makes, never block new ones. king/queen/monarch/
emperor are absent from every table, so they refuse by design (flagged below).

## Stacking
`OfficeholderGuardMixin` overrides only `hear()`: it repoints
`B73.hear_teach_template` at the guarded parse for the duration of
`super().hear()` (restored in `finally`). The wrapped loop calls the parse by
module attribute — including the inner `Bench73Stage` chain and bench92's
bench73-first path — so all teach logic, guards, and the question side run
byte-identical otherwise. `Loop135Ears(Mixin, Loop129bEars)`; tonight's
integration stacks further mixins by inheritance order.

## Evidence (registered; PASSMARKS sealed 8325d463…, probe 97859e60…)
- K1 PASS: 52-sentence probe. 0 writes on 30/30 non-office (base wrote 30/30:
  30 sentences became "didn't understand"); 18/18 office-table byte-identical
  replies and write counts; 4/4 monarch refused on 135, written on base.
- K2 PASS: 600/600 bench rows per-item identical (verdict+reply+rejects);
  edit200 150/50/0, old 157/43/0, new 136/63/1.
- K3 FAIL on the letter: 9/10 suite verdicts identical. Soak PASS→FAIL on ONE
  turn replying "I didn't catch anything." (empty-turn mailbox race; audits
  0/0/0, lost 0); rt110 PASS on both but P5/M6 moved BUG→OK, same empty-turn
  signature on possessive shapes the guard provably cannot touch (no `The X
  is Y` in those cases; guard fires only there). Zero guard-caused moves.
- K4 PASS: registered compute ≈ 6 min wall (< 25 min), OMP=MKL=1, offline.

## What it means
One mixin removes the whole confident-wrong-write class for non-office
`The X is Y` sentences with zero measured behaviour change anywhere else.

## What it does not mean
It does not teach mother/father relations (those now clarify); it does not
cover monarch titles (not in the tables); it does not fix the mailbox
empty-turn race (needs a harness-side receipt/read retry).

## Deviations
None from the brief. Note: brief's K1 example named `king` as an office head;
king is in no bench73/bench92 table, so per the registered mechanical rule it
refuses — probed as observe-only rows, question for the director whether a
follow-up should add monarch titles.
