# dl-6: do lighter nights (1 epoch instead of 3) stop the slow forgetting of copy-practice nights?
(Fix-sleep thread. Registered when this file is committed, before the run.)

## Why
- dl-2 (registered PASS) lifted lucky guesses 64 -> 237 and 249 but lost 26 of the base's 200 right general-panel
  items by night 7. Its placebo, trained on WRONG answers, lost about as many (17 and 19): losses seem to track how much
  the model is trained, not what it is trained on (suggested, not shown).
- dl-3 (greedy replay) is a registered FAIL. dl-4 (KL anchor) is being rerun (first rental destroyed before its anchor
  arm ran). dl-6 runs alongside it as the plainest lever, not as a tuned setting: train less per night.

Code: scripts/claude_dl6_light.py (the docstring is the method), reusing claude_dl1_nights and dl-3's scorer unchanged.
Plain MiniCPM5-1B, thinking off, no download.

## ONE change from dl-2's S arm: 1 epoch per night instead of 3
Same examples each night, lr 2e-4, batch 8, one growing LoRA. Arms: S = dl-2's night (3 epochs); L = 1 epoch.
Seeds 10 and 11, 7 nights each. New TEST seed 3590: 100 fresh puzzles x 20 guesses. HARM: the same 300 items;
"lost" = right at base and wrong now.

## Marks: dl-3's F1-F5, unchanged, with L in place of A
- F1 forgetting cut: L's night-7 lost <= 0.5 x S's (sums over seeds), and each L seed is below each S seed.
- F2 low forgetting every night: at most 1 of L's 14 nights has lost > 10.
- F3 still learns: L's night-7 lucky >= 2 x L0 on each seed, and L's gain over L0 >= 0.8 x S's gain.
- F4: at most 1 of L's 14 nights has TEST lucky more than 15% below the night before.
- F5: L's night-7 puzzles reached >= base, on each seed.
Verdict: PASS = F1-F5. INCONCLUSIVE if L0 < 10 or S's night-7 lost sum < 20. Proved wrong: L's night-7 lost >= S's on
both seeds.
Reported, not marked: lost vs the night before, KL per night, gained, greedy solves, per-item panel for a kind breakdown.

## Limits stated before the run
One kind of work. Short general answers with a 16-token reply cut. Two seeds (dl-3 saw 39 vs 24 lost with one rule).
F3 is the real trade: 1 epoch may learn too little, and that is a FAIL, not a retune.
