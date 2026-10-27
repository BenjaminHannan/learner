COMMON RULES (the "Making things up about you" thread, Claude, wrote this task on 2026-09-26). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Follow ALL of origin/main:design/v3/30-modes/330-rent-kit.md (streaming, rental rules, setup, independence, labels). Report in your final reply: verdict first, integer counts, every deviation.
GPU: rent
BUDGET: $1.00 for this whole task, re-rents included (from Ben's $2 for this thread, 12:59 UTC 09-26; $0.36 already spent on mu-402; the Director keeps the ledger and may lower this). Label: claude-madeup-mu404.
DISK: 1 (nothing large touches the Mac: the reader comes from the Director's depot rental-to-rental; no adapter in this task)
CREDIT GATE (first): `vastai show user --raw` and report ONLY the balance/credit number. Under $3.00: rent nothing, stop with CREDIT-STOP. Re-check before any re-rent. Read the key only as $(cat ~/.config/vastai/vast_api_key); never print it.
RENTAL RULES: RTX 5090 first, else 4090; reliability >= 0.98. Keep a running total of dph x hours; at $0.90 kill running commands by exact PID, copy back what exists, destroy, stop with BUDGET-STOP. Not running within 6 min or no log progress for 10 min: destroy and try another host (max 3 rentals). Launch runs detached (nohup/setsid) so they survive SSH closing. Destroy at the end and confirm it is gone. Append a ledger line.
TIME CAP: 90 minutes on the rental. If reached: stop by exact PID, copy back what exists, destroy, report "partial".
DUPLICATE GATE: stop with DUPLICATE if origin/builder-outbox already has artifacts/claude-mu403-20260926/run or a live instance is labelled claude-madeup-mu404.
READER ROUTE (as rent-sf401's RELEASE line): READER319 comes from the Director's depot rental (artifacts/claude-depot-20260926/REPORT.md on builder-outbox names the instance; copy inside vast: `vastai copy <depot_id>:/root/reader319 <your_id>:/root/reader319`). Never write to or stop the depot. If the depot is not running: stop with NO-READER before renting (the thread will ask the Director for another route); do not rsync from the Mac.

YOUR TASK: mu-404 + mu-403, one registered run with four arms (R control, F no notebook facts in the 1B prompts, P the made-up-claims fix, T plain 1B). The thread wrote the code: run it, never edit it. If something breaks, copy back what exists, destroy, and report the exact error and traceback. DEV data only: the panel artifacts/claude-mu403-20260926/devchat is readable dev data. No TEST-ONLY panel or bank is involved.
READ FIRST (origin/main): artifacts/claude-mu403-20260926/PASSMARKS.md and the docstring of scripts/claude_mu404.py.
Needs: torch with CUDA, transformers, plain MiniCPM5-1B at revision 87179e5c1f455ef22e6223592d2d61351b525bfc and all-MiniLM-L6-v2 (kit section C; no other model), the lis-319 reader (READER ROUTE).

1. Tree (stream, never stage on the Mac):
   git archive origin/main scripts design/v3/60-listener artifacts/claude-gram360-20260925 artifacts/claude-relationtable-20260922 artifacts/claude-table237-20260922 artifacts/fable-abstain76-20260921 artifacts/fable-self122-20260922 artifacts/fable-self127-20260922 artifacts/claude-e2e02c-20260926/SEAL-code.sha256.txt artifacts/claude-mu403-20260926 | gzip | ssh <rental> 'mkdir -p ~/tree && gunzip | tar -x -C ~/tree'
   Then self122_head.pt as the kit says (sha256 5ca02173...).
2. Reader: READER ROUTE above to /root/reader319; `sha256sum /root/reader319/model.safetensors` must be e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76, else destroy and stop with READER-FAIL.
3. Setup: kit section C (pip, snapshot_download with revision='87179e5c1f455ef22e6223592d2d61351b525bfc'; record BASE and the commit hash; the route122 check must not raise). Then, from ~/tree:
   export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1
   sha256sum -c artifacts/claude-mu403-20260926/SEAL.sha256.txt              -> every line OK, else stop
   sha256sum -c --ignore-missing artifacts/claude-e2e02c-20260926/SEAL-code.sha256.txt  -> every present line OK, else stop
   python -B scripts/claude_mu404.py --selftest                              -> "mu404 selftest 5/5 ok", else stop
   python -B scripts/claude_pick403.py                                       -> "pick403 selftest 13/13 ok", else stop
   python -B scripts/claude_readersha_wrap.py --selftest                     -> its OK line, else stop
4. The four arms, each launched ONCE, all at the same time on the one GPU, each with its own log (P = artifacts/claude-mu403-20260926/devchat, OUT = out404, RS = e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76):
   R: nohup setsid env -u SLEEP02C_ADAPTER READER_SHA=RS python -B scripts/claude_readersha_wrap.py scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel chat --panel-dir P --arm claude_mu404:build_r --name R --model /root/reader319 --gen-model BASE --out OUT > logR.txt 2>&1 &
   F: the same with --arm claude_mu404:build_f --name F > logF.txt
   P: the same with --arm claude_mu404:build_p --name P > logP.txt
   T: nohup setsid env -u SLEEP02C_ADAPTER python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel chat --panel-dir P --arm twin --name T --model BASE --gen-model BASE --out OUT > logT.txt 2>&1 &
   V0 (check at once): logR, logF and logP each start with "readersha: reader weights sha256 e688e1b2... match READER_SHA" and contain "mu404: arm R404; adapter loaded = none", "mu404: arm F404-nofacts; adapter loaded = none", "mu404: arm P403-sysline; adapter loaded = none" respectively. If any is wrong: kill all four by exact PID, copy back the logs, destroy, stop with V0-FAIL.
   Progress: each log prints one "[382/chat/<arm>] dev403-NN" line per conversation (80 each).
5. When all four exit 0: logR, logF and logP must each end with a "mu404: facts {...}" line. Then: python -B scripts/claude_panel382_run.py --panel chat --panel-dir P --score OUT --names R,F,P,T (counts only). Never open the chat_pair_*, chat_turns_* or grammar_* files it writes.
6. Copy back to the Mac as artifacts/claude-mu403-20260926/run/: OUT/chat_R.jsonl, chat_F.jsonl, chat_P.jsonl, chat_T.jsonl, summary_chat.json, and logR.txt, logF.txt, logP.txt, logT.txt (force-add; artifacts/ is git-ignored). Check sizes and sha256 match before destroying.
7. RESULTS-rent.md in artifacts/claude-mu403-20260926/: credit number, GPU name, BASE commit hash, reader sha line, the seal/selftest lines, the V0 lines, the end-of-run "mu404: facts" lines, rows per arm (expected: every turn of 80 conversations = 446), exit codes, wall minutes per arm, median ms per turn per arm, summary_chat.json's counts, dollars. Append one ledger line (cat >> artifacts/fable-predictions-ledger.md).
Never push weights.
PUSH: artifacts/claude-mu403-20260926/run artifacts/claude-mu403-20260926/RESULTS-rent.md artifacts/fable-predictions-ledger.md
