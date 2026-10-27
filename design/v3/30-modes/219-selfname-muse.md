# 219 — Selfname: "you never told me" replies must be true (Muse)

## Problem
On loop138i, teaching "My name is Juno." stores (USER, name, Juno) and the
notebook question path ("What is my name?", "Do you know my name?") answers
"Your name is Juno.". But paraphrases the notebook ears do not parse — "Do
you remember my name?", "Did I tell you my name?", "Have I told you my
name?", "What's my name again?" — miss the notebook, route to self intent D8
via route127, and are served the hard-coded "You never told me your name, so
I do not know it." (fable_self99.py:590-591, listed "plain" and passed through
unchanged by fable_fix168_ground.py). With the fact sitting in the notebook,
that sentence is false. It was the only wrong reply in a 31-turn demo dry run.

## Design (one change)
Check every never-told/taught self reply against the notebook before sending
it. Census of such replies in fable_self99.answer_self + fable_fix168_ground:
D8 my-name (contradictable: USER/name fact — grounded HERE); D9 Mira-age
(contradictable — already grounded by fix168's D9 arm, passthrough); D6 Tom
(handled by fix168's entity-known arm, passthrough); D5 why (reasons are never
stored — byte-identical always); C22 "(never taught)" (only annotates records
already MISSING_FACT — byte-identical always). New code: scripts/
fable_fix219_selfname.py (ground219_reply: exact-D8-denial + stored USER name
→ "Yes. Your name is X.", X = N173.current_name, the same literal the normal
path renders; else byte-identical; pure, never writes) and scripts/
fable_loop219_agent.py (Loop219AgentLoop subclasses Loop138iAgentLoop; turn()
is the 138g body + 138h raw-USER backstop verbatim with the single swapped
call to grounded219_self_answer). Ears, _act, _listening_tick, reasoner,
notebook, sleep145, settle daemon: loop138i's, inherited untouched. Config:
artifacts/fable-selfname219-20260922/loop219-config.json.

## Why this shape
The bug is reply-side, not storage-side: the notebook is right, the canned
denial ignores it. Grounding at the single choke point (the self-answer call
inside turn) fixes all D8-routed paraphrases at once, including future ones,
without touching routing, parsing, or any stored fact. Gating on the exact
base string plus a live notebook read keeps the change minimal: untaught-name
replies and all other intents fall through byte-identical by construction,
which is why the frozen suites move 0 cases.

## Evidence
Sealed pre-run: agent code, config, PASSMARKS, 3 case files, base replies
(SEAL 8/8 OK post-runs). M1: 20 fictional-name sessions × 5 probes, 100/100
pass, 0 false denials while held. M2: 25/25 byte-identical untaught. M3: D9
20/20 state the stored age (5–14) equal to base, 20/20 byte-identical empty.
M4: rt136/rt143/sessions152/bench 0 moves. M5: smoke identical to 138i
(sleeps=1, installed=1, probes 5/5, wrong 0, taught 50/50, ow 0, broken
abstain). M6: 0 new wrong/junk incl. marks123 diff. Verdict PASS.

What it means: memory denials are now Gentzen-true against the notebook.
What it does not mean: no new knowledge, no reason storage, no write-path
change — "Why" questions answer exactly as before.
