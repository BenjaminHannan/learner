# 216 — Decline intents need their cue (Muse, on loop138i)

## Problem
Director-verified on loop138i: when the notebook misses, route127 sends
ordinary world questions to canned decline answers, and decline intents skip
the novelty guard ("novelty: vacuous (always-decline intent)"). "Who painted
Tin Stars?" → "I do not have favourites." (D1, 0.82); "Who composed Blue
Rain?" → D1; "What did Barnaby Quillfeather direct?" / "Who designed Xenon
Lullabies?" → "You never told me why. ..." (D5). No false fact, but the reply
answers a question nobody asked. Base serves D-intent on 6/40 of the fresh
world panel (P1-01/02 D1; P1-03/04/21/32 D5).

## The one change
`scripts/fable_loop216_agent.py` (new file; loop138i untouched): a decline
verdict Dk (D1–D10 of `fable_self105.CANONICAL`) is served only when the turn
holds Dk's cue or a second-person word; else the turn gets exactly today's
DECLINE reply (`HONEST_DECLINE + DECLINE_SUFFIX`). Cue table (whole tokens,
case-insensitive; D6 needs tell-word + second-person; D8 needs name + my/i/me;
D4 also fires on "going to"): D1 favourite/favorite(s); D2
feel/feeling(s)/emotion(s); D3 yesterday/ago/earlier/last/week/night/time(s);
D4 will/tomorrow/future/next/year/week/month(s)/going-to; D5
why/reason(s)/because; D6 tell/told/say/said; D7
better/worse/best/worst/prefer/than; D8 name(s); D9 old/age; D10
dream(s)/dreamt/dreamed. Second-person: you, your, yours, yourself, u, ur.

## Call site and stacking with exp 212
The 138g notebook-miss branch reads `L138._route127(text)`. The 216 turn
wrapper swaps in a stand-in that calls the saved router and downgrades cueless
Dk to DECLINE (restored in `finally`). It delegates to whatever the attribute
holds, so exp 212's statement gate (same swap pattern) nests in either order:
statement-without-you → 212 declines; cueless question → 216 declines; a turn
failing both still declines; genuine self questions pass both. Each fix is
deliberately blind to the other's problem (cue-carrying statements still
route here; cueless self questions still decline).

## Why the DECLINE text is the safe fallback
It is the router's own DECLINE branch output, already the reply for 34/40
world questions and for every guarded-out turn: zero new sentences, zero
names/numbers, and the bench/redteam abstain bits ("didn't understand",
"don't know", "another way") keep judges scoring abstention.

## Verification (registered)
P1 0/40 D-intent; P2 30/30 identical; frozen moves exactly the 4
scan-predicted (rt143 J8/K9/O5 all off WRONG-ANSWER, rt81 I_edges-03
UNCLEAR→OK), 0 new wrong/writes everywhere; bench 800 0 moves; smoke passes
(5/5, installed, 0 wrong). Seal 8/8 OK post-runs.

## Limits
Cueless-but-genuine self phrasings ("Is Ambrax better than Corvin?") decline
rather than answer — accepted per spec (cues Required). Over-broad cues
("last", "time", "name"-adjacent "you") can still serve a D reply on a world
question; none of the 40 panel shapes or frozen suites hit this. The gate
reads the turn only, never notebook state, so it cannot fix answers that are
wrong for state reasons.

What it means: missed world questions now abstain honestly; self questions
are untouched. What it does not mean: the router is not smarter — cueless
self questions still decline, and statement-shaped turns are 212's job.
