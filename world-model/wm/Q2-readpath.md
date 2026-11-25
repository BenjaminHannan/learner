Advice question (stand-alone). A recurrent "board" model: R board rows (D dims each) are updated per tick by a
sparse-MoE transformer trunk that cross-attends to context tokens; the update is rows += sigmoid(gate)*out_proj(h),
gate bias init -2 (~0.12), out_proj init std 0.02. We feed a 16x16x3 game frame as 16 context tokens
(Linear(48->D) patches + pos emb, unit RMS per token), init the board, run 2 ticks, then train a decoder that reads
ONLY the board rows to predict the next-frame change. Result: the board rows vary ~1% across different frames
(row std across batch 0.005-0.03 vs row magnitude 0.3-1.8), decoder loss equals the predict-zero baseline, gradient
reaching the patch reader is ~1e-11 at a 6.6M-active size. Same with 8 ticks and lr 3e-3.
Constraint: we may NOT edit the core model; we may only change the harness around it (how frames become context
tokens, how many ticks, which rows we pin/write via a pin_row API, losses, init of harness-owned layers).
Questions: (1) most likely cause; (2) the single best harness-only fix to make the board carry the frame; (3) a cheap
no-training or short-training gate to prove the board holds the frame before a scored run (give a threshold);
(4) if no harness fix can work, the minimal core change to propose. Be concrete and short.
