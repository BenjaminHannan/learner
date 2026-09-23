# 180b — silent case-insensitive known-name match on loop138h (design)

One change on loop138h (`scripts/fable_loop138h_agent.py`,
`artifacts/fable-agent138h-20260922/`, loop138h-config.json — all
read-only): names are matched to the notebook regardless of case,
silently. New files only: `scripts/fable_loop180b_agent.py`,
`scripts/fable_fix180b_{probe,suites,comparem}.py`,
`artifacts/fable-case180b-20260922/`, this doc.

## Diagnosis (exp 180, registered FAIL)

Exp 180 re-cased only unparsed turns and gated teaches behind a "Did
you mean" confirm. The director's fresh check showed the real gap is
narrower and user-visible: the base already parses "who is oda's
boss?" but echoes the user's casing ("oda's boss is Pim."), and the
confirm questions Ben explicitly banned (typos are fixed silently).
180b therefore resolves known names BEFORE parsing on every non-say
turn — asks included — and never confirms. It does not reuse any of
180's confirm design.

## Mechanism (one, outermost ears + display)

`notebook_names180b(nb[, overrides])` maps lower(name) to canonical
casing for taught+active single-token subjects and single-token
values (multi-word values are phrases, never names — 180's D1 guard,
so "the" never misfires), plus the user's own name. The display path
also honours the loop's 166c override map, because for an
all-lowercase stored display the Title-case override IS the agent's
canonical render.

`resolve180b` rewrites any token/possessive matching a known name in
any case, preserving every other byte. `Case180bMixin.hear` (outside
`Loop138hEars`) resolves the input then delegates, so the parse never
sees the lowercase surface: no second entity differing only in case
can be created, already-stored facts hit the base "I already have
that.", and unknown words ("gus", "kofis") plus common words that are
not notebook names ("will", "may", "rose", "mark") pass through
untouched. `Loop180bAgentLoop._listening_tick` re-renders said lines
the same way after 138h's own rendering (rebuilt after super's tick
so fresh 166c overrides win).

Two ownership guards keep sealed behaviour: (1) a non-all-lowercase
token is never rewritten to an all-lowercase canonical — 166c owns
that direction ("Biscuit" stays "Biscuit"; the base stores the
surface as typed and renders Title-case, 180b identical); (2)
pretend `say ...` turns skip both paths, so the echo quotes user
bytes exactly with 0 writes. The input path never uses display
overrides (a lowercase mention must parse exactly as the base sees
it, keeping stored events identical).

## Evidence (pilots, pre-seal, final code)

T1 44/44 (10 setup parity, 14 asks == twin replies incl. 2-hop and
165's "Who is toms boss?" -> "Tom's boss is Lee.", 8 silent teaches
with twin-identical events and 0 case-dupes, 12 traps). Frozen
suites: rt136/rt143 0 moves; bench 4x200 0 moves 0 new wrong;
sessions152 exactly the 9 predicted reply-casing upgrades, 0 writes;
marks123 per-case identical to sealed marks138h except 4
reply-casing moves (rt110 L6/M5/S2, q1 M5), timing-volatile rt110
`statuses` (proven flaky: sealed 138h rerun mismatches its own row),
and predicted renames/timing.

## What it does not do

No guessing of unknown names, no confirms, no overwrites of taught
facts by inference, no notebook format change (append-only kept), no
multi-word name matching, no shouting normalization beyond stored
casing. Out of scope by design.
