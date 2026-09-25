# slp-364d verification (blind recount by a separate Opus agent, 2026-09-25 ~07:55 UTC)

Recounted from results.json with its own script (not score()): V2 15/20 faults rejected, V1 10/20; honest rejected
0/20; main log and sandbox 40/40; honest replies identical 20/20; 0 errors. Every mark verdict matches: registered FAIL
on P364d.1. Not proved wrong (15 is exactly at the "fewer than 15" edge). Seals: all 10 hashes OK. Commit order: marks,
gate and runner (06:45) -> dev disclosure (06:55, 4 lines added, no bar changed) -> bench (07:23) -> results (07:49).

Disagreement, accepted and fixed in RESULTS.md: it credited v4's new rules with catching 27; v1's L rule caught it, and
L2/U fired on no bench night.
Notes: p_restored is None (not True) on 32 and 40, where slp-368 stopped the sleeper before the sandbox ran; both
rejected. score()'s proved_wrong omits the "changes an honest reply" clause (no effect: 20/20 identical). The recounter
could not check the bench-side "how the fault works" column (bench not opened by it).
