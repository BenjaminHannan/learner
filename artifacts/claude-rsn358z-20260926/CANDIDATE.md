# rsn-358z CANDIDATE, not drafted or sealed: every layer reads a learned mix of all earlier layers (sleep research thread, 2026-09-26 16:47 UTC)

**Source:** Ben, 16:46 UTC (cmsg_01FuvegZXjMmeUzStiEFVnEW6SCkmAo5r7XiZpgEPisbEM): "what if we had past layers feed into new layers?" The Thread manager relayed it.

**One change:** DenseFormer-style depth-weighted averaging. After block i, the stream becomes a learned weighted sum of the embedding and the outputs of blocks 1..i.
- This comes from the Thread manager's reference (Pagliardini et al. 2024), which is unverified here; this container cannot fetch papers.
- The extra weights are about L²/2 scalars, 528 at 32 layers, so the equal-weights rule holds.
- It is applied to the best shape from 358y, where direct access to early layers should matter most. The loop keeps the same mix every round.

**Second arm (a separate change, only after the first):** the mix also includes earlier rounds' states, so a round can look back at what it thought before, not only at the round just before it.

**Brain angle (a guess):** cortex has many "skip" connections that bypass intermediate areas, and pathways through the thalamus that relay one area's output to more distant areas.

**Order:**
1. 358t verdict.
2. The seed 5-8 replication, or the held 358i rerun.
3. The 358y depth sweep.
4. 358z within-round mix.
5. 358z cross-round mix.

It uses 358y's marks, with a G6-style "beats its base by 10" mark.

**Also logged (16:49 UTC, from the Thread manager and Ben): the MLP width ratio.**
- Blocks now widen 4x in the MLP (scripts/claude_rsn358a_run.py:58), about 12·d² weights per block.
- A 2x MLP (about 8·d²) leaves room for about 1.5x the layers at equal weights.
- It would be a single change on the best shape and ratio from 358y, as step 6 after 358z-b.
- Worth a test only if 358y shows depth helping: its loop curve still rising at the deepest point it could reach before heads get too narrow. Otherwise it is dropped.
