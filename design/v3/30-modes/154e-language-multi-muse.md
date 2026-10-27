# 154e — language becomes multi-valued (Muse)

Ben's ruling (09:48): a person can have more than one language. Loop154c
deliberately deny-lists `language` (with citizenship) as single-valued;
154e moves ONLY `language` onto the multi-valued allow-list. Citizenship
and every other deny-listed relation stay single-valued, unchanged.

## The one change

`scripts/fable_fix154e_allowlist.py`: `MULTI_VALUED_154E =
MULTI_VALUED_154C + {"language"}`, `is_multi154e`. `scripts/
fable_loop154e_agent.py` subclasses loop154c read-only (`Loop154eEars`,
`Loop154eAgentLoop`, `_wrap_relation154e`, `build_agent154e`,
`Loop154eDaemon` with `idle_seconds=30.0`) and swaps the gate predicate
in exactly three places (ears correct-not pre-scan, ears forget-one
pre-scan, `_act` teach/correct routing, `_post_ask` list/clarify). All
multi-value behaviour (add parenthetical, oldest-first and-join,
mid-chain clarify, correct-not, forget-one, repeat no-op) is inherited
VERBATIM from 154b; all single-value behaviour falls through to the
loop138b path, exactly as 154c does. No 154c/154b/138b file is touched.

## Behaviour (sealed forms)

`Rana's language is Hindi.` then `Rana's language is Urdu.` keeps BOTH:
`Saved: Rana's language is Urdu. (I also have Hindi.)` — no
change-prompt, no overwrite. `What is Rana's language?` lists all
current values in notebook order (`Hindi and Urdu.`; 3+:
`Hindi, Urdu and Bengali.`, no Oxford comma). Correct-not
(`No, Rana's language is Tamil, not Hindi.`) adds Tamil and retracts
only Hindi, naming remainers. Forget-one (`Forget Rana's language
Urdu.`) retracts only Urdu. A repeat (`Rana's language is Urdu.` again)
replies `I already have that.` and writes 0 facts (verified: no
duplicate row). Asks never write, so taught values are never
overwritten by inferences. Citizenship/city/boss re-teaches keep the
loop154c change-prompt byte-identical, including the `no.` ->
`Okay, I left it as it was.` close-out. Unknown-person asks keep
`I don't know ...`.

## Composition with loop167d's verb rewrite (doc only, no code)

`scripts/fable_fix167d_verb.py:69` maps `Rana speaks Hindi.` to the
possessive twin `Rana's language is Hindi.` (relation surface
`language`). The loop's relation map (lowercase + underscores) turns
that surface into the key `language` — the exact key 154e allow-lists.
So when the layer-B merge stacks the 167d mixin OUTSIDE the 154e ears
(verb rewrite first, multi-value gate second), verb-taught `speaks`
values flow into `_act_multi_teach` and accumulate multi-valued for
free, and `What language does Rana speak?` (rewritten to `What is
Rana's language?`) lists all of them. Key-name check, verified
statically pre-seal: 167d twin surface `language` ->
`relation_key154b("language")` = `language` ->
`is_multi154e("language")` = True. Mismatches found: NONE on the
canonical path. Two non-blocking notes for layer B: (1) no alias
(`languages`, `spoken`, `speaks` as keys) is allow-listed — only turns
that pass through 167d's twin rewrite benefit; a raw possessive teach
with a plural surface (e.g. `Rana's languages are ...`) would take the
base path, exactly as 154c treats other non-canonical surfaces; (2)
ordering matters — the verb mixin must run BEFORE the multi gate sees
the turn (rewrite to the twin, then gate on the twin's key), which is
167d's documented design (it hands the twin to `super().hear()`).

## Evidence

L1 76/76 exact incl. quotas (8 pairs, 4 triples, 4 removals, 3 repeats
with 0 new facts, 12 traps reply-equal to 154c). L2: bench 800 items 0
moves/0 new wrong; marks123 11/11 reports per-case identical (raw diffs:
timings + 1 predicted sleep filename); G3 0 moves/0 new wrong. Pre-seal
scan: 0 language triggers in any frozen suite (predicted EMPTY move
set, held). Seal 10/10 OK post-run; no post-seal edits.

## What it means

One key moved lists; everything else frozen — the smallest possible
step toward people having several languages.

## What it does not mean

It does not change citizenship, city, boss, or any other relation; it
does not implement or test the 167d stack (that merge is layer B's
job); it does not guess, merge, or order values by anything but
notebook age.
