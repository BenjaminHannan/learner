# 146b — Doubt with hearsay exemption (Muse)

## Problem

Exp 146 fixed stale confident answers after refused corrections (11/11
guard-broken chains + bench132-022 abstain, 0 correct lost) but FAILED D4:
its sealed rule also records doubts on F1-hearsay refusals. A quoted
contradiction ("The capital of Poland is Krakow, Tom said.") records
(Poland, capital), and the follow-up question abstains instead of
answering the standing taught fact (p2 A2/A6/A8, rt110 T4). A third
party's quoted claim then vetoes what the owner taught -- a manipulation
route the project rules forbid: hearsay must never change what the agent
says about taught facts. 146's FAIL stands; this is the registered
single-change follow-up.

## Design: one exemption, no edits

`Doubt146bMixin` subclasses the read-only 146 mixin and stacks outermost
on loop129b (loop146c) and loop139b (loop146d), at ears-hear and
loop-_act/_ask levels. No existing file is edited; 146 is imported
read-only.

**Exemption (the one change).** `is_hearsay_exempt146b(turn)` is true when
(a) the loop's own F1 classifier fires (`L102.is_hearsay` -- trailing ",
X said.", "according to", "I read online/that", "I heard", "apparently",
"reportedly", leading "quote", "the web says"); (b) the 146-parsed teach
subject is hearsay-shaped (`L102.subject_is_hearsay_shaped`); or (c) the
turn carries reported-speech / quoted-content markers (leading "Ann said
...", "X says ...", "someone told me ...", "I heard ...", "apparently
...", "according to ...", quotation marks). The set is deliberately
narrow: bare first-person teaches ("Tom's boss is Bob.", "Actually, ...",
"No, ...", all 22 first-person refuse turns of the sealed 146 probe)
contain none of these tokens (verified pre-seal, 0/22 exempt).

**Enforcement.** `hear()` pre-computes exemption and runs the identical
146 logic with `_record_doubt` suppressed for exempt turns (flag +
turn-text check, defense in depth); `_act()` suppresses recording when a
teach/correct action's name/value carries attribution markers. Ask-side
walk screening is untouched -- a question after an exempt turn still
screens against older first-person doubts, and hearsay neither records
nor clears (only a successful teach clears). Same doubt reply, same
notebook-side atomic store, same daemon/mailbox shape.

## Evidence

H4a: 146c bench 800 items, 0 verdict moves vs sealed 146 rows. H4b: 146d
bench 600 items vs sealed 139b rows, exactly 069 wrong->abstain, 0 worse,
0 lost. H3: marks123 on 146c per-case identical to the loop129b reference
on every suite (p2 64/64 incl. A2/A6/A8, rt110 62/62 incl. T4 on rerun,
q1/q4/rt81/bench/sleep/soak identical). H2: 21/24 -- all 10 hearsay/quoted
contradictions keep the standing answer with 0 doubts, all 4
first-person refusals doubt + abstain, mixed/restart/clear orders
correct; 3 sealed expectation errors (139-base negation refusal +
plain-value-change re-teach on a 129b base), each byte-identical on old
loop146. H1: 28/32 -- B07 as predicted plus 3 loop139-base expectations
run on the 129b base, byte-identical on old loop146. Control: 7/7
non-vacuous hearsay dialogues abstain under old 146, answer standing
under 146c. All runs < 1500 s Mac CPU.

## Boundaries

Leading-attribution hearsay ("Ann said ...") gets a generic clarify
("another way"), not the hearsay reply -- exempt regardless, since the
bar is behavioral. Doubt replies still abstain rather than judge truth;
CONFLICT/forget/sleep paths untouched; cross-base (139-reply on
129b-loop) probe expectations remain unmatched by construction. The
sealed rt110 harness shows volatile `statuses` log races under load
(annotation-only, different cases per run, worse on unmodified base);
verdicts + replies are the stable comparator and match fully.

## Reuse and plugs

Parsers, cue lists, F1 classifier, notebook resolve/current/triples,
scorer contract, bench and marks123 harnesses all imported read-only.
Composes with sibling mixins (139b-guard inside, 146b-doubt outside).
Adapter note: none needed -- replies are plain clarifies through
FakeMouth.

## Questions for Ben

None. Defaults taken: see RESULTS.md.
