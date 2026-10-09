# PR #56 body (copied from GitHub, open, 10-09): Token test TK/TKN and B3 group 1
Title: Token test TK/TKN and B3 group 1 (any-round calls, Gemma + outside calculator, 2,000 letters, learned stop); no runs yet

Before: the calculator-outside model (T1SDR) and the learned stop (H1R) lived on another code line, could not run with the Gemma reader (tool.py:120 refused it), could call the calculator only after rounds 2 to 8, and read at most 280 letters. The thinker always read one spot per letter.

After: one model, `b3`, on G1's code line. It has two real switches, both off by default (off = H1R bit for bit): `eg_embed` (Gemma reads the question; calculator replies are read by the letter window only) and `any_round` (with `gap_p`: calls can follow any thinking round, filling a 16-entry tape). The other two parts of group 1 are not switches: 2,000-letter inputs come from the caps file `caps_b3.json` (G1's `caps_g.json` keeps 280), and the learned stop is H1R's own and always on. It builds at 3M, 10M, 30M and 100M from one config (100M = 21 blocks at width 512). Separately, the token switch `tok_think` lets the thinker read one spot per Gemma token, for the TK/TKN test.

A failed 3M test can be bisected by turning `eg_embed` and `any_round` off one at a time, or by running at G1's caps; the stop can only be removed by running H1R's parent T1SDR.

How:
- Token test (spec design/tokens-experiment-2026-10-09.md, Addenda A and B): `tok_think` in ledger.py (off = G1's code, 50 CPU steps torch.equal); g8a/analyze_tk.py scores marks M1-M5 and the kill-first --stop-check.
- B3 group 1 (spec architecture/B3-GROUP1-BUILD-2026-10-09.md): ports tool.py, tool_h1.py and their tests from 17a356e62; adds models/b3.py (any-round calls, gap schedule on 25% of training rows with no op label at gap rounds); the tool reads Gemma; registers follow N_REG; arm B3 in g8a/configs.py and job.py; length-bucket readout.
- Fix: caps.apply had set every listed module's CAP to plain_target, which turned H1's fixed 32-round cap into 109 under both caps files. CAP is no longer patched; a test checks it stays 32.
- Checks (CPU, stub Gemma): H1R and b3 with no switches equal 17a356e62 over 50 steps, 77 tensors; test_b3, test_b3_run (50 steps at 2,000 letters), test_tok_think, test_analyze_tk print ALL OK; test_g8a passes 17 of 17.
- Sizes at caps_b3: 3M 4,039,957 trained; 10M 9,832,977; 30M 29,789,693; 100M 102,116,618; plus 271,002,624 frozen Gemma.

Runs: none yet. The token test waits for a PC gap; B3 waits for G1's GO. Both need Ben's go in the Mac session.
