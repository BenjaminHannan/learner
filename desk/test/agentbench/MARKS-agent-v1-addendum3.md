# MARKS-agent-v1 addendum 3 (2026-11-04 22:50, during v1 run 1)

**1. Correction to addendum 2's contamination rule.**
- `tools=6410` in the gateway's size line is the bench itself (the gateway measures the tool list differently from run.js).
- The bench's own requests are the ones with system = 2747 chars (1978 with diet), plus the 1-token ready probe. **Any other request is foreign** (Ben's Glim app: system 3000 for chat steps, 373/629 for small background calls).
- Baseline run 3: app requests (system 3000) are seen at 21:48, during pizza_search. The rest of 21:30–21:50 can't be re-checked: that log was overwritten at the 22:00 gateway restart. Runs 1–2: unknown. The baseline stays as registered, with these limits stated.

**2. Quiet gate and per-task tag (bench harness only, from v1 run 1 wave 2 on).**
- Before each task, run.js waits until no foreign request has appeared for 180 s (at most 30 min; the lock is refreshed while it waits).
- It records `foreign` (foreign requests during the task), `quietWaitS` and `quietOk`.
- A task with `foreign > 0` is contaminated. It is re-run once at the end of its version; the re-run replaces it (report.js keeps the later row).
- v1 run 1 wave 1 ran before the gate. Its tasks are tagged after the fact from the gateway log (tagcont.js).

**3. report.js fix (7551dfda9).** A task that hits the 240 s cap now counts as failed, as this file always said. Baseline run 1 had one capped task the scorer passed (shop_buy_ask). The baseline is therefore 12, 12, 8 → mean **10.67** (not 11.0). A version needs a mean ≥ 12.67.
