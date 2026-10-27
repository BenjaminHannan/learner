# 162 — Possessive frame for "The"-initial names (Muse)

## The bug (file:line first)

- The officeholder catch-all is scripts/fable_bench73_english_arm.py:127,
  `(re.compile(r"The (.+?) is (.+?)"), "officeholder")`, last in
  STATEMENT_PATTERNS. Any "The ___ is ___" sentence the specific patterns
  miss is stored as `(head, officeholder, value)` with the "The" dropped:
  "The Hobbit's author is Tolkien." becomes ("Hobbit's author",
  officeholder, "Tolkien").
- Exp 135's guard (scripts/fable_fix135_office.py:175 `hear_teach135`,
  :205 `OfficeholderGuardMixin.hear`, sealed in
  artifacts/fable-fix135-20260922/) turns that wrong write into a refusal
  by allowing officeholder triples only for table-derived office heads.
  Either way the fact is unteachable, so multi-hop chains whose head is a
  work, band, paper, ship or company cannot start.

## The one change

`TheName162Mixin` (scripts/fable_fix162_thename.py), stacked outer-first as
`Loop162Ears(TheName162Mixin, OfficeholderGuardMixin, Loop150Ears)` —
the same stacking pattern as
artifacts/fable-inverted155-20260922/loop155x135-config.json.

Teach, matched BEFORE the base hear (the base would route it to the
catch-all): strict full-turn `The <X>('s|s') <R> is <V>` (capital "The"
like the base; trailing "." stripped; loop121 trailing-qualifier strip
applied; correction prefix stripped with correct-vs-teach left to
`Bench73Stage._teach_action`'s existing-row rule). R must be
letters/spaces/slash/hyphen, normalise to ALLOWED_KEYS (union of the
bench73/bench92 cue-table keys plus `PERSON_RELATIONS`, minus the 135
office family — the same construction as exp 155, 42 keys), and not be a
135 office head. The triple `(The X, R, V)` is built with
`Bench73Stage._teach_action` (structured teach, `is_person=True` like every
bench value, so values are entities and hops work), accepted only if the
loop121 value screen, the loop102 hearsay-subject check and the 150 subject
screen all pass; anything else falls through to the base path. Loop `_act`
guards (139b value + 150 subject) still apply, so replies are the canonical
"Saved: …" / clarify strings by construction.

Ask: possessive chains (`Who is The X's R1's R2?`, singular and plural) and
the of-form (`Who is the R of The X …?`, optional trailing chain) resolve
the leading The-name through the notebook's own case-insensitive `resolve`
("the" case ignored) and return the FakeEars-equivalent ask; unresolvable
turns stay on the base path byte-identical.

## Why this shape

- Pre-empting before the catch-all (rather than patching the catch-all)
  keeps office phrases byte-identical: they contain no possessive, so they
  never match either frame.
- `is_person=True` is bench parity (bench teaches all values as entities),
  not a semantic claim; it is what lets a T2 chain hop through Tolkien and
  Mabel with no exp-159 rule.
- Relations outside the tables (drummer, editor, mood, birthplace, uncle,
  captain) and office-family Rs (president, mayor, manager, director…)
  deliberately stay on the base path: drummer/editor refuse, manager-shaped
  possessives take the base officeholder write — identical to the reference
  stack, verified frozen in the probe.

## Limits (claims never exceed evidence)

- Plural `s'` teaches fail (T1 FAIL, see RESULTS.md diagnosis): the teach
  regex consumes the stem-final "s" into the `s'` alternative, so the
  stem guard rejects every plural. Singular path is 19/19.
- Drummer/editor-class facts remain untaught (outside the loop's tables);
  teaching them needs a relation-table change, out of scope here.
- The ask frame also parses of-form descriptions ("the R of the
  <description>"); only the resolve gate (exactly one taught entity) keeps
  those on the base path — verified by the pre-seal scan plus the 600/600
  bench and full marks123 diffs.

## Reproduce

Sealed configs + 51-case probe in artifacts/fable-thename162-20260922/;
`scripts/fable_fix162_probe.py`, `scripts/fable_fix162_bench.py
--variant loop162` (reference `--variant loop150x135` pre-seal),
`scripts/fable_marks123_all.py --agent scripts/fable_loop162_agent.py
--config …/loop162-config.json`, `scripts/fable_fix162_marksdiff.py`.
Daemon: `scripts/fable_loop162_agent.py --daemon --dir DIR
--idle-seconds 30` (both variants).
