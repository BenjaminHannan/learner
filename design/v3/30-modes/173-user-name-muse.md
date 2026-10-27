# 173 — User-name learning on loop166 (muse)

## Problem

Loop166 owns a reserved USER entity for "me"/"my", but the `name`
relation is unreachable: `is_office_head("name")` is True
(table-derived titles), so the me-frames veto it and every name turn
("My name is Sam.", "What is my name?", "Who am I?") clarifies with zero
writes. The agent can never learn who it is talking to, so it also cannot
resolve the user by name ("Nell's sister" stays an unknown stranger).

## Design (one change)

`Name173Mixin` (scripts/fable_fix173_username.py) stacked outermost:
`Loop173Ears(Name173Mixin, Loop166Ears)`. It claims only (a) five
statement shapes and five question shapes (pure functions, no notebook),
and (b) stored-name-headed possessive/check turns (possible only after a
name is set -- and no suite input sets one, proven by a 2885-turn
pre-seal scan with 0 fires). Everything else is the loop166 code
literally, so non-name behaviour is byte-identical by construction.

Naming rule. X must be 1-3 tokens, each capitalised (for `I'm`/`I am`
capitalised as typed, never silently; for `My name is`/`Call me` a
lowercase token is capitalised) and name-shaped: its lowercase form is
absent from /usr/share/dict/words or a genuine given name. Ordinary
vocabulary ("tired", "happy", "later", "nurse", "teacher", "friend",
"sick", "important") therefore never names, and look-alikes fall through
to the loop166 path untouched.

Storage. `(USER, name, X)` is stored LITERAL (`is_person=False`, so a
name statement creates no non-USER entity) through 166's own gates, with
`act="teach"` forced. Because `name` is functional, a second different
name hits the listening CONFLICT and takes the EXISTING change-prompt
path (yes replaces, no keeps) -- never the silent supersede that 166's
`_teach_action` would otherwise apply. Same-name reteach duplicates
harmlessly. Questions run the normal hop: set -> "Your name is X.";
unset -> "I don't know your name yet." (the me166 first-person unknown
form; the nothing-ever-taught UNKNOWN_ENTITY line maps to the same
sentence, never the raw key).

Third person. A possessive turn headed by the stored name is
re-dispatched with the head rewritten to "my" (same USER facts, same
replies, same supersede semantics as "my"). "Is X `<Owner>`'s `<R>`?"
looks up (`<Owner>`, `<R>`) and compares to X (yes/no; a miss returns the
reasoner's own record, preserving existing unknown wordings).

Rendering. Reuses loop166's `rewrite_me166_reply` verbatim, plus one
UNKNOWN_ENTITY line and `yes`/`no` turns completing a pending name
change (scripts/fable_loop173_agent.py, which also answers the
`namecheck` action). No 166/162b file is edited.

## Evidence

T1 52/52 byte-identical; T1b 45/45 (13 statements, 11 look-alikes, 4
renames, 7 third-person, 5 unset, 5 other); T2 zero wrong writes, zero
non-USER entities from name statements. G1 600/600 zero moves. G2
per-case identical to marks166 everywhere (p2 64, p4 30, rt81 74, rt110
62, p3/l2-cases 74, whole-files after scrub); rt110 showed only
verdict-equal log-observability flakes with varying sets across two runs
(documented mailbox/log race, also in the base's sealed row). G3 zero
moves on 145+124+180 turns. Max run 219.4 s (< 1500 s).

## Limits

`?`-suffixed name statements stay clarifications; chained teaches
("My mom's city is X") and office heads are untouched; yes/no checks only
cover the single `Is X <Owner>'s <R>?` shape. The given-name list is
hand-built: an unusual genuine name absent from it AND present in
/usr/share/dict/words would be refused (falls back to clarify, never a
wrong write).
