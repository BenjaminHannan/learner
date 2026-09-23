# 138h — merge layer B part 1: five verified text fixes onto loop138g (design)

One new file (`scripts/fable_loop138h_agent.py`) subclasses the frozen
loop138g stack. Every rule body is imported read-only; no existing file is
edited. Drivers are `scripts/fable_fix138h_{m1pieces,m2,suites}.py`.

## Step 1: one change per piece + composition

- 162b plurals: `Plural162bMixin.hear` (`scripts/fable_fix162b_plural.py:99`)
  claims plural "s'" teaches only (stem + "s" name via Bench73 teach);
  singular "'s" delegates untouched. Ported mixin only, never the
  139b/150/135/162 chain (that would drag each stage's sealed behaviour).
- 165 typos: `Typo165Mixin.hear` (`scripts/fable_fix165_typo.py:164`)
  rewrites no-apostrophe "W R is V" / "Q be W R" to "W-minus-s's …" iff the
  stripped name resolves uniquely and W itself is unknown, then delegates
  the fixed text inward. Sits OUTSIDE Plural162b and outside 167b/167, so
  fixed text re-enters the possessive and verb stages.
- 166c me: `Me166Mixin.hear` (`scripts/fable_fix166_me.py:196`) teaches
  "My \<R> is \<V>" and asks "my \<chain>" under USER_KEY; 166b not ported.
  Reply rendering needs two layers: `rewrite_me166_reply`
  (`scripts/fable_loop166_agent.py:57`, claimed-turn gate :89-90) plus the
  166c Title-case display pass (`scripts/fable_loop166c_agent.py:147`,
  helpers :58-141, agent-layer override map, notebook append-only).
- 173 name: `Name173Mixin.hear` (`scripts/fable_fix173_username.py:324`)
  outside Me166 (sealed order), plus loop173's `_act` namecheck router
  (:87), `_answer_namecheck` (:92) and the `_listening_tick` name rewrite
  (:108 via `rewrite_name173_reply`). 173b not ported: it has
  SEAL.sha256.txt but no RESULTS.md saying PASS, so the brief gates 173b
  re-entry on its seal and 173 is ported instead.
- 167b verbs: `Verb167Mixin.hear` (`scripts/fable_fix167_verb.py:212`,
  verb→possessive twin, delegated) with `ValueScreen167bMixin.hear`
  OUTSIDE it (`scripts/fable_fix167b_valuescreen.py:158`, tail-strip +
  determiner/lowercase refuse with 167's own clarify; sealed order
  `scripts/fable_loop167b_agent.py:46`).

Ears outer→inner: Typo165 > ValueScreen167b > Verb167 > Name173 > Me166 >
Plural162b > Loop138gEars. Loop _act: 173 namecheck > 138g tail chain.
_listening_tick: 173/166 rendering then 166c display (mirrors loop173-over-
loop166 and loop166c-over-loop166). turn(): 138g 168 shape + a my-file-only
raw-USER backstop (scrubs residual raw keys unless the turn mentions USER
literally — fixes the pilot-found A22 unsure-listing leak; O13 control
stays raw). Reasoner/notebook/sleep/daemon: 138g unchanged
(Reasoner138d, IndexedLoopNotebook, sleep145 retrofit, settle + exactly-once
daemon with idle_seconds).

## Left out (and why)

- 173b word-names (needs its PASS seal; porting unsealed deltas is banned).
- 166b capitalised-surface variant (superseded by 166c; do not port).
- 155 inverted frames (not in the 139b→150→162→162b chain; verified absent
  by MRO + module scan in the M1 output).

## Known edges (all sealed with expected replies)

- R1: multiword Saved labels render spaces ("place of birth") — 138b-mouth
  lineage; stored identical (162b 13 + 167b 11 rows).
- R2: unclaimed clarifies use 138g wording (the 165 guard asks keep verdict
  OK — the "didn't understand" mark is contained).
- R3: self-questions ground via 168 (A-rows, L02/L03, E07-T1).
- R4: singular/multiword shapes the 162 chain vetoes save via the 138g
  path (N03/N04/N07/N08, Mary-Jane rows, Zib-United/Dune rows, W04 missed);
  chained "X of Y" asks answer as 138g.
- R5: entity-count-only diffs (138h mints no value-entity; replies+stored+
  asks identical; O03, B-O07, C-E01).
- 137e 6 + 158c 7 rows behave as 138g; 158c-O01 answers via the verb twin
  ("Sue's city is Leeds."); 168-A10/B-ask/A22 take 173/grounded replies;
  sessions-S4 "my dog is biscuit" saves (intended me-teach); rt110-P1/P3 and
  rt81/p3-l2 O_user rows move exactly as on loop167/loop166 (stale judge
  labels documented, not patched); "Juno"/"drummer" clarify exactly as
  loop173/loop162b (dictionary word / outside inventory).
