# 138l merge: 138k + six safety pieces (Opus)

Agent: `scripts/claude_loop138l_agent.py` (`Loop138lDaemon`, built on
`Loop138kDaemon`). The pieces are 209, 212, 216, 222 (built on 215), 223
and 226. Every piece's own classes are reused through the MRO; no piece
file and no 138j/138k file is edited. Results are in
`artifacts/claude-merge138l-20260922/RESULTS.md`.

## Phase 1: how each piece hooks in

| Piece | What it hooks | Built on | Touches something 138j changed? | Place in the 138l MRO / expected conflict |
|---|---|---|---|---|
| 209 write screen | ears: post-screens every action the full chain returns; loop: `_act` value backstop | 138i | No shared method. Reads layer-C output only as actions. | Outermost ears mixin and first loop mixin above 138j's loop. No conflict: its own cases give 63/65 identical to 209-own. N24 is a 138j base difference; N30 is a 212+188 interaction (below). |
| 212 statement gate | loop `turn()`: swaps `L138._route127` so the self-router is off on statement turns | 138i | Yes. 138j's turn sends a notebook miss through 187 → `_route127` → 188. With the router gated, a statement miss reaches 188, which rewords it to the statement fallback. | Loop, below 226. Expected moves: G01–G32 and 209 N30 get the 188 statement fallback ("I couldn't save that as a fact…") instead of 212-own's question decline. Nothing is stored either way. |
| 216 decline cue gate | loop `turn()`: swaps `_route127`, and decline intents need their cue word | 138i | Same router seam as 212. 216 wraps whatever router is current, so the nesting order does not matter (216's docstring says so). | Loop, below 212. Its own 70 cases are identical to 216-own. Moves: rt143 O5 and rt81 I_edges-03, as 216 registered them. |
| 222 a/an of-teach (+215) | ears: 215's of-rewrite plus 222's table gate. The gated path calls `Loop138iEars.hear` directly | 215 → 138i | Layer C (Case180b…Replace154g) sits above the 138i ears. | Placed directly on the 138i chain, below layer C. This keeps 222's direct `Loop138iEars.hear` call skipping exactly the 215 mixin and nothing more, as on its own stack. Layer C sees the raw turn first. Moves: rt136 C019–C031, bench 25 `-fwd` rows, rt143 J8/K9/O3, all identical to 222's sealed rows. The 215 question rewrite answers J8/K9 before 216 is reached. |
| 223 "What can't you do?" | ears: patches `S148.trigger_spans` for the whole `hear`, and routes the intent with `_route127` | 138i | 138j's 187 capability regexes do not match "can't", so they do not conflict. | Ears, just below 209. Its own 76 cases are identical to 223-own. |
| 226 "Who told you that?" | loop: outermost `_listening_tick` intercept (before the ears, so it cannot write) and a `turn()` wrapper that classifies the last reply | 138i | Yes, two places. (a) 226 confirms a backwards answer by re-running the 153 reverse stage and matching its wording, but 138j answers with the 190b wording. (b) 138j's 187 capability sheet is not a routed DECLINE, so it can't be classified as "no fact given". | Outermost loop mixin. Expected moves: S40/S42/S44.t2 and S60.t2 get 226's safe UNTRACED reply ("I can't say where that came from…") instead of the named source. 0 writes. |

Daemon: `Loop138lDaemon(Classes138lMixin, Loop138kDaemon)`. The 228
guard cannot be the literal first base: C3 puts `Loop138lDaemon`'s own
mixin first, and the guard is already a base of 138k. So the guard is
installed at import and again first thing in `__init__`, and `_check`
asserts it is installed on every build.

Base differences (138l == 138k, so not interactions):
- 138j's 188 statement fallback (209 N24, 212 S43/S46–S49, 222 B1-Lima and O02–O20).
- 138j identity replies (212 S40, S41).
- 138j wording (226 S16–S18.t1 "Updated…", S40/S42/S44.t1 "Y's boss is X.").
- 138k's 220 index fix (226 S61–S65 no longer list a triple twice).

The full list, with reasons, is in `artifacts/claude-merge138l-20260922/predicted_moves138l.json`.

## Known weak spots found while piloting (not fixed here)
- The 226 backwards source answer does not work on 138j wording (safe decline instead). A 226c follow-up would match 190b's wording.
- For 212 G-type statements ("I feel happy today."), 138l says it couldn't save a fact, where 212-own said it didn't know. Both save nothing; the new wording suits a statement better.
- 222's bench `-fwd` and rt136 C019–C031 rows are still labelled wrong by the frozen scorers because the golds are stale. The director accepted them for 222; they are carried here as declared exceptions.

## Result
PASS on all six sealed marks (L1–L6); see `artifacts/claude-merge138l-20260922/RESULTS.md`. L2's pass relies on the declared, inherited 222 exceptions (rt136 C019–C031, the 25 bench `-fwd` rows). K1b (the 138k verifier's dialogs) was run unregistered after the seal: 0 changes vs 138k and 60/60 duplicate audits OK.
