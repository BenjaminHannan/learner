# ADDENDUM rt-02d (2026-09-26 ~14:05 UTC; PASSMARKS-rt02d.md is sealed and unchanged)

1. Seed description: PASSMARKS "Test data" says 0.2c's day puzzles are seeds 4700-4702 and TEST is the first 100 of
   4790. The code (claude_sleep02c.run) uses nights 1..3 = seeds 4701-4703, and TEST = the first 100 of
   puzzles(4790, 400) not in any day. The blind panel writer followed the code AND also excluded seed 4700 and the
   literal description (673 keys excluded); none of the 100 panel puzzles is in either set (panel README). No mark changes.
2. Route details fixed before the run (in claude_rt02d.py, sealed): greedy answer, then N_TRIES = 20 sampled answers
   at T 1.5 (the nights' TEST setting) with a per-puzzle seed shared by B1 and B1off; the first answer that passes
   the exact checker is given. Runner seeds torch before every turn (TURN_SEED + turn index) in every arm and turns
   on deterministic algorithms, so R4's byte-identical comparison is meaningful.
3. Dev gate (not a mark): before the registered runs, B0 runs the 55 dev cases twice; if any reply differs, R4 cannot
   be measured on this machine and the job stops with NONDETERMINISTIC before any registered run.
4. Dev results (my 8 dev wordings incl. CHAT_ASK, 40 dev puzzles seed 4880, 15 dev negatives): parser 55/55; CPU
   smoke test with the plain 1B (no adapter): route answered 1 of 4 dev puzzles, restored LoRA scales after an off call.
