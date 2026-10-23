# V1 SPEC — FROZEN 2026-10-21

Ben's directive (Oct 21): trade trust for speed. Working model first, perfect later. Approved by Ben Oct 21 ("Sounds good") with the Opus consult changes (V1-Assembly-Opus-Consult-2026-10-21.md).

## Goal
The first full, working, end-to-end model + a full checkpoint. Nothing like it exists yet. Everything not listed here is post-v1.

## The two arms (same data, same seed, same steps)
- FULL: main brain (d128) + creative module (d256, one linear projection each way) + sleep + G1 guard (KL weight 30) + Muon + S2 unwashed-copy fix + defer (only if the bit-equality harness passes on the v1 config on CPU; fail = off, no debugging).
- FLOOR: same, minus Muon, minus S2, minus defer; AdamW instead of Muon.
- Width call: the brain stays d128 (keeps the fleet numbers and the G1 evidence valid); the creative module stays d256 where its evidence lives.

## Known untried combination (verified Oct 21)
C2b's sleep arm ran with NO KL guard anywhere (checked: no KL weight/term/anchor in any commit of the creative code or results). Sleep + G1@30 has never been tried. Gate S must show the KL term live and nonzero; abort rule A3 covers it if it freezes learning.

## Definition of "working" (written before any run)
- W1: sealed main-task accuracy at least 10 points above the best no-learning baseline.
- W2: creative at least 20% first-try on held-out puzzle kinds (about half of C2b's 39.29%).
- Open-seal rule: a dev split exists alongside the sealed read. The seal opens only if the chosen arm meets W1/W2 on dev first. Never open on hope.

## Gate S — the one pre-training gate (smoke test, no judgment calls)
1. Pinned-environment preflight on the actual box.
2. Overfit-one-batch on Ben's PC.
3. Component-ran log: S2 copy reaches the decoder; Muon group non-empty; G1 KL term nonzero; sleep phase starts.
4. About 2% of training steps with the loss falling.
5. Save / kill / resume check passes.
Gate S fails = fix the wiring and re-run Gate S. It is not a park.

## Muon scope
2D hidden matrices only. Embeddings, head, norms, biases stay on AdamW. The grouping is printed and checked once in Gate S.

## Infrastructure rules (the parks' lessons, as spec, not gates)
- Memory guard read from the detected card's memory, never a constant.
- Pinned box image.
- Code ships as a tarball + commit-hash file. No box needs git.
- Checkpoint + resume everywhere: a dead box is a restart, never a park.

## Abort rules (written now, applied mechanically)
- A1 Instability (loss NaN/diverging): stop, judge the last checkpoint.
- A2 Not learning by 10% of steps: stop, judge the last checkpoint.
- A3 KL term frozen or dominating: stop, judge the last checkpoint.
- A4 Spend cap reached: evaluate the last checkpoint as v1.
- A5 Box death: resume from checkpoint. Two deaths: move venue (PC or Modal).

## Budget (week 1)
- FULL at most $20, FLOOR at most $20, at least $10 of the Vast week kept in reserve. Expected actual: under $15 total.
- Modal about $5 for Gate S + the sealed read. Ben's PC at $0 wherever it fits.

## Review
One round, blocking-only. Blocking means: wrong numbers, a sealed-data leak, or a component that crashes or is silently off. Everything else goes to KNOWN_ISSUES and does not stop the run.

## Dropped for v1 (no regret)
DM1/DM3 marks; E0 as a gate (it becomes a post-run diagnostic); Muon Stage 1 as its own stage; multi-seed v1; every parked line's fixes; any FLOP-calibration pass; S5 (village count kills it for now: 70.6% of village questions name no person).

## Post-v1 improvement queue (in order)
1. Defer guard holes, then defer on by default.
2. Clean Muon A/B on the v1 config.
3. G1 tuning via E0 / DM marks.
4. Width (Bid C).
5. S5 / relation choice.
6. Swarm.
7. Shinka redesign question (Ben's call, still open).
