# 172 — copula/verb-shape re-teach asks before replacing (design, Muse)

Base: loop154c (`scripts/fable_loop154c_agent.py`), subclassed read-only. No base or other-agent file edited. New files: `scripts/fable_loop172_agent.py` (agent), `scripts/fable_fix172_scan.py` (Step-2 move scan), `artifacts/fable-copula172-20260922/` (scan + RESULTS). Status: STOPPED at Step 2 by the brief's own gate (681 bench movers > 20). Nothing sealed, nothing registered.

## The bug

"Tavo is a citizen of Peru." then "Tavo is a citizen of Chile." silently replaces (notebook logs `correct ... -> Chile`); the same meaning in possessive shape ("Tavo's country of citizenship is Chile.") asks "I have ... Do you want me to change it ...?". Cause (Step 1): `scripts/fable_loop90_agent.py:153-170` — `Bench73Stage._teach_action` maps any second different value for one (subject, relation) to `act="correct"`, i.e. supersede, while `FakeEars` (`scripts/fable_agent_loop.py:145`) maps prefix-free possessive teaches to `act="teach"`, so `Listening` (`scripts/fable_listening_m1.py:106-127`) raises CONFLICT and asks. Every bench73 template ("is a citizen of", "speaks the language of", "was founded by", "The capital of X is Y", ...) and every bench92 extra ("is employed by", "works in the field of", "X's child is Y", ...) reaches the correct-route through that one stateful rule (plus the F3 explicit-correction path, `scripts/fable_loop102_agent.py:92-95,260-269`, for prefixed turns).

## The one change

`Loop172Ears.hear` (`scripts/fable_loop172_agent.py`) post-processes the unchanged 154c ears output: any `act="correct"` whose relation key is NOT on `MULTI_VALUED_154C` and whose raw turn carries NO base correction prefix (`Actually,` / `No,` / `Correction:` / `Sorry I meant,` — `Loop102Ears`' own RE) becomes `act="teach"`. `Loop172AgentLoop._act` is inherited verbatim, so the downgraded teach flows to the loop138b path: identical wording, identical yes/no pending state as the possessive shape. Prefixed turns still correct silently; allow-listed relations (incl. copula-shaped "famous for" -> notable_work) still add. Verified open on the director probe (see RESULTS.md).

## Why it stopped

Step-2 scan (`scripts/fable_fix172_scan.py`, real 154c ears + slot tracking, `trigger_scan172.json`): 681/800 bench items would move (191+197+99+194 across the 4 splits), plus p2x7 / rt110x3, all else zero. Bench counterfactual edits ARE copula-shape re-teaches, so asking first leaves the stale chain (diagnostic: bench121-4hop-001 final flips Tampa -> Washington, D.C.). The probe fix and the bench scorer disagree about what an edit turn should do — that is Ben's call (two options in RESULTS.md). If Ben exempts edit-style turns, the natural next revision is: downgrade only when the turn is NOT part of a multi-teach edit sequence — but "edit vs conversation" needs a director-approved marker, so 172 stops here.

## What it means

One ears-level line-flip makes every non-possessive surface shape ask before replacing, with zero changes to replies, pending state, allow-list, or explicit corrections.

## What it does not mean

It does not resolve whether bench edits should auto-apply; it does not touch the notebook contract, the allow-list, or any suite input.
