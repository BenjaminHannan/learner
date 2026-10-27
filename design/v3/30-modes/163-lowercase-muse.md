# 163 — Lowercase names at the entity layer (Muse)

Phone users type lowercase constantly, and the director showed the loop
punishing that: after `Omar's sister is Priya.`, `is priya omar's sister?`
fell back to `I only know that omar's sister is Priya.` instead of Yes, and a
first-mention lowercase teach (`tom's boss is ann.`) stored lowercase display
forms verbatim. The fix is one change at the entity layer, on loop150.

## Where names are matched and written (Step 1)

Matched on lookup: `scripts/fable_notebook_contract.py:116-117` (`_norm`
case-folds alias keys, so `resolve` at :235-242 is already case-insensitive)
and the hop loop `ask` at :390-421; reasoner entry
`scripts/fable_fix77_core.py:208-228` (resolves the ask name); ears question
parses `scripts/fable_agent_loop.py:122-129`,
`scripts/fable_bench73_english_arm.py:215-237` + `:246-314`,
`scripts/fable_bench92_english_arm.py:145` + `:198-243`;
`scripts/fable_loop90_agent.py:153-170` (teach/correct detect). Written:
`scripts/fable_listening_m1.py:46-58` + `:106-127`,
`scripts/fable_notebook_contract.py:268-277` (display stored verbatim);
`scripts/fable_agent_loop.py:344-350`, `scripts/fable_loop90_agent.py:353-373`;
replies echo the typed span at `scripts/fable_agent_loop.py:155-172` (the echo
bug this experiment fixes).

## The one change

`scripts/fable_fix163_lowercase.py` (`Lowercase163Mixin`, stacked onto loop150
as `scripts/fable_loop163_agent.py` in the style of `fable_loop140_agent.py`):
every teach/correct under a person relation and every ask name span is
canonicalised through the notebook's own case-insensitive resolve, at ears
`hear()` and again at loop `_act()` just before the write. (a) All-lowercase
span resolving to exactly one entity: replaced by its display form, so replies
print it. (b) All-lowercase new person-name span: stored capitalised per token
(`tom` -> `Tom`); later capitalised mentions resolve to it. (c) Non-person
relations (cities, sports, positions, exp-102 common nouns): byte-identical,
lookup already merges via `_norm`. (d) Inner-capital/mixed spans (McDonald,
DeShawn, iPhone, TOM, eBay): `str.islower()` is false, kept typed. Ambiguous
spans (two stored entities differing only by case, both typed capitalised):
untouched, base clarify owns the turn, never merged.

## Why this shape

Lookup was already case-insensitive; only the stored display form and the
reply echo were case-sensitive. Canonicalising spans (instead of touching the
notebook) keeps the change additive and leaves forget/alias/person/quote and
non-person paths byte-identical, which the per-item regression marks confirm.

## Evidence and limits

Sealed probe 46/53: lowerQ 26/26, lowerTeach 12/12, innerCaps 8/8; the 7 sealed
noMerge cases FAIL because their `person Tom`/`person TOM` setup stores no
entities on the base loop, so the expected clarify can never fire (recorded
FAIL; corrected open cases 53/53). G1 600 bench items 0 moves; G2 per-case
identical except rt110/soak load flakes, both clean on open rerun; G3 exactly
the 8 predicted session turns; G4 slowest run 196.1 s. Two post-seal
harness-only edits (daemon wrapper, probe `--cases` flag) are reported in
RESULTS.md with open re-runs; sealed files verify with `shasum -c`.
Pre-seal scan showed no suite inputs outside the predicted turns touch the
all-lowercase person path.

## What it means

Lowercase name typing works end to end with no measured regression anywhere.

## What it does not mean

It does not create case-only entity collisions (uncreatable via teaches), nor
change literals, relation keys, or the inherited p2/q1/rt81 suite FAILs.
