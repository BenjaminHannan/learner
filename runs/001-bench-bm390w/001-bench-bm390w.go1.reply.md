Starting the second-attempt bench — fetching refs and checking your guard rails.
Your duplicate checks clear — digging up how to reach the Windows box.
SSH works and the GPU is free — mapping your existing setup.
Duplicate guard holds — building your new tree for the retry.
Fresh tree built — copying it to your PC now.
Core models verified — confirming the Windows line-ending fix works.
Quoting solved — verifying your router and remaining deps.
Setup done — running your seal checks.
Seals pass, but the wrapper tripped on startup — inspecting the failure.
Found the wrapper bug — confirming the exact breakage.
Base checkpoint matches — copying it and fetching your data.
Both rivals load — running your smoke test with the wrapper.
Both smokes hit the same wrapper fault — gathering evidence for your report.
No real data touched — writing your results file.
Verdict: SMOKE-FAIL (second attempt, bm-390 on BensPC). The registered run never started on real items. No run/ was created. Nothing trained. No file edited.

Marks table (integer counts, PASSMARKS artifacts/claude-bm390-20260925/PASSMARKS.md):
- M1 (LoCoMo cats 1-4, P vs every "yes" arm, >=3.0 pts + bootstrap>0): 0 arms run, 0 scored. VOID, not FAIL.
- M3 (confident-wrong counts cats 1-4): 0 counted. VOID.
- M4 (P >= T-3.0 on MMLU-300 and GSM8K-300): 0 items run. VOID.
- Validity: seals 8/8 + 3/3 + 229/229 OK; data sha OK (1986/300/300); 0/1986 LoCoMo rows; sleep log 0/272 rows. VOID (stopped at smoke, as registered).
- Predictions P390.1-P390.6: 0 tested.

Every move:
1. DUPLICATE guard PASS: origin/builder-outbox has only bm-390 RESULTS-benspc.md (0 run files, 0 RESULTS-rent.md for bm-390); runs/rent-bm390/rent-bm390.exit exists rc=0.
2. Built tree2 (builder-outbox + main on top, self122_head.pt 5ca02173... match), scp to BensPC C:/Users/benja/lis301/work/bm390/tree2 (new folder, first tree untouched). 1 new local file for transport only (in /tmp, not repo).
3. BensPC checks: READER sha b4fd93a2... match; BASE 87179e5c present; Q2DIR + L12DIR exist; route122 prints D8 conf 0.9732; pyarrow 25.0.1 OK; installed 0 packages; created DATA2 (new).
4. Step1 seals: 8 OK, 3 OK, 229 OK, 0 FAIL.
5. Step2 plain: JSON {"stage":"base","seed":4102,"seconds":12.9,...} exit 0; .pt sha 4655b761... size 2969 bytes, copied into tree2. Extra diagnosis run of same command through wrapper: exit 1 (wrapper TypeError, see below).
6. Step3 fetch plain: 1 line, locomo_qa 1986, mmlu 300, gsm8k 300, hashes 1a44e304... + 073acc01... match. Exit 0. Load checks: Q2 Qwen3_5ForCausalLM 1881825088 exit 0; L12 Lfm2ForCausalLM 1170340608 exit 0. Both rivals RUN (but never launched).
7. Step4 smoke through W: P exit 1 (0.2s, 06:39:58 UTC), T exit 1 (0.1s, 06:40:21 UTC). 0 "wrote..." lines. sleep_P.jsonl 0 rows (never created). smoke2/ 0 files (folder never created), 0 CRLF. Each launched ONCE, no retries.
8. Step5: 0 lane-1 + 0 lane-2 commands launched. run/ 0 files.
9. Step6: nothing to copy (run/ absent on BensPC and Mac). Models left on BensPC.
10. Step7: created 1 new repo file artifacts/claude-bm390-20260925/RESULTS-benspc2.md, counts only. Edited 0 files.

Misses/deviations:
- SMOKE-FAIL root cause is the sealed wrapper itself, not the turn log. Both smokes crash at load_locomo Path.read_text with `TypeError: argument of type 'WindowsPath' is not iterable` (winnl_wrap.py:35). Full tracebacks in RESULTS file. The wrapper replaces io.open with a Python function; on BensPC Python 3.10 pathlib captures it at fresh import and it binds as a method, so `mode` gets a Path. AMEND tested on 3.11 with pathlib pre-imported, so it never hit this. Sealed turn-log issue was never reached.
- Deviation: step2 run twice (once plain as listed = registered checkpoint; once through wrapper = diagnosis, exit 1). Reported above.
- PUSH: artifacts/claude-bm390-20260925/RESULTS-benspc2.md exists (new); artifacts/claude-bm390-20260925/run does not exist (0 files, nothing to push).

What it means (high-school English): The fix for the Windows line-ending bug has its own Windows bug. It breaks every Python command on Ben's PC before any model work starts, because it confuses the file-opening tool on that Python version. So we learned nothing new about the memory model vs plain models today.

What it doesn't mean: It does not mean the memory idea failed, or the plain models won, or the data is bad. All model scores are still VOID. It also does not mean Linux runs are affected (wrapper is a no-op there).

COMMON RULES report (first 13 lines of lis-302-gpu.md): additive only (1 new repo file created, 0 edited, 0 deleted); fictional names only (smoke data fictional, never quoted); TEST-ONLY panels never read item-by-item, never tuned on, never quoted (benchmark files only counted: 1986/300/300 rows + hashes, 0 questions/answers/replies opened, printed or quoted). No secrets printed. Mac disk 22 GB free (>3 GB). BensPC one job at a time, no rentals. Time 13 min of 7 h cap.

PUSH: artifacts/claude-bm390-20260925/RESULTS-benspc2.md artifacts/claude-bm390-20260925/run (run/ absent, 0 files).
