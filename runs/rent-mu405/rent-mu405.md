COMMON RULES (the "Making things up about you" thread, Claude, wrote this task on 2026-09-26). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Follow ALL of origin/main:design/v3/30-modes/330-rent-kit.md (streaming, rental rules, setup, independence, labels). Report in your final reply: verdict first, integer counts, every deviation.
GPU: rent
BUDGET: $0.35 for this whole task, re-rents included (from Ben's $2 for this thread, 12:59 UTC 09-26; about $1.06 already spent on mu-402 and mu-404; the Director keeps the ledger and may lower this). Label: claude-madeup-mu405.
DISK: 1 (nothing large touches the Mac; no reader, no adapter, no weights moved)
CREDIT GATE (first): `vastai show user --raw` and report ONLY the balance/credit number. Read the key only as $(cat ~/.config/vastai/vast_api_key); never print it.
RENTAL RULES: RTX 5090 first, else 4090; reliability >= 0.98. Keep a running total of dph x hours; at $0.30 kill running commands by exact PID, copy back what exists, destroy, stop with BUDGET-STOP. Not running within 6 min or no log progress for 10 min: destroy and try another host (max 3 rentals). Launch runs detached (nohup/setsid), each in its OWN ssh command (never chain several `&` launches in one command). Destroy at the end and confirm it is gone. Append a ledger line.
TIME CAP: 60 minutes on the rental. If reached: stop by exact PID, copy back what exists, destroy, report "partial".
DUPLICATE GATE: stop with DUPLICATE if origin/builder-outbox already has artifacts/claude-mu405-20260926/run or a live instance is labelled claude-madeup-mu405.

YOUR TASK: mu-405, one registered run with four arms (N, K, W, H) of the plain MiniCPM5-1B talker. The thread wrote the code: run it, never edit it. If something breaks, copy back what exists, destroy, and report the exact error and traceback. DEV data only: the panel artifacts/claude-mu405-20260926/panel is readable dev data. No TEST-ONLY panel or bank is involved.
READ FIRST (origin/main): artifacts/claude-mu405-20260926/PASSMARKS.md and the docstring of scripts/claude_mu405_talk.py.
Needs: torch with CUDA, transformers, plain MiniCPM5-1B at revision 87179e5c1f455ef22e6223592d2d61351b525bfc only (kit section C; no other model; the MiniLM download and the route122 check in section C are not needed for this task).

1. Tree (stream, never stage on the Mac):
   git archive origin/main scripts artifacts/claude-mu405-20260926 | gzip | ssh <rental> 'mkdir -p ~/tree && gunzip | tar -x -C ~/tree'
2. Setup: kit section C pip line, then snapshot_download('openbmb/MiniCPM5-1B', revision='87179e5c1f455ef22e6223592d2d61351b525bfc'); record BASE, its commit hash and torch.__version__. Then, from ~/tree:
   export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1
   sha256sum -c artifacts/claude-mu405-20260926/SEAL.sha256.txt       -> every line OK, else stop
   python -B scripts/claude_mu405_talk.py --selftest                    -> "mu405 selftest 6/6 ok", else stop
   python -B scripts/claude_mu405_talk.py --count-prompts --panel artifacts/claude-mu405-20260926/panel/items.jsonl --facts artifacts/claude-mu405-20260926/facts.jsonl   -> record the JSON line; K and W with_all_3 must be 300 each, else stop
3. The four arms, each launched ONCE in its own ssh command, all at the same time on the one GPU, each with its own log (P = artifacts/claude-mu405-20260926/panel/items.jsonl, F = artifacts/claude-mu405-20260926/facts.jsonl, OUT = out405):
   nohup setsid python -B scripts/claude_mu405_talk.py --panel P --facts F --model BASE --arm N --out OUT > logN.txt 2>&1 &
   the same with --arm K > logK.txt, --arm W > logW.txt, --arm H > logH.txt
   Progress: each log prints one "[mu405/<arm>] mu405-NN (n/60)" line per chat (60 each). Each log ends with a JSON line (rows_session2 must be 300).
4. Copy back to the Mac as artifacts/claude-mu405-20260926/run/: OUT/talk_N.jsonl, talk_K.jsonl, talk_W.jsonl, talk_H.jsonl, and logN.txt, logK.txt, logW.txt, logH.txt (force-add; artifacts/ is git-ignored). Check sizes and sha256 match before destroying.
5. RESULTS-rent.md in artifacts/claude-mu405-20260926/: credit number, GPU name, torch version, BASE commit hash, the seal/selftest/count-prompts lines, each log's last JSON line, exit codes, wall minutes per arm, dollars, every deviation. Append one ledger line (cat >> artifacts/fable-predictions-ledger.md).
Never push weights.
PUSH: artifacts/claude-mu405-20260926/run artifacts/claude-mu405-20260926/RESULTS-rent.md artifacts/fable-predictions-ledger.md
