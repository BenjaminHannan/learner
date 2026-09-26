COMMON RULES (the "Creative answers in chat" thread, Claude, wrote this task on 2026-09-26). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Follow ALL of origin/main:design/v3/30-modes/330-rent-kit.md (streaming, rental rules, setup, independence). Report in your final reply: verdict first, integer counts, every deviation.
GPU: rent
BUDGET: $0.80 for this whole task, re-rents included (from Ben's $2 for this thread, 12:59 UTC 09-26; standing caps <= $4 per job, $30 total; the Director keeps the ledger and may lower this). Label: claude-creativechat-k1a.
DISK: 1 (only small files touch the Mac: the 16.5 MB adapter goes BensPC -> rental with `scp -3`; nothing else is staged)
CREDIT: record `vastai show user --raw`'s balance number only (vast auto-refills, per Ben via the Director; this is not a gate). Read the key only as $(cat ~/.config/vastai/vast_api_key); never print it.
RENTAL RULES: RTX 5090 first, else 4090; reliability >= 0.98. Keep a running total of dph x hours; at $0.75 kill running commands by exact PID, copy back what exists, destroy, stop with BUDGET-STOP. Not running within 6 min or no log progress for 10 min: destroy and try another host (max 3 rentals). Launch runs detached (nohup/setsid) so they survive SSH closing. Destroy at the end and confirm it is gone. Never destroy an instance whose label this task did not create. Append a ledger line.
TIME CAP: 75 minutes on the rental. If reached: stop by exact PID, copy back what exists, destroy, report "partial".
DUPLICATE GATE: stop with DUPLICATE if origin/builder-outbox already has artifacts/claude-k1a-20260926/run or a live instance is labelled claude-creativechat-k1a.

YOUR TASK: k1a and k1b, the registered run (does the creative writer answer more usefully when it also sees the chat? does keeping a finished list or poem whole fix the cut-off last items?). The thread wrote the code: run it, never edit it. If something breaks, copy back what exists, destroy, and report the exact error and traceback.
READ FIRST (origin/main): artifacts/claude-k1a-20260926/PASSMARKS-k1a.md and the docstrings of scripts/claude_k1a_cre.py, scripts/claude_k1b_cre.py and scripts/claude_k1ab_cre.py.
TEST-ONLY, never open, print or quote: artifacts/claude-k1apanel-20260926 (only the runner reads it) and the creative_judge.jsonl / creative_judge_u.jsonl the scorers write. Run it ONCE.
Needs: torch with CUDA, transformers, plain MiniCPM5-1B at revision 87179e5c1f455ef22e6223592d2d61351b525bfc and all-MiniLM-L6-v2 (kit section C; no other model), 0.2c's sleep adapter.

1. Tree (stream, never stage on the Mac):
   git archive origin/main scripts design/v3/60-listener artifacts/claude-gram360-20260925 artifacts/claude-relationtable-20260922 artifacts/claude-table237-20260922 artifacts/fable-abstain76-20260921 artifacts/fable-self122-20260922 artifacts/claude-e2e02c-20260926/SEAL-code.sha256.txt artifacts/claude-k1a-20260926 artifacts/claude-k1apanel-20260926 artifacts/claude-panel382-dev-20260925 | gzip | ssh <rental> 'mkdir -p ~/tree && gunzip | tar -x -C ~/tree'
   Then self122_head.pt as the kit says (sha256 5ca02173...), and from builder-outbox the sidecar: git show origin/builder-outbox:artifacts/claude-e2e02c-20260926/run/sleep/adapter02c.json | ssh <rental> 'mkdir -p ~/adapter && cat > ~/adapter/adapter02c.json'
2. Adapter (a file read on BensPC over ssh; nothing runs on BensPC's GPU):
   scp -3 benspc:C:/Users/benja/lis301/work/e2e02c/tree/artifacts/claude-e2e02c-20260926/run/sleep/adapter02c.pt <rental>:adapter/adapter02c.pt
   If scp -3 fails, use one mktemp dir on the Mac and remove it by exact path right after. On the rental: sha256sum ~/adapter/adapter02c.pt must be a33211dc9bdb4e26bc7161b62147cb4dfc04fb605ba1aecbb26948f86e7936f5, else stop with ADAPTER-MISMATCH. If BensPC can't be reached, stop with NO-ADAPTER (do not run without it).
3. Setup: kit section C (pip, snapshot_download with revision='87179e5c1f455ef22e6223592d2d61351b525bfc'; record BASE and the commit hash; the route122 check must not raise). Then, from ~/tree:
   export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1
   sha256sum -c artifacts/claude-k1a-20260926/SEAL.sha256.txt                 -> every line OK, else stop with SEAL-MISMATCH
   sha256sum -c --ignore-missing artifacts/claude-e2e02c-20260926/SEAL-code.sha256.txt  -> every present line OK, else stop
   (cd artifacts/claude-k1apanel-20260926 && sha256sum -c SEAL.sha256.txt)    -> OK, else stop with SEAL-MISMATCH
   python -B scripts/claude_k1a_test.py      -> "k1a tests: 7/7 OK", else stop
   python -B scripts/claude_k1b_test.py      -> "k1b tests: 5/5 OK", else stop
   python -B scripts/claude_k1ab_test.py     -> "k1ab tests: 4/4 OK", else stop
   python -B scripts/claude_mu402.py --selftest   -> "mu402 selftest 7/7 ok", else stop
   DEV GATE (readable DEV data, 3 items): SLEEP02C_ADAPTER=$HOME/adapter/adapter02c.pt python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel creative --panel-dir artifacts/claude-panel382-dev-20260925/creative --arm claude_k1a_cre:build_null_k1a --name K --model NULL --gen-model BASE --out devk1a > logdev.txt 2>&1
   SLEEP02C_ADAPTER=$HOME/adapter/adapter02c.pt python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel creative --panel-dir artifacts/claude-panel382-dev-20260925/creative --arm claude_k1ab_cre:build_null_k1ab --name KB --model NULL --gen-model BASE --out devk1a > logdevkb.txt 2>&1
   -> each must exit 0 with 3 "[382/creative/<name>]" lines, and "k1a: creative writer = install_creative_k1a" in logdev.txt, "k1ab: creative writer = install_creative_k1ab" in logdevkb.txt; otherwise stop with DEV-FAIL, copy both logs back, destroy, report the traceback in full.
4. The six arms, each launched ONCE, each with its own log (P = artifacts/claude-k1apanel-20260926/creative, OUT = outk1a, AD = $HOME/adapter/adapter02c.pt). On a 5090 launch all six at once; on a 4090 launch X, K, B first and KB, KB0, T when those three have exited (per-turn seeds make the order irrelevant):
   X:   nohup setsid env SLEEP02C_ADAPTER=AD python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel creative --panel-dir P --arm claude_mu402:build_null02c --name X --model NULL --gen-model BASE --out OUT > logX.txt 2>&1 &
   K:   nohup setsid env SLEEP02C_ADAPTER=AD python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel creative --panel-dir P --arm claude_k1a_cre:build_null_k1a --name K --model NULL --gen-model BASE --out OUT > logK.txt 2>&1 &
   B:   nohup setsid env SLEEP02C_ADAPTER=AD python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel creative --panel-dir P --arm claude_k1b_cre:build_null_k1b --name B --model NULL --gen-model BASE --out OUT > logB.txt 2>&1 &
   KB:  nohup setsid env SLEEP02C_ADAPTER=AD python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel creative --panel-dir P --arm claude_k1ab_cre:build_null_k1ab --name KB --model NULL --gen-model BASE --out OUT > logKB.txt 2>&1 &
   KB0: nohup setsid env -u SLEEP02C_ADAPTER python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel creative --panel-dir P --arm claude_k1ab_cre:build_null_k1ab --name KB0 --model NULL --gen-model BASE --out OUT > logKB0.txt 2>&1 &
   T:   nohup setsid env -u SLEEP02C_ADAPTER python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel creative --panel-dir P --arm twin --name T --model BASE --gen-model BASE --out OUT > logT.txt 2>&1 &
   (write AD out as the full path.)
   V1 (check each log as soon as its first "[382/creative/" line appears):
     logX, logK, logB, logKB: "mu402: adapter loaded = /.../adapter02c.pt"; logKB0: "mu402: adapter loaded = none (B = 0, base 1B)".
     logK only: "k1a: creative writer = install_creative_k1a". logB only: "k1b: creative writer = install_creative_k1b". logKB and logKB0 only: "k1ab: creative writer = install_creative_k1ab". logX: none of those three lines.
     If any check fails: kill every arm by exact PID, copy back the logs, destroy, stop with V1-FAIL. A "refusing to load" error: same.
   Progress: each log prints one "[382/creative/<arm>] kc-NN" line per item (60 each).
5. When all six exit 0 (counts only are printed; never open the files these write):
   python -B scripts/claude_panel382_run.py --panel creative --panel-dir P --score OUT --names K,X,B,KB,KB0,T
   python -B scripts/claude_k1a_score.py --dedupe OUT
6. Copy back to the Mac as artifacts/claude-k1a-20260926/run/: OUT/creative_{K,X,B,KB,KB0,T}.jsonl, creative_judge.jsonl, creative_key.json, creative_judge_u.jsonl, creative_key_u.json, summary_creative.json, and log{X,K,B,KB,KB0,T}.txt, and devk1a/creative_K.jsonl, devk1a/creative_KB.jsonl, logdev.txt, logdevkb.txt as run/dev/ (force-add; artifacts/ is git-ignored). Check sizes and sha256 match before destroying.
7. RESULTS-rent.md in artifacts/claude-k1a-20260926/: credit number, GPU name, BASE commit hash, the seal/test/selftest lines, the adapter sha256 line, the V1 lines, rows per arm (expected 60 items each), exit codes, wall minutes per arm, median ms per turn per arm, the two scorers' printed counts, dollars. Quote no reply. Append one ledger line (cat >> artifacts/fable-predictions-ledger.md).
Never push weights (the adapter stays off git).
PUSH: artifacts/claude-k1a-20260926/run artifacts/claude-k1a-20260926/RESULTS-rent.md artifacts/fable-predictions-ledger.md
