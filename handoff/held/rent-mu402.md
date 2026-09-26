COMMON RULES (the "Making things up about you" thread, Claude, wrote this task on 2026-09-26). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Follow ALL of origin/main:design/v3/30-modes/330-rent-kit.md (streaming, rental rules, setup, independence). Report in your final reply: verdict first, integer counts, every deviation.
GPU: rent
BUDGET: $1.00 for this whole task, re-rents included (from Ben's $2 for this thread, 12:59 UTC 09-26; standing caps <= $4 per job, $30 total; the Director keeps the ledger and may lower this). Label: rent-mu402.
DISK: 1 (only small files touch the Mac: the 16.5 MB adapter goes BensPC -> rental with `scp -3`; nothing else is staged)
CREDIT GATE (first): `vastai show user --raw` and report ONLY the balance/credit number. Under $3.00: rent nothing, stop with CREDIT-STOP. Re-check before any re-rent. Read the key only as $(cat ~/.config/vastai/vast_api_key); never print it.
RENTAL RULES: RTX 5090 first, else 4090; reliability >= 0.98. Keep a running total of dph x hours; at $0.90 kill running commands by exact PID, copy back what exists, destroy, stop with BUDGET-STOP. Not running within 6 min or no log progress for 10 min: destroy and try another host (max 3 rentals). Launch runs detached (nohup/setsid) so they survive SSH closing. Destroy at the end and confirm it is gone. Append a ledger line.
TIME CAP: 75 minutes on the rental. If reached: stop by exact PID, copy back what exists, destroy, report "partial".
DUPLICATE GATE: stop with DUPLICATE if origin/builder-outbox already has artifacts/claude-mu402-20260926/run or a live instance is labelled rent-mu402.

YOUR TASK: mu-402, the registered run (does 0.2c's sleep adapter make chat replies make up things about the user?). The thread wrote the code: run it, never edit it. If something breaks, copy back what exists, destroy, and report the exact error and traceback. DEV data only: the panel artifacts/claude-mu402-20260926/devchat is readable dev data. No TEST-ONLY panel or bank is involved.
READ FIRST (origin/main): artifacts/claude-mu402-20260926/PASSMARKS.md and the docstring of scripts/claude_mu402.py.
Needs: torch with CUDA, transformers, plain MiniCPM5-1B at revision 87179e5c1f455ef22e6223592d2d61351b525bfc and all-MiniLM-L6-v2 (kit section C; no other model), 0.2c's sleep adapter.

1. Tree (stream, never stage on the Mac):
   git archive origin/main scripts design/v3/60-listener artifacts/claude-gram360-20260925 artifacts/claude-relationtable-20260922 artifacts/claude-table237-20260922 artifacts/fable-abstain76-20260921 artifacts/fable-self122-20260922 artifacts/claude-e2e02c-20260926/SEAL-code.sha256.txt artifacts/claude-mu402-20260926 | gzip | ssh <rental> 'mkdir -p ~/tree && gunzip | tar -x -C ~/tree'
   Then self122_head.pt as the kit says (sha256 5ca02173...), and from builder-outbox the sidecar: git show origin/builder-outbox:artifacts/claude-e2e02c-20260926/run/sleep/adapter02c.json | ssh <rental> 'mkdir -p ~/adapter && cat > ~/adapter/adapter02c.json'
2. Adapter (a file read on BensPC over ssh; nothing runs on BensPC's GPU):
   scp -3 benspc:C:/Users/benja/lis301/work/e2e02c/tree/artifacts/claude-e2e02c-20260926/run/sleep/adapter02c.pt <rental>:adapter/adapter02c.pt
   If scp -3 fails, use one mktemp dir on the Mac and remove it by exact path right after. On the rental: sha256sum ~/adapter/adapter02c.pt must be a33211dc9bdb4e26bc7161b62147cb4dfc04fb605ba1aecbb26948f86e7936f5, else stop with ADAPTER-MISMATCH.
3. Setup: kit section C (pip, snapshot_download with revision='87179e5c1f455ef22e6223592d2d61351b525bfc'; record BASE and the commit hash; the route122 check must not raise). Then, from ~/tree:
   export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1
   sha256sum -c artifacts/claude-mu402-20260926/SEAL.sha256.txt              -> every line OK, else stop
   sha256sum -c --ignore-missing artifacts/claude-e2e02c-20260926/SEAL-code.sha256.txt  -> every present line OK, else stop
   python -B scripts/claude_mu402.py --selftest                              -> "mu402 selftest 7/7 ok", else stop
4. The three arms, each launched ONCE, all at the same time on the one GPU, each with its own log (P = artifacts/claude-mu402-20260926/devchat, OUT = out402):
   A: nohup setsid env SLEEP02C_ADAPTER=$HOME/adapter/adapter02c.pt python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel chat --panel-dir P --arm claude_mu402:build_null02c --name A --model NULL --gen-model BASE --out OUT > logA.txt 2>&1 &
   B: nohup setsid env -u SLEEP02C_ADAPTER python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel chat --panel-dir P --arm claude_mu402:build_null02c --name B --model NULL --gen-model BASE --out OUT > logB.txt 2>&1 &
   T: nohup setsid env -u SLEEP02C_ADAPTER python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel chat --panel-dir P --arm twin --name T --model BASE --gen-model BASE --out OUT > logT.txt 2>&1 &
   V1 (check at once): logA must contain "mu402: adapter loaded = /.../adapter02c.pt" and logB "mu402: adapter loaded = none (B = 0, base 1B)". If either is wrong: kill all three by exact PID, copy back the logs, destroy, stop with V1-FAIL. A "refusing to load" error in logA: same.
   Progress: each log prints one "[382/chat/<arm>] dev402-NN" line per conversation (80 each).
5. When all three exit 0: python -B scripts/claude_panel382_run.py --panel chat --panel-dir P --score OUT --names B,A,T (counts only). Never open the chat_pair_*, chat_turns_* or grammar_* files it writes.
6. Copy back to the Mac as artifacts/claude-mu402-20260926/run/: OUT/chat_A.jsonl, chat_B.jsonl, chat_T.jsonl, summary.json, and logA.txt, logB.txt, logT.txt (force-add; artifacts/ is git-ignored). Check sizes and sha256 match before destroying.
7. RESULTS-rent.md in artifacts/claude-mu402-20260926/: credit number, GPU name, BASE commit hash, the three seal/selftest lines, the adapter sha256 line, logA's and logB's "mu402: adapter loaded" lines (V1), rows per arm (expected: every turn of 80 conversations), exit codes, wall minutes per arm, median ms per turn per arm, summary.json's counts, dollars. Append one ledger line (cat >> artifacts/fable-predictions-ledger.md).
Never push weights (the adapter stays off git).
PUSH: artifacts/claude-mu402-20260926/run artifacts/claude-mu402-20260926/RESULTS-rent.md artifacts/fable-predictions-ledger.md
