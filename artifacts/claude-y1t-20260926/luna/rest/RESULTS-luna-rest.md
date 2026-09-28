# RESULTS-luna-rest (y1t Luna rest run: the 255 non-pilot dialogs of 315)

Label: y1t-luna-rest. W (workers): 3. GPU: no (Mac CPU; Luna calls via scripts/claude_luna_codex.py, $0 extra).
origin/main commit: 3e8cf1186bf64cca8a77f0e5428596bd2bc70b30
origin/builder-outbox commit (at fetch): e6eba4d0c8939c377fe34cfa3cedd54d0276d3d4
DUPLICATE GATE: origin/builder-outbox had no artifacts/claude-y1t-20260926/luna/rest/RESULTS-luna-rest.md. Not a duplicate.
Common rules: additive only, fictional names, no TEST-ONLY panels read, max 4 parallel processes, no branch checkout/push by hand.

RESUME NOTE: two earlier passes by cut-off agents already wrote all 255 Luna rows
(rest2: 160 calls then stopped "time"; rest3: 95 calls then stopped "done").
This agent verified seals/seeds, adopted rest3's 315-row file byte-for-byte, and ran
one verification pass that made 0 new calls (all 315 skipped). No dialog was called twice.
No row was deleted or edited.

## SEAL (step 2, from fresh $D tree)
`shasum -a 256 -c artifacts/claude-y1t-20260926/SEAL-y1t-add5.sha256.txt`: every line OK
(non-OK count: 0).

## SEEDS (step 3, verbatim printed lines)
seed: {"dialogs": 2400, "turns": 16816, "intents": {"ambiguous_pronoun": 517, "ask": 1253, "backref": 1548, "confirm": 480, "correct": 1586, "doubt": 544, "former": 1271, "hypothetical": 516, "jobhome": 825, "negation_only": 484, "plan": 482, "question": 502, "smalltalk": 652, "someone_else": 468, "teach": 5688}}
split: {"seeds": 2400, "raw_rows": 1021, "parsed_kept": 645, "to_redo": 1755, "raw_rows_unparsed": 376}
pick: {"redo": 1755, "done": 1440, "left": 315}
shasum checks (all match expected):
42b344fba2dad802fa3109295dd3548c8aa7bdd5c947a356ba1c61c480360f43  seeds.jsonl
e80e84156cb2ac003711c97ad8d9d4761962c6c42b83d3730477dad8abc4ef8b  split/seeds_redo.jsonl
6184cd224078ad2eb71cdd606129cb29fc14e513960c26c0ee0b295f57b483de  luna_seeds.jsonl
5e98dec2f5f48042123e9c0b52a114923d8842a5b0148441f02c179d162e6e78  raw_luna_rf.jsonl (pilot 60)

## CHECKS (step 4, verbatim)
y1t luna selftest: "y1t luna selftest ok (no network)" (a preceding line "lis320 glm_oc selftest 4/4 ok" also printed)
y1t routefilter selftest: {"rows": 9, "empty": 1, "r1": 1, "r2": 3, "kept": 4} then "y1t routefilter selftest ok"
uptime at checks: up 4 days, 9:54; load averages ~57/64/65
df -g /: 460 1G-blocks, 12 used, 24 available, 35% capacity (24 GB free; DISK limit 1 respected)

## RESUME FILE (step 5)
cp pilot raw_luna_rf.jsonl (60 lines) to $O/rest/raw_luna.jsonl, then replaced with the
prior agents' complete 315-row file (rest3). No pilot row re-called.

## RUN (step 6)
Prior pass A (rest2/luna_rest2.log, file mtime Sep 27 06:09:22 local 2026):
{"calls": 160, "parsed": 160, "skipped": 60, "failed_calls": 0, "batches": 11, "stopped": "time", "minutes": 53.3}
Prior pass B (rest3/luna_rest3.log, file mtime Sep 27 06:58:50 local 2026):
{"calls": 95, "parsed": 95, "skipped": 220, "failed_calls": 0, "batches": 16, "stopped": "done", "minutes": 33.9}
This agent's verification pass (pass 1 cmd: --seeds luna_seeds.jsonl --out rest/raw_luna.jsonl --workers 3 --batch 20 --max-minutes 55 --max-failed 20; wall 00:01:19-00:01:19 UTC 2026-09-28, 0.0 min):
{"calls": 0, "parsed": 0, "skipped": 315, "failed_calls": 0, "batches": 16, "stopped": "done", "minutes": 0.0}
stopped="done": no pass 2 run. Third pass: never.
New Luna calls this agent: 0. Total new Luna calls across all agents: 255 (160 + 95). Failed calls: 0.
"[y1tluna] call failed" lines: 0 in all three logs. Distinct errors: none.

## ROUTE FILTER (step 7, verbatim counts line)
{"rows": 315, "empty": 0, "r1": 0, "r2": 0, "kept": 315}

## COUNTS (step 8, counts only)
lines in rest/raw_luna.jsonl: 315
rows with parsed not null: 315
rows with parsed null: 0
distinct dialog ids: 315
luna_seeds.jsonl ids (315) with a row: 315 of 315
model values: codex/gpt-6-luna (only value, 315 rows)
lines in rest/raw_luna_rf.jsonl: 315
rest/raw_luna.jsonl sha256: b49327ced60b24d74186025bd5be8648467ae1046889a03ed896667bf328e56e
rest/raw_luna_rf.jsonl sha256: b49327ced60b24d74186025bd5be8648467ae1046889a03ed896667bf328e56e
(raw and rf files are byte-identical: filter dropped nothing.)
Adopted file matches prior rest3 files byte-for-byte (cmp: identical).

## FILES (step 9)
artifacts/claude-y1t-20260926/luna/rest/raw_luna.jsonl (315 lines)
artifacts/claude-y1t-20260926/luna/rest/raw_luna_rf.jsonl (315 lines)
artifacts/claude-y1t-20260926/luna/rest/luna_rest_1.log (1 line: verification-pass totals)
artifacts/claude-y1t-20260926/luna/rest/RESULTS-luna-rest.md (this file)
Prior agents' intermediate dirs artifacts/claude-y1t-20260926/luna/rest2/ and rest3/ left untouched.
Temp tree $D removed after copy; confirmed gone.
No Luna text is summarised or quoted here (counts only).
