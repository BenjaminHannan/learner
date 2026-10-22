# Follow-up: your three arms ran, plus two of ours. Results, and a harder question

This is the second turn. Your earlier answer is above. Everything is still the 3.3M card model on the sheet subject (card experiments only, not the village model). Seed 201 is the hard seed. "Near" is the gain on the new subject. "Drop" is the pooled DEV in_dist drop vs the parent, in points. A family "fires" if its drop is > 5 points and its paired bootstrap interval is below 0. Pass means near >= +30, drop <= 1.5 and no family fired. All marks were fixed before each run.

## Results

| Arm | What changed | Nights | Near | Drop | Fired | Verdict |
|---|---|---|---|---|---|---|
| N99 (reference) | K-FAC lock, per-example G, energy 0.99 | 12 | +60.7 | 1.84 | none | fail (drop) |
| NK | N99 + 10 x KL(parent ‖ model) on the 32 replay rows (replaces the replay cross-entropy) | 12 | **+68.1** | **0.74** | fewshot_number_rule 47.5 -> 32.5 | fail by one family |
| F100 screen | N99 + your state anchor, lambda 100 | 1 | +3.8 | 0.00 | none | proved wrong (learns too little) |
| F25 screen | N99 + anchor, lambda 25 | 1 | +5.7 | 0.37 | none | fail |
| F0-25 screen | anchor 25 alone, no lock | 1 | +18.3 | 1.25 | digits_parity, kin_chain | fail |
| F0-100 screen | anchor 100 alone | 1 | +7.9 | 0.59 | kin_chain | fail |
| **F0-100 full** | anchor 100 alone | 12 (night 10 undone) | +50.5 | 2.28 | digits_parity 95->80, cipher_map 100->90, kin_chain 87.5->77.5 | **proved wrong** |
| G3 screen (seed 200) | N99 with padded positions kept out of the A factor | 1 | +13.3 | 0.51 (N99: 0.59) | none | pass, effect tiny |
| K full | 10 x KL alone, no lock | 2 (both undone) | 0 | 0 | none | proved wrong |
| K100 screen | 100 x KL alone, no lock | 1 (undone) | 0 | 0 | none | proved wrong |

Per-night drops:
- **NK:** 0.37, 0.44, 0.44, 0.44, 0.29, 0.29, 0.74, 0.81, 1.03, 0.59, 0.66, 0.74. Night 1 is 0.37, against N99's 1.47, so the KL removed the night-1 spike. fewshot_number_rule fires on night 4 and on every night from night 7.
- **F0-100 full:** 1.99 (night 3), 1.76 (5), 1.91 (7), 2.28 (12). The harm arrived early and stayed. It did not wash out.

Agreement is the share of 512 held-out old prompts the model answers exactly as the parent did, greedy, measured after each night. A night below 97 is undone in full. Night-1 agreement by arm:
- every projected arm: 97.3 to 99.8;
- anchor alone: 98.4 to 99.2;
- replay half left unprojected with its own Adam (an older arm, cross-entropy replay, seed 200): 91.6;
- KL alone at weight 10: 90.4;
- KL alone at weight 100: 88.3.

Replay KL per row on night 1 was 0.024 for NK, 0.151 for K and 0.176 for K100. At the end of the night it was about 0.1 at both weights. The new half's loss starts each night near 25 and falls to about 1. The optimizer is AdamW at lr 3e-4, and replay rows are fresh old questions on every batch.

Join-transfer test (Far transfer's setup: a different card task, every weight trains at lr 1e-4 for 4,000 updates on 12,000 rows; HO = accuracy on a never-practised layout). Our marks were pass HO >= 25 and proved wrong HO <= 10.

| Run | HO | DEV drop |
|---|---|---|
| Unguarded | 35.0 | 53.2 |
| N99 lock (factors from the parent's diary, re-measured every 500 updates; no replay) | 9.3 | 7.8 |

So the lock proved wrong: it blocks transfer.

## How your predictions did
- You expected NK to add little. Instead it more than halved the drop and learned the most.
- You expected F to fix night 1. With the lock, the anchor learns almost nothing.
- You expected F0 to be the transfer candidate. Its full run proved wrong.

## What is running now (seed 201, full runs)
- F25 (N99 + anchor 25).
- NK30 (NK with KL weight 30, aimed at fewshot_number_rule).

## Questions
1. Why does KL-to-parent replay hold old answers only on top of the projection? And why does 10x the weight make one night drift more? Our guess is suggested, not tested: AdamW scales every weight's step to about lr whatever the loss size, so a big replay gradient taken on fresh rows moves every weight it touches by a full step. Give other explanations, and one cheap test (a single one-night screen) that tells them apart, with its pass mark and the result that would prove each explanation wrong.
2. The guard that ships must do two things. It must keep old skills during nights at home, and it must not block learning that has to reuse old directions (the join test). The lock does the first and fails the second. Every no-lock guard we tried fails the first. Propose the single next arm most likely to do both, then at most two backups, ranked. For each, give:
   - what it changes (one change against N99 or NK);
   - why;
   - the pass marks for a night-1 screen and for a full run;
   - the result that would prove it wrong;
   - its cost against a night (a screen is about 1 h on 2 CPU threads, a full run 8-10 h).
   Same constraints as before: free CPU only, no new teacher data, no hand-written per-family or per-task rules, and the model must run it alone after it ships.
3. fewshot_number_rule is the weakest old family (the parent gets 47.5% of 40 DEV prompts), and it slips in most arms on both seeds. Is our fires rule fair to a family near 50%? Answer only this: what would you do? We will not change the marks of runs already started.

Please label every claim shown (our numbers above show it), suggested (reasoning) or untested. End with a plain-language summary for Ben, a high-school senior, in under 120 words.
