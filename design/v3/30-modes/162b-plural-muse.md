# 162b — Plural "The Xs'" possessives save (Muse)

## The bug (file:line first)

- Exp 162's teach regex, scripts/fable_fix162_thename.py:88,
  `The\s+(.+?)('s|s')\s+(.+?)\s+is\s+(.+?)`, consumes the stem-final "s"
  into the `s'` alternative: "The Beatles' founder is Lennon." parses as
  inner "Beatle" + marker `s'`. The guard at :156-158
  (`if not inner.lower().endswith("s"): return None`) then rejects every
  plural, and the turn falls through to the base refusal. Singular `'s`
  is 19/19. Registered FAIL in
  artifacts/fable-thename162-20260922/RESULTS.md (diagnosis note 1).
- Same folder's daemon wrapper, scripts/fable_loop162_agent.py:104-129
  (`_DaemonBase.__init__`), dropped the `self.idle_seconds =
  float(idle_seconds)` line its loop150 template has
  (scripts/fable_loop150_agent.py:72), so `run()` raises AttributeError on
  the first idle check; daemon-mailbox suites p3/rt110/q4 hang (diagnosis
  note 2).

## The one change (behaviour)

`Plural162bMixin` (scripts/fable_fix162b_plural.py), stacked outermost as
`Loop162bEars(Plural162bMixin, TheName162Mixin, OfficeholderGuardMixin,
Loop150Ears)` in scripts/fable_loop162b_agent.py. `parse_plural_teach` is
162's teach shape with one fix: only the `s'` marker is accepted and the
subject is stem + "s". Same gates (ALLOWED_KEYS relation gate, loop121
value screen, loop102 hearsay check, 150 subject screen,
`Bench73Stage._teach_action` with `is_person=True`), same loop `_act`
guards. The mixin claims only `s'` turns loop162 always rejects; all
singular `'s`, office, and ask turns take the loop162 code literally --
singular byte-identity by construction, not by testing. Ask side is 162's
unchanged code: once "The Beatles" is taught, "Who/What is The Beatles'
founder?" and "Who is the founder of The Beatles?" resolve through the
notebook's case-insensitive `resolve`, and the C2-style 2-hop chain
("The Beatles' founder's mother") works with no hop rule.

Harness-only second change (disclosed): `_DaemonBase162b` delegates to
162's `__init__` then re-adds `self.idle_seconds = float(idle_seconds)`.
No teach/ask code touched; mailbox bytes unchanged.

## Why this shape

- Outermost-only-claims-what-base-rejects keeps the blast radius at one
  line: the pre-seal disjointness audit shows zero inputs claimed by both
  parsers across all 127 probe turns, except the ss-stem edge ("The
  Class'": base saves truncated "The Clas", 162b saves "The Class") --
  itself a wrong-write fix, with no such input in any sealed suite.
- `is_person=True` stays (bench parity; values stay entity-valued so the
  C2/C3 chains hop with no exp-159 rule).
- Relations outside the tables (drummer/editor/manager) still fall through:
  "The Beatles' manager" takes the identical base officeholder write
  (frozen as O12).

## Limits (claims never exceed evidence)

- ss-stem plurals ("The Class'") change base behaviour from a truncated
  wrong write to the correct write; no sealed input hits this edge.
- Drummer/editor-class facts remain untaught (outside the loop's tables).
- The daemon fix only restores the documented `--idle-seconds` contract;
  soak/rt110 mailbox races under heavy load remain possible and are
  re-run-once-reported-both per the brief.

## Reproduce

Sealed config + 76-case probe in artifacts/fable-plural162b-20260922/;
`scripts/fable_fix162b_probe.py`, `scripts/fable_fix162b_bench.py` (vs the
base folder's frozen loop162 rows), `scripts/fable_fix162b_g3.py`,
`scripts/fable_marks123_all.py --agent scripts/fable_loop162b_agent.py
--config …/loop162b-config.json --workers 2`,
`scripts/fable_fix162b_marksdiff.py` (vs marks162, vs marks150 for
p3/rt110/q4).
