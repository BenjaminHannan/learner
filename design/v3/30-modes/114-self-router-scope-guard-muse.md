# 114 — Self-router scope guard: decline out-of-scope questions (Muse)

Exp 105 (registered FAIL) left a precise diagnosis: 5 of its 6 blind WRONGs
were questions about someone else ("How many facts does Tom know?"), the
future ("How many facts will you know by the end of today?"), or
policy/capability ("is it gone-gone?", "which sources do you trust?", "Can
you forget on request?") — answered with present-state content for a
neighboring intent. Exp 114 makes ONE change (guard only) and tests it on a
100-question panel written blind by another agent.

## The one change

`scripts/fable_self114.py` subclasses the exp-105 agent and overrides ONLY
the entry to routing: `scope_guard()` runs first, and a decline returns the
identical inherited HONEST_DECLINE sentence ("I ... have no record ...",
carrying the frozen decline markers). If the guard passes, the frozen 105
scored router runs unchanged (same normalisation, keyword tables,
thresholds, margin 2) and answers come from the untouched exp-99 bodies.
Guard clauses, in check order:

1. **Future**: token in {will, shall, tomorrow, next, future, predict,
   tonight, soon, eventually, gonna} or token-pair {go to, about to}.
   Bare "would" is excluded on purpose: exp-100 Q14 and exp-105 Q048 are
   CORRECT existing questions containing it.
2. **Hypothetical**: token in {suppose, imagine, pretend, hypothetical} or
   pair "what if". Bare "if" excluded (Q14 again).
3. **Third party**: token "tom" (post-normalisation, so Tom/Tom's match);
   standalone {he, him, his, she, her, hers, they, them, their, theirs};
   a capitalised name adjacent to a knowledge verb ("does Alice know",
   "Tom believes") unless it is a session name/place; a raw 's-possessive
   on a non-session capitalised name (contraction bases excluded).
   "Anyone/someone" are excluded (C26 needs them); "its" is excluded (C27
   needs it); "lives" is not a knowledge verb (C15/C30 need it).
4. **Policy/capability**: "standard(s)"; plural "sources" (singular
   "source" is the live C27 question); "trust"+"source" together;
   "forget" with a capability marker (can/could/will/would/ever/gone/
   somewhere/keep/still/request/... — history forms like "what have you
   forgotten" pass); (can/could/will/would)+"fix"; standalone "gone".

## What tuning taught (dev: exp99-40 + exp100-80 + exp105-panel-100)

Two near-mistakes caught before freezing, both from checking every guard
fire against dev verdicts. First, substring matching on the joined tokens
fired "about to" inside "about total" (exp-100 Q03, CORRECT) — bigrams now
match on token pairs. Second, co-occurrence of a capitalised word with a
knowledge verb fired on sentence-case "Like," and "Give" (exp-105 Q022,
then CORRECT) — the knower rule now requires adjacency (name+verb or
does+name+verb). At freeze: exp99 40/40, exp100-80 WRONG 0, guard fires on
zero of 220 dev questions answered CORRECT, and the 105-panel re-score is 1
WRONG (Q003 "individuals", a synonym gap this change does not touch).

## Freeze and blind run

Router hashed (sha256 in PASSMARKS.md), PASSMARKS sealed with shasum,
ledger P114.1–P114.5 appended — all before the panel was opened. The panel
author used a bare-list shape (not `{"questions": ...}`) and a
panel-dir-relative seal, so the runner (my own file, pre-run) verifies the
seal from the panel dir and accepts both shapes; the router file itself was
never touched after its hash (re-verified in-run). One 1.0 s run: K1 4/100
WRONG (FAIL), K2 17/70 (FAIL), K3 10/10 (PASS), K4 PASS (40/40, exp100-80
zero WRONG). Dev-context re-score: 105 panel exactly 1 WRONG (Q003).

## Reading the FAIL honestly

The guard did its job and cost nothing: it caused 4 of the 50 existing
declines, all already declining under 105, and six fresh tricks declined by
guard reason. Three of the four WRONGs sit in machinery this experiment
was forbidden to change (synonym "tally", keyword overlap C6/C27, NEW-rule
C4 content); the fourth, Q017's "Assuming...", is a hypothetical marker
outside the frozen set — the single in-scope miss and the obvious next
one-change experiment, alongside synonym work ("tally", "origin", "cite").

## What it means

Scope-traps are now declines, not misfires, with zero coverage cost — but
the router's ceiling on oblique phrasing is vocabulary, and K2 (17/70)
says so plainly.

## What it does not mean

No new answering power was added: 79 of 100 answers are declines, and the
guard cannot rescue questions the keyword scorer cannot reach. Nothing here
touches real English understanding, only the scaffolding router.
