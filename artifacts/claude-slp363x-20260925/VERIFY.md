# slp-363x verification (blind recount by a separate Opus agent, 2026-09-25 ~12:45 UTC)

Recounted from results.json with its own script: all five marks pass (0 notebook changes over 28 nights; 0 nights in a
turn; 14/14 sabotaged nights rejected, both end on base.pt; replies 4/4 identical; panel +7 / -4). Re-applied the keep
rule to all 28 nights: every flag and reason agrees; the checkpoint chain is consistent. Seal 9/9 OK. Commit order:
marks + seal 12:09:40 -> time fix 12:09:49 -> results 12:33:23; seeds 3 and 4 as registered.
Disagreements on numbers: none. Accepted and fixed in RESULTS.md: crediting the general set with preventing drift
is suggested, not shown (no same-seed comparison in the registered run); "never delay a reply" was not measured;
noise and weight count come from outside this run. Code notes: score()'s proved_wrong omits the panel clause (no
effect here); scripts/claude_slp360_test.py is imported but not in the seal (it is unchanged on main since slp-360).
