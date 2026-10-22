Premonition experiment recovery runbook

Version 1.1   |   1 October 2026   |   Consult at task start and every blocker

Solve routine failures within existing authority, preserve progress, and keep useful work moving while Ben is asleep. At task start and every blocker, record this guide’s version, the applicable rule, action and evidence. This guide grants no new permission.

1 Know which kind of limit applies

Explicit user limits. Keep the overall 100 GB storage limit, no current cloud spend, and the agreed architecture, data and held-out-test restrictions. Check the current instructions before each run.

Agent planning caps. Fit budgets, output allowances and forecasts created by the agent are planning choices. Record their source and reserve recovery space inside the authorized resources. Revise an estimate when evidence changes; never describe it as Ben’s restriction.

Safety and approval boundaries. Actual resource permissions, privacy and spending boundaries, and explicit denials still apply. A denied expansion stays pending until approved. Renaming a run, changing tools, or calling a cap an estimate cannot bypass a denial.

2 Prepare before a run starts

Check state. Confirm objective, success and stop criteria, active job state and last durable checkpoint. Avoid duplicate runs. Record code version, configuration, provenance and seeds.

Leave recovery headroom. Estimate peak storage including checkpoints, temporary files, receipts, logs and replacement overlap. Reserve time for checkpointing, justified repair and validation within authorized resources. A proposed reserve authorizes no increase.

Protect progress. Verify checkpoint and receipt writing on the actual platform. Save expensive progress at recoverable boundaries. Retain the last good checkpoint until its replacement is verified.

Prepare the next branches. Before the active run ends, prepare success and failure branches: validate and continue the next authorized step, or preserve state and repair. Identify independent useful work if blocked.

Overnight readiness check. Before saying “I have everything I need,” verify resources, permissions, recovery headroom, checkpoints and feasible completion of the whole plan. Launching alone is insufficient. Surface unresolved dependencies before bedtime; do not promise readiness while they remain.

Readiness incident. Ben reports that a storage question arrived at 2 AM after his before-bed check about whether anything was needed. Prevention: complete the readiness check above before giving overnight assurance.

3 Use this decision path at every blocker

A  Preserve and classify. Capture the exact error, failing operation, run ID, paths, timestamps, logs, checkpoint and resource totals. Separate observed facts from hypotheses. Do not overwrite the only evidence.

B  Diagnose narrowly. For a known transient fault, use a bounded retry of the failed operation. For an unknown fault, choose the smallest test that distinguishes plausible causes. Do not repeat a full fit or run arbitrary marginal tests just to stay busy.

C  Act or isolate. If a remedy is authorized and fits remaining resources, test it, apply it and verify recovery. If only an agent estimate is wrong, re-plan within actual authority. If a real permission or irreplaceable input is missing, pause that branch and continue independent authorized work.

Communication incident on 1 October 2026. During voice coordination, ‘No one yet’ was stated without checking while this document was in progress. Ben challenged it; saving was confirmed at 11:24 UTC and delivery at 11:24:53 UTC. Prevention: distinguish requested, in progress, confirmed saved and verified integration. Report the latest confirmed state with its timestamp. A missing completion notice does not mean nonexistence. Say ‘checking’ only when actually checking.

4 Recover from the known Windows failures

Incident record. Two receipt failures lost experiment progress. Treat receipt persistence as part of the recovery path, not as proof that the model computation failed.

WinError 2 during the storage scan. An atomic temporary file vanished while storage was being scanned. Recheck or tolerate only the expected transient disappearance of that owned temporary file. Do not suppress missing checkpoints, corrupt data or persistent directory errors. Keep storage accounting conservative.

WinError 5 replacing the receipt. Receipt replacement returned access denied. A transient file lock is a hypothesis, not a proven cause. Preserve the completed output and last valid receipt; retry only the replacement with bounded backoff. Persistent denial needs diagnosis, not permission changes or deletion of evidence.

Tested repair. The repair passed 33 tests and a real Windows probe. This validates those checks; it does not prove that an interrupted full experiment finished or produced a scientific gain. Verify the recovered run and its artifacts separately.

Sources: repair commit b0f4446 https://github.com/BenjaminHannan/learner/commit/b0f444660912acdc4e07f3a0ad791201a644d7fc and Premonition PR 17 https://github.com/BenjaminHannan/learner/pull/17

5 Make retries bounded and reproducible

Before retrying, set a maximum attempt count and elapsed-time bound from the resources still authorized. Use a deterministic backoff schedule; log every attempt. Stop early if evidence shows a persistent permission, integrity or capacity problem. A retry bound never authorizes a budget increase.

Retry the same idempotent write or replacement without changing experiment inputs. Retry delays, temporary names and receipt handling must not consume the model or data-loader RNG. Verify that a retry leaves seeds, RNG state, sampling order and results unchanged. Resume computation only from a validated checkpoint.

Record three separate lines: hypothesis and its discriminating check; tested repair and validation evidence; recovered experiment result or what remains unverified. Preserve the original failure alongside the successful repair.

6 Recheck the current approval status

As of 1 October 2026, the agent-created 9,600-second fit budget and 1,140,850,688-byte output allowance lacked recovery space. The requested additional 20 minutes and 192 MiB were denied and remain pending approval. Do not spend that expansion or quietly obtain it through another route. Recheck the latest decision before acting; this dated status is not a permanent new user limit.

7 Close the loop without an unnecessary wakeup

If recovery succeeds, validate the durable output and continue the prepared authorized branch. If blocked, preserve a resumable state and progress independent work such as inspecting existing logs, validating saved artifacts, or preparing the next already-authorized comparison. Do not create unrelated work.

Ask only when permission or irreplaceable input is truly required. Give the blocker, what was preserved, and one exact question. Queue a non-urgent question for when Ben is awake. Example: “The repair is validated, but the extra 20 minutes and 192 MiB remain blocked. May I use that expansion for the recovery run?”

Update the living incident log instead of repeating “sorry, that’s my bad.” Record the actual failure, correction, prevention check, evidence and current state. Label hypotheses, tested repairs and results separately; do not invent a mistake. Consult the updated guide at the next start or blocker. A version acknowledgment alone does not establish understanding.
