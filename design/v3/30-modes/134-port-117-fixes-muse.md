# 134 — Port the loop117 fixes onto loop121 (Muse)

Port, not new science. Tonight the agent loop split into two lineages:
loop102 → loop117 (three red-team fixes: F5 please-forget, M5 shouted
possessives, underscore leaks) and loop102 → loop113 → loop113b → loop121
(teach-side phrasing coverage). The 121 lineage fails q1 (F5, M5) and q4
(underscore leaks); loop117 passes them. This doc reunites the lineages:
loop134 = loop121 + the three loop117 fixes, same logic, re-expressed as
small mixin classes layered on the Loop121 classes.

## What loop121 is (untouched)

Loop121Ears extends Loop113bEars: "?" turns are byte-identical to loop113b
(N-hop router + fallback to the exact loop102 chain); non-"?" turns add
teach-pattern coverage (exp-92 employer/occupation/child patterns tried
after bench73, same structured actions) and narrow the exp-91 word-count
screen so a single Title-Case name containing "and" passes. Everything else
delegates to the exact old path. None of this file changes any of that.

## The three ported fixes (loop117 logic, unchanged)

1. F5 please-forget space. Loop102's `_parse_forget` strips the
"please" prefix with `"forget" + t[m.end(1):]`, dropping the space, so
"Please forget Mira city" becomes "forgetMira city", never matches the
forget verb, and the stale value keeps being answered.
`PleaseForgetSpaceMixin134` overrides `_parse_forget` byte-identical to
loop117 except restored: `"forget " + t[m.end(1):]`. Because
Loop102Ears.hear calls `self._parse_forget`, dynamic dispatch picks the
mixin up through the whole loop121 fallback chain (including the
explicit `Loop102Ears.hear(self, turn)` call in loop113b), so the fix
works end-to-end with no change to `hear()`.
2. M5 shouted possessives. FakeEars splits possessives with the module
global `_APOS = r"['’]s\b\s*"`, lowercase-s only, so "MIRA'S CITY" never
splits and the turn clarifies. Loop117 overrode the global at import to
`['’][sS]\b`; this file applies the identical value (stored relation
keys unchanged — `_relation` still lowercases to the same key), and
`ShoutedPossessiveMixin134` re-asserts it in `bind()` so the fix
travels with every Loop134Ears instance.
3. Underscore leaks. Internal keys ("country_of_citizenship",
"maternal_grandmother") leaked into replies. Loop117 wrapped the mouth;
`UnderscoreSpaceMouthMixin134` re-expresses it as a mixin over
FakeMouth via `super().say(record).replace("_", " ")`. Stored keys,
actions, and notebook rows are never touched.

## Explicit method resolution order

`Loop134Ears(PleaseForgetSpaceMixin134, ShoutedPossessiveMixin134,
Loop121Ears)`: `hear` resolves to Loop121Ears.hear (unchanged teach
coverage + question side); `_parse_forget` resolves to the F5 mixin;
`bind` runs the M5 mixin then the loop121 chain. Full chain:
Loop134Ears → F5-mixin → M5-mixin → Loop121Ears → Loop113bEars →
Loop113Ears → Loop102Ears → object.
`Loop134Mouth(UnderscoreSpaceMouthMixin134, FakeMouth)`: `say` renders
spaces, then FakeMouth. `Loop134AgentLoop` inherits the forget2 action
unchanged; `Loop134Daemon` is the loop121 mailbox shape around
`build_agent134` (sleeper seed kept at 4121, as loop121).

## Why mixins, not edits

Additive-only rule: no existing file is edited. The mixins change three
narrow behaviours while every other turn takes the exact loop121 code
path — verified by reply-level diffs (RESULTS.md): outside F5/M5/
underscore shapes and their direct state consequences, zero replies
changed anywhere across marks123 and bench121.

## Evidence (registered, sealed PASSMARKS e7d9d211…)

M1: q1 PASS (F5+M5 OK), q4 PASS (0 leaks); all other suites identical to
loop121 on the same runner (p2/p3/p4/bench/sleep/soak identical incl.
case ids; rt110 fixes exactly F5+M5, rest same); rt81 bug == 0. M2:
bench121 per-item verdicts identical to loop121, 400/400 (new 136/63/1,
old 157/43/0), 0 reply diffs. M3: Fable-Edit split 200 items, 0 wrong.
M4: loop134 wave 129.6 s < 25 min.
