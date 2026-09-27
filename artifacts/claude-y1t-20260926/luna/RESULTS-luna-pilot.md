# RESULTS: y1t Luna pilot (label y1t-luna-pilot)

Verdict: RAN OK. Pilot wrote the first 60 of the 315 redo dialogs. Nothing trained, checked or judged here. Counts only; no dialog text is summarised in this file.

## Provenance
- Task file: origin/main:handoff/queue/y1t-luna-pilot-mac.md (same text as the assignment; written 2026-09-27 03:51 UTC).
- Common-rules source: first 14 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, at most 4 parallel processes, report in final reply). Followed: 3 workers (<=4), new files only, no panel touched, no branch checked out or pushed.
- Worktree branch left untouched; main's files came only from `git archive` after `git fetch -q origin main builder-outbox` (fetch exit 0).
- Temp tree: /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.upTJmkoAyJ (removed after copy; see bottom).
- DUPLICATE GATE: origin/builder-outbox had no artifacts/claude-y1t-20260926/luna/RESULTS-luna-pilot.md, so this is not a duplicate.

## SEAL (verbatim)
```
artifacts/claude-y1t-20260926/ADDENDUM-5-luna-writer.md: OK
scripts/claude_y1t_luna.py: OK
scripts/claude_luna_codex.py: OK
scripts/claude_y1t_routefilter.py: OK
scripts/claude_lis320_glm_oc.py: OK
scripts/claude_lis320_glm.py: OK
scripts/claude_y1t_topup.py: OK
scripts/claude_lis320_seed.py: OK
```
All 8 lines OK; no SEAL-MISMATCH.

## SEEDS (verbatim printed lines)
- seed: `{"dialogs": 2400, "turns": 16816, "intents": {"ambiguous_pronoun": 517, "ask": 1253, "backref": 1548, "confirm": 480, "correct": 1586, "doubt": 544, "former": 1271, "hypothetical": 516, "jobhome": 825, "negation_only": 484, "plan": 482, "question": 502, "smalltalk": 652, "someone_else": 468, "teach": 5688}}`
- split: `{"seeds": 2400, "raw_rows": 1021, "parsed_kept": 645, "to_redo": 1755, "raw_rows_unparsed": 376}`
- pick: `{"redo": 1755, "done": 1440, "left": 315}` (matches expected "left": 315)
- shasum check (all match, no SEED-MISMATCH):
```
42b344fba2dad802fa3109295dd3548c8aa7bdd5c947a356ba1c61c480360f43  seeds.jsonl
e80e84156cb2ac003711c97ad8d9d4761962c6c42b83d3730477dad8abc4ef8b  split/seeds_redo.jsonl
6184cd224078ad2eb71cdd606129cb29fc14e513960c26c0ee0b295f57b483de  luna_seeds.jsonl
```

## CHECKS (verbatim)
- `y1t luna selftest ok (no network)` (preceded by lis320 glm_oc selftest `lis320 glm_oc selftest 4/4 ok`)
- routefilter selftest counts line: `{"rows": 9, "empty": 1, "r1": 1, "r2": 3, "kept": 4}` then `y1t routefilter selftest ok`
- uptime: `2:37 up 3 days, 16:30, 4 users, load averages: 116.83 123.31 111.00`
- df: `/dev/disk3s1s1 460 12 33 28% 484014 350728400 0% /` (33 GB free; above the 1 GB floor)

## PILOT
- W=3. Why: the task default (W=3 unless the Director's current Luna share says otherwise); no Luna-share override was found on origin/main (checked bm398w-luna-mac.md and k1h-luna-pilot-mac.md queue files; neither sets a Luna worker share), so the default applied.
- Command as specified, `--workers 3 --batch 20 --max-minutes 50 --max-failed 10 --limit 60`, single run, no rerun.
- Wall time: start 2026-09-27 06:38:12 UTC, end 2026-09-27 06:58:43 UTC (~20.5 min; script's own `minutes: 20.5`). Exit 0.
- Totals line (last line of luna_pilot.log, verbatim):
```
{"calls": 60, "parsed": 60, "skipped": 0, "failed_calls": 0, "batches": 3, "stopped": "done", "minutes": 20.5}
```
- Log shape: 61 lines = 60 per-dialog `ok` lines plus the totals JSON. Per-dialog lines look like `[glm320] s320-4027-02087 ok` (that label is the script's own wording, recorded as-is).
- `[y1tluna] call failed` errors: none. Zero distinct errors to report (grep found 0 such lines).

## ROUTE FILTER (verbatim)
```
{"rows": 60, "empty": 0, "r1": 0, "r2": 0, "kept": 60}
```
60 rows in, 60 kept, 0 dropped.

## COUNTS (raw_luna.jsonl; counts only)
- lines: 60
- rows with "parsed" not null: 60
- rows with parsed null: 0
- distinct dialog ids: 60
- row keys: dialog_id, model, parsed, prompt_chars, raw, temperature, usage
- model field value: codex/gpt-6-luna (all rows)

## COPIES (worktree artifacts/claude-y1t-20260926/luna/)
- raw_luna.jsonl sha256: 5e98dec2f5f48042123e9c0b52a114923d8842a5b0148441f02c179d162e6e78 (matches temp tree)
- raw_luna_rf.jsonl sha256: 5e98dec2f5f48042123e9c0b52a114923d8842a5b0148441f02c179d162e6e78 (identical content to raw_luna.jsonl: filter kept all 60)
- luna_pilot.log sha256: da661cda7de7b1a0a29ee984347ba72b82c17a28a02eff65ab78200e8dc1216e (matches temp tree)

## ERRORS / DEVIATIONS
- None. No SEAL-MISMATCH, no SEED-MISMATCH, no failed calls, no rerun, no timeout, no disk pressure.

## CLEANUP
- `rm -rf /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.upTJmkoAyJ` executed; confirmed gone (ls: no such directory).

PUSH: artifacts/claude-y1t-20260926/luna
