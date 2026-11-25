Advice on pass marks only (stand-alone, under 300 words). Toy recurrent "board" world model (2.5M active) on a
Minecraft-like 2D game, 16x16x3 pooled frames, 17 discrete actions, random-ish exploration policy, 20k train
transitions / 160 worlds, 5k held-out / 16 worlds. Already shown: after reading frames t-1 and t, a CLOSED-FORM ridge
readout (fit on real boards from train worlds) redraws frame t at 0.062 of mean-frame error, moving pixels 0.059 of
copy-last-frame error, with blank/shuffle controls passing.
Planned test: train ONLY the imagination step (same trunk + action embedding) with a k=1 loss: imagined next board vs
the detached real board after reading frame t+1 (reconstruction loss kept so the real board stays sharp). Score by
applying the SAME frozen ridge readout to imagined boards at k=1,3,5 (rollouts fed back, never trained at k>1).
Baseline B_k = better of copy-frame-t and a fixed shrink-to-mean blend fit on train (blend beats copy by 4/11/17%
at k=1/3/5; 82-88% of steps change the frame).
Proposed marks (held-out): E_k/B_k <= 0.80 / 0.90 / 0.95 at k=1/3/5; action-shuffle (within world) error on moved
windows >= 1.25x at k=1 and >= 1.10x at k=5 in >= 12/16 worlds; predicted-change std per first-action within
0.25-2x of real. PASS = all; PARTIAL = k=1 + k=1 shuffle + std pass.
Questions: are these marks fair and not too easy or too hard? Is there a cheat the marks miss (e.g. imagined board
just copies, readout exploits something)? One extra control you'd add? Give your PASS/PARTIAL/FAIL odds.
