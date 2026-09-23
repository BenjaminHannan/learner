# 180 — lowercase-names recase on loop138g (design)

One new file, `scripts/fable_loop180_agent.py`, subclasses the frozen
loop138g stack read-only. The one change is `Loop180Ears`, an outermost
ears stage; loop, reasoner, notebook, sleep, daemon are 138g-unchanged.

## Why this shape

Director probes showed lowercase turns failing on sibling loops
(154d yes/no `is lou kip's boss?`, 174 of-chain `what is the city of
Kim's boss?`, 138f `what is kofis city`). Measured on loop138g itself:
first-word-only lowercase already answers identically (the stack folds
case for known shapes), while lowercase *names* diverge — asks echo the
wrong case (`kofi's city is Lyon.`) and teaches save immediately with no
check. The fix therefore repairs names, never touches already-parsing
asks, and confirms (never writes) on teaches.

## The rule (closed, sealed before any run, refined post-seal as D1-D3)

`hear(turn)`: (1) pending-confirm + `yes/yeah/yep` commits the stashed
recased teach (twin events); anything else drops the stash. (2) Base
138g `hear`. (3) ASK-bearing parses return untouched — asks answer
directly, echo included. (4) TEACH/CORRECT parses with all names
canonical return untouched. (5) TEACH/CORRECT needing a known-name fix
**and** whose first+last word-stems are known names (D3) return
`Did you mean: <recased>?` with zero writes. (6) All-clarify parses
retry `recase(turn)` once through the full stack: asks returned, teaches
confirmed only under the same predicate on the original turn (D2), else
base reply byte-identical. `recase` capitalises the first word plus any
lowercase token matching a taught+active notebook subject or
single-token value (D1: multi-word values are phrases, never names),
using notebook-canonical casing; unknown words are never capitalised.
Stored text therefore always uses the notebook's existing casing.

## Why D1-D3 were forced (evidence, not taste)

- D1: value token `The` (from `The Glass Orchard`) misfired a confirm on
  rt143 C5's determiner. Single-token-values-only fixed it.
- D2/D3: frozen sessions S2/S3/S5 deliberately teach new lowercase names
  (`vera's city is lima`, `btw marta's brother is kai`) and the sealed
  base saves them — 29 session turns moved under the broad trigger.
  Confirming only when both ends resolve to known names restores 0 moves
  while keeping all six T1 teaches (all-known names) confirming.
- S6 (`no Vera's city is Quito`, first-word-only repair into a
  correction) never confirms per D2.

## Composition

Outermost-first: Recase180 > Frame137g > WhCity158cPort > Tail139eGuard >
Loop138fEars. No method collision (new `hear` calls
`Loop138gEars.hear` as the base pass). `_act`/`turn` untouched, so the
yes-commit path produces bit-for-bit the capitalised twin's events
 tail guard, doubt store, sleep145, settle daemon included.

## Out of scope (owned elsewhere)

Missing-apostrophe typos (`kofis`): `kofis` is not a notebook name, so
it is never capitalised; trap X02 pins base-identical behaviour (exp
165). Yes/no answering: 138g has no yes/no module, so both cases clarify
identically (trap X10). Wh-city/of-chain shapes behave twin-identically
(Q11/Q12).

## Limits

A lowercase teach mixing known and unknown names saves as-is (base
behaviour) rather than confirming — the confirm only fires when the
recase is fully canonical. A pending confirm is single-slot and drops on
any non-yes turn. `yes` is recognised as exactly yes/yeah/yep plus an
optional period.
