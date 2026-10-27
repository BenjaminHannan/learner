# Experiment 43B — shared-gradient sleep vs plain replay — pass marks (fixed before any full run, and before 43A results were read)

Date: 2026-09-21. Script: scripts/fable_sharedsleep43b.py. Seeds 4102, 4103, 4104.
Base: the 43A `randpos` model of the same seed if it passes G0 (lengths 4-8 >= 0.95);
use `randpos-loop` instead only if 43A says G1/G2 fail and G3 passes.
Awake log: 100 raw episodes of the new skill, 10 with a wrong random answer; 20 held out
for checkpoint choice; 3,000 updates; old-skill replay in every batch; identical episodes,
positions and replay in every arm.  Only the way four group gradients are combined differs.

Scored object = the checkpoint the fixed rule selects (lowest held-out loss, checked every 250 updates).
All comparisons are against `plain` on the SAME seed.  Every seed reported separately.

| Mark | Meaning | Condition | Needed |
|---|---|---|---|
| V0 | validity | base old-skill accuracy before sleep >= 0.95 | per seed |
| H1 | learns from fewer/noisier experiences | arm fresh >= plain fresh + 0.15 | 3/3 valid seeds |
| H2 | ignores noisy exceptions | arm noise_memorised <= plain - 0.30 AND arm fresh >= plain - 0.05 | 3/3 valid seeds |
| H3 | keeps old skills (acceptance gate) | selected old_skills >= before - 0.02 | per seed, per arm |
| H4 | new skill reaches longer inputs | long_9_10 >= 0.50 | 3/3 valid seeds, any arm incl. plain |

Decision rule fixed now:
- A gradient filter (sign / snr / subspace) or the rank-4 limit joins Sleep-vNext only if it passes H1 or H2 and passes H3 in every valid seed.
- If none does: Sleep-vNext = plain replay + held-out checkpoint choice + old-skill gate, and the next effort goes to architecture and to gathering more experience, not to gradient filtering.
- H4 is an architecture read-out (does 43A's change carry to a newly slept skill); it is not credited to any filter unless that filter beats plain by >= 0.15 on it in 3/3 seeds.
- Toy only. No claim about language or multiplication.
