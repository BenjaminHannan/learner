# 24b — Talker decisions (Ben, 20 September 2026)

Recorded by Fable (coordinator). Ben was shown the D1–D9 decision sheet of
`24-talker-from-scratch-fable-design.md` and the 1B-scale answer, and replied:
**"Just choose your recommendations for each."** So every row is the recommended option:

| # | Decision |
|---|---|
| D1 | Thought = one 416-number vector with the typed layout (act 8 · subject 48 · relation path 48 · object 48 · flags 8 · gist 256). |
| D2 | Small transformer encoder + decoder, size M (≈ 33M total). GRU decoder = 20-minute side arm in S0. **Scale-up steps, only after S1/S2 work at 33M: 85–100M, then ≈ 200M** (Ben asked about 200M the same evening; coordinator estimate ≈ 50–110 GPU-hours on BensPC, fits in 16 GB; S0 benchmarks the 200M preset's real throughput so the hours can be quoted from a measurement before Ben decides). No 1B (cost ≈ $200+, data too small, faithfulness risk). |
| D3 | Full reading list (SimpleStories, TinyStories-V2, TinyDialogues, simple SODA slice, generated dialogues, Qwen "knows-nothing" chat). Download ≈ 5–6 GB approved; builder confirms exact sizes first and stops if the total exceeds 7 GB. |
| D4 | Typed thought fields are the notebook row / canonical question; frozen 79,316-parameter operator unchanged; names only by copy. |
| D5 | 4-layer thinker predicts the reply thought, trained through the frozen decoder. |
| D6 | Yes — one ordinary ≈ 29M chat LM on the same data, as the yardstick only. |
| D7 | Free on BensPC (≈ 9–10 GPU-hours over 2–3 nights). **No rental.** Any later rental is a new question to Ben (quote first; he presses Run; cap $8). |
| D8 | Exception granted: up to 3 unattended runs of ≤ 6 h each, resumable, 10-minute checkpoints, kill test. The 30-minute rule stays for everything else. |
| D9 | Claims box of §6, including the "English learned second-hand from model-written text" footnote. |

Still needing Ben later: the Qwen generation nights on BensPC (blocks training meanwhile), his 100 sealed
L3 sentences (≈ 20 minutes of typing), and any rental.
