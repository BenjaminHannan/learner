Registered bm-390 run — checking seals, plans, and duplicate status before touching the GPU box.
No duplicate on the builder branch — now mapping the BensPC access path.
BensPC is reachable with GPU free — setting up the registered run.
Tree build is next — verifying the MiniLM snapshot layout first.
Tree archive is ready — creating the destination on BensPC.
Tree is in place — restoring the missing MiniLM router cache.
Router and reader verified — installing the missing data reader.
Setup complete — starting the sealed verification steps.
Both seals pass — generating the sleep base checkpoint.
Data fetch verified — downloading the two approved rival models.
Both rivals load — running smoke on fictional data.
Smoke hit a Windows log-write fault — inspecting the sealed code path.
Smoke output never materialized — confirming the failure point.
Plain-model smoke passes; the agent path fails — checking for stray processes before capturing the full error.
Full traceback captured — verifying what exists before writing the report.
Worktree lacks the results folder — creating it and writing the report.
Report is written — confirming it's staged as a new file.
Verdict: SMOKE-FAIL. bm-390 never started on real benchmark items. Nothing ran on the real data, nothing was trained, no code was edited.

Marks table (integer counts; registered bars from PASSMARKS.md):

| Mark | Bar | Result | Count |
|---|---|---|---|
| DUPLICATE check | run/ absent on origin/builder-outbox | not a duplicate, ran once | 0 prior runs |
| Seal bm390 (8 lines) | every line OK | 8 OK, 0 FAIL | 8/8 |
| Seal e2e336b (229 lines) | every line OK | 229 OK, 0 FAIL | 229/229 |
| Step 2 r44 base | JSON line + .pt | printed, sha256 recorded | 1 file, 2969 bytes |
| Step 3 fetch | locomo_qa 1986, mmlu 300, gsm8k 300 | exact match | 1986 / 300 / 300 |
| Rivals download | Q2 + L12 approved revs | both downloaded | 2/2 |
| Rivals load | each loads to cuda | Q2 1881825088 params, L12 1170340608 params | 2/2 RUN |
| Smoke P (agent) | exit 0, rows=5 | exit 1, 0 rows | FAIL |
| Smoke T (plain) | exit 0, rows=5 | exit 0, 5 rows | PASS |
| Smoke sleep log | 2 rows, both checkpoint_exists true | file never created, 0 rows | FAIL |
| M1 / M3 / M4 | registered marks | not measured (no real-data run) | n/a |
| run/*.jsonl rows | 1986 + 300 + 300 per arm | 0 files (run/ never created) | 0 |

Every move:
1. Fetched origin main + builder-outbox; confirmed no run/ on builder-outbox (not DUPLICATE). Read PASSMARKS.md and the bench plan via git show only.
2. Built tree (builder-outbox archive + main on top + self122_head.pt sha256 5ca02173… match), copied to NEW folder C:/Users/benja/lis301/work/bm390/tree on BensPC.
3. BensPC setup: READER safetensors sha256 b4fd93a2… match; BASE snapshot present; MiniLM was missing so copied the Mac's pinned snapshot (rev 1110a243…, 3 files, copy only, nothing moved/deleted), router check prints a route; pyarrow was missing so installed pyarrow 25.0.1 into the same venv (had to unset the machine's broken REQUESTS_CA_BUNDLE path). Nothing else installed or upgraded.
4. Step 1 seals ALL-OK. Step 2 r44 base JSON `{"stage": "base", "seed": 4102, "seconds": 12.9, ...}`, .pt sha256 4655b761… (2969 bytes), copied into the tree's runs folder. Step 3 fetch line verbatim with the counts above; Q2DIR and L12DIR downloaded; both load checks pass.
5. Smoke: T passes (`wrote locomo_T.jsonl rows=5 convs=1`, file verified 5 rows). P crashes on the first turn with `TurnLog323Corrupt: turnlog323: read-back mismatch` (full traceback in RESULTS-benspc.md). Ran P a second time only to capture the full console after confirming no python process remained; identical exit 1. No step-5 command ever launched.
6. run/ never existed on BensPC, so step 6 had nothing to copy and no size/sha256 check applied. Models and data left on BensPC.
7. Wrote new file artifacts/claude-bm390-20260925/RESULTS-benspc.md (counts only, full traceback, no question/answer/reply quoted).

Misses and deviations:
- Miss: smoke bar not met (P exit 1, sleep log 0 rows), so per spec the task stops with SMOKE-FAIL and no real-data commands run. M1, M3, M4 unmeasured.
- Deviation: P smoke launched twice (result run + log-capture re-run), not once; both exited 1 identically, and no registered arm was retried or duplicated. T smoke wall time not separately measured (only P's 8.2 s was).
- Diagnosis (no code touched): the sealed turn-log writer writes text-mode `"\n"` then reads back binary expecting `"\n"`; on Windows the write becomes `"\r\n"`, so every first agent turn fails. The plain path never uses that writer, which is why T passes. This same sealed file would hit any Windows agent run (including 336b's P/G arms) until the owning thread fixes it.
- Common-rules report: additive only (one new RESULTS file, nothing edited/deleted); fictional names only (smoke data as shipped); no TEST-ONLY panel ever opened, printed, or tuned on (benchmark files only row-counted; full file contents never displayed).

What it means in plain English: the measuring tape is fine (data, models, seals all check out), but the agent's notebook pen breaks on Windows before writing a single word, so tonight's comparison could not happen. The plain baseline works, which proves the break is in the agent's logging code, not the machine or models.

What it doesn't mean: it says nothing about whether Premonition 0.1 beats same-size models. No score was produced, so predictions P390.1–P390.6 are all still untested, and this is not a FAIL of M1 — the registered verdict is simply unmeasured.

PUSH: artifacts/claude-bm390-20260925/RESULTS-benspc.md (written in the worktree; artifacts/ is git-ignored locally so the watcher will need to force-add it). artifacts/claude-bm390-20260925/run does not exist anywhere (never created) — nothing to push for it. Time used about 18 min of the 7-hour cap; GPU (RTX 5070 Ti, 16303 MiB, driver 591.86) was idle before and after, one job at a time kept.
