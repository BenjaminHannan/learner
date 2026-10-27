# dl-6c: dl-6 with a GLM-written puzzle instruction (Fix-sleep thread; registered when committed; HELD, not queued)
Ben chose "Count it" (16:50 UTC 09-26), so dl-6 counts as sealed and dl-6c does not run unless someone later rules
that the Claude-written instruction frame disqualifies a result. Kept ready per the Thread manager (16:49).
Code: scripts/claude_dl6c_glmframe.py imports scripts/claude_dl6_light.py unchanged and swaps claude_blurt1's
instruction for GLM 5.3 Flash's: "Using each number in {NUMS} exactly once with +, -, *, /, and brackets, write an
expression that equals {TARGET}, and reply with only that expression." (artifacts/claude-glmframes-20260926/
frames.json, sha256 3c1fe9c190837704878759cd4f0f17d9c88aa2a0795536c4dbc90be4a80014bc, pinned in the code).
Marks: artifacts/claude-dl6-20260926/PASSMARKS.md unchanged (F1-F5 with L in place of A; seeds 10 and 11; TEST 3590;
INCONCLUSIVE if L0 < 10, which the new frame re-measures). If it runs, it is compared with dl-6 as a report-only row.
