# 154g — "No," corrections replace on multi-valued relations (Muse)

Base: loop154e (`scripts/fable_loop154e_agent.py`,
`scripts/fable_fix154e_allowlist.py`,
`artifacts/fable-lang154e-20260922/` incl. `loop154e-config.json`),
subclassed read-only. One change, nothing else moves.

## The problem

Director probe 10:12 on loop154e: after `Rana's language is Hindi.`,
the turn `No, Rana's language is Urdu.` replies `Saved: Rana's language
is Urdu. (I also have Hindi.)` — it ADDS, but the user was correcting.
"Actually," behaves the same (both map to act `correct`, which the 154e
`_act` routes into `_act_multi_teach154b`). `Correction:` is worse: the
154e stack never strips it, so it grows a junk subject (`Correction:
Rana` becomes an entity).

## The one change

`scripts/fable_fix154g_nocorrect.py` (pure helpers) +
`scripts/fable_loop154g_agent.py` (`Loop154gEars`, `Loop154gAgentLoop`,
`build_agent154g`, `Loop154gDaemon` with `idle_seconds=30.0`).
`Loop154gEars.hear` runs the 154e path first (correct-not / forget-one /
base stay byte-identical), then diverts a bare `<No,|Actually,|
Correction:> X's R is Y.` turn (single-hop, one-word name, R
multi-valued per `is_multi154e`, value/subject screens pass) by how many
current values `(X, R)` holds: one -> `correct_single154g` (replace);
two or more -> `ask_replace154g` (0 writes, one fixed sealed question,
pending answer state on the ears); none -> plain-teach behaviour (base
path, or an emulated plain teach for `Correction:`). The next turn with
a pending question either names exactly one listed value
(`replace_one154g`) or cancels (0 writes, processed normally).
`Loop154gAgentLoop._act` serves the three new actions and falls through
to the 154e `_act` for everything else. Plain teaches without a prefix
keep adding.

Reply forms: replace -> `Saved: Zara's language is Urdu. (It was
Hindi.)`; question -> `Which one should Urdu replace: Hindi or Tamil?`
(3+: `Hindi, Tamil or Telugu`). Replace mechanics: `Listening._teach`
with `correction=True` (the exact call the base `correct` act makes)
plus a RETRACT of the replaced row -- the contract only sets
`supersedes` on functional relations, so FACT+RETRACT is the replace
(the same two kinds the 154b correct-not path writes; never CONFLICT).

## Evidence

C1 95/95 lines (91 turns, quotas 8/6/4/3/19 traps, every question/
cancel/repeat turn 0 events); trap differential 19/19 reply- and
event-identical to loop154e. C2: bench 800 items 0 moves/0 new wrong;
marks123 0 real moves (sleep filename + seconds + 2 race-confirmed
rt110 log-statuses only; p3/rt81 FAILs inherited); G3 0 moves/0 new
wrong/write. Pre-seal trigger scan over every frozen input: 0 flags
(predicted EMPTY, held).

## What it means

Saying "No," about a language now fixes the language instead of
collecting a second one; with several languages the assistant asks
which one you meant, and anything else you say next still works.

## What it does not mean

It does not change plain teaches (they still add), correct-not
(`Y, not Z`) and forget-one forms, asks, quotes, single-valued
relations, or any frozen suite (all 0-move); it does not guess which
value to replace (it asks, then only an exact name counts).
