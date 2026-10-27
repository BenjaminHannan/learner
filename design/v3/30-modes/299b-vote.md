# 299b: think five times, then vote (the one follow-up to rsn-299)

rsn-299 (the 1B writes its steps and an exact calculator fills every "=") is a registered FAIL: +4 over the plain 1B on its blind panel against a bar of +12. The calculator removed arithmetic errors (0), but 24 misses came from setting the problem up wrong, and neither arm ever said "not sure".

One change: run the calculator arm 5 times with sampling and take a majority vote on the final answer. An answer needs 3 of 5 votes. Otherwise Premonition says "I'm not sure", because its own worked answers disagree. The idea is that setup mistakes are often random, so the right setup may win the vote, and when it doesn't, disagreement is an honest signal of doubt.

- Runner: scripts/claude_rsn299b_run.py (arms P and V; the scorer is 299's, unchanged).
- Agent layer: scripts/claude_think299b_agent.py, install_think299b(loop, model). It uses 299's router, read-only check and fallback.
- Fresh blind panel: artifacts/claude-thinkpanel299b-20260924 (60 items, blind Opus audit 0/60 mismatches).
- Pass marks: artifacts/claude-rsn299b-20260924/PASSMARKS.md (bar +12, 0 arithmetic errors, wrong must not rise).
- Registered run: handoff/queue/rsn-299b-panel.md on BensPC, daytime.
