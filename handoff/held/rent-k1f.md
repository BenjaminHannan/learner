STATUS: HELD. Waiting on Ben's yes (through the Thread manager) to test LFM2.5-1.2B-Instruct as the creative writer. The "Creative answers in chat" thread moves this file to handoff/queue/ only then. Do not run it from here.

COMMON RULES (the "Creative answers in chat" thread, Claude, wrote this task on 2026-09-26). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Follow ALL of origin/main:design/v3/30-modes/330-rent-kit.md (streaming, rental rules, setup, TORCH rules, independence). Report in your final reply: verdict first, integer counts, every deviation.
GPU: rent
BUDGET: $0.60 for this whole task, re-rents included (from Ben's $2 for this thread; $0.56 spent on rent-k1a and rent-k1c; standing caps <= $4 per job; the Director keeps the ledger and may lower this). Label: claude-creativechat-k1f.
DISK: 1 (only small files touch the Mac: the 16.5 MB adapter goes BensPC -> rental with `scp -3`; nothing else is staged)
CREDIT: record `vastai show user --raw`'s balance number only (vast auto-refills; not a gate). Read the key only as $(cat ~/.config/vastai/vast_api_key); never print it.
RENTAL RULES: RTX 5090 first, else 4090; reliability >= 0.98; disk >= 40 GB. Keep a running total of dph x hours; at $0.55 kill running commands by exact PID, copy back what exists, destroy, stop with BUDGET-STOP. Not running within 6 min or no log progress for 10 min: destroy and try another host (max 3 rentals). Launch runs detached (nohup/setsid) so they survive SSH closing. Destroy at the end and confirm it is gone. Never destroy an instance whose label this task did not create. Append a ledger line.
TIME CAP: 75 minutes on the rental. If reached: stop by exact PID, copy back what exists, destroy, report "partial".
DUPLICATE GATE: stop with DUPLICATE if origin/builder-outbox already has artifacts/claude-k1f-20260926/run or a live instance is labelled claude-creativechat-k1f.

YOUR TASK: k1f, the registered run (does the creative writer answer more usefully when LFM2.5-1.2B-Instruct writes its drafts instead of MiniCPM5-1B, and how does that compare with plain same-size models?). This is an eval-only job (no training): the image's torch may stay; record torch.__version__. The thread wrote the code: run it, never edit it. If something breaks, copy back what exists, destroy, and report the exact error and traceback.
READ FIRST (origin/main): artifacts/claude-k1f-20260926/PASSMARKS-k1f.md and the docstrings of scripts/claude_k1f_cre.py and scripts/claude_k1f_score.py.
TEST-ONLY, never open, print or quote: artifacts/claude-k1fpanel-20260926 (only the runner reads it), the creative_*.jsonl run files of the panel run, and the creative_judge*.jsonl packets the scorers write. Run each arm ONCE on the panel. The DEV files (artifacts/claude-k1a-dev-20260926 and the devk1f outputs) are readable, but report counts only.
Needs: torch with CUDA, transformers, plain MiniCPM5-1B at revision 87179e5c1f455ef22e6223592d2d61351b525bfc, all-MiniLM-L6-v2 (kit section C), Qwen/Qwen3.5-2B at revision 15852e8c16360a2fea060d615a32b45270f8a8fc and LiquidAI/LFM2.5-1.2B-Instruct at revision 0f604ada3f766f9f257460c4c9f0b5d6f69d431b (Benchmarks' pins; Ben approved both 02:12 UTC 2026-09-25; downloaded on the rental only, never on the Mac or BensPC), and 0.2c's sleep adapter. No other model.

1. Tree (stream, never stage on the Mac):
   git archive origin/main scripts design/v3/60-listener artifacts/claude-gram360-20260925 artifacts/claude-relationtable-20260922 artifacts/claude-table237-20260922 artifacts/fable-abstain76-20260921 artifacts/fable-self122-20260922 artifacts/fable-self127-20260922 artifacts/claude-e2e02c-20260926/SEAL-code.sha256.txt artifacts/claude-k1c-20260926/JUDGE-k1c.md artifacts/claude-k1f-20260926 artifacts/claude-k1fpanel-20260926 artifacts/claude-k1a-dev-20260926 | gzip | ssh <rental> 'mkdir -p ~/tree && gunzip | tar -x -C ~/tree'
   Then self122_head.pt as the kit says (sha256 5ca02173...), and from builder-outbox the sidecar: git show origin/builder-outbox:artifacts/claude-e2e02c-20260926/run/sleep/adapter02c.json | ssh <rental> 'mkdir -p ~/adapter && cat > ~/adapter/adapter02c.json'
2. Adapter (a file read on BensPC over ssh; nothing runs on BensPC's GPU):
   scp -3 benspc:C:/Users/benja/lis301/work/e2e02c/tree/artifacts/claude-e2e02c-20260926/run/sleep/adapter02c.pt <rental>:adapter/adapter02c.pt
   If scp -3 fails, use one mktemp dir on the Mac and remove it by exact path right after. On the rental: sha256sum ~/adapter/adapter02c.pt must be a33211dc9bdb4e26bc7161b62147cb4dfc04fb605ba1aecbb26948f86e7936f5, else stop with ADAPTER-MISMATCH. If BensPC can't be reached, stop with NO-ADAPTER (do not run without it).
3. Setup: kit section C (pip line; the route122 check must not raise). Downloads, with HF_HUB_OFFLINE=0 for this one command:
   python -c "from huggingface_hub import snapshot_download as s; print(s('openbmb/MiniCPM5-1B', revision='87179e5c1f455ef22e6223592d2d61351b525bfc')); print(s('sentence-transformers/all-MiniLM-L6-v2')); print(s('Qwen/Qwen3.5-2B', revision='15852e8c16360a2fea060d615a32b45270f8a8fc')); print(s('LiquidAI/LFM2.5-1.2B-Instruct', revision='0f604ada3f766f9f257460c4c9f0b5d6f69d431b'))"
   BASE, Q2DIR, L12DIR = the first, third and fourth printed paths. Then, from ~/tree:
   export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1
   sha256sum -c artifacts/claude-k1f-20260926/SEAL.sha256.txt                 -> every line OK, else stop with SEAL-MISMATCH
   sha256sum -c --ignore-missing artifacts/claude-e2e02c-20260926/SEAL-code.sha256.txt  -> every present line OK, else stop
   (cd artifacts/claude-k1fpanel-20260926 && sha256sum -c SEAL.sha256.txt)    -> OK, else stop with SEAL-MISMATCH
   python -B scripts/claude_k1a_test.py            -> "k1a tests: 7/7 OK", else stop
   python -B scripts/claude_k1f_test.py            -> "k1f tests: 6/6 OK", else stop
   python -B scripts/claude_k1f_score.py --selftest -> last line "k1f score selftest 5/5 ok", else stop
   python -B scripts/claude_k1rival_score.py --selftest -> "k1rival score selftest 4/4 ok", else stop
   python -B scripts/claude_mu402.py --selftest    -> "mu402 selftest 7/7 ok", else stop
   DEV GATE (readable DEV data, 40 chats; D = artifacts/claude-k1a-dev-20260926; AD = the full path of ~/adapter/adapter02c.pt):
   K1F_WRITER_MODEL=L12DIR SLEEP02C_ADAPTER=AD python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel creative --panel-dir D --arm claude_k1f_cre:build_null_k1f --name F --model NULL --gen-model BASE --out devk1f > logdevF.txt 2>&1
   -> must exit 0 with 40 "[382/creative/F]" lines; logdevF.txt must contain "mu402: adapter loaded = " followed by the adapter path, and a line starting "k1f: creative writer = install_creative_k1f; writer = lfm" that contains "@0f604ada"; and among the rows of devk1f/creative_F.jsonl with "last" true, at most 2 replies equal to the fallback line (python: import claude_cre333_agent as C; compare with C.FALLBACK) and none empty (print counts only). Otherwise stop with DEV-FAIL, copy logdevF.txt and devk1f back, destroy, report the counts and any traceback in full.
4. The arms, each launched ONCE, each with its own log. P = artifacts/claude-k1fpanel-20260926/creative, OUT = outF.
   On a 5090 launch all five at once; on a 4090 launch K, F, T first and Q, L when those have exited (per-turn seeds make the order irrelevant).
   F: nohup setsid env K1F_WRITER_MODEL=L12DIR SLEEP02C_ADAPTER=AD python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel creative --panel-dir P --arm claude_k1f_cre:build_null_k1f --name F --model NULL --gen-model BASE --out OUT > logF.txt 2>&1 &
   K: nohup setsid env -u K1F_WRITER_MODEL SLEEP02C_ADAPTER=AD python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel creative --panel-dir P --arm claude_k1a_cre:build_null_k1a --name K --model NULL --gen-model BASE --out OUT > logK.txt 2>&1 &
   T: nohup setsid env -u SLEEP02C_ADAPTER -u K1F_WRITER_MODEL python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel creative --panel-dir P --arm twin --name T --model BASE --gen-model BASE --out OUT > logT.txt 2>&1 &
   Q: nohup setsid env -u SLEEP02C_ADAPTER -u K1F_WRITER_MODEL python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel creative --panel-dir P --arm twin --name Q --model Q2DIR --gen-model Q2DIR --out OUT > logQ.txt 2>&1 &
   L: nohup setsid env -u SLEEP02C_ADAPTER -u K1F_WRITER_MODEL python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel creative --panel-dir P --arm twin --name L --model L12DIR --gen-model L12DIR --out OUT > logL.txt 2>&1 &
   (Launch each arm with its own ssh command.)
   V1 (check each log as soon as its first "[382/creative/" line appears):
     logF, logK: "mu402: adapter loaded = /.../adapter02c.pt".
     logF only: a line starting "k1f: creative writer = install_creative_k1f; writer = lfm" containing "@0f604ada", and no "k1a:" line.
     logK only: "k1a: creative writer = install_creative_k1a", and no "k1f:" line.
     logT, logQ, logL: "twinb: the plain twin is Twin336b" and no "mu402:", "k1a:" or "k1f:" line.
     If any check fails: kill every arm by exact PID, copy back the logs, destroy, stop with V1-FAIL. A "refusing to load" error: same.
   Progress: each log prints one "[382/creative/<arm>] <item id>" line per item (100 per arm).
5. When all five runs exit 0 (counts only are printed; never open the files these write):
   python -B scripts/claude_panel382_run.py --panel creative --panel-dir artifacts/claude-k1fpanel-20260926/creative --score outF --names F,K,T,Q,L
   python -B scripts/claude_k1f_score.py --dedupe outF
6. Copy back to the Mac as artifacts/claude-k1f-20260926/run/: from outF, creative_{F,K,T,Q,L}.jsonl, creative_judge.jsonl, creative_key.json, creative_judge_u.jsonl, creative_key_u.json, summary_creative.json, grammar_creative_F.jsonl, and the five logs; and devk1f/ (everything in it) with logdevF.txt as run/dev/ (force-add; artifacts/ is git-ignored). Check sizes and sha256 match before destroying.
7. RESULTS-rent.md in artifacts/claude-k1f-20260926/: credit number, GPU name, torch/transformers/python versions, BASE/Q2DIR/L12DIR paths and commit hashes, the seal/test/selftest lines, the adapter sha256 line, the DEV gate lines and counts, the V1 lines, rows per arm (expected 100 items), exit codes, wall minutes per arm, median ms per turn per arm, peak GPU memory seen, the two scorer outputs, dollars. Quote no reply. Append one ledger line (cat >> artifacts/fable-predictions-ledger.md).
Never push weights (the adapter stays off git).
PUSH: artifacts/claude-k1f-20260926/run artifacts/claude-k1f-20260926/RESULTS-rent.md artifacts/fable-predictions-ledger.md
