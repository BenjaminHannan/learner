# 227 — Identity sheet: questions about the assistant (Muse)

## Problem
On loop138i (fresh notebook), "What is your name?" and "Who made you?" both
return the user-name intent D8 reply "You never told me your name, so I do
not know it." That answers about the user; the question was about the
assistant. A Step-0 census (45 identity questions, census138i-rows.json in
the artifact folder) mapped the damage: NAME-about-assistant and
MAKER-made/created route D8 (wrong); every other identity phrasing
(WHAT/LEARN/HOME/AGE-how-old, plus built/invented/designed/maker/creator and
"Do you have a name?") gets an unrelated DECLINE; "What is your age?" and
"birthday" get D9, the Mira's-age reply (wrong subject). All census turns
wrote 0 facts. User-about questions work: after teaching, "What is my name?"
and "Do you know my name?" hit the notebook namecheck.

## Design
One fixed identity sheet (scripts/fable_identity227.py, plain software like
the capability sheet), six intents with one literally-true answer each: NAME
"I don't have a name yet." MAKER "Ben built me." WHAT (small program,
notebook, answers from it, declines instead of guessing) LEARN (learns from
plain taught sentences, saves each one) AGE (no age; does not measure life in
years) HOME (lives nowhere; runs on a computer, keeps a notebook file). AGE
and HOME are included only because the census shows wrong replies for them.

Routing is deliberately narrow: a "?" turn reaches the sheet only with a
second-person word (you/your/yours/yourself) AND an exact normalised match
against 38 sealed templates (scripts/fable_identity227_templates.json) —
templates, not keywords, so no near-miss can fire. The gate sits inside the
notebook-miss branch of turn() (scripts/fable_loop227_agent.py, a loop138i
subclass), so taught-fact answers always win, and it is reply-only: zero
notebook writes by construction. User-about first-person questions are not
templates, so they keep today's route exactly (exp 219 owns those).

## Evidence
M1 36/36 (6/intent, 12 taught-first, 0 writes); M2 32/32 byte-identical to
138i; suitediff rt136/rt143/sessions152/bench 0 moves; sleep smoke identical
to 138i (5/5 probes, 0 wrong, taught 50/50); marks123 0 moves. Verdict PASS.

## Limits
The sheet covers 38 phrasings; anything outside them still declines. The
assistant claims no name, age, or home — by design, not by missing data.
