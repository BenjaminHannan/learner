# 333c: creative with a stricter request detector. Marks fixed 2026-09-24 ~17:45 UTC, before 333c runs

One change from 333b: routing. is_creative333c = 333's cue AND the turn is a request to the assistant (a question
mark, "can you/could you", an imperative such as write/give/help/suggest/plan at the start, "help me", "I need
ideas", "what should I", "any ideas") AND not a recall question ("no idea", "any idea what/where...", "did I tell",
"remind me", "who wrote", "whose idea"). scripts/claude_cre333b_agent.py.
Dev evidence (not the panel; the thread's own sentences in scripts/claude_cre333b_test.py): 15/15 own creative
requests still routed; own look-alikes routed 333 13/20, 333c 0/20. DEV bank: 10/10 creative, 0/184 other (both).
Arms: P = 292t + 333 with Gen333b and is_creative333c (scripts/claude_cre333b_wrap.py c); B and T as in 333b.
Marks and bars: P333.1-P333.5 exactly as in PASSMARKS.md. Proved wrong if P333.2 is still below 29/30 or if fewer
than 23/40 creative items are routed (the 333 cue already caught only 25/40, so the detector may lose at most 2).
