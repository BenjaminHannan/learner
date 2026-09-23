VAST RESCUE (director, 2026-09-23 18:40 UTC). Small, urgent task on Ben's Mac. Read the vast key only as $(cat ~/.config/vastai/vast_api_key); never print it or any key.
Context: own-m1-train rented an RTX 5090 (host 180.189.55.38, $0.485/hr, reliability 89.66%). At about 18:37 UTC vast.ai showed it "Offline / not running": the host dropped off. Account credit is $6.39.
1. Run `vastai show instances --raw` and write a table (id, gpu, actual_status, cur_state, public_ipaddr, reliability, dph, label) to runs/000-vast-rescue/instances.txt, with no secrets.
2. Destroy (by exact instance id) every instance whose public IP is 180.189.55.38, or whose actual_status is offline / exited / not running. Never destroy a running, healthy instance. Log each id you destroyed.
3. Find the own-m1-train builder process on the Mac (pgrep -fl own-m1). If it's still alive and waiting on the dead box, kill only the exact PIDs of that task's runner and its children, then remove ~/premonition-watch/queue/own-m1-train.running (or the watcher's equivalent marker) so it's not treated as running.
4. Append a ledger line to artifacts/fable-predictions-ledger.md: the cost of the dead rental (from vastai's billing, or $0.485/hr x minutes alive if billing can't be read).
5. Final line: RESCUED <ids destroyed> or NOTHING-TO-DESTROY.
PUSH: runs/000-vast-rescue/instances.txt artifacts/fable-predictions-ledger.md
