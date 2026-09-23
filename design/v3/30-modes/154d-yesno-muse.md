# 154d — grounded yes/no on the clean stack (design)

## Problem

Loop138f removed the 154 yes/no stage for cause (redteam143 M3: the wh-run
said "Yes — Norland's capital is Aldport" where abstain is sealed), at the
cost of all yes/no capability: after "Zuri's sister is Bela.", both
"Is Bela Zuri's sister?" and "Is Ama Zuri's sister?" fall back to the base
abstain (director probe 08:55). The 138f doc queues the fix: answer yes/no
only on single-mention grounded frames. 154d is that fix, as the single
allowed change on loop138f.

## Design

New files only: `scripts/fable_fix154d_yesno.py` (parse + lookup + mixin),
`scripts/fable_loop154d_agent.py` (stacking + daemon),
`scripts/fable_fix154d_probe.py` (T1), `scripts/fable_fix154d_suites.py`
(frozen suites + bench). Loop138f and every other file are imported
read-only, never edited.

`YesNo154dMixin` sits over `Loop138fAgentLoop` (same stacking style as
loop154 over loop150). `_listening_tick` peeks at the inbox head through
the unchanged ears `hear` and diverts only on the conjunction of three
facts: (a) the base returns exactly the single didn't-understand clarify;
(b) the turn parses as exactly "Is V X's R?" or "Is X's R V?" — capital
"Is", one "'s", single-token capitalised V and X (lowercase names fall
through), lowercase relation surface, no "or"/"and", trailing "?"; (c)
the notebook grounds it — `nb.resolve(X)` is OK and
`nb.current(X, key)` is non-empty, using the loop's own relation map
(`FakeEars._relation`) and value normalisation (collapse + 129 strip,
case-sensitive). Of-forms, two-hop, hypotheticals, statements and
unknown/ambiguous frames all fail (b) or (c) and delegate byte-identical
to `super()`.

The grounded reply: stored value equals V → "Yes, X's R is V.";
different value and key in `SINGLE_VALUED_154` (imported read-only from
`fable_fix154_yesno.py` — the table only, never the mixin) →
"No, X's R is W."; different value on any other relation →
"Not that I know of. I have W as X's R." (never "No"). W is the stored
display (`entity` → name, else literal). The final record is a clarify
the mouth renders verbatim, so `turn()` serves it directly (records
without "didn't understand" skip the self-router). The divert path calls
only `nb.resolve`/`nb.current` — no teach/correct/forget path is
reachable, so it provably never writes. Ears are unchanged; diverted
turns are tagged `loop154d-yesno+<stage>` for traceability.

## Why not the wh-run

The old stage rewrote the question and re-ran the ears, so anything the
wh path "understood" (including walked-prefix and didn't-understand
shapes like M3's of-form) could produce Yes/No. Reading the notebook
directly removes that_: ungrounded frames cannot answer by construction,
and M3's "Is Aldport the capital of Norland?" (of-form, two mentions)
stays on the base abstain — verified byte-identical in T1 (n38) and in
the registered redteam143 re-run (M3 identical to 138b).

## Evidence

T1 38/38 (9 yes / 7 no-single / 4 multi exact strings; 10 fall-through
byte-identical; 0 writes on all 30 question turns). marks123 per-case
identical to marks138f across all 16 reports with an empty predicted
move set. Six frozen suites plus all four bench splits: 0 moves vs 138f,
0 new wrong/write vs 138b. One sealed-F3 mailbox flake (rt110 R5
statuses metadata only) resolved identical on the single open re-run;
both runs kept. Seal 7/7 OK after all runs; ledger P154d.1–P154d.8 all
HELD.

## Limits

Only single-token capitalised names answer; multi-word values fall
through (safe, never wrong). "Is X's R V?" takes V as one trailing token.
Multi-valued slots with 2+ stored values join with "and". No new
capability beyond these two shapes; inverted teaches and the 138c serve
rule stay off as sealed on 138f.
