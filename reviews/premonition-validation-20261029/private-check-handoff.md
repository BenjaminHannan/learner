# Private candidate process controller — 2026-10-29

## Implemented and shown

`desk/src/private-check.js` owns a dedicated temporary llama-server and an HTTP-only Python grader. It has no ordinary gateway hookup, port reclaim, automatic model restart or fallback to a public server. `getPrivateCheck(root)` supplies the same controller to Builtin and WinSleep.

`check({exe, model, adapter, cards, python, sleepmlxParent, expectedAdapterSha256, expectedHeldSha256, flavor, signal})` copies the candidate and its held-card snapshot into a protected job directory, checks their hashes, starts the private engine with a random loopback port, unique alias and private key, and waits for authenticated `/v1/models` to advertise exactly that alias. The grader is spawned with the private key/alias in its environment and a unique command marker. A verdict leaves the controller only after both grader and engine have exited; cancellation and input mutation are checked again after shutdown. Input hashes and the model file fingerprint are rechecked before returning a result. Successful cleanup removes the copies and journal.

- A complete check returns the grader verdict plus `processStopped: true` and a controller-issued v4 `checkId`.
- Interrupted/timed-out/inconclusive checks return `ok: null`; `processStopped: true` is still possible when shutdown succeeds.
- Unconfirmed shutdown overrides any pass with `ok: null, processStopped: false, blocked: true` and a structured reason.
- `ensureIdle()` / `cancel()` return `{ok: true, processStopped: true}` only after confirmed cleanup; otherwise they return `{ok: false, processStopped: false, blocked: true, error}`.

The durable intent is `root/sleep/private-check-jobs/owned.json`. It is written before each spawn, including the random job markers, executable and model identity; PID and OS creation time are then added. Restart recovery can discover a child that existed before PID publication. An explicit creation-time mismatch proves that the old PID owner exited, so the new owner is never signalled. Unknown/partial inspection, ambiguous discovery, invalid journal or failed termination remain blocked with their journal intact. Windows uses a protected current-user-only ACL for the private folder and inherited journal/copies.

Recovered Windows termination opens a process handle, verifies its creation time, executable and exact unique markers while that handle remains open, then terminates and waits on the same handle. It does not run PID-only taskkill. Windows retains the process object/PID while a handle is open; this avoids the check-PID/kill-reused-PID race. Sources: [Microsoft process handles](https://learn.microsoft.com/en-us/windows/desktop/procthread/process-handles-and-identifiers), [Microsoft explanation of PID reuse](https://devblogs.microsoft.com/oldnewthing/20110107-00/?p=11803), [OpenProcess](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocess).

Node's private readiness HTTP uses core `http`, bypasses environment proxies and never follows redirects. Python `sleepmlx/served.py` now centralizes HTTP authentication for health, models, chat and adapter-control routes, verifies the alias before answering, bypasses private proxies, refuses redirects and never retries anonymously. The existing `served-check --server ... --cards ...` CLI remains HTTP-only; its private path imports no Torch or model backend.

## Tests and evidence

- `desk/test/private-check.test.js` covers real lifetime contracts with fake children: pass only after both exits, cancellation during startup/grading/shutdown, late health, timeout, ignored TERM/KILL, model crash, grader failure, source/snapshot mutations including shutdown, fresh copies on retry, restart recovery, pre-PID intent discovery, PID reuse, unknown/partial/hung inspection, malformed journal, no port reclaim, key redaction and private HTTP redirect/proxy behavior.
- The latest combined controller/candidate/runtime run passed **80 tests** in 2.454 seconds.
- `sleepmlx/tests/test_served_private.py` plus existing `test_sleepcheck.py` passed **22 tests** in 2.001 seconds. Tests cover all HTTP routes' auth, wrong key/alias, partial credentials, nonloopback endpoints, proxy bypass, redirect refusal and HTTP-only CLI behavior.
- An actual **no-model Windows smoke** passed on benspc using only an owned sleeping Python 3.10 child. It verified native helper compilation, current-user-only directory and journal ACLs, PID/executable/birth inspection, refusal to kill on wrong birth or marker, discovery after simulated pre-PID crash, and confirmed owned-child exit. No existing process was killed and no ML library/GPU was used. Audit: `private-process-windows-smoke.json`; reproducible runner: `private-process-smoke.cjs`.

Windows smoke directory: `C:/Users/benja/learner-ops/premonition-private-check-20261029/5282352c-56f5-40a4-af91-4735d59adfe7`. The audit records the exact module SHA256 used for its native ownership/ACL checks. Later changes added bounded probe calls, streaming hashes and a phantom-active-job recovery fix, with focused regressions; the Windows native helper itself was unchanged. Private keys/command lines are not included in the audit.

## Integration owned by Terra

Terra owns `sleep-candidates.js`, WinSleep and Builtin integration. Current draft calls the shared idle gate before public start/resume and training, uses private checking instead of `resumeModel(candidate)`, and requires `processStopped === true` plus a v4 `checkId` for accepted/recovered manifests. Unbound legacy adapters are quarantined. I reviewed those hooks without finding an additional material issue; Terra's latest focused candidate suite passed 14 tests.

## Limits and pending work

The coordinated actual private-engine/real HTTP grader smoke has now passed with Root's synthetic zero-LoRA fixture: see `private-real-smoke.md` and `private-real-smoke.json`. Both real children exited, the idle gate confirmed cleanup, public LFM3 service was restored, and the production diary snapshot was unchanged. The zero-LoRA retention grade proves plumbing, not learning quality.

Automatic recovered-orphan termination is implemented for **Windows**. On other platforms, direct owned child shutdown works, but recovery without a live Node child handle fails closed unless an atomic platform-specific process provider is supplied. Unknown Windows inspection also stays blocked rather than guessing. This can require an explicit later recovery attempt or manual owned-process diagnosis.

The journal is private state, not an untrusted-input privilege boundary against the same logged-in user. It is schema checked and protected; arbitrary local administrator or same-user tampering is outside the ownership guarantee. No user diary, adapters, settings or production model service were modified by this subtask. No commit, push or deployment was performed.
