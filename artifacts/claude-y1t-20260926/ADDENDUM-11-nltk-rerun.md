# y1t addendum 11: install nltk on the rental, check every import before launch, and run the vast route again (Answering-from-memory thread, written 2026-09-27 17:25 UTC, before any y1t training run finished; sealed in SEAL-y1t-add11.sha256.txt)

**Why:** the first vast run (job rent-y1t-vast-p1, kit 4a0b63b3a) ended PARTIAL at 16:55 UTC. Its drafts step ended
rc=0 in 7.5 minutes on an RTX 4080 at $0.2833/h, and its train step ended rc=1 after 30 seconds with
"ModuleNotFoundError: No module named 'nltk'" (builder-outbox 943be1641, artifacts/claude-y1t-20260926/run). The
cause: claude_bm398r_train.py imports the scorer claude_bm390_score.py inside right() (line 72), which the DEV check
calls before training, and the scorer imports nltk at its top (line 28). The rental's setup did not install nltk, and
none of the four selftests reach that import (claude_bm398r_train.py's selftest printed PASS 6/6). The copy-back was
checked and the instance was destroyed. The run cost $0.19 over 3 instances (RESULTS-vast.md). No model was trained,
so nothing in the design has been seen yet. The Thread manager (17:14 UTC) asked for nltk on the rental and an import
selftest on the rental before launch, then a new pinned kit.

**The change (one fix, kit re-pinned):**
1. **Setup installs nltk 3.10.3, regex and pyarrow** (remote/bov.sh), after transformers. nltk 3.10.3 is the version
   of the venv that recounted bm390 (artifacts/claude-bm390-20260925/recount3/recount.md). regex is the scorer's other
   import. pyarrow is imported inside claude_bm390.py, which the train script also reaches. The scorer's PorterStemmer
   needs no nltk data download.
2. **A fifth check before launch: the import check.** It reads the four step scripts with Python's ast module (nothing
   is run) and follows every import, at the top of a file or inside a function, through the scripts/ files they
   import: 247 files. Then it imports the four step scripts and each of the 49 other modules found (torch,
   transformers, huggingface_hub, numpy, regex, nltk.stem, pyarrow, pyarrow.parquet and standard-library modules).
   It prints IMPORTS OK, or IMPORTS FAIL with each module that failed and exits 1. The chain launches only with 5 of 5
   checks ok (4 selftests and this one); otherwise the pass writes CHECK-FAIL, copies back and destroys. Tested here:
   without nltk and pyarrow it printed "IMPORTS FAIL nltk.stem (ModuleNotFoundError: No module named 'nltk'); pyarrow
   ...; pyarrow.parquet ..." and exited 1. With nltk 3.10.3, regex and pyarrow installed it printed "IMPORTS OK the 4
   step scripts, 247 local files read, 49 other modules imported (nltk 3.10.3)", and the train script's right()
   scored "I don't know." as an abstention on a missing row.
3. **A new run folder.** This run writes to artifacts/claude-y1t-20260926/run2 (notes, vast state, lock, results).
   The first run's files in run/ stay as they are. The BensPC and rent-kit duplicate checks look in both folders; a
   RESULTS-vast.md in run/ does not stop this run. The H1 rows still go to artifacts/claude-y1tH1-20260926/run, where
   the first run wrote nothing. The lock is now run2/.pass-lock; the BensPC passes that shared the old lock are in
   handoff/held/superseded.
4. **Money.** The cap for this run is $1.30: ADDENDUM-9's $1.50 for the whole task less the first run's $0.19,
   rounded up to $0.20. pass.sh and the guard use it. The estimate is unchanged ($0.30 to $0.70). The whole task stays
   under Ben's $4 per job.
5. **The passes.** handoff/held/rent-y1t-vast-p1b (the only pass that rents; the watcher does not run a job file a
   second time, so p1 gets a new name), then rent-y1t-vast-p2 and p3, re-pinned. The Director releases them.

Everything else is unchanged: the data, the sealed scripts, the panel, the six steps, the DEV marks, the card rule
(the best TFLOPS per $/h that fits), the time cap and the guard. The drafts step runs again on the new rental; the
first run's drafts stay in run/ and are not reused.

**Tests:** the fake vast and fake rental cases pass with the new kit: the normal run (5 of 5 checks, COMPLETE,
results in run2/), the first run's RESULTS-vast.md present in run/ (the run goes ahead), an import check that fails
(CHECK-FAIL, nothing launched, copied back, destroyed), a selftest that prints FAIL with exit code 0 (CHECK-FAIL), a
BensPC launch recorded in run/ (DUPLICATE), the money cap, the guard's money, time and chain-done actions, and the
last pass locked out.
