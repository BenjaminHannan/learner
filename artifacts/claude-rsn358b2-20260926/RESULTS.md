# rsn-358b2 results (builder claude-sleep-358b2, 2026-09-26)

Verdict: INCONCLUSIVE. B0 validity is not met at any size (copy-exact 25/39/28 vs the required >= 80/100), so per PASSMARKS.md this is a copying problem, not a reasoning one. Code sealed by the sleep research thread; run once, never edited.

Question: does putting the learned loop reasoner between the 1B's reading and the 1B's reply solve chat requests the 1B alone cannot? The 1B alone solved 0/100 at every size; the bridge solved 19/30/13, but copying is far below the validity bar, so no registered conclusion follows.

## Marks (PASSMARKS.md, integer counts)

B0 validity: 1B copy exact >= 80/100 at each size. Actual: 5x5: 25; 6x6: 39; 7x7: 28. NOT MET at any size -> INCONCLUSIVE.

B1: bridge right minus 1B-alone right >= +40/100 on 6x6 AND on 7x7. 6x6: 30 - 0 = +30. 7x7: 13 - 0 = +13. NOT MET.

B2: bridge "wrong answer given" <= 1B-alone "wrong answer given" at every size. 5x5: 8 <= 100 yes. 6x6: 7 <= 100 yes. 7x7: 9 <= 100 yes. MET (the bridge says "I couldn't" instead of guessing: 73/63/78 couldn't).

B3 report (per size: A right / couldn't / wrong-given; B the same; B stage counts; C; mean rounds):

| size | A right | A couldn't | A wrong_given | B right | B couldn't | B wrong_given | copy_exact | copy_unreadable | net_right_given_copy | internal_check_pass | reply_faithful | C right | C couldn't | C wrong_given | B_mean_rounds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | 0 | 0 | 100 | 19 | 73 | 8 | 25 | 63 | 27 | 27 | 21 | 100 | 0 | 0 | 9.05 |
| 6 | 0 | 0 | 100 | 30 | 63 | 7 | 39 | 57 | 37 | 37 | 31 | 95 | 0 | 5 | 5.21 |
| 7 | 0 | 0 | 100 | 13 | 78 | 9 | 28 | 66 | 22 | 22 | 13 | 71 | 0 | 29 | 6.21 |

n = 100 per size, seed 35900 + size, code templates. Every score read by code from the final message against the true puzzle. Transcripts: run/transcripts-5.jsonl, run/transcripts-6.jsonl, run/transcripts-7.jsonl (100 rows each: req, alone, copy, bridge).

PASS = B0, B1 and B2: not met (B0 and B1 fail). "Anything else with B0 met = FAIL": B0 is not met, so the registered verdict is INCONCLUSIVE, not FAIL.

Proved-wrong clause ("a learned reasoner in the middle beats the 1B alone on its own kind of problem" is proved wrong if B0 met and bridge minus alone <= +10 at 6x6 and 7x7): NOT APPLICABLE, B0 not met (diffs were +30 at 6x6 and +13 at 7x7 in any case, both above +10).

Note for the thread: the ceiling C (code reads the request, loop net fills it) is 100/95/71, so the loop net solves when it can read; the 1B's copy step is the bottleneck (copy_exact 25/39/28, unreadable 63/57/66). Reply faithfulness given a passed check: 21/27, 31/37, 13/22.

## Setup (sealed, verified)

- Code: `sha256sum -c artifacts/claude-rsn358b2-20260926/SEAL-code.sha256.txt` 6/6 OK on the rental. `python -B scripts/claude_rsn358b2_bridge.py selftest` -> "selftest ok". No edits.
- 1B: plain MiniCPM5-1B, openbmb/MiniCPM5-1B @ 87179e5c1f455ef22e6223592d2d61351b525bfc (kit section C expected commit), bf16, enable_thinking=False, greedy. Downloaded from Hugging Face on the rental (the approved base model, not a new model).
- Loop net: ~/premonition-models/rsn358a/loop-s1/final.pt from the Mac (25,764,244 bytes), sha256 c9f4934f2ab62a0abd0c5103c10785b6286aea9fdafabd06ebbf7727bf3ca2c4 verified on both ends before the run.
- Run (once): `python -B scripts/claude_rsn358b2_bridge.py run --model <MiniCPM5-1B dir> --ckpt /root/loop-s1-final.pt --sizes 5,6,7 --n 100 --seed 35900 --out W/b2`, compute 1.0 min (bridge.json "minutes": 1.0).
- Rental env: torch 2.8.0+cu128 (image, CUDA True), transformers 5.17.0, numpy 2.3.2 (+ safetensors, huggingface_hub, accelerate per kit C), HF_HUB_OFFLINE=1 for the run.

## Cost

- GPU: NVIDIA GeForce RTX 5090, vast.ai instance 52766179 (label claude-sleep-358b2, offer 45520225), dph $0.49444444, reliability >= 0.98, 60 GB disk.
- Rental 2026-09-26 15:01:21 UTC, destroyed 15:09:35 UTC (~8.2 min wall, ~0.137 h x $0.49444444 = ~$0.07 of the $0.40 budget; budget-stop $0.35 and 1 h 10 min never approached; 1 rental of max 3). Destroy confirmed (instance gone from `vastai show instances`).
- Credit at gate: 6.236215526269859; rental credit gate: none (Director 13:50 UTC 09-26, Ben 13:23 auto-refill; kit: no low-credit stop). Sleep research thread budget: $0.40 of its $2 (Director 14:45 ledger line).
- Copy-back sha256 (rental == Mac): bridge.json 69054ac6946784a016793520219dd951855b7bf658f3b0ec48a946ae0eff9789, transcripts-5 718fb2b31c2dde3ef65cb76d878378edf4b58eb29c18925c6f3269151aec7460, transcripts-6 69fbd5decb6f8c602532a78c05f2b07228b3ce94fd0f42c7f8b33bb15e802374, transcripts-7 4a69a9f9fbc1d9d72a2f88a87232a0defab12e037c76c82248076c826888a5, b2.log 6a3b4c4991b64957a99de3cc647cef3cddeaf8abc12e3d9b1fd1d7fd545da02e. No weights pushed.

## Every deviation

1. `git fetch -q origin main builder-outbox` failed on builder-outbox (cannot lock ref: remote is at daecec3d but local expected b2939358). origin/main fetched OK; builder-outbox state read via `git ls-remote` + `git ls-tree -r origin/builder-outbox` instead. Duplicate gate checked both: no artifacts/claude-rsn358b2-20260926/RESULTS.md on either, no live instance labelled claude-sleep-358b2 -> proceeded.
2. torch NOT pip-installed (image torch 2.8.0+cu128 with CUDA kept, per kit C "image torch if True"); installed "transformers>=5" + safetensors, huggingface_hub, accelerate, numpy -> transformers 5.17.0, numpy 2.3.2.
3. Model revision pinned to 87179e5c1f455ef22e6223592d2d61351b525bfc (kit C expected commit); the task named no revision.
4. Detached launch used `> W/b2-launch.log 2>&1 &` + `cp W/b2-launch.log W/b2.log` instead of the literal `2>&1 | tee W/b2.log`, because `nohup setsid ... &` held the requesting SSH session open (first launch command hit the 60 s client timeout even though the run had started). The run executed exactly once; b2.log is the run's stdout+stderr.
5. Billed dph $0.49444444 vs the search-listed $0.46898 for the offer; running total stayed far below the $0.35 stop.
6. Local `zsh: == not found` noise from unquoted `===` echo separators in inspection commands only; no effect on the run or artifacts.
7. Ledger appended to this worktree's artifacts/fable-predictions-ledger.md, which carries local outcome lines ahead of origin/main and lacks the Director's 15:09 rent-zdl5 line; left as-is (additive only).
