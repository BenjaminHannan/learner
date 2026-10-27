# 31 — Modes: audit + integrated design (Fable review, 21 Sep 2026)

Status: DESIGNED only. Nothing here is built or tested. Inputs read: `shared-brief.md`, `decided-inputs-fable.md`, the three GPT xhigh mode designs. Decided inputs are treated as fixed.

---

## PART A — Audit

### A1. WORKING (gpt-xhigh-working-mode.md)
**Sound:** scope → act → verify; `call_id` echo with rejection of unknown IDs; tool safety classes; no `GIVE_UP`; read-back beats "write returned OK"; transition authority stays plain code.
**Wrong / weak:**
- `WAITING_FOR_BEN` and `wait_for_ben(reason)` contradict the decided "no WAITING mode". Budget exhausted → `WAITING_FOR_BEN` "or a scheduler decision" is vague and clashes with the decided rest behaviour.
- Attributes ability to a model that does not exist: "normalize the request" and failure check #1 ("map every clause to a checklist item") assume something can read job English. The parser covers facts/queries only. v1 jobs must come from fixed structured job templates; scoping is hand-written, so the "key discipline" is NOT tested by its own suite.
- Per-job "GPU time" counter: unenforceable if self-reported, meaningless in v1 (plain code uses no GPU).
- "Two materially different retries" is undefined. Define: distinct normalised `(tool, args-signature)`.
- Tool discoveries → `proposed` rows clashes with CREATIVE ("tool observations remain tool evidence").
- Test: golden transcripts against a same-author scripted oracle is a conformance test, not competence. Baseline ("first schema-compatible tool") is a strawman. Needed: an ablation (same executor minus acceptance checks) that must produce false `JOB_DONE`s, or the suite proves nothing.
**Cut:** learned-scoping talk; per-job GPU counters; `proposed` rows from raw tool output.

### A2. CREATIVE (gpt-xhigh-creative-mode.md)
**Sound:** frozen success conditions; every lead needs a falsifiable check; `REJECTED` vs `BLOCKED`; enumeration before any dreamer; equal-budget comparison; "does not prove creativity".
**Wrong / weak:**
- Entry on `MISSING_FACT` is unsafe: a missing personal fact is a question for Ben, not a search problem; searching invites guessed facts.
- `append_inferred(row, deps)` lets the proposing mode also commit — a gameable checker. Only the checker may commit.
- Step 9 "adversarial sanity check" is the same checker run twice, not independent. Keep one rule: the checker sees only structured claim + dependency IDs, never wording.
- "Cheap lookups do not consume the same budget": unenforceable loophole.
- `charge_compute` / `charge_search` are self-reported = unenforceable. `handoff(job_id, target_mode, payload)` lets a mode command a transition; clashes with WORKING ("transition authority stays plain code").
- Rank term "would materially advance the job" is unmeasurable.
- "SLEEP may enter after the job reaches a safe boundary" contradicts "assigned job pre-empts sleep".
- "BORED may submit a practice problem": BORED's design never does; a second entry path.
- Test: with 4–12 branches and budget 8, fixed-order enumeration solves most jobs by construction; 48/60 mostly measures the suite author. Missing the strongest cheap baseline: cheapest-check-first.
**Cut:** step 9, the free-lookup exemption, `handoff`, `charge_*`, direct `append_inferred`.

### A3. BORED (gpt-xhigh-bored-mode.md)
**Sound:** every activity must cite a `gap_id` or `skill_key`; one bounded activity per loop; quarantine evidence fields; fixed-size digest; pre-emption tested per activity type; v1 enumerator not neural dreamer.
**Wrong / weak:**
- **Practice is vacuous in v1.** With no learned component in the loop nothing can improve; "learning progress" over a deterministic executor is noise.
- `claim_extracted` from web pages assumes a reader that does not exist (harness/model confusion). v1 stores the quoted span; Ben reads it.
- Score "expected future usefulness × severity × recency": first term unmeasurable. Use counts.
- `notebook.append_event(event)` is a generic write that bypasses tag permissions. `scheduler.request_mode(...)` clashes as above.
- Writes `inferred` only "when an approved rule proves them"; CREATIVE writes `inferred` for any dependency-backed deduction: two definitions of one tag.
- Sleep failure path missing: failed sleep → BORED → pressure still high → sleep again, forever.
- Test: uniform-random baseline (25%) against a 90% pass mark is far too weak; labels and rules share an author. "10/10 injections ignored" is vacuous for plain code with no instruction channel; it supports no claim about a future learned reader.
**Cut:** practice (v1), `claim_extracted`, `publisher`, `append_event`, `request_mode`.

### A4. Cross-design clashes (exact names)
Order: WORKING / CREATIVE / BORED.
- Resolve: `resolve` / `resolve_entity` / `current_view()`.
- Lookup: `query`, `execute` / `lookup`, `execute_chain` / none.
- Proposed write: `propose(row, deps)` / `append_proposed(row)` / `append_event(event)`.
- Conflicts: none / `get_conflicts(entity, relation)` / `find_conflicts(candidate)`.
- Job and budget: `current_job`, `remaining_budget` / `get_active_job`, `get_budgets` / `budget.remaining(kind)`.
- Mode change: `request_mode(CREATIVE, packet)` / `handoff(...)` / `scheduler.request_mode(str)`.
- Pre-emption: none / `preemption_pending()` / `has_ready_job()` + cancel flag.
- Gaps: BORED requires `report_gap` from both; neither emits it.
- None knows LISTENING exists: all say "job pre-empts", none says what pre-empts a job.

---

## PART B — Integrated design

### B1. State machine (v1 = plain rules, owned by the scheduler only)
Modes never switch themselves. A mode returns an **exit event**; the scheduler picks the next state.

**Priority (highest first):** LISTENING > WORKING/CREATIVE (one job, two phases) > SLEEP > BORED.active > BORED.rest.
`rest` is a sub-state of BORED, not a sixth mode: no spending, one diary line on entry ("idle budget spent: <kind>; resting until <refill time>"), wakes on inbox, refill tick, or Ben's answer.

| # | From → To | Trigger | Guard | In-flight state |
|---|---|---|---|---|
| T1 | any → LISTENING | inbox non-empty | next step boundary (step deadline ≤ 10 s; an irreversible call is never cut mid-flight) | WORKING/CREATIVE: write park record. BORED: cancel activity, discard uncommitted, log. SLEEP: set abort flag (see T7). |
| T2 | LISTENING → next | inbox empty, reply sent, writes validated | — | scheduler re-evaluates priorities |
| T3 | → WORKING | runnable job (queued, or parked and its question answered / budget refilled) | job budget > 0 | resume from park record; if `notebook_version` changed, re-validate dependencies and re-run affected acceptance checks |
| T4 | WORKING → CREATIVE | job flagged `open_ended` at scoping; OR one checklist item failed 2 attempts with distinct signatures; OR `BROKEN_CHAIN` with all entities known | creative budget > 0; objective frozen | same job record |
| T5 | CREATIVE → WORKING | a lead `SURVIVED` | — | route appended to checklist |
| T6 | WORKING/CREATIVE → park | `MISSING_FACT`, `AMBIGUOUS_REFERENCE`, `UNKNOWN_ENTITY`, approval needed, leads exhausted, or job budget spent | — | pending-question record; job `PARKED`; `report_gap`; next job or fall through |
| T7 | → SLEEP | no runnable job, inbox empty, pressure ≥ threshold or body-clock window | sleep reserve > 0; sleep not faulted | sleep runs in chunks ≤ 60 s, each its own transaction on staged events. Commit only if `live_version == snapshot_version` AND wake-up check (told-ledger) passes; else discard staging = rollback. Abort flag → rollback unless already in atomic commit. |
| T8 | SLEEP → next | chunk committed or rolled back | 2 consecutive check-failure rollbacks → `sleep_faulted`, `SLEEP_FAULT` question to Ben, no retry until he answers | — |
| T9 | → BORED.active | nothing above applies | idle budget > 0 and an eligible gap exists | — |
| T10 | → BORED.rest | idle budget spent or no eligible activity | — | — |

No sleep while a runnable assigned job exists (ruling; starvation risk noted in B6). LISTENING is metered but never blocked by budget. Job assignment, answers, approvals and cancellations all enter through LISTENING (one door).

**Could become learned later:** T4 stall detection, sleep threshold, BORED activity choice, effort. Evidence required: ≥ 50 logged held-out episodes where the rule was demonstrably wrong, and a learned replacement that beats the rule at equal budget with zero safety regressions. **Never learned:** priority order, pre-emption, permissions, budgets.

### B2. Shared interface

**Notebook row (event; append-only):**
```
row_id        monotonic, immutable
entity_id     stable; aliases are rows (relation=alias)
relation, value, value_type
tag           taught | proposed | inferred | web-quarantine | sleep-derived
supersedes    row_id | null
deps[]        row_ids / evidence_ids  (mandatory for inferred, sleep-derived)
evidence_id   -> evidence store
written_by    mode + job_id | activity_id | sleep_id
t_written
status        derived in the view (ACTIVE | SUPERSEDED | STALE | REJECTED | PENDING_APPROVAL); changes are events
```
**Evidence store (immutable):** `evidence_id, kind (utterance | tool_result | web_capture), payload, hash, t`. Web captures hold `url, query, retrieved_at, quoted_span, gap_id` — not the row.

**Tag meanings (one each):** `taught` = Ben asserted or approved it (promotion = LISTENING writes a new `taught` row whose deps point at the approved row). `inferred` = a fact instance from applying a Ben-approved rule to `taught`/`inferred` rows, committed by the checker only. Plain chain answers are NOT stored (the executor recomputes them exactly; caching only adds staleness). `proposed` = anything awaiting Ben: candidate facts, candidate rules (`relation=rule`), alias merges. `sleep-derived` = NREM maintenance events (stale marks, conflict flags, dedupe links), never new facts. Answers use `taught` + `inferred` only. No written source policy exists yet, so all promotion is by Ben.
*Link to the decided REM rule:* "verified" is read as exact derivation → `inferred`; a rule merely consistent with examples is `proposed`. Ben to confirm this reading.

**Records:**
- **Job:** `job_id, request_evidence_id, objective (frozen), constraints, checklist[{step_id, action, acceptance_check, status, attempts[]}], open_ended, risk_class, status (QUEUED | RUNNING | PARKED | DONE | CANCELLED-by-Ben-only), park{reason, question_id, step_id, notebook_version}, budget, spent`.
- **Lead:** `lead_id, owner (job_id | activity_id | sleep_id), claim (structured), deps_required[], check, signature, status (UNTESTED | REJECTED | SURVIVED | BLOCKED), evidence_ids[], reason`. Failed leads are never deleted.
- **Gap:** `gap_id, origin (job_id + step_id | lead_id), executor_status, query, entity_ids, relation, blocked_jobs_count, attempts, last_attempt, state (OPEN | ASKED | QUARANTINED_ANSWER | CLOSED)`. Closes only when re-running `query` returns `OK` (= "curiosity rewarded only on confirmation", checked mechanically).
- **Pending question:** `question_id, owner, kind (CLARIFY | APPROVE_ACTION | APPROVE_PROMOTION | MERGE_PROPOSAL | BUDGET | SLEEP_FAULT), text (template), options[], asked_at, answered_at, answer_evidence_id`.

**Diary:** JSONL, `t, mode, event, ids, cost, outcome`. **Digest** = template over the diary, ≤ 12 lines, every line carries IDs: (1) questions blocking jobs, max 3; (2) approvals waiting, count + top 3; (3) jobs done / parked; (4) BORED, ≤ 3 lines; (5) sleep: committed / rolled back; (6) budget spent / left; (7) faults.

**Budget ledger:** `t, mode, owner_id, kind (gpu_s | web_search | wall_s | tool_call), amount, balance`. Daily envelopes: jobs, idle, sleep reserve. **Metered by gateway and scheduler, never self-reported:** the web tool returns `DENIED` at balance 0; GPU work runs only in a scheduler-owned runner with a hard timeout (hence resumable); a watchdog enforces wall-clock. v1 is plain code, so `gpu_s` reads ~0 until a learned part is in the loop.

**Permissions (enforced by a capability token the scheduler issues per mode; `write` rejects other tags):**
| Mode | taught | proposed | inferred | web-quarantine | sleep-derived | Tools | Other |
|---|---|---|---|---|---|---|---|
| LISTENING | YES (only) | – | – | – | – | none | create/cancel job, answer question |
| WORKING | – | yes | via checker | yes | – | all classes; outward/irreversible needs `APPROVE_ACTION` | `report_gap`, `ask` |
| CREATIVE | – | yes | via checker | yes | – | stub + read-only only | `report_gap`, `ask` |
| BORED | – | yes | via checker | yes | – | web search only | `ask` (digest only) |
| SLEEP | – | yes (merges, rules) | via checker (REM) | – | yes | none | `commit_staged` |

**Calls (one spelling each):** notebook `resolve, lookup, execute → {status, result, deps}, validate_deps, conflicts, write(row, cap), version, snapshot, commit_staged`; checker `check(claim, deps) → PASS | FAIL | BLOCKED, commit_inferred, test_rule`; scheduler `active_job, budget(scope), should_yield, exit(event, payload), report_gap, ask`; tools `describe_tools, call(call_id, tool, args)`.

### B3. Shared components (build once)
1. Notebook + executor + evidence store. 2. Scheduler + ledger + watchdog + park/resume. 3. Tool gateway (`call_id`, classes, metering). 4. **Lead engine**: proposer → signature dedupe → cost rank → checker → lead log. Proposer is pluggable (v1 enumeration). CREATIVE, BORED rule-search and REM differ only in candidate space, budget, and owner ID. 5. One gap list. 6. One question queue + diary + digest.

### B4. Resolved conflicts
1. `WAITING_FOR_BEN` vs no WAITING mode → **park + pending question** (decided input wins).
2. Who switches modes → **scheduler only; modes call `exit(event)`** (one authority is testable).
3. Self-charged budgets → **gateway meters** (self-report is unenforceable).
4. Tool output as `proposed` vs evidence → **evidence record; `proposed` only for a fact candidate Ben could confirm**.
5. Two meanings of `inferred` → **approved-rule application, checker-committed only** (stops gaming and stale caches).
6. CREATIVE entry on `MISSING_FACT` → **park and ask** (no guessing personal facts).
7. BORED → CREATIVE path → **cut; BORED calls the lead engine directly** (CREATIVE = assigned jobs only).
8. Sleep during an open job → **no** (decided pre-emption rule).
9. Practice in v1 → **deferred** (nothing learnable in the loop).
10. CREATIVE write tools → **none; writes belong to WORKING's checklist** (keeps search side-effect-free).
11. Free notebook lookups → **metered with a per-job cap**.
12. Web claim extraction → **quoted span only** until a reader exists.

### B5. Build order
Every suite: seeded generator frozen before the code under test; pass marks below are fixed now; all run < 30 min on the Mac CPU; no neural training anywhere in M1–M7. "Baseline" for a conformance suite means a naive implementation that **must fail**, proving the suite discriminates.

| M | Built (all plain code) | First test and pass mark | Claim supported? |
|---|---|---|---|
| **M1** Notebook contract + LISTENING, template replies | log, view, executor statuses, capability-gated writes, evidence store, LISTENING loop. Tier a: structured events injected. Tier b: English via the existing parser, scored separately. | 120 scripted multi-turn cases: teach, correct, all 6 statuses, two Miras, quotes / hypotheticals / reported speech, crash between ack and durable write, restart. Pass: 0 `taught` rows from non-assertions, 0 "saved" without a durable row, 0 merges, told-ledger 100% after restart, ≥ 118/120 statuses. Baseline: last-write-wins dict must fail ≥ 30. Tier b: ≥ 90% exact parse on 200 held-out sentences, 0 wrong `taught` writes; misses reply "not understood". | Yes: contract holds on the suite. No: broad English; learning. |
| **M2** Scheduler, ledger, diary/digest, park/resume | B1 on a fake clock, stub modes | 200 seeded random schedules with crashes. Pass: 0 violations of {one state, LISTENING within one boundary, no spend at balance 0, parked job resumes at same step, restart reproduces state}. Baseline: FIFO loop without pre-emption must violate. | Yes: control logic conforms in simulation. No: usefulness. |
| **M3** WORKING + tool gateway | checklist executor, `call_id`, gap reporting, stub/read-only tools, 6 fixed job templates | 40 multi-turn transcripts with lying tools, wrong IDs, `DENIED`. Pass: 0 false `DONE`, 0 unauthorised writes, 0 bad IDs accepted, ≥ 38/40 terminal states. Baseline: same executor minus acceptance checks must give ≥ 5 false `DONE`. | Yes: harness protocol. No: any model ability (none in the loop); scoping. |
| **M4** Lead engine + CREATIVE | enumeration proposer, cost rank | 60 jobs, 4–24 branches, budget 8. Pass: 0 unsupported commits, ≥ 9/10 impossible jobs reported unresolved, budget never exceeded. Ranker kept only if it beats cheapest-first by ≥ 5 solved; else ship cheapest-first. | Yes: bounded safe search. No: creativity. |
| **M5** BORED | triage, ask-later, fixture web, rule enumeration (reuses M4) | 60 idle situations. Pass: 0 trusted web writes, 10/10 pre-emptions before a second costly op, every activity has `gap_id`, retry cap held, gaps close only on `OK`. Baseline: one-line status→action map; richer rules kept only if they beat it. | Yes: safe idle behaviour. No: injection resistance of a learned reader; self-improvement. |
| **M6** SLEEP | NREM chunks as transactions, then REM via lead engine | 50 notebooks with planted duplicates / stale rows / conflicts + fault injection. Pass: told-ledger 100%, all faults rolled back, planted-issue recall ≥ 90%, 0 automatic merges. Baseline: same housekeeping awake, in place. | Yes: sleep is safe. No: sleep helps. |
| **M7** Windows soak | native Python port | 30 simulated days, 20 process kills, Mac seeds. Pass: logs identical to Mac, 0 invariant violations, digests ≤ 12 lines. | Yes: resumable on the home PC. No: long-run value. |

### B6. Top 8 risks and cheapest detection
1. **Wrong `taught` write** (quote, hypothetical, negation misparsed). Test: non-assertion suite, 0 wrong writes; every reply echoes what was saved.
2. **Trust laundering** (quarantine/proposed leaks into answers; injection once a learned reader exists). Test: invariant that every answer's deps ground in `taught`; re-run hostile fixtures on any change to the web path.
3. **Harness credit given to the model.** Test: every report states how many learned parts were in the loop; remove the model — if the score is unchanged, claim nothing about it.
4. **Checker gaming / consistency mistaken for truth.** Test: planted false-but-consistent rules; count reaching `inferred` must be 0.
5. **Budget leak.** Test: spend attempts at balance 0 are `DENIED`; ledger total within 5% of OS-measured process time.
6. **Pre-emption / resume corruption.** Test: M2 fault schedules, including Ben teaching a fact mid-job.
7. **Sleep damage or sleep-fail loop; sleep starved by a long job.** Test: M6 fault injection; consecutive-rollback counter; log pressure at job end.
8. **Ben becomes the bottleneck** (questions pile up, parked jobs starve). Test: simulate Ben answering one question a day for 30 days; pending-question count and oldest age must stay bounded.

### B7. Summary for Ben (12 lines)
1. The assistant is always in one of five states: listening, working, creative, bored, or asleep.
2. You always win: when you type, it stops at the next safe point and listens.
3. Only listening can save something as "Ben told me this"; it says "saved" only after the save really happened.
4. A job blocked on you gets parked with a question at the top of your digest; it never gives up on its own.
5. If a job's path is unclear, it tries a few ideas, checks each one strictly, and keeps the failures on record.
6. When idle, it works only on gaps it actually hit during your jobs; web finds stay in quarantine until you approve.
7. One "guess then check" engine is shared by creative, bored and dreaming, so it is built once.
8. Sleep tidies the notebook on a copy, in small chunks; if any taught fact goes missing, the night is undone.
9. Budgets are enforced by the program around it, not by its own honesty; when spent, it rests and logs it.
10. One traffic controller decides the state using plain rules; nothing is learned there yet.
11. Build order: notebook + listening first, then the controller, working, creative, bored, sleep, then a run on your PC.
12. All of this is a design. Each step has a test with its pass mark fixed beforehand; nothing is proven yet.
