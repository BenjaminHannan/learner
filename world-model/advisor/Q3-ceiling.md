Advice question (stand-alone, short answer please). Recurrent "board" model: 64 rows x 256 dims (24 slow, 40 fast),
updated per tick by a sparse-MoE transformer trunk (2 blocks, 2.5M active params) that cross-attends to context
tokens; row update is gated (gate bias init sigmoid(-2)~0.12, out_proj std 0.02). We CANNOT edit the trunk; we own
the harness: frame reader (16x16x3 game frame -> 16 context tokens via Linear(48->256)+pos emb, unit RMS), ticks
per read, optional pinning of rows (pinned rows are frozen during ticks; we can write values into them), decoder,
losses, optimizer.
Observed: a ridge probe from the untrained board recovers the frame (R^2 0.68 unpinned; 0.98 with patches pinned
into 16 fast rows) but the signal is ~1% of row magnitude. A trained MLP decoder from rows (BatchNorm-standardized
input, zero-init last layer, Adam 3e-4, 1500 steps x batch 64, 20k frames) only reaches ~5% below a copy baseline
when asked to predict the frame change from a board that read frames t then t+1.
Goal now (separate from any forecasting): make the board hold the CURRENT frame sharply after reading it, without
pinning the answer into rows that the decoder reads (otherwise it's trivial). Questions: (1) the best harness-only
recipe (reader, ticks, which rows the decoder may read, loss, lr); (2) fair pass marks on held-out worlds (e.g.
normalized MSE vs mean-frame baseline, and on moving pixels only), with the trivial-cheat controls we need;
(3) what result would prove the trunk itself is the bottleneck. Keep it under 400 words.
