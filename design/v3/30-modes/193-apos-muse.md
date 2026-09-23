# 193 — missing-apostrophe possessives on loop138h (design)

## Problem

Director probe 09:56 on loop138h (and loop138g): after `Kofi's city is
Lagos.`, the asks `What is kofis city?` and `What is Kofis city?` reply
`I have no opinions.` The turn never splits owner from relation (the
base splits possessives on the apostrophe-s in
`scripts/fable_agent_loop.py:93`), so it falls through the whole ears
stack into the small-talk/opinion route, which claims it. Exp 165
covers `who is toms boss` but only for person-relations
(`REL165 = PERSON_RELATIONS`), and its own agent also fails `kofis
city` with `I didn't understand that`.

## The one change

`Apos193Mixin.hear` (`scripts/fable_fix193_apos.py`), stacked
OUTERMOST as `Loop193Ears(Apos193Mixin, Loop138hEars)` in
`scripts/fable_loop193_agent.py`. A word token that equals, ignoring
case, a name ALREADY IN THE NOTEBOOK plus a trailing "s" (`kofis`,
`Kofis`, `toms`, `Juans`; also "s'" forms such as `Kofis'`),
immediately followed by a relation word the base can already parse, is
replaced by the notebook-canonical `Name's` form; the rewritten turn is
delegated to `super().hear()` and parsed by the unchanged base,
silently (Ben's ruling: typos are fixed silently). The reply shows the
reading, exactly like the apostrophe twin's.

## Gates (all per token; anything else falls through untouched)

- (a) The candidate token itself carries no apostrophe except one
  trailing "s'". Turns whose every token already parses (e.g. `Kofi's
  city`) yield no candidate, so the base owns them byte-identical.
- (b) The stem matches the DISPLAY name of exactly one known entity
  case-insensitively, and that display is one word. Alias-only matches
  never fire (a `bob`-for-`Robert` rewrite would echo the wrong casing).
- (c) The full token is not itself known (no alias match, not the tail
  of a multi-word entity), so plurals (`cats`, `bus`, `Wills` with Will
  unknown) stay untouched; an "s'" token after `the` is declined (162b
  owns `The Xs' ...` plural teaches).
- (d) The next word (whitespace-adjacent) is a known relation: a person
  relation, `city` (sealed 138h rows save/answer it, G3h-5a/b), a
  relation key already taught into the notebook, or the
  possessive-stripped form of one (`boss's` counts as `boss`, so 2-hop
  `Kofis boss's city` and of-chain `city of Kofis boss` work).

Canonical (not typed) casing is used because the mouth echoes the
parsed name (`Who is toms boss?` via 165 alone answers `tom's boss is
Lee.`); only canonical-cased rewrites are byte-identical to the twin.

## Composition

Rewritten turns re-enter the full 138h stack: Typo165 declines them
(apostrophe present), the 162b plural stage owns only plural "s'"
teaches, and save path/screens/replies are the base's own. Loop,
reasoner, notebook, sleep, and daemon are loop138h unchanged
(read-only imports). No existing file is edited.

## Left out (and why)

- Fully apostrophe-less 2-hop middles (`kims bosss city`): the middle
  token is a relation, not a notebook name -- outside the brief's
  name rule; it clarifies exactly like the base.
- First-ever teaches of never-taught non-person relations with a
  missing apostrophe: the next word is not a *known* relation, so the
  turn clarifies per the brief's gate; the apostrophe twin teaches
  normally.
- Unknown stems and real plurals: never rewritten (verified traps).

## Known edges (all sealed with expected replies)

- Reteaches answer `I already have that.` on both loops (X09).
- The of-chain twin (`What is the city of Kofi's boss?`) answers `I
  don't know anyone called the city of Kofi.` on the base; the repair
  matches it byte-identical (Q12).
- rt110 harness `statuses` log-metadata may vary run-to-run under
  parallel load (daemon.log harvest race); verdict+reply+fact_writes
  are enforced exact by the compare driver.
