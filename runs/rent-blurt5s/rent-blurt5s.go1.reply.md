Starting your blurt5s GPU run — fetching branches and checking gates.
Credit and duplicate gates passed — searching for a GPU.
Found a candidate host — verifying credit and rental details.
Selected a host — creating the rental now.
Rental is running with CUDA — setting up code and model.
Environment ready — downloading the model.
Pre-checks passed — launching the main run.
Run is progressing through DEV sampling — monitoring.
Run finished in under 18 minutes — copying results back.
Results show a clear outcome — checking ledger format and costs before finalizing.
Files secured — computing final costs and verdict.
Costs tallied — destroying the rental.
Results and ledger written — staging files for push.
Verdict: PROVED WRONG (blurt-5s S1 fails; "correct supervision is enough" holds). Not a pass, not "no difference shown", not inconclusive.

Credit: 7.631491817599901 (first check 7.6363399005999; both above the $5.00 gate, so rented). Duplicate gate: clear (origin/main and origin/builder-outbox had no gpu-5s; no live rent-blurt5s).

Run (1 rental, no re-rents): contract 52639754, RTX 5090, offer 49024377, $0.5037/h, ~0.47 h (~28 min, vast duration 1686 s) = ~$0.24 of the $3.00 budget ($2.70 kill threshold never hit). Created and running within ~3 min; destroyed 20:05:03Z 2026-09-25, confirmed 0 rent-blurt5s live. Launched detached (setsid/nohup, PID 604), survived SSH closing. Code unedited; selftest printed "selftest ok"; pzcheck 60/60 identical (sha e2023094…); "[b5s] practice" printed ~2 min in (no TOO-SLOW). BASE = /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc, commit 87179e5c1f455ef22e6223592d2d61351b525bfc (matches expected). torch 2.8.0+cu128 CUDA True, transformers 5.17.0. No weights saved or pushed.

Integer counts (from gpu-5s/blurt5s_summary.json, 98 lines; log.txt 71 lines, both sha-verified before destroy): DEV missed 58, lucky 37 @1.0 vs 44 @1.5, temp chosen 1.5. n_train 400, n_test kept 184 of 240 (56 overlap drops, so D = ceil(184/10) = 19), 116 3-number. Base cov@1/cov@5/cov@10/cov@30 = 3/28/45/77, lucky 167. Practice own 20, wins 191, examples 211. Mean target len W 8.13 vs E 6.96; E equals own hit 9/191. W cov@30 = 112/108/110; E cov@30 = 123/113/117; C cov@30 = 14/12/11. CI W-E [-8.70, 0.54]; CI E-base [15.77, 28.96]. Wall 17.8 min.
- S1 FAIL: seed margins W-E = -11/-5/-7 (need >= +19 every seed); CI includes zero.
- Proved-wrong TRUE: E >= 77+19=96 every seed (+46/+36/+40); W-E upper 0.54 < +5.
- Not inconclusive (191 >= 20 wins; 20 >= 10 own). Sanity passes (W 112/108/110 > base 77 every seed).

Deviations (every one): (1) test set kept 184 puzzles, not 240, after 56 overlap drops — the registered procedure itself drops overlaps and defines D for this case (D=19 applied). (2) E_equal_to_own_hit = 9, not ~0 — the fixed solver rule keeps the own hit when no alternative solution remains; reported as-is, no patch. (3) Wall 17.8 min, faster than the 1-2.5 h estimate (5090 faster than the 5070 Ti reference) — no rule broken. No other deviations: temps, seeds, n-test, prompts, LoRA recipe all as registered; no TEST-ONLY panel.

PUSH (staged, force-added, artifacts/ is git-ignored): artifacts/claude-blurt5s-20260925/gpu-5s/blurt5s_summary.json, artifacts/claude-blurt5s-20260925/gpu-5s/log.txt, artifacts/claude-blurt5s-20260925/RESULTS-gpu-5s.md (full JSON + marks + verdict + GPU/wall/dollars/hash), artifacts/fable-predictions-ledger.md (one line appended).
