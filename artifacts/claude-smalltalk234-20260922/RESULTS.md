# Exp 234 RESULTS — one honest small-talk reply

**Verdict: FAIL** (registered). M1 panel failed: 13/20 wellbeing items got
the fixed reply (65%, bar 90%). M2-M5 all passed. Seal verified 6/6 OK after
all runs; nothing was re-sealed or re-run.

| Mark | Bar | Result | Status |
|---|---|---|---|
| M1 panel wellbeing fixed reply | >= 18/20 | 13/20 | FAIL |
| M1 fixed reply in other families | 0 | 0 / 36 | ok |
| M1 non-wellbeing replies byte-identical to 138i | 36/36 | 36/36 | ok |
| M1 setup replies / notebooks identical to 138i | 56/56 | 56/56, 56/56 | ok |
| M1 writes on wellbeing turns | 0 | 0 | ok |
| M2 dev | >= 95% | 84/84 (40/40 wellbeing, 44/44 others unchanged) | PASS |
| M3 suites vs 138i (rt136, rt143, sessions152, bench, marks123) | 0 new WRONG/WRONG-WRITE/junk, GATE clean | 0 moves in all five, GATE clean | PASS |
| M4 sleep smoke vs s1-138i | identical except seconds | sleeps=1 installed=1 episodes=20 probes=5/5 wrong=0 broken=abstain taught=50/50 ow=0; only seconds/agent/config/label differ | PASS |
| M5 latency (median paired delta) | <= +5 ms | panel -0.031 ms (mean 0.000, n=56); dev +0.023 ms (mean +0.057, n=84) | PASS |

Panel expect-field agreement (not a bar): 49/56.

## Every move
Panel: 13 moves, all wellbeing items, all to the fixed reply (s234-001..006,
009..013, 018, 019). 0 moves in people_wellbeing (12), status (8),
greeting_plus_question (8), plain_questions (8).
Dev: 40 moves, all wellbeing, all to the exact predicted reply. Suites: 0.

## Every panel miss (234 reply = 138i reply in each)
- s234-007 "hello" -> 138i greeting reply (bare greeting; not matched by design)
- s234-008 "Hi there!" -> generic decline (bare greeting; not matched)
- s234-017 "good afternoon" -> 138i greeting reply (bare greeting; not matched)
- s234-014 "whats up" -> mode-status line (deliberately excluded in the design note as closer to a status question)
- s234-015 "Hey! How's your morning been?" -> decline ("morning" not in the grammar)
- s234-016 "Hi, hope you're well. How are you?" -> decline ("hope you're well" not in the grammar)
- s234-020 "hey, how's everything with you" -> decline (tail "with you" not in the grammar)

## Diagnosis (one note)
Two causes. (1) Spec reading: the brief says "a greeting and/or a question
about how the assistant is doing"; I read bare greetings as staying on 138i's
existing greeting reply, while the panel counts 3 bare greetings as
wellbeing that must get the fixed reply. (2) Grammar coverage: 4 real
wellbeing phrasings ("whats up", "how's your morning been", "hope you're
well", "how's everything with you") are outside my closed list. The dev set
was written by me and shared my blind spots, so 84/84 dev did not predict
this.

## Deviations
- First registered launch attempt failed at the shell (a zsh quoting error
  in my command, exit 127, before any Python ran or the panel was opened);
  relaunched with the identical command spelled out. No code changed.
- The smoke root (smoke234/) and suite rows (suitediff/) sit in this folder.

## What it means
The change does what it was built to do on the phrasings it knows: "Hi, how
are you?" (the demo opener) now gets "Hi! I'm here and ready to learn. Tell
me something, or ask me about what you've told me." instead of a mode-status
line, with no writes and no change anywhere else (0 moves on every frozen
suite, sleep unchanged, no measurable slowdown). It never fired on questions
about people, status questions, or greeting + real question.

## What it doesn't mean
It does not pass: on a fresh, blind set of ways people ask "how are you",
only 13 of 20 got the new reply, so a family member who phrases it
differently ("How's your morning been?", "what's up") still gets the old
confusing answer. It also does not settle whether a bare "Hello" should get
the new reply or keep the old teach/ask greeting — that is a decision for
Ben/the director, not something this run shows. Nothing here says the
assistant understands small talk; it is a fixed list of phrases.
