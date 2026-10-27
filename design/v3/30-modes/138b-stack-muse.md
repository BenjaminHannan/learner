# 138b — stacking tonight's verified fixes onto loop138 (design)

One new file (`scripts/fable_loop138b_agent.py`) subclasses the frozen
loop138 agent. L2 (`turn()`, the 127 router + Self99 live answers +
decline rule) is inherited verbatim — other agents own the self layer.
Everything else is a port of a verified mixin, reused read-only, composed
in one place so the vetoes agree with each other.

## Where each piece lives

Teach side, inside a single transient 135 patch window
(`B73.hear_teach_template → hear_teach135`, restored in `finally`):
`super().hear()` (151 "?"-twin → 148b screen → loop138 134-teach/113c
path), then 140 tail-clean (a superset of the 129 strip, so it runs
first), the 139b value veto, the 150 subject veto, the 137 upgrade, the
144 upgrade, and the 132 rewrite. Loop `_act()` mirrors the same order:
tagged asks go through the 148b reasoner record path; teach/correct go
140 → 139b → 150 → `super()._act()`.

## Two composition vetoes (the only judgment calls)

A 137- or 144-upgraded teach is additionally checked by the 139b value
screen and the 150 subject screen. Without this, the upgrades would
re-teach exactly what the stacked guards refuse (a 137-taught "Oslo and
Paris", a 144-taught compound value), because 144's length screen is
narrower than 139b's and 137's value screen predates 139b. Officeholder
sentences parse to `None` under the held 135 patch, so no upgrade path
can re-teach them.

## Question-side ordering

The 148b negation/time screen runs on the original text before the 132
rewriter sees anything, and the rewriter's second pass re-enters the
screened path — a rewritten question that carries "not" or a year is
refused, never answered around. 149 whole-word matching is applied at
import (the same process-wide pattern loop134 uses for `_APOS`) and
re-asserted at bind, so the composers and the rewriter's seed selection
share one mention rule.

## Sleep, daemon, and what was left out

L3 calls `retrofit_sleep145` instead of `retrofit_sleep131`: the
grow-one-slot sleeper plus taught-beats-sleep for every word, with
`sleep145-*` filenames so sealed 104/131 state is never touched.
`Loop138bDaemon` inherits loop138's exactly-once `process_file`
(receipts, routed log, 104-schema sleep logs) and overrides only the
poll: files are served when settled (same size+mtime across two polls,
or past grace; truly-empty files still get their one existing reply)
and tmp/dot files are skipped. Drivers write the inbox by tmp+rename
(the atomic-write client rule). 113e is OUT: it is a registered FAIL on
its own bars, and swapping the frozen 113c gate to fix the single A2-174
item risks new wrongs on unseen phrasing. 142's index is OUT: it needs an
`IndexedLoopNotebook` lower-layer swap, which the brief bars; B7 reports
wall-clock ask times instead.

## Known edges (measured, not guessed)

The 137 upgrade accepts any 2–4 Title-case tokens, so discourse-led
subjects ("Suppose Tom", "Hi. Tom") teach on 138b exactly as they do on
loop137 itself (verified live) — inherited, not introduced. The 150
hedge list is case-insensitive, so the Title-Case song name "I Believe I
Can Fly" refuses as a hedge (150's own probe exempted "I Feel …" songs
but never met "I Believe …"). The 132 rewriter repairs 113c over-fires
at scale and is almost always right, but its officeholder chains guess
confidently on three bench items and it answers H5, whose seal demands
abstain. All four are recorded as FAILs with per-item evidence in
RESULTS.md; nothing was re-tuned after the seal.
