Bug hunt before a scored run (advice only; be concrete, cite file:line).

Code: forecast2.py (the run), wm_fit.py (WorldModel, read = 2 run_ticks), board_swarm.py (BoardCell.imagine/_imagine_impl, read-only core).
Task: Crafter 16x16x3 frames. Train the shared trunk so that the EXACT linear readout of the imagined next board matches the REAL next frame (only real transitions as targets). The readout is a closed-form ridge fit on REAL train-world boards (standardized, lambda = n*0.2^2 = "robust to 20% per-coordinate jitter"), refit every 250 steps and once more on the final weights before scoring on held-out worlds. Imagination is context-blind: the only context token is the action (plus the cell's own action row). Training start board is the real board + 0.2*std noise. Loss = img + rec + 0.1*row/ROWSD^2 + 0.01*aux, Adam 1e-4, 100-step warmup, clip 1.

Probe evidence (120 steps): rec (readout of the REAL board vs real frame) goes 0.0008 -> 0.066 after ONE step at lr 1e-6, then 681 by step 19, then falls to ~10 by step 119; img starts at 2813 (noisy start) and falls to ~11. Readout val SSE 626 vs mean-baseline 8607.

Questions:
1. Any bug that makes the score invalid or optimistic (leak of held-out or next-frame info into imagination, readout fit on non-real boards, shuffle control broken, eval/train mode mismatch, refit using wrong weights)?
2. Why would one Adam step at lr 1e-6 move the real-board readout 80x? Point to the exact mechanism in the code (fixed-scale rms_level monkeypatch, MoE routing, norms...).
3. Smallest fix you'd make before the scored run. Keep the shared trunk; no hand rules; no readout-to-context bypasses.
