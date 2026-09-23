---
name: exp43-length-gate-and-shared-sleep
description: "2026-09-21 exp 43A/43C/43B all FAIL — length wall is architectural (old skills 0% at length 12); gradient filters and rank-4 do not beat plain replay"
metadata:
  type: project
---

Ben's Shared-Subspace Sleep proposal was reviewed and tested (design/v3/30-modes/41-shared-subspace-sleep-review-fable.md).

- Probe: registered CardFold bases lose even OLD skills past trained lengths (len 10 ≈ 0.18, len 12 = 0.00, even INC3 copy). Length wall = architecture, not sleep.
- 43A randomised positions: len 10 → 0.40–0.52, len 12 ≤ 0.03; looped shared block no different. All marks FAIL.
- 43C segment-relative positions (input digit i and answer digit i share a position): len 12 = 0.00, worse at len 10; model ignored the shared numbers. Sealed next rung = relative-position attention.
- 43D relative-position attention (no absolute positions; learned bias on clipped start/end index differences ±4): all marks FAIL but first non-zero length-12 results — REV 0.93–0.95 and INC3 0.82–1.00 in most seeds with start+end indices; REV = 0.00 without the end index; SWAP/FOLD 0 (no parity/halving signal); at length 16 only the last two answer places break; seed-fragile. Sealed rule: stop position work, wait for GPT review.
- 43B sign / snr / subspace(SVD, normalised) / rank-4 vs plain, 100 episodes with 10 noisy, 20 held out: all marks FAIL; rank-4 most consistent. Held-out LOSS picked update 250 in all 15 runs (bad selector); H2 mark had a floor problem.

**Why:** filters only remove information; sample efficiency must come from the prior. **How to apply:** Sleep-vNext = plain replay + held-out gate until something measured beats it; keep [[exp42-automatic-sleep-result]] as baseline; never test architecture and sleep changes in one experiment. Ben was given a self-contained GPT prompt covering D1 length, D2 sample efficiency, D3 noise, D4 selection; adjudicate GPT's reply against these numbers. GPT bridge (claude-web) was down on 2026-09-21 (chatgpt.com would not load, 4 tries).
