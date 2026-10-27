# Notebook-2 K2 reader run on the Radeon PC (RX 7700 XT 12 GB) via llama.cpp Vulkan
Uses the K2-Horizon-3.7B Q4_K_M GGUF and llama.cpp b11913 Vulkan build already on the PC (Windows). No trust_remote_code:
stage1.py's `k2raw` backend renders K2's no-think prompt itself and calls llama-server's native /completion.
Queue: after "Make the thinking block pay off" says free; tell "Let the model practice puzzles, then sleep" when done.
Etiquette: write C:\Users\timot\GPU-BUSY.txt and C:\Users\timot\pc-jobs\nb2-k2.md (with a `log:` line); clear both at the end.

1. On the PC (Windows), start the server (paths from the Mac session's notes):
   llama-server.exe -m <K2-Horizon-3.7B-Q4_K_M.gguf> -ngl 99 -c 32768 --host 127.0.0.1 --port 18090 -np 1
2. Harness: run it on the M1 through an ssh tunnel (`ssh -fN -L 18090:127.0.0.1:18090 radeonpc`), from the same sparse
   checkout as RUN-M1.md (~/learner-ops/nb2-src/gaps/notebook2, venv ~/learner-ops/nb2-venv, EMB_CACHE ~/learner-ops/nb2-emb):
   python stage1.py --backend k2raw --base-url http://127.0.0.1:18090/v1 --reader k2q4 --retriever S2 --out-dir ~/learner-ops/nb2-out --limit 1
   (smoke: short answers in pred), then the same without --limit under nohup (~840 calls; ~1.5-2 h at 2100 tok/s prompt).
3. Commit ~/learner-ops/nb2-out/rows_k2q4.jsonl to gaps/notebook2/results/k2q4/ on branch claude/project-thread-qhf0vt; stop the server.
