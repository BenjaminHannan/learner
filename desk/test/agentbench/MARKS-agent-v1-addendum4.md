# MARKS-agent-v1 addendum 4 (2026-11-05 16:50, after the 14:37 reboot; no v1 result yet)

**1. Reboot.** The M1 rebooted at ~14:37 and wiped /tmp, which held every bench result.
- The baseline's printed table is kept in ~/learner-ops/aon-notes/agent1-20261104/BASELINE.md: 12/12/8, mean 10.67 under the capped-fails rule.
- The bench now lives in ~/learner-ops/agentbench-agent1 and its scripts in ~/learner-ops/aon-notes/agent1-20261104/tools.
- v1 restarts from run 1.

**2. Contamination, made workable.** Ben's always-on app sends small background calls without pause: system 373 / 1110 chars, about 1–2k chars each, several a minute. With addendum 3's gate, every task waited its full 30 min.
- Now only **big** foreign requests (> 8,000 chars before prepare: Ben's chat steps) gate a task and count as `foreign` (contaminated → re-run once).
- Small ones are counted as `smallForeign` and are part of every condition.
- The like-for-like control is the post-switch baseline run `base-g`, interleaved with the v1 runs, and reported next to the registered comparison (rule (a) of addendum 2 still decides).
