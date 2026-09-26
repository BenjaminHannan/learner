Scoring 560 judged chats with GLM — setting up the sealed run.
The first seal check ran from the wrong folder — rerunning it from the right place.
Seal and selftests passed — starting the 560-call marking run.
Start time logged — launching the full marking job now.
The run stopped early on failures — inspecting what went wrong.
The helper itself works — probing a single transcript to see the failure mode.
Partial verdict is in — assembling the results package.
Results filed — cleaning up the temp tree.
Verdict: partial, INCONCLUSIVE (V false on 23/560 usable; G1/G2/G3 true on the usable subset; proved_wrong false). Later task resumes from glm.jsonl.

Label: madeup-g406. GPU: no, Mac CPU only, $0. No reader, no rental, no BensPC, no OpenRouter.

First-13-lines compliance: additive only (created artifacts/claude-g406-20260926/run/ only, no edits/deletes), fictional names only, TEST-ONLY panels never read, report is this reply. No branch checkout or push by me; PUSH path for watcher: artifacts/claude-g406-20260926/run.

Marks table (integer counts, no transcript quotes):
- packets total: 560
- packets written this run: 80
- usable (ok true): 23
- unparsed (ok false, flags null): 57
- replies counted: 113
- judge either: 11
- judge both: 8
- GLM flags: 12
- GLM catches both: 6
- GLM catches either: 8
- GLM clean: 101
- either in GLM clean: 3
- recall_both: 0.75, recall_either: 0.727, base_either_rate: 0.0973, either_rate_in_glm_clean: 0.0297, either_rate_in_glm_flagged: 0.6667, yield_clean: 0.894, kappa_vs_either: 0.661
- V: false, G1: true, G2: true, G3: true, proved_wrong: false, verdict: INCONCLUSIVE
- per_source: only claude-mu402-20260926 present (113 replies, 11 either, 8 both, 12 GLM flags, 6 catches both); 0 mu-403 rows yet.

Every move:
1. git fetch -q origin main; origin/main commit 0cf94a1a826c2af694fb33edda6238fb0cf681bf.
2. Extracted git archive (scripts + claude-g406 + claude-mu402 + claude-mu403) to temp dir /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.oSZKfdQy6j; mkdir -p run.
3. Seal: shasum -a 256 -c artifacts/claude-g406-20260926/SEAL.sha256.txt → 45/45 OK, exit 0.
4. Selftests via uv run --offline --no-project --python 3.12 python -B: g406 selftest 6/6 ok; g406 count selftest 5/5 ok.
5. date -u start: Sat Sep 26 19:36:01 UTC 2026; ran workers-4 command to $O/glm.jsonl > $O/glm.log; date -u end: Sat Sep 26 20:08:02 UTC 2026.
6. glm.log last line verbatim: {"packets": 560, "already": 0, "written": 80, "unparsed_this_run": 57, "minutes": 32.0, "stopped": "failed"}
7. wc -l glm.jsonl: 80. Calls per minute: 80/32.0 = 2.5 total; 23/32.0 = 0.72 usable.
8. Count --write verdict.json, printed line verbatim: {"packets": 560, "usable_packets": 23, "replies": 113, "judge_either": 11, "judge_both": 8, "glm_flags": 12, "glm_catches_both": 6, "glm_catches_either": 8, "glm_clean": 101, "either_in_glm_clean": 3, "recall_both": 0.75, "recall_either": 0.727, "base_either_rate": 0.0973, "either_rate_in_glm_clean": 0.0297, "either_rate_in_glm_flagged": 0.6667, "yield_clean": 0.894, "kappa_vs_either": 0.661, "V": false, "G1": true, "G2": true, "G3": true, "proved_wrong": false, "verdict": "INCONCLUSIVE", "per_source": {"claude-mu402-20260926": {"replies": 113, "either": 11, "both": 8, "glm_flags": 12, "glm_catches_both": 6}}}
9. Copied glm.jsonl (sha256 147818e3…), glm.log, verdict.json (sha256 c8295dfb…) + wrote RESULTS.md into worktree artifacts/claude-g406-20260926/run/. rm -rf exact temp path done, confirmed gone (ls: No such file or directory).

Every miss / deviation:
- stopped=failed: 57 unparsed > max-failed 40 after 80 packets. Partial per spec.
- One early shasum from worktree reported 44 unreadable; rerun from temp dir passed 45/45. No files changed.
- Helper health ok: claude_glm_opencode --selftest ok; single-packet workers-1 probe on a pid that failed under workers-4 succeeded in 17.1s. Points to concurrency/load, not auth. Machine load ~185, disk 53 GB free.
- No opencode config/auth/key read, printed, copied, or committed. Helper deleted only its own sessions. Python only via uv offline 3.12 stdlib.

What it means / doesn't mean (plain):
- It means we only got 80 of 560 done, so the gate can't pass or fail yet. On the small usable piece the numbers look good, but 23 packets is too few to trust.
- It doesn't mean GLM is bad or good yet. The high failure rate looks like a plumbing/load issue with 4-at-a-time, not a judgment on GLM's accuracy. Resume from glm.jsonl.
