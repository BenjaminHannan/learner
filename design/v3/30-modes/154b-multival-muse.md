# 154b — second values for multi-valued relations (design, Muse)

Base: loop138b (`scripts/fable_loop138b_agent.py`), subclassed read-only.
No loop138b file is edited. New files: `scripts/fable_loop154b_agent.py`
(agent), `scripts/fable_fix154b_multival.py` (helpers),
`scripts/fable_fix154b_probe.py` + `scripts/fable_fix154b_regress.py`
(drivers), config `artifacts/fable-multival154b-20260922/`.

## Step 1: can the notebook hold two current values? YES

No contract change is needed. Three file:line facts:

- `scripts/fable_notebook_contract.py:335` — `assert_fact` refuses a
  second different taught value with CONFLICT only when
  `relation in self.functional`. Otherwise it appends a new FACT row
  and both rows stay active (`current()`, lines 244–255).
- `scripts/fable_notebook_contract.py:413–419` — `ask()` on a
  non-functional relation with 2+ rows returns OK with `multi=True`,
  answers joined together.
- `scripts/fable_notebook_contract.py:678–682` (case c27) — the
  lifecycle suite proves it: teaching Mira's friend as Tom then Ana
  SAVEs both and the answer names both.

What blocks second values on loop138b is NOT the contract but two upper
layers: `scripts/fable_listening_m1.py:33` (`FUNCTIONAL_BY_DEFAULT=True`)
with `_relation` (lines 60–63) declaring EVERY unseen relation
functional, and the teach path mapping any second different value to a
change-prompt/supersede. This experiment overrides exactly those two
behaviours for relations NOT in `SINGLE_VALUED_154`
(`scripts/fable_fix154_yesno.py:64–76`, read-only). On notebooks where a
relation was already declared functional, the earlier append-only
RELATION event sticks — a documented limit, not a silent rewrite.

## The one change (sealed reply forms)

For a relation NOT in SINGLE_VALUED_154 (sister, friend, brother,
child, pet, and everything else not on that list), a new different
value ADDS instead of offering a replacement:

- Teach: `Saved: Omar's sister is Lena. (I also have Priya.)`
- Ask (single hop, oldest first, one fixed join): `Omar's sister is
  Priya and Lena.` (3+: `Priya, Lena and Ana.` — no Oxford comma)
- 2-hop through a non-final multi hop with 2+ values never guesses:
  `Omar's sister is Priya and Lena. Which one do you mean?`
- Correction `No, Omar's sister is Lena, not Priya.` retracts Priya
  only and adds Lena: `Saved: Omar's sister is Lena.` (plus an
  `(I also have ….)` parenthetical when other values remain, plus
  `(I didn't have {old}.)` when the named old value was not current).
- `Forget Omar's sister Priya.` retracts that value only:
  `Forgotten: Omar's sister Priya.` Whole-slot forget, yes/no
  confirm, and EVERY single-valued turn take the untouched base path.

Single-valued relations (boss, mother, city, spouse, …) keep today's
change-prompt byte-identical: `I have Omar's boss as Ann. Do you want
me to change it to Beth?`

## How it is built (mixin, additive only)

`Loop154bAgentLoop` subclasses `Loop138bAgentLoop`; `turn()` is
inherited verbatim. Two overrides: (1) at build, the loop's Listening
instance gets a bound `_relation` that declares single-valued
relations functional and everything else non-functional, so the
contract accumulates values by its own rule; (2) `_act` intercepts
`teach`/`correct` actions whose relation key is multi-valued and runs
the add path (base `_teach` + parenthetical), and post-processes OK
multi answers into the sealed `and`-join. Two narrow pre-scans in
`Loop154bEars` (correct-not, forget-one-value) fire only on
multi-valued shapes that the base would mishandle; anything else falls
through to `super().hear()` byte-identical. Sleep145 retrofit,
148b screens, and the daemon settle/atomic rules are inherited
unchanged. `Loop154bDaemon` swaps only the agent class so the marks123
loader picks it up.

## What it means

People really do have several sisters, friends, children, and pets.
After this change the assistant keeps every value it was taught, lists
them when asked, and asks which one you mean before reasoning through
one of them — instead of silently swapping Priya out for Lena.

## What it does not mean

It does not change anything about single-valued facts (boss, mother,
city): those still ask before replacing. It does not merge or deduplicate
values, and it does not guess which sister you meant in a longer question.

## Registered results (2026-09-22, sealed PASSMARKS.md)

T1 PASS (probe 81/81), T2 PASS (0 wrong writes, full_state exact), G1 PASS
(bench 4x200: 613 moves all on multi-dup items, 55 new wrong all
final-hop list form), G2 FAIL by design (p2 B1/B2/B3/B5/B8/F2 + p3 l5z2
mquake-twohop encode replace-semantics for multi-valued relations; the
pre-seal scanner missed copula and multi-word-subject shapes — one
diagnosis note in RESULTS.md, no re-run), G3 PASS (0 moves), G4 PASS (max
run 257.6 s). Question for Ben: p2 group-B/F vs 154b disagree on whether
re-teaching citizenship/language replaces or adds — current default adds.
Full table: `artifacts/fable-multival154b-20260922/RESULTS.md`.
