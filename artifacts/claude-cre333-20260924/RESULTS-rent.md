# rent-333-creative: REGISTERED run of exp 333 (creative v1) — HOST-FAIL, nothing ran

No arm ran. Four rentals were attempted (the kit maximum); none yielded a working
Linux GPU with shell access, so the panel seal check, SEAL-code-rent, arms B/P/T
and the score step were never started. Month-end code untouched (no edits
anywhere). Panel items never opened, printed, or quoted; judge_creative.jsonl was
never produced and never opened; no reply is quoted anywhere in this file.

## Preconditions checked on the Mac (integer counts)

- `git fetch -q origin main builder-outbox`: ok.
- DUPLICATE check: `git ls-tree -r origin/builder-outbox --name-only` lists
  `artifacts/claude-cre333-20260924/PASSMARKS.md`,
  `RESULTS-run.md`, `SEAL-code.sha256.txt` and no `run/` dir: NOT a duplicate,
  proceed was correct.
- Credit at start: $9.97 (task BUDGET $1.50). No instance labelled
  `rent-333-creative` was live at start (1 unrelated instance live:
  `rent-338-chat`).
- Code tree built per the rent kit: `git archive origin/builder-outbox` + `git
  archive origin/main` (main on top) + `self122_head.pt` copied in, sha256
  `5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25` (match).
  Packed `/tmp/cre333_tree.tgz` (155 MB). Never uploaded (no shell anywhere).
- Panel: `artifacts/claude-creativepanel333-20260924/` present in the tree
  (filenames only: `README.md`, `SEAL.sha256.txt`, `audit.jsonl`,
  `items.jsonl`); items never opened.

## Rentals: 4 of 4 allowed, 0 usable

| # | Offer (RTX 5090) | dph ($/h) | Contract | Outcome |
|---|---|---|---|---|
| 1 | 45669552 (KR, 16 cores, 505 GB, 296/364 Mbps, rel 0.9976) | 0.4690 | 52415556 | `success: false` on create; destroyed, $0 |
| 2 | 50236329 (CN, 24 cores, 150 GB, 998/877 Mbps, rel 0.9935) | 0.5347 | 52415599 | `success: true`, reached `running`, but the ssh proxy tunnel never came up (`vastai logs`: `Error: remote port forwarding failed for listen port 15598`, repeating; proxy `Permission denied (publickey)` x10 over ~6 min; reboot did not fix; `vastai copy` via rsync daemon worked, proving the host was up but container shell unreachable); destroyed, ~0.17 h x $0.5347 ≈ $0.09 |
| 3 | 43165153 (US, 32 cores, 282 GB, 242/38 Mbps, rel 0.9953) | 0.4727 | 52417098 | `success: false` on create; destroyed, $0 |
| 4 | 49837280 (US-CA, 24 cores, 684 GB, 460/147 Mbps, rel 0.9848) | 0.4994 | 52417106 | `success: false` on create; destroyed, $0 |

All creates used image `pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime`, `--disk
80`, `--label rent-333-creative`, `--ssh`. Post-destroy `vastai show instances`
confirms 0 `rent-333-creative` instances live (3 unrelated instances running).

## Spend

- Total ≈ $0.09 over 4 rentals (cap $1.50; trip wire never reached).
- Credit was $9.97 at rental; nothing else billed by this task.

## Arms run: 0 of 3. Scorer summary: none (no `arm_*.jsonl` exists anywhere)

- Wall time per arm: B/P/T not started; score step not started.
- GPU: none (the single `running` instance never ran `nvidia-smi`; name unknown).
- BASE model commit hash: never resolved (snapshot_download never ran; the
  kit's expected value `87179e5c1f455ef22e6223592d2d61351b525bfc` is unverified).
- `SEAL-code-rent.sha256.txt`: not written (the task orders it written on the
  rental before running; no working rental existed).
- Panel `SEAL.sha256.txt` check: not run (needs the rental).

## Diagnosis

Three hosts returned `success: false` at create time (immediately destroyable
stub contracts; no shell, no billing), and the one host that reached `running`
had a persistently broken ssh proxy tunnel (`remote port forwarding failed`),
so no command ever executed on any GPU. This is rental-lottery failure, not a
creative-agent result. The Windows blocker from e2e-333-creative (`import
resource` on BensPC) was never re-tested here; Linux would have avoided it, but
no Linux shell was ever obtained.

What it means (plain high-school English): the test never started — zero chats,
zero answers, zero grades. This says nothing about whether creative v1 works.

What it doesn't mean: the creative agent, 292t, the panel, and BASE are not
shown broken — none got to execute. The twin arm is not shown broken either.
