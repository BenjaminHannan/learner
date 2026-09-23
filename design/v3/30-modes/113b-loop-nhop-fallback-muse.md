# 113b — Loop113 + fallback to the exact loop102 chain on double-None (Muse, 2026-09-22)

For Ben in plain language: last time (exp 113) the assistant learned to
answer long chain questions, but the new wiring grabbed EVERY question —
including simple ones like "Who is Forget's city?" — and then gave up on
the simple ones because neither of its two question-understanders could
parse them. This experiment adds one fallback: if both understanders come
up empty, hand the question to the old path exactly as it was. The simple
questions work again — but 4 tricky cases still answer when they should
stay quiet, and we know exactly why.

## The one change

`scripts/fable_loop113b_agent.py` (new, prefix-owned; nothing else edited).
`Loop113bEars` subclasses `Loop113Ears` and keeps v1 routing exactly,
except for one new branch: when `B92.compose_n_hop` AND
`B73.compose_question` both return None on a "?" turn, it calls
`Loop102Ears.hear` on the same instance — the same notebook binding, the
same inner loop96 chain, the same FakeStage path loop102 used. Flat
clarify is kept only for compound-guard hits (notebook holds MORE than
the walk) and non-explicit 2-hop frames (the truncation shape). Non-"?"
turns inherit v1 behaviour, which already delegates byte-identical to
loop102. `scripts/fable_bench113b_run.py` runs loop113-before and
loop113b-after on both splits with scorer v2 (identical to exp 113);
`scripts/fable_loop113b_marks.py` replays loop102's P2/P3(L1–L6)/P4 marks
against loop113b (agent class swapped only, plus the P4 innocent-30 gate
exp 113's marks script omitted).

## Evidence (sealed P113b.1–P113b.4: 3/4 TRUE)

Registered run: split-A 200/200 right behaviour, 0 wrong, 0 teach rejects
under both arms (M2 PASS); fresh 145 correct / 50 abstain / 5 wrong with
the identical 5 teach-gap ids under both arms (M3 PASS — the change fires
only on double-None questions, as designed); P3 L1–L6 all pass (L6 back to
200/200 × 3 seeds, L5-Z1 back to 60/60), P4 30/30 with 0 false refusals;
M4 PASS (22.0 s + 24.0 s). M1 FAIL: P2 shows 2 OK->BUG (B7, D8) + 2
still-BUG (C2, C5) versus loop102's clean sheet.

## The M1 lesson (short frames, not None)

The fallback condition is necessary but not sufficient. A post-hoc probe
with hand-built triples (analysis only, no re-run) showed
`B92.compose_n_hop` returning 1-hop PREFIX frames where the question names
2 hops: B7/C2 ("official language of the country of citizenship of
Roberto Merhi" with a broken/overwritten second hop -> `[citizenship]`),
C5 ("Where was the author of Fasti born?" after the birthplace was
forgotten -> `[author]`), D8 ("Who is Poland's capital in 2019?" ->
`[capital]`, qualifier ignored). A non-None frame means no fallback, so
the inherited v1 ask-path answers a shorter question than was asked —
the exact truncation class exp 113 fixed on the fresh split, now
surfacing on broken chains and qualifier questions. B92's coverage gate
checks parse coverage, and the compound-subject guard only fires when the
notebook holds MORE (a continuation), never when it holds LESS (a missing
hop). Loop102's ChainEars coverage check clarified all four. Scoped fix
for a follow-up, not applied here: treat a frame naming fewer hops than
the question as double-None (route to the exact loop102 chain, which
carries the qualifier and broken-chain abstentions).

## Limits

The change is purely question-side routing; teach patterns, the 22
fresh-phrasing rejects, the 5 teach-gap fresh wrongs, and qualifier
semantics are untouched. P2's kill9-burst leg runs the 113b daemon binary
and writes under the exp-113b folder.

## What it means

Everyday possessive and FakeStage-shape questions are restored with zero
movement on anything the N-hop composer covers: the N4 regression is
fixed for the whole double-None class.

## What it does not mean

It does not mean composer-covered questions are safe: short-prefix
frames on broken chains and qualifier questions still answer confidently
(4 P2 cases) — the partial-frame rule must land before this routing is
kept.
