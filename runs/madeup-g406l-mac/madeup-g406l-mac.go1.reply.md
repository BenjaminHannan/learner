Labeling run locked in — setting up the sealed Luna packet batch.
Archive verified — now sealing the inputs and checking the runners.
Seal passed and most self-tests are green — diagnosing the one failure.
Found the missing rubric blocking the wrapper — pulling it from the sealed archive.
All green — starting the 10-packet pilot through Luna.
Pilot needs more time than the default window — restarting it with an extended budget.
Pilot passed 10/10 — launching the full 240-packet run.
40 packets done and clean — continuing the sweep.
130 packets clean at the halfway mark — keeping the run going.
Run stopped at 220/240 on the time cap — moving to counts on what finished.
Counts complete — packaging the sealed results for handoff.
Results filed — cleaning up the temp workspace.
partial — pilot PASS, full run time-stopped: INCONCLUSIVE on 220/240

Verdict: pilot PASS (10/10 usable). Full run wrote 210 new rows + 10 pilot = 220/240 usable, 0 failed rows, stopped “time” (48.9 min, max-minutes 45). Count says INCONCLUSIVE (V false). 20 packets have no usable row.

Marks table (integer counts, best_b.jsonl, 220 usable packets / 1100 replies):

- packets: 240, usable_packets: 220
- replies: 1100, judge_either: 158, judge_both: 122
- Luna flags: 363, Luna catches both: 121, catches either: 149
- Luna clean: 737, either in Luna clean: 9
- recall_both: 0.992, recall_either: 0.943
- base either rate: 0.1436, either rate in Luna clean: 0.0122, in flagged: 0.4105, yield clean: 0.67, kappa vs either: 0.465
- V: false, G1: true, G2: true, G3: true, proved_wrong: false, verdict: INCONCLUSIVE

Per arm (packets / replies / Luna flags / either / both / catches both):
- H: 57 / 285 / 80 / 33 / 23 / 23
- N: 55 / 275 / 80 / 24 / 18 / 17
- U: 53 / 265 / 144 / 83 / 72 / 72
- W: 55 / 275 / 59 / 18 / 9 / 9

Every move:
- TREE from origin/main aa34f14d1ba050d78b360c6e1357b45fb3f7af9d (at 06:24:45 UTC origin/main was e49be974; work used aa34f14).
- SEAL: 24/24 OK.
- Selftests: selftest-luna 7/7 ok; --selftest 7/7 ok; count 5/5 ok; luna_codex selftest ok.
- Pilot 05:31:55–05:34:39 UTC: 10 written, 0 failed; pilot-check `{"pilot_packets":10,"rows":10,"usable":10,"limit_errors":0,"pass":true}` exit 0.
- Full run 05:34:47–06:24:22 UTC, PID 82254, workers 1: batches 30/60/90/120/150/180/210, then time-stop. Final: `{"mode":"two","packets":240,"usable_before":10,"written":210,"failed_this_run":0,"usable_now":220,"minutes":48.9,"stopped":"time"}`. wc luna_b.jsonl 220, best_b.jsonl 220.
- Error prefixes: 1 distinct; `''` 220 (all ok).
- Copied luna_b.jsonl, pilot.log, luna_b.log, best_b.jsonl, verdict_b.json, arms_b.json + RESULTS.md to artifacts/claude-g406l-20260927/run/. Removed $D (confirmed gone).

Every miss / deviation:
- 20/240 packets missing (time cap, not failures). No failed rows.
- --selftest first failed (missing artifacts/claude-mu402-20260926/JUDGE-claims.md, not in TREE list). Extracted that one file from same aa34f14 commit, reran: 7/7 ok. SEAL unaffected.
- Never reworded any prompt. Never read TEST-ONLY panels. Never touched ~/.codex. Never checked out/pushed.

What it means / doesn’t mean (plain):
- It means Luna flagged almost all replies both judges flagged (121/122) and kept its clean set very clean (9/737 either). G1/G2/G3 all true on what finished.
- It doesn’t mean a PASS: V needs 228/240 usable, we have 220, so the gate is INCONCLUSIVE. It doesn’t pick training replies for mu-406. It doesn’t say Luna equals the judges.

labeller: Luna (gpt-6-luna), helper sha256 342a0fb7e15ebf22da763c21eddecb0c58cfcbd43c74481d8421b5709023024e
PUSH: artifacts/claude-g406l-20260927/run
