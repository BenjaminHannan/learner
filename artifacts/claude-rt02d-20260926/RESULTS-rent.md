# RESULTS-rent.md — rt-02d registered run, rental attempt (PARTIAL, infra stop)

Task: handoff/queue/rent-rt02d.md (Plain-English puzzles thread, 2026-09-26).
Verdict: PARTIAL — no registered PASS/FAIL. The dev gate passed, then the
rental's ssh proxy died mid-step-2 and the instance was unrecoverable, so no
panel/negatives/general/chatdev/score output exists. Nothing was copied back
(ssh dead); the rental was destroyed to cap spend. Sealed code was run, never
edited. No TEST-ONLY panel file was opened, printed or quoted (only directory
listings and the runners' own summary lines below).

## Rentals (label claude-plainpuzzles-rt02d; budget $1.50, 3 rentals used of max 4)

- 52760176 (offer 43165154, RTX 5090, $0.4060/hr, host US): created 14:19:15
  UTC, create returned success False, still "loading" past 6 min → destroyed
  ~14:27 per kit rule. Never ran. ~$0.
- 52761382 (offer 49024471, RTX 5090, $0.4690/hr, host KR): created 14:27:06,
  success True, running ~14:30, dph $0.5037.ssh key sync broken on that host
  (key associated at API, container sshd kept refusing; reboot did not help)
  → destroyed ~14:40. ~0.17 h x $0.5037 ≈ $0.08.
- 52763126 (offer 51858235, RTX 5090, $0.4727/hr, host US-CA): created
  14:39:42, running ~14:42, ssh OK 14:43, dph $0.5630. GPU: NVIDIA GeForce
  RTX 5090. Destroyed 16:45:30, confirmed gone. ~2.05 h x $0.563 ≈ $1.15.
- Total ≈ $1.23 of $1.50. Offer search re-run before every create; cheapest
  qualifying 5090/4090 taken each time (kit filter: rel>=0.98, 8+ CPU,
  60+ GB disk, net>=200).

## Setup (all on 52763126, ~/tree unless noted)

- S1 code tree: git archive origin/builder-outbox + origin/main (main on top)
  streamed, 2.0 GB on rental; self122_head.pt scp'd (65 KB). Tar "future
  timestamp" warnings only (4 s clock skew). OK.
- S2 kit C: image torch 2.2.1 CUDA True; pip line (transformers>=5 etc.) OK;
  snapshot_download MiniCPM5-1B + all-MiniLM-L6-v2 OK; route122 check OK
  (D8, conf 0.97). BASE =
  /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc,
  commit hash 87179e5c1f455ef22e6223592d2d61351b525bfc = expected. Done ~15:02.
- S3 sleep base ckpt: fable_reasoner44.py --stage base --seed 4102 finished
  in 25.8 s; base-seed4102.pt (2560 B) copied into
  artifacts/fable-reasoner44-20260921/runs/. Done 15:04.
- S4 reader: DEPOT source (preferred path). REPORT.md on origin/builder-outbox
  14:18 UTC (depot 52755827, /root/reader319, sha e688e1b2…6a76) + depot
  running → rented, then `vastai copy 52755827:/root/reader319
  52763126:/root/reader319` launched 14:43:18. Copy nested one level
  (reader319/reader319, same as depot agent saw); flattened. All 6 files with
  exact source byte sizes (model.safetensors 2161290944 B). Verified complete
  ~14:55 (~12 min max). sha256(model.safetensors) =
  e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76 — MATCH.
- S5 adapter: streamed BensPC→Mac→rental purely by pipe (nothing kept on Mac).
  sha256(adapter02c.pt) =
  a33211dc9bdb4e26bc7161b62147cb4dfc04fb605ba1aecbb26948f86e7936f5 — MATCH;
  adapter02c.json alongside. Done 14:57.
- S6 seals: SEAL-code 02c OK, SEAL-code-rt02d OK (6/6 incl. marks), SEAL-panel
  OK (4/4). Selftests: claude_rt02d 55/55, readersha_wrap 9/9.

## Env deviation (setup repair, no sealed line touched)

The kit pip line (transformers 5.17.0) is incompatible with the image torch
2.2.1 (transformers>=5 needs torch>=2.5): first dev attempt exited 1
(AutoModelForCausalLM "PyTorch not found"). Installed torch==2.11.0+cu128
(CUDA True), then torchvision==0.26.0+cu128 (stale torchvision broke
transformers lazy import: "torchvision::nms does not exist"), then uninstalled
torchaudio 2.2.1 (stale .so broke transformers audio_utils import). Two dev
attempts failed on env with exit 1 and wrote no output files; the gate's two
clean runs started after the env was fixed.

## Runs (each under setsid/nohup with own log, one at a time, ps-checked)

- dev B0a: launched 15:39:11, done 15:59 (~20 min). Printed line:
  {"task": "dev", "name": "B0a", "rows": 55, "routed": 0}. EXIT 0.
- dev B0b: launched 16:04:11, done ~16:25 (~21 min). Printed line:
  {"task": "dev", "name": "B0b", "rows": 55, "routed": 0}. EXIT 0.
- Dev gate compare (dev files only, one-line check): 55/55 rows, 0 differing
  replies → deterministic, gate PASSES. No NONDETERMINISTIC.
- panel B0 (registered): launched 16:26:13. Rental ssh proxy began refusing
  ~16:31; still refused after 15+ min; instance reboot did not restore ssh
  (API: running, proxy: connection refused). Run outcome unknown; no output
  recovered. Steps 2b/3/4/5 never launched (ONCE rule + no access).
- VRAM peak observed during dev: 5086 MiB. Score line: none (never reached).

## Outcome

PARTIAL: setup S1–S6 green, dev gate passed, zero registered panel items
completed. Cause of stop: rental infra failure (ssh loss), then BUDGET guard
(destroyed at ~$1.23 of $1.50). run/, score/, logs/ were lost with the rental
and are NOT pushed. A retry needs a fresh rental; suggest budgeting for the
slow pace (~20 min per 55-turn B0 process on this stack).
