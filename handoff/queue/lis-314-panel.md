COMMON RULES (the listener thread, Claude, wrote this task on 2026-09-24). Same COMMON RULES block as handoff/queue/lis-311-chat292.md (read its first 13 lines and follow them in full: additive only, fictional names, TEST-ONLY panels never read, uv run python, etc.).
GPU: no (Mac CPU/MPS, like lis-311 and lis-313; the reader runs on MPS). Run only after lis-313-f0 has finished (one reader job on the Mac at a time).
TIME CAP: 240 minutes in total (six arms). macOS has no `timeout`, so run long steps in the background and kill their exact PID if they overrun. If any single turn takes more than 5 minutes, stop and report.

YOUR TASK: builder for lis-314, lis-315 and lis-316. Score the listener wrapper stack on the sealed confirm panel. Artifacts go in artifacts/claude-lis314-20260924/. The listener thread wrote the code. Run it and never edit it. If it breaks, stop and report the exact error.

GETTING THE CODE: build the tree exactly as for lis-313-f0. Start from a fresh `git archive origin/builder-outbox`, overlay a fresh `git archive origin/main` on top, and copy in artifacts/fable-self122-20260922/self122_head.pt from the Mac repo. Run everything from the root of that combined tree.

READ FIRST: artifacts/claude-lis314-20260924/PASSMARKS.md and scripts/claude_lis314_run.py. The panel artifacts/claude-lispanel314-20260924/ is TEST-ONLY: never open, print or quote its panel.jsonl, key.jsonl, label_B.jsonl or key_v2.jsonl. The runner reads them itself.

1. Checks:
   - `shasum -a 256 -c artifacts/claude-lispanel314-20260924/SEAL.sha256.txt` must be all OK;
   - `shasum -a 256 -c artifacts/claude-lis314-20260924/SEAL.sha256.txt` must be all OK (pass marks and code, sealed by the listener thread);
   - ~/premonition-models/lis301-merged safetensors sha256 must be b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890;
   - `python -B scripts/claude_lis314_test.py` must print 13/13 passed;
   - `uptime` and disk.
2. Run the six arms (output dir artifacts/claude-lis314-20260924/run):
   python -B scripts/claude_lis314_run.py --arm A --out artifacts/claude-lis314-20260924/run
   then the same with --arm C, P, K, S and G, each adding --model ~/premonition-models/lis301-merged
   python -B scripts/claude_lis314_run.py --score artifacts/claude-lis314-20260924/run
3. RESULTS.md, verdict first:
   - P315.1–3, P314.1–5 and P316.1–3, with integer counts and PASS/FAIL, plus every count of summary.json for all six arms;
   - device and ms;
   - for arms K, S and G, every wrong saved fact as "stored triple (turn kind)", triples only, never the user turn.
   Append ledger lines P314.1–5, P315.1–3 and P316.1–3 (cat >> artifacts/fable-predictions-ledger.md).
PUSH: artifacts/claude-lis314-20260924 artifacts/fable-predictions-ledger.md
