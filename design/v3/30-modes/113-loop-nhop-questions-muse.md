# 113 — Loop102 + N-hop questions, scorer v2 (Muse, 2026-09-22)

For Ben in plain language: last time (exp 111) the assistant flunked long
questions because it only ever walked two links of a four-link chain and
then answered confidently anyway. This experiment plugs in the full-chain
walker and adds one safety rule: never answer a shorter question than was
asked. Long-question wrongs fell from 130 to 5 — but two new FAILs showed
up, both explained below.

## The one change

`scripts/fable_loop113_agent.py` (new, prefix-owned; nothing else edited).
`Loop113Ears` subclasses loop102's ears and reroutes turns ending in "?"
in this order: (1) hearsay screen first (unchanged); (2) exp-103's
`compose_n_hop` walks the FULL taught chain with its coverage gate — on a
frame, the compound-subject guard checks the notebook for further facts
about the walk-end entity under a compound subject the walk couldn't cross
(e.g. the walk ends at "Madonna" but the notebook holds "director of
Madonna" — answering the 1-hop prefix would answer a shorter question, so
clarify); (3) exp-73's `compose_question` is accepted ONLY for explicit
single-hop/structural probes (Who-is-X-of-name, Who-verb-by-name,
never-taught-relation), which can never be truncations; (4) otherwise
clarify/decline, never guess. Non-"?" turns delegate byte-identical to
loop102, so teaching, forgetting, corrections and qualifiers are
untouched. `scripts/fable_bench113_run.py` runs loop102-before and
loop113-after on both splits with scorer v2; `scripts/fable_loop113_marks.py`
replays loop102's P2/P3 marks against loop113 (agent class swapped only).

## Scorer v2 (registered before the run)

Exp 111's scorer had two interface flaws: it compared the whole mouth
sentence against a short gold phrase (so right answers counted wrong),
and its "not" substring marker misread "notable" as abstaining. V2
extracts the answer value (text after the final " is "/" are ", trailing
period stripped) and exact-matches it normalised against gold+aliases;
abstain = the loop's own decline/clarify/"I don't know" forms on WORD
boundaries; else wrong.

## Evidence (sealed P113.1–P113.5: 3/5 TRUE)

Pre-seal probes showed compose_n_hop agreeing with the 2-hop composer on
all 100 split-A chains, explicit routing covering all 100 reversal+abstain
questions, and 148 full-4hop / 12 guard-declined / 38 unparsed / 2
child-missing frames on fresh. Registered run: split-A 200/200 right
behaviour, 0 wrong, 0 teach rejects (N2, N3 PASS); fresh 145 correct / 50
abstain / 5 wrong (N1 FAIL at bar ≤ 2 — all 5 are teach-gap partials the
notebook gives no evidence of, hence unfixable from the question side);
N4 FAIL (P2 16 OK→BUG/19 still-BUG; P3 l5z1 47/60, l6 0/200); N5 PASS
(46.2 s total). Teach rejects identical under both loops (22 in 12 fresh
items) — out of scope, reported. Full tables in the artifact RESULTS.md.

## The N4 lesson (over-broad interception)

V1 reroutes EVERY "?" turn, including M1-possessive shapes neither
composer parses ("Who is Forget's city?") that the FakeStage answered.
Scoped fix for a follow-up, not applied here: delegate to the exact
loop102 chain when both composers return None; keep flat clarify only for
guard hits and non-explicit 2-hop frames (the truncation shape).

## Limits

The compound guard only sees notebook evidence; wholly-missing hops
(child sentences, "and"-guard rejects) still answer short — that is N1's
5. Cue-substring mention counting was measured (78/100 good split-A items
carry spurious cue extras) and deliberately NOT used as a gate.

## What it means

End-to-end long questions now work through the real mailbox whenever the
facts were teachable; remaining wrongs are all missing teaches, and the
regression has a scoped one-line-class fix.

## What it does not mean

It does not mean the loop handles fresh phrasings (teach patterns for
occupation/employer/child/"and"-objects are still missing) nor that v1 is
safe to keep (N4 regressed everyday possessive questions — the follow-up
fix must land first).
