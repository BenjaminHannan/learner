# MARKS-agent-v1 addendum 2 (2026-11-04 22:25, before any v1 result)

**1. Brain guard on the M1 from 22:19:19.**
- At the lead's request, the M3 brain fix was installed on the M1 (glim_mlx_server_guard.py + watchdog.sh + serve.sh).
- Prompts over 4,096 tokens are now served alone. Most bench requests are 8–10k tokens.
- Speed per request changes slightly (about +6% on the M3 A/B). Waits are longer only while another client is sending at the same time.
- Baseline runs 1–3 ran before the switch; every version run comes after it.
- **Drift check (like with like):** one extra baseline run after the switch (`base-g`, code src-base, no kit). The comparison for a version is reported two ways:
  (a) the registered one, against the baseline mean of 11.0;
  (b) against base-g as well.
- The verdict stays rule (a), as registered. If base-g lands outside the baseline range (8–13), the verdict is flagged as unsafe in the report.

**2. Other traffic on the gateway (contamination).**
- Ben's installed Glim app is open on the M1 with always-on on (lead ruling: it stays on). It calls the model outside realmodel.lock.
- From 22:05, gateway.log is archived continuously (/tmp/aon/agentbench/gw-archive.log).
- A task is **contaminated** if a request from the app (tools=6410 chars in the gateway's size line) finished between the task's first and last request.
- Contaminated tasks are re-run once at the end of their version, and the re-run replaces them. If the re-run is contaminated too, it is kept but marked.
- Before the archive existed: baseline run 3 had app traffic during runclub_backout, bank_code and pizza_search (21:34–21:48; all three timed out). The app was open from ~20:58, so the earlier run-3 tasks may also have overlapped it, but that can't be checked (the log was reset at each gateway restart).
- Runs 1–2: unknown. The baseline is kept as registered and these limits are stated.

**3. Aux bench note.** The per-task JSON in an aux arm directory is overwritten each run; summary.jsonl keeps every run.
