# MARKS-agent-v1 addendum (2026-11-04, 18:20, written before the restarted baseline)

The first baseline run was stopped after 11 of 20 tasks. Its results were discarded (kept in /tmp/aon/agentbench/discarded-base-r1-nosafety; not scored).

Why: the bench left out the app's safety levels (track I5, `src/safety-levels.js`). The real app gates these clicks with an approval card: "Place order and pay" (buy), "Send message" (send), "Submit form" (post). The real app's main.js passes `safety: glimSafety()` to every Agent; the bench now does the same (default levels, fresh dir). Ben's tap is scripted:
- every approval is answered "once" (yes);
- `shop_buy_ask`, where Ben says no, is answered "deny";
- an approval counts as asking Ben (`tr.asks`).

Nothing else changed:
- MARKS-agent-v1.md is unchanged;
- the pass marks, tasks, scorers, caps and settings are unchanged.

The bench also gained `--kit` (settings.agentKit). It is empty for the baseline.
