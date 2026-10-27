# Exp 146 RESULTS — refused-correction doubt (Muse). REGISTERED MIXED: D1 PASS, D2 PASS, D3 FAIL, D4 FAIL, D5 PASS.

Target: loop146 = loop129b + Doubt146Mixin; loop146b = loop139 + Doubt146Mixin
(scripts/fable_doubt146_store.py, fable_loop146_agent.py, fable_loop146b_agent.py;
configs artifacts/fable-doubt146-20260922/loop146-config.json, loop146b-config.json).
One change only: a refused known-subject teach records a notebook-side doubt on
(subject, relation); doubted answer walks abstain ("could not store, say it again
as one fact"); a later successful teach clears it. Old facts never edited/deleted.

## Marks table (integer counts, every case reported, never averaged)

| mark | bar (PASSMARKS.md, sealed) | got | verdict |
|---|---|---|---|
| D1 loop146b bench 600 items | 11 flipped items no longer wrong; 0 other worse vs loop139 | 11/11 abstain (doubt replies); moves also 069 wrong->abstain (improvement); 0 worse | PASS |
| D2 loop146 bench 800 items | 0 new wrong, 0 correct lost except predicted (069, 022); 022 no longer wrong | moves exactly 069 + 022 (both wrong->abstain, predicted); 105 abstain, 162 wrong as predicted; rest identical | PASS |
| D3 probe 32 dialogues | 32/32 pass; 0 stale, 0 lost on no-doubt | 31/32; stale 0, lost 0 | FAIL |
| D4 marks123 per-case vs loop129b ref | identical except predicted (none) | 4 moves: p2 A2/A6/A8, rt110 T4; all else identical | FAIL |
| D5 time per run | < 1500 s Mac CPU | probe 0.8 s, D1 11.5 s, D2 27.5 s, marks123 136.4 s | PASS |

D1 detail: new_121 moves 019 047 136 139 142 195 196 + 069; old_s2fresh 056 103 124 196;
edit200 none. All 11 abstain via traversal (047, 069) or doubted-sink + mentioned /
wants-more (rest, incl. 142's paraphrase "calls home"). 069 (wrong on both bases) also
abstains — improvement, not worse. D2 detail: edit200/old identical; new_121 only 069;
bench132 only 022 (wrong->abstain); 105 abstain (CONFLICT reject creates no doubt);
162 wrong (doubted hop off the asked walk). D4 detail: p3/p4/bench/rt81/soak per-case
identical; q1 same FAIL replies byte-identical; sleep SKIP; q4 same 7 pre-existing
leaks (doubt reply contributes none); p2 still-BUG +3 (A2/A6/A8 now abstain), rt110 T4
OK->BUG (abstain). Soak 2000 turns 3 kill-9s: 0 lost/wrong/doubled, audits clean.

## Cause of the D3 FAIL (case-authoring error, not mechanism)

Sealed case B07 step 0 expects "Peanuts is great." to Save; the loop correctly
clarifies (opinions do not parse as teaches — the intended no-doubt behavior).
Steps 1-2 of B07 still pass (teach saves, question answered). Functional bars held
across all 32 dialogues: 0 stale confident answers, 0 lost answers on no-doubt
dialogues (31/32 step expectations pass; the 1 failure is the wrong expectation).

## Cause of the D4 FAIL (single cause, all 4 moves)

The sealed rule records doubts on F1-hearsay refusals too: quoted/attributed
contradictions ("The capital of Poland is Krakow, Tom said.", "..., according to the
web.", "..., I read online.") parse with the known subject + relation cue, get the
hearsay clarify, and record (subject, relation). The follow-up question then abstains
instead of answering the standing fact (p2 A2/A6/A8 sealed-BUG->OK->BUG; rt110 T4
OK->BUG). Hearsay thus gains a veto over standing answers — an availability
regression. A follow-up one-change (exempt F1-hearsay turns, which the loop screens
before teach parsing) must be a new experiment, not an edit here.

## What it means

Refused corrections no longer answer stale values confidently: 11/11 guard-broken
bench chains and bench132-022 abstain with a re-teach prompt; re-teach/repeat clears;
doubts persist across restarts; chit-chat never doubts; 0 correct lost anywhere.

## What it does not mean

The mixin is not safe to integrate as-is (hearsay veto + the sealed D4); abstains are
not knowledge (nothing judges truth); CONFLICT/forget paths are untouched (CONFLICT
neither records nor clears); doubts never add, edit, or delete facts.

## Deviations

1. Pre-seal base-loop evidence run (loop129b bench132 into scripts/scratchpad/
   doubt146-evidence/) + pure-function/offline analyses only; the new loops never ran
   before seal (seal: SEAL.sha256.txt over PASSMARKS.md + doubt146-cases.json).
2. The truncation/wants-more clause was sealed in PASSMARKS before any run (needed so
   truncated frames abstain, incl. paraphrased cues); it is part of the registered
   rule, not a deviation from it.
3. All registered waves ran solo (no parallel contention); daemon --idle-seconds
   honored (copied fixed pattern; no crash).

Reproduce: PASSMARKS.md command block (sealed SEAL.sha256.txt).
Ledger: P146.1 TRUE, P146.2 TRUE, P146.3 FALSE, P146.4 FALSE, P146.5 TRUE.
