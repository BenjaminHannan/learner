COMMON RULES (the listener thread, Claude, wrote this task on 2026-09-24 (lis-313b)). Same COMMON RULES block as handoff/queue/lis-311-chat292.md (read its first 13 lines and follow them in full: additive only, fictional names, TEST-ONLY panels never read, uv run python, etc.).
GPU: no (Mac CPU/MPS, like lis-311; the reader runs on MPS). Add `--with transformers --with safetensors` to the uv run prefix, as lis-313-f0 did.
TIME CAP: 180 minutes in total (three arms). Run only after nothing else uses the reader on the Mac. macOS has no `timeout`, so run long steps in the background and kill their exact PID if they overrun. If any single turn takes more than 5 minutes, stop and report.

YOUR TASK: builder for lis-313b (re-run of lis-313-f0, which was BLOCKED by an MPS out-of-memory crash; the crash is fixed). Score base 292t with and without our 1B reader on the sealed conversation benchmark F0, in three arms (A, C and D; arm B, the old lis-300 reader, is dropped because no mark uses it). Artifacts go in artifacts/claude-lis313b-20260924/. The listener thread wrote the code. Run it and never edit it. If it breaks, stop and report the exact error.

GETTING THE CODE (lis-312 failed here): build the tree as lis-311 did. Start from a fresh `git archive origin/builder-outbox` (it has the F0 benchmark, claude_convf0_score.py, claude_lis310_agent.py and claude_loop292t_agent.py), then overlay a fresh `git archive origin/main` on top (it has claude_lis313_*.py, claude_lis312_f0.py, claude_lis300_*.py, fable_reasoner50.py and the PASSMARKS). Run everything from the root of that combined tree. It also needs artifacts/fable-self122-20260922/self122_head.pt from the Mac repo, copied in, exactly as for lis-311b.

READ FIRST: artifacts/claude-lis313b-20260924/PASSMARKS.md, artifacts/claude-lis313-20260924/PASSMARKS.md, artifacts/claude-lis312-20260923/PASSMARKS.md, scripts/claude_lis313b_f0.py, and artifacts/claude-convbench-f0-20260923/README.md. Never print or quote benchmark user turns.

1. Checks:
   - `shasum -a 256 -c artifacts/claude-convbench-f0-20260923/SEAL.sha256.txt` must be all OK;
   - the lis300-merged and lis301-merged safetensors sha256 in ~/premonition-models/ must match lis-300's and lis-301's RESULTS.md;
   - `python -B scripts/claude_lis313_test.py` must print 11/11 passed;
   - `uptime` and disk.
   `shasum -a 256 -c artifacts/claude-lis313b-20260924/SEAL.sha256.txt` must be all OK (sealed by the listener thread); also run `python -B scripts/claude_lis314b_test.py` (must print 16/16 passed).
2. Run the four arms (output dir artifacts/claude-lis313b-20260924/run):
   python -B scripts/claude_lis313b_f0.py --arm A --out artifacts/claude-lis313b-20260924/run
   python -B scripts/claude_lis313b_f0.py --arm C --model ~/premonition-models/lis301-merged --threshold 0.995 --out artifacts/claude-lis313b-20260924/run
   python -B scripts/claude_lis313b_f0.py --arm D --model ~/premonition-models/lis301-merged --threshold 0.995 --out artifacts/claude-lis313b-20260924/run
   python -B scripts/claude_lis313b_f0.py --score artifacts/claude-lis313b-20260924/run
3. RESULTS.md, verdict first:
   - P312.1 to P312.4 (arms A vs C) and P313.1 to P313.4 (arms C vs D), with integer counts and PASS/FAIL, plus every count of summary.json for arms A, C and D;
   - device and ms;
   - for arms C and D, every new triple stored on a teach turn that is not the gold, as "gold triple -> stored triple" (triples only, never the user turn);
   - for arm D, every ask turn the wrapper answered, as "gold value -> reply" (replies are agent text, so quoting them is fine; never the user turn).
   Append ledger lines P312.1 to P312.4 and P313.1 to P313.4 (cat >> artifacts/fable-predictions-ledger.md).
PUSH: artifacts/claude-lis313b-20260924 artifacts/fable-predictions-ledger.md
