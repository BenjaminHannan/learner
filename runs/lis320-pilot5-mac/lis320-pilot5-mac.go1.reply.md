Pilot5 queued — extracting the run pack and spinning up the isolated run.
Seals, self-tests and leak-check all passed — generating the pilot seeds.
Wording finished — running verification and scoring.
Core data collected — preparing the final delivery.
Files staged — writing the final results record.
PASS — lis320-pilot5 complete. No stop conditions hit.

PUSH: artifacts/claude-lis320-20260926/pilot5 (seeds.jsonl, raw.jsonl, kept.jsonl, drops.jsonl, check.json, style.json, glm.log, RESULTS.md). I did not check out or push any branch.

Common rules followed: additive only (new pilot5/ files only), fictional names (seeds use avoid lists), TEST-ONLY panels never read item-by-item, report here.

Moves:
1. TREE: D=/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.q0XocW72He via `git archive origin/main ... | tar -x -C $D`. origin/main=1f6d336dd5293b1a3a6044734c0a6c2e747c9009
2. SEALS: all OK — SEAL-ADDENDA-5, -6, -7 each 6/6 OK
3. SELFTESTS: all ok — glm_oc 4/4 ok + glm_oclow ok (variant low, no network); seed_cr OK 400 dialogs; check_cr OK 1 kept/1 dropped; check_we OK 1 kept/1 dropped (group_speaker); rawcheck 4/4 ok
4. LEAK CHECK (1 call): {"exit": 0, "reply_ok": true, "left_after_cleanup": 0}, exit 0
5. SEEDS (seed 325, n 60, ask-back): {"dialogs": 60, "turns": 428, "intents": {"ack_after_ask": 12, "ambiguous_pronoun": 8, "ask": 17, "backref": 41, "confirm": 9, "correct": 32, "correct_ref": 10, "doubt": 11, "former": 35, "hypothetical": 13, "jobhome": 19, "negation_only": 10, "plan": 10, "question": 13, "smalltalk": 19, "someone_else": 8, "teach": 143, "yes_after_ask": 18}}
6. SHARE: date -u Sat Sep 26 23:50:55 UTC 2026, uptime 19:50 up 3 days 9:43 load 78.95 75.58 73.05, N=11, W=5 (no wait needed)
7. WORDING (workers 5, max-minutes 40): start Sat Sep 26 23:50:58 UTC 2026, end Sat Sep 26 23:58:25 UTC 2026, uptime end 19:58 up 3 days 9:51 load 70.62 71.00 72.32. Last line verbatim: {"calls": 60, "parsed": 55, "skipped": 0, "failed_calls": 0, "batches": 2, "stopped": "done", "minutes": 7.4}. "call failed" lines: 0. Distinct errors: none.
8. RAWCHECK: {"rawcheck": "OK", "rows": 60, "duplicate_ids": 0, "model_ok": 60, "temperature_null": 60, "not_in_seeds": 0}
9. CHECK_WE: kept 327, dropped 66, turns 428, dialogs 60, dialogs_unparsed 5, drop:group_speaker 18, drop:dialog_unparsed 35, kept correct_ref 9, kept correct 27 (full check.json verbatim in RESULTS.md). STYLE printed line: {"glm_kept": {"turns": 327, "words_median": 19, "words_p90": 29, "lowercase_start": 0.994, "noapos_contraction": 0.434, "over20_words": 0.398, "shapes_per_100": 100.0, "write_facts_per_turn": 1.012, "write_facts_in_over20": 0.529}, ...} (full in RESULTS.md)
10. COPIED 7 files to worktree pilot5/ + wrote RESULTS.md (counts only). rm -rf "/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.q0XocW72He" done — confirmed gone (ls: No such file).

Counts table (integers):
- dialogs seeded 60, turns seeded 428
- calls 60, parsed 55, unparsed dialogs 5, skipped 0, failed_calls 0
- kept turns 327, dropped turns 66, drops lines 66, kept lines 327
- group_speaker drops 18
- dialogs/min 8.11 (60/7.4), parsed/min 7.43

Misses/deviations: none. No route-mismatch, no leak, no flag changes, no opencode config read, Python via `uv run --offline --no-project --python 3.12 python -B` only.

What it means in plain English: the new route produced wording for all 60 test dialogs in ~7.4 minutes with zero call failures; 55 parsed and 327 turns survived all filters including the new group-speaker check. What it doesn't mean: this is not a pass/fail against pilot thresholds (director judges that from RESULTS.md) and nothing was trained.
