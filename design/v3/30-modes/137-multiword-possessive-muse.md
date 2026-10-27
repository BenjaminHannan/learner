# Design 137 — multi-word possessive subjects (Muse)

## Problem

On loop129b the possessive teach frame ("<Name>'s <relation> is <value>")
accepts only a ONE-WORD subject. The guard lives in FakeEars
(scripts/fable_agent_loop.py): after `_STATEMENT` matches and `_chain`
splits on the possessive, `if " " in name` clarifies. Through the
ChainEars the clarify becomes a miss ("I didn't understand that…", 0
writes; verified: base loop129b stores 0/42 N1 teaches). People have full
names, so natural teaching ("Dara Fenn's city is Lyon.") is blocked.

## Change (one)

Accept 1–4 capitalised name tokens as the possessive subject. Token rule:
starts uppercase, letters/hyphens/apostrophes only (ASCII or U+2019), at
most one trailing period (exp-129 abbreviation rule, e.g. "St."); a token
is a single uppercase initial OR contains a lowercase letter (Title-case —
ALL-CAPS refused). Subject rule: 2–4 tokens on the mixin path; 1-token
subjects stay with the base ears (never overridden). Relation vocabulary
(FakeEars' open lower/underscore map), value rules (exp-91 screen +
exp-129 punct strip), hearsay/forget/qualifier/correction handling, and all
clarify texts are unchanged.

## Why a mixin, and where it sits

`Fix137PossessiveMixin.hear` (scripts/fable_fix137_names.py) calls
`super().hear(turn)` first and only upgrades an ALL-clarify result (no
teach/correct/ask/forget/person/alias/quote action) into a structured
teach/correct action when `parse_possessive137` — a FakeEars-identical
parse (qualifier strip → correction prefix → statement → 2-part chain →
relation map → non-empty value) with the widened name rule — succeeds AND
the exp-91 value screen passes. Any refusal returns the base clarifies
byte-identical. Actions carry `"structured": True` so
`Loop90AgentLoop._act` calls `Listening._teach` directly: the M1 line
renderer (`teach NAME REL arrow VALUE`, single-token `rest[0]`) cannot
carry multi-word names. Stacking: `class Loop137Ears(Mixin,
Loop129bEars)`; the 129b `_act` sanitize still applies on top.

## Question side

No change needed. FakeEars' question branch (`_QUESTION` + `_chain`) never
had the one-word guard, and `"?"` turns bypass the mixin entirely. One
design constraint for probes: keep value strings distinct from subject
strings so bench73's `compose_question` abstains and every question tests
the possessive-question path. Verified: 42/42.

## Evidence

N1 42/42 stored exactly + 42/42 answered, 0 wrong writes, across
mother/father/city/boss/friend/employer with hyphen/apostrophe/initial/
4-token names. N2 registered FAIL: 4/18 traps wrote — 2 inherited base
behaviours (officeholder catch-all, one-word digit name, both verified
byte-identical on loop129b) and 2 frame-consistent accepts (possessive
value without second copula, valid 4-token name); zero subject-split /
value-junk / relation-swap errors anywhere. N3: marks123 suite verdicts
identical (10/10 rows; p2/rt110/rt81/bench per-case identical), bench
600/600 per-item identical. N4 ≈ 5.9 min.

## Integration notes

Tonight's build stacks the mixin under/over other mixins by MRO order;
each mixin only upgrades all-clarify results, so stacking is
order-independent except when two mixins claim the same clarify (last in
MRO wins — report the stage tag `fix137-teach`). Known neighbours: the
"child" possessive already routes via loop121's extra patterns; exp-135's
officeholder guard composes underneath (T09 shows the unguarded catch-all).

## What it means

Full-name teaches store exactly and answer exactly, with no measured
regression on any sealed suite.

## What it does not mean

It does not fix the officeholder catch-all or one-word digit names, and it
does not widen values, relations, or question phrasing.
